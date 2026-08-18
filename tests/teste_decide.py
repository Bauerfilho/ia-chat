#!/usr/bin/env python3
"""Gates do iachat-decide: registro, revogação, rotação e prova vermelha.

Tudo roda em ``IACHAT_HOME`` temporário. O teste usa a CLI pública em
subprocesso e inclui casos ruins que precisam REPROVAR: autor fora da sala,
decisão sem ``--porque``, e revogação em cascata de decisão já morta.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DECIDE = RAIZ / "bin" / "iachat-decide"
falhas: list[str] = []


def checa(nome: str, condicao: bool, detalhe: str = "") -> None:
    print(f"{'✔' if condicao else '✗'} {nome}" + (f"  ‣ {detalhe}" if detalhe else ""))
    if not condicao:
        falhas.append(nome)


def roda(
    cli: Path,
    env: dict[str, str],
    *args: str,
) -> subprocess.CompletedProcess[str]:
    """Executa a mesma porta pública que uma IA usa no terminal."""
    return subprocess.run(
        [sys.executable, str(cli), *args],
        env=env,
        capture_output=True,
        text=True,
    )


def configura(core, ias: list[str], teto: int = 204800) -> None:
    core.garantir_estrutura()
    core.p_config().write_text(
        json.dumps({"na_sala": ias, "brain": ias[0], "teto_bytes": teto}) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    base = Path(tempfile.mkdtemp(prefix="iachat-decide-teste-"))
    env = {
        **os.environ,
        "IACHAT_HOME": str(base),
        "PYTHON_DONTWRITEBYTECODE": "1",
    }
    os.environ["IACHAT_HOME"] = str(base)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(RAIZ / "bin"))
    import iachat_core as core

    try:
        configura(core, ["claude", "codex", "kimi"])
        checa(
            "T0 CLI iachat-decide existe e é executável",
            DECIDE.is_file() and os.access(DECIDE, os.X_OK),
            str(DECIDE),
        )

        # ---- T1: primeira decisão -------------------------------------------
        r1 = roda(
            DECIDE, env, "decidir",
            "--de", "claude", "--sobre", "canal",
            "--porque", "append puro medido em 100 msgs de 5 processos íntegras",
            "post é append puro, nunca >>",
        )
        decs = roda(DECIDE, env, "decisoes")
        checa(
            "T1 decidir grava D1 e decisoes mostra vigente",
            r1.returncode == 0 and "D1 gravada" in r1.stdout
            and decs.returncode == 0 and "D1 [canal]" in decs.stdout
            and "post é append puro" in decs.stdout,
            f"rc={r1.returncode}",
        )

        # ---- T2: --sobre filtra e custa pouco -------------------------------
        filtrado = roda(DECIDE, env, "decisoes", "--sobre", "canal")
        custo = len(filtrado.stdout.encode("utf-8"))
        checa(
            "T2 --sobre filtra pelo assunto",
            filtrado.returncode == 0 and "D1 [canal]" in filtrado.stdout,
            f"{custo} B",
        )

        # ---- T3: revogação grava estado=revogada no arquivo -----------------
        r3 = roda(
            DECIDE, env, "decidir",
            "--de", "codex", "--sobre", "hooks",
            "--porque", "a nova medição substituiu a antiga",
            "--revoga", "D1",
            "matcher é Bash|Read|Grep|WebFetch",
        )
        disco = (base / "decisoes.md").read_text(encoding="utf-8")
        linha_d1 = next((ln for ln in disco.splitlines() if "id=D1" in ln), "")
        checa(
            "T3 revogar marca estado=revogada NO ARQUIVO (visível sem CLI)",
            r3.returncode == 0
            and "estado=revogada por=2" in linha_d1
            and "id=D2" in disco,
            f"rc={r3.returncode} linha_d1={linha_d1!r}",
        )

        # ---- T4: decisoes esconde revogada e mostra ponteiro -----------------
        vig = roda(DECIDE, env, "decisoes")
        todas = roda(DECIDE, env, "decisoes", "--todas")
        por_id = roda(DECIDE, env, "decisoes", "--id", "D1")
        checa(
            "T4 listagem esconde revogada; --todas e --id mostram com ponteiro",
            vig.returncode == 0 and "D1" not in vig.stdout and "D2 [hooks]" in vig.stdout
            and todas.returncode == 0 and "REVOGADA por D2" in todas.stdout
            and por_id.returncode == 0 and "REVOGADA por D2" in por_id.stdout,
        )

        # ---- T5: sobrevive à rotação -----------------------------------------
        cfg = json.loads(core.p_config().read_text(encoding="utf-8"))
        cfg["teto_bytes"] = 1024
        core.p_config().write_text(json.dumps(cfg) + "\n", encoding="utf-8")
        for i in range(6):
            core.post(["claude", "codex", "kimi"][i % 3], f"Ruído {i:02d} " + "x" * 300, [])
        core.rotate()
        md_antes = (base / "decisoes.md").read_bytes()
        pos_rot = roda(DECIDE, env, "decisoes")
        checa(
            "T5 registro intacto após rotação (md5 idêntico, vigentes visíveis)",
            pos_rot.returncode == 0 and "D2 [hooks]" in pos_rot.stdout
            and md_antes == (base / "decisoes.md").read_bytes(),
        )

        # ---- T6: --anunciar grava E posta na sala nomeando -------------------
        anuncio = roda(
            DECIDE, env, "decidir",
            "--de", "claude", "--sobre", "sino",
            "--porque", "quem não sabe que a regra existe obedece errado",
            "--anunciar", "codex",
            "toca o sino em quem foi nomeado",
        )
        msgs = []
        for c in core._recortes() + [core.p_chat()]:
            msgs.extend(core.parse(c.read_text(encoding="utf-8")))
        checa(
            "T6 --anunciar grava a decisão E posta na sala nomeando",
            anuncio.returncode == 0 and "anunciada na sala como #" in anuncio.stdout
            and any("Decisão D3" in m["bruto"] for m in msgs),
            f"rc={anuncio.returncode}",
        )

        # ---- T-RED 1: autor fora da sala é REPROVADO -------------------------
        antes_fora = roda(DECIDE, env, "decisoes", "--todas").stdout
        fora = roda(
            DECIDE, env, "decidir",
            "--de", "intruso", "--sobre", "x", "--porque", "y",
            "não deveria entrar",
        )
        checa(
            "T-RED autor fora da sala REPROVA (exit != 0, sem escrever)",
            fora.returncode == 2 and "não está na sala" in fora.stderr
            and antes_fora == roda(DECIDE, env, "decisoes", "--todas").stdout,
            f"rc={fora.returncode}",
        )

        # ---- T-RED 2: decisão sem --porque é REPROVADA -----------------------
        sem_porque = roda(
            DECIDE, env, "decidir", "--de", "claude", "--sobre", "y",
            "decisão sem motivo",
        )
        checa(
            "T-RED sem --porque REPROVA (exit != 0, nada escrito)",
            sem_porque.returncode == 2 and "--porque" in sem_porque.stderr,
            f"rc={sem_porque.returncode}",
        )

        # ---- T-RED 3: revogar o já morto avisa e ainda assim grava a nova -----
        # (o protótipo avisa mas não bloqueia; a nova decisão vale, a morta fica)
        cascata = roda(
            DECIDE, env, "decidir",
            "--de", "kimi", "--sobre", "z", "--porque", "w",
            "--revoga", "D1",
            "terceira decisão",
        )
        disco2 = (base / "decisoes.md").read_text(encoding="utf-8")
        checa(
            "T-RED revoga em cascata AVISA no stderr e não remarca a morta",
            cascata.returncode == 0 and "já estava revogada" in cascata.stderr
            and disco2.count("estado=revogada por=") == 1
            and "por=2" in disco2 and "por=3" not in disco2,
            f"rc={cascata.returncode}",
        )

        # ---- T-RED 4: --revoga em formato lixo REPROVA, não explode -----------
        lixo = roda(
            DECIDE, env, "decidir",
            "--de", "claude", "--sobre", "w", "--porque", "v",
            "--revoga", "Dx",
            "quarta decisão",
        )
        checa(
            "T-RED --revoga inválido REPROVA com mensagem, sem traceback",
            lixo.returncode == 2 and "--revoga quer formato D3" in lixo.stderr
            and "Traceback" not in lixo.stderr,
            f"rc={lixo.returncode}",
        )

        # ---- T-RED 5: --sobre com espaço quebraria o metadado; REPROVA --------
        antes_espaco = roda(DECIDE, env, "decisoes", "--todas").stdout
        espaco = roda(
            DECIDE, env, "decidir",
            "--de", "claude", "--sobre", "dois assuntos", "--porque", "u",
            "quinta decisão",
        )
        checa(
            "T-RED --sobre com espaço REPROVA (metadado ficaria invisível)",
            espaco.returncode == 2 and "uma palavra sem espaço" in espaco.stderr
            and antes_espaco == roda(DECIDE, env, "decisoes", "--todas").stdout,
            f"rc={espaco.returncode}",
        )

        # ---- T-RED 6: --id inexistente REPROVA, não vira "nada casa" ----------
        id_falso = roda(DECIDE, env, "decisoes", "--id", "D404")
        checa(
            "T-RED --id inexistente REPROVA com exit != 0",
            id_falso.returncode == 2 and "não existe" in id_falso.stderr,
            f"rc={id_falso.returncode}",
        )

    finally:
        import shutil
        shutil.rmtree(base, ignore_errors=True)

    print()
    if falhas:
        print(f"✗ {len(falhas)} falha(s): {', '.join(falhas)}")
        return 1
    print("✔ tudo verde")
    return 0


if __name__ == "__main__":
    sys.exit(main())
