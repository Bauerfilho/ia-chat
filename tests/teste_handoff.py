#!/usr/bin/env python3
"""Gates do ia-handoff: critério obrigatório, estado visível, prova para fechar.

Roda a CLI pública `bin/iachat-handoff` em subprocesso com ``IACHAT_HOME``
temporário; nunca toca a sala real. Inclui chat pré-existente (fixture sala-v1)
e casos que TÊM que reprovar: abrir sem critério, fechar sem prova.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


RAIZ = Path(__file__).resolve().parent.parent
CLI = RAIZ / "bin" / "iachat-handoff"
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "sala-v1"
falhas: list[str] = []


def checa(nome: str, condicao: bool, detalhe: str = "") -> None:
    print(f"{'✔' if condicao else '✗'} {nome}" + (f"  → {detalhe}" if detalhe else ""))
    if not condicao:
        falhas.append(nome)


def roda(env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
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


def corpo_ok(titulo: str, criterio: str) -> str:
    return (
        f"# {titulo}\n\n"
        "## Estado\n"
        "Medido nesta sala de teste: handoff/ ainda vazio no início do caso.\n\n"
        "## Não faça\n"
        "- Não reescreva o iachat.md à mão.\n\n"
        "## Pronto quando\n"
        f"{criterio}\n"
    )


def escreve_corpo(base: Path, nome: str, texto: str) -> Path:
    p = base / nome
    p.write_text(texto, encoding="utf-8")
    return p


def n_handoffs(base: Path) -> int:
    pasta = base / "handoff"
    if not pasta.is_dir():
        return 0
    return len(list(pasta.glob("HO-*.md")))


def meta_do(base: Path, hid: str) -> dict:
    txt = (base / "handoff" / f"{hid}.md").read_text(encoding="utf-8")
    cabeca, _, _ = txt[4:].partition("\n---\n")
    out = {}
    for linha in cabeca.splitlines():
        k, _, v = linha.partition(":")
        if k.strip():
            out[k.strip()] = v.strip()
    return out


def hid_de(stdout: str) -> str:
    for tok in stdout.split():
        if tok.startswith("HO-"):
            return tok
    return ""


def main() -> int:
    checa(
        "H0 CLI é iachat-handoff (não iahandoff) e é executável",
        CLI.is_file()
        and CLI.name == "iachat-handoff"
        and os.access(CLI, os.X_OK),
        str(CLI),
    )
    checa(
        "H0 não existe bin/iahandoff no repo (nome que o install.sh nunca instala)",
        not (RAIZ / "bin" / "iahandoff").exists(),
    )

    base = Path(tempfile.mkdtemp(prefix="iachat-handoff-teste-"))
    env = {
        **os.environ,
        "IACHAT_HOME": str(base),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    os.environ["IACHAT_HOME"] = str(base)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(RAIZ / "bin"))
    import iachat_core as core

    try:
        configura(core, ["claude", "codex", "kimi"])

        # ---- T-RED 1: abertura sem critério é bloqueada (o caso que reprova) --
        sem_criterio = escreve_corpo(
            base,
            "sem-criterio.md",
            "# Meio\n\n## Estado\nAlgo.\n\n## Não faça\n- Não faça X.\n",
        )
        msgs_antes = len(core.parse(core.p_chat().read_text(encoding="utf-8")))
        r_sem = roda(
            env, "abrir",
            "--de", "claude", "--para", "codex",
            "--titulo", "meio",
            "--corpo", str(sem_criterio),
        )
        msgs_depois = len(core.parse(core.p_chat().read_text(encoding="utf-8")))
        checa(
            "T-RED abrir sem ## Pronto quando REPROVA (0 msgs, 0 arquivos)",
            r_sem.returncode == 2
            and "critério de pronto" in r_sem.stderr
            and msgs_antes == msgs_depois
            and n_handoffs(base) == 0,
            f"rc={r_sem.returncode} msgs {msgs_antes}→{msgs_depois} arquivos={n_handoffs(base)}",
        )

        heading_vazio = escreve_corpo(
            base,
            "heading-vazio.md",
            "# Meio\n\n## Estado\nAlgo.\n\n## Não faça\n- Não faça X.\n\n## Pronto quando\n\n",
        )
        r_vazio = roda(
            env, "abrir",
            "--de", "claude", "--para", "codex",
            "--titulo", "heading vazio",
            "--corpo", str(heading_vazio),
        )
        checa(
            "T-RED ## Pronto quando vazio REPROVA (heading não basta)",
            r_vazio.returncode == 2
            and "critério de pronto" in r_vazio.stderr
            and n_handoffs(base) == 0,
            f"rc={r_vazio.returncode} stderr={r_vazio.stderr.splitlines()[0] if r_vazio.stderr else ''}",
        )

        # ---- H1: abertura válida ---------------------------------------------
        ok = escreve_corpo(
            base,
            "ok.md",
            corpo_ok(
                "Fechar o omni na casca do Codex",
                "sqlite3 omni.db conta agent_id=codex > 0 depois de uma tool real.",
            ),
        )
        r_abrir = roda(
            env, "abrir",
            "--de", "claude", "--para", "codex",
            "--titulo", "Fechar o omni na casca do Codex",
            "--corpo", str(ok),
        )
        hid1 = hid_de(r_abrir.stdout)
        msgs = core.parse(core.p_chat().read_text(encoding="utf-8"))
        checa(
            "H1 abrir válido grava arquivo + ponteiro e estado=aberto",
            r_abrir.returncode == 0
            and hid1.startswith("HO-")
            and (base / "handoff" / f"{hid1}.md").is_file()
            and meta_do(base, hid1).get("estado") == "aberto"
            and any("HANDOFF" in m["bruto"] for m in msgs),
            f"rc={r_abrir.returncode} hid={hid1} msgs={len(msgs)}",
        )

        # ---- H2: aceite ------------------------------------------------------
        r_alheio = roda(env, "aceitar", hid1, "--quem", "kimi")
        checa(
            "H2 terceiro não aceita (é do dono nominado)",
            r_alheio.returncode == 2 and "não pode aceitar" in r_alheio.stderr,
            f"rc={r_alheio.returncode}",
        )
        r_aceita = roda(env, "aceitar", hid1, "--quem", "codex")
        checa(
            "H2 dono aceita e estado vira aceito",
            r_aceita.returncode == 0
            and meta_do(base, hid1).get("estado") == "aceito"
            and "aceito" in r_aceita.stdout,
            f"rc={r_aceita.returncode} estado={meta_do(base, hid1).get('estado')}",
        )

        # ---- H3: recusa ------------------------------------------------------
        ok2 = escreve_corpo(
            base,
            "ok2.md",
            corpo_ok("Portar os gates", "tests/teste_handoff.py sai 0 na bateria desta peça."),
        )
        r_abrir2 = roda(
            env, "abrir",
            "--de", "claude", "--para", "kimi",
            "--titulo", "Portar os gates G1-G5",
            "--corpo", str(ok2),
        )
        hid2 = hid_de(r_abrir2.stdout)
        r_recusa = roda(
            env, "recusar", hid2,
            "--quem", "kimi",
            "--motivo", "já estou no outro braço",
        )
        checa(
            "H3 recusar grava estado=recusado e devolve a bola",
            r_abrir2.returncode == 0
            and r_recusa.returncode == 0
            and meta_do(base, hid2).get("estado") == "recusado"
            and "recusado" in r_recusa.stdout,
            f"rc={r_recusa.returncode} estado={meta_do(base, hid2).get('estado')}",
        )

        # ---- H4: abandonado aparece na cobrança ------------------------------
        ok3 = escreve_corpo(
            base,
            "ok3.md",
            corpo_ok("Tarefa órfã", "arquivo X existe com a linha medida."),
        )
        r_abrir3 = roda(
            env, "abrir",
            "--de", "claude", "--para", "kimi",
            "--titulo", "Tarefa que ninguém assumiu",
            "--corpo", str(ok3),
            "--prazo", "0",
        )
        hid3 = hid_de(r_abrir3.stdout)
        r_lista = roda(env, "lista")
        r_cobrar = roda(env, "cobrar")
        r_cobrar_id = roda(env, "cobrar", hid3)
        estado3 = meta_do(base, hid3).get("estado") if hid3 else ""
        checa(
            "H4 --prazo 0 vira abandonado e aparece em lista e em cobrar",
            r_abrir3.returncode == 0
            and estado3 == "abandonado"
            and "abandonado" in r_lista.stdout
            and hid3 in r_lista.stdout
            and r_cobrar.returncode == 0
            and hid3 in r_cobrar.stdout
            and "abandonado" in r_cobrar.stdout
            and r_cobrar_id.returncode == 0
            and "cobrança" in r_cobrar_id.stdout,
            f"estado={estado3} lista={r_lista.stdout!r} cobrar={r_cobrar.stdout!r}",
        )

        # ---- H5: fechar sem prova é bloqueado --------------------------------
        r_sem_prova = subprocess.run(
            [sys.executable, str(CLI), "fechar", hid1, "--quem", "codex",
             "--resultado", "terminei"],
            env=env,
            capture_output=True,
            text=True,
        )
        r_alegacao = roda(
            env, "fechar", hid1,
            "--quem", "codex",
            "--resultado", "terminei",
            "--prova", "Terminei",
        )
        checa(
            "T-RED fechar sem --prova REPROVA (argparse / gate)",
            r_sem_prova.returncode != 0
            and meta_do(base, hid1).get("estado") == "aceito",
            f"rc={r_sem_prova.returncode} estado={meta_do(base, hid1).get('estado')}",
        )
        checa(
            "T-RED fechar com prova='Terminei' REPROVA (alegação não é artefato)",
            r_alegacao.returncode == 2
            and "prova" in r_alegacao.stderr.lower()
            and meta_do(base, hid1).get("estado") == "aceito",
            f"rc={r_alegacao.returncode} stderr={r_alegacao.stderr.splitlines()[0] if r_alegacao.stderr else ''}",
        )

        prova = str(base / "handoff" / f"{hid1}.md")
        r_fecha = roda(
            env, "fechar", hid1,
            "--quem", "codex",
            "--resultado", "banco tem agent_id=codex",
            "--prova", f"sqlite3 omni.db count → 41 (era 0); arquivo {prova}",
        )
        checa(
            "H5 fechar com prova cita o artefato e estado=fechado",
            r_fecha.returncode == 0
            and meta_do(base, hid1).get("estado") == "fechado"
            and "prova" in meta_do(base, hid1),
            f"rc={r_fecha.returncode} estado={meta_do(base, hid1).get('estado')}",
        )

        r_fecha_aberto = roda(
            env, "fechar", hid3,
            "--quem", "kimi",
            "--resultado", "não aceitei",
            "--prova", str(base / "handoff" / f"{hid3}.md"),
        )
        checa(
            "H5 fechar a partir de abandonado (sem aceitar) REPROVA",
            r_fecha_aberto.returncode == 2
            and "aceito" in r_fecha_aberto.stderr,
            f"rc={r_fecha_aberto.returncode}",
        )

        # ---- H6: chat pré-existente (fixture sala-v1) ------------------------
    finally:
        shutil.rmtree(base, ignore_errors=True)

    # Sala nova a partir da fixture congelada — o gate que os testes antigos não tinham.
    if not FIXTURE.is_dir():
        checa("H6 fixture sala-v1 existe", False, str(FIXTURE))
    else:
        foto_antes = {
            str(p.relative_to(FIXTURE)): p.read_bytes()
            for p in sorted(FIXTURE.rglob("*"))
            if p.is_file()
        }
        base2 = Path(tempfile.mkdtemp(prefix="iachat-handoff-hist-"))
        env2 = {
            **os.environ,
            "IACHAT_HOME": str(base2),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        try:
            shutil.copytree(FIXTURE, base2, dirs_exist_ok=True)
            os.environ["IACHAT_HOME"] = str(base2)
            import importlib
            import iachat_core as core2
            importlib.reload(core2)

            texto0 = core2.p_chat().read_text(encoding="utf-8")
            msgs0 = core2.parse(texto0)
            nums0 = [m["n"] for m in msgs0]
            checa(
                "H6 parser lê as 8 mensagens da sala antiga ANTES do handoff",
                len(msgs0) == 8 and nums0 == list(range(1, 9)),
                f"leu {len(msgs0)} nums={nums0}",
            )

            corpo_hist = escreve_corpo(
                base2,
                "hist.md",
                corpo_ok(
                    "Não destruir o histórico",
                    f"parser continua lendo as 8 mensagens de {FIXTURE}/iachat.md e o ponteiro é #9.",
                ),
            )
            r_hist = roda(
                env2, "abrir",
                "--de", "claude", "--para", "codex",
                "--titulo", "Não destruir o histórico",
                "--corpo", str(corpo_hist),
            )
            msgs1 = core2.parse(core2.p_chat().read_text(encoding="utf-8"))
            nums1 = [m["n"] for m in msgs1]
            hid_hist = hid_de(r_hist.stdout)
            checa(
                "H6 handoff em chat pré-existente vira #9 e preserva 1..8",
                r_hist.returncode == 0
                and nums1 == list(range(1, 10))
                and any("HANDOFF" in m["bruto"] and m["n"] == 9 for m in msgs1)
                and hid_hist.startswith("HO-"),
                f"rc={r_hist.returncode} nums={nums1} hid={hid_hist}",
            )
            foto_depois = {
                str(p.relative_to(FIXTURE)): p.read_bytes()
                for p in sorted(FIXTURE.rglob("*"))
                if p.is_file()
            }
            checa(
                "H6 fixture do repo saiu intocada",
                foto_antes == foto_depois,
            )
        finally:
            shutil.rmtree(base2, ignore_errors=True)

    print()
    if falhas:
        print(f"❌ IA-HANDOFF REPROVOU: {falhas}")
        return 1
    print("✅ IA-HANDOFF PASSOU")
    return 0


if __name__ == "__main__":
    sys.exit(main())
