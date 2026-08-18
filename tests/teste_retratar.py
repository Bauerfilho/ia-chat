#!/usr/bin/env python3
"""Gates do ia-retratar sobre uma sala v1 pré-existente.

O teste copia a fixture congelada com oito mensagens, cursores e histórico. Ele
exercita apenas as CLIs públicas em ``IACHAT_HOME`` temporário e inclui casos
que precisam REPROVAR sem acrescentar byte ao chat.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


RAIZ = Path(__file__).resolve().parent.parent
RETRATAR = RAIZ / "bin" / "iachat-retratar"
IACHAT = RAIZ / "bin" / "iachat"
FIXTURE = RAIZ / "tests" / "fixtures" / "sala-v1"
falhas: list[str] = []


def checa(nome: str, condicao: bool, detalhe: str = "") -> None:
    print(f"{'✔' if condicao else '✗'} {nome}" + (f"  → {detalhe}" if detalhe else ""))
    if not condicao:
        falhas.append(nome)


def roda(
    cli: Path,
    env: dict[str, str],
    *args: str,
) -> subprocess.CompletedProcess[str]:
    """Usa a mesma porta pública que uma IA chama no terminal."""
    return subprocess.run(
        [sys.executable, str(cli), *args],
        env=env,
        capture_output=True,
        text=True,
    )


def main() -> int:
    base = Path(tempfile.mkdtemp(prefix="iachat-retratar-teste-"))
    shutil.copytree(FIXTURE, base, dirs_exist_ok=True)
    env = {
        **os.environ,
        "IACHAT_HOME": str(base),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    os.environ["IACHAT_HOME"] = str(base)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(RAIZ / "bin"))
    import iachat_core as core

    chat = base / "iachat.md"
    try:
        checa(
            "R0 CLI iachat-retratar existe e é executável",
            RETRATAR.is_file() and os.access(RETRATAR, os.X_OK),
            str(RETRATAR),
        )

        # ---- R1: o gate começa de história real, não de sala recém-criada ---
        antes = chat.read_bytes()
        mensagens_antes = core.parse(antes.decode("utf-8"))
        original_7 = next(m["bruto"] for m in mensagens_antes if m["n"] == 7)
        checa(
            "R1 fixture pré-existente tem 8 mensagens e cursores avançados",
            len(mensagens_antes) == 8
            and core.cursor("claude") == 8
            and core.cursor("codex") == 8
            and core.cursor("kimi") == 5,
            f"msgs={len(mensagens_antes)} cursores={[(ia, core.cursor(ia)) for ia in ('claude', 'codex', 'kimi')]}",
        )

        # ---- R2: retratação simples preserva todos os bytes anteriores ------
        publicada = roda(
            RETRATAR,
            env,
            "post",
            "--de",
            "codex",
            "--msg",
            "7",
            "--motivo",
            "a medição posterior contrariou a frase",
            "Arroba colado precisa ser revalidado; a afirmação anterior não vale.",
        )
        depois = chat.read_bytes()
        mensagens = core.parse(depois.decode("utf-8"))
        nova = mensagens[-1]
        checa(
            "R2 retratação simples vira mensagem #9 append-only",
            publicada.returncode == 0
            and depois.startswith(antes)
            and [m["n"] for m in mensagens] == list(range(1, 10))
            and nova["n"] == 9
            and nova["de"] == "codex"
            and "retrata: #7" in nova["bruto"]
            and "estado: RETRATADA" in nova["bruto"],
            f"rc={publicada.returncode} msgs={len(mensagens)}",
        )
        checa(
            "R2 mensagem original permanece byte a byte intacta",
            next(m["bruto"] for m in mensagens if m["n"] == 7) == original_7,
        )

        # ---- R3: quem recebeu/leu a errada volta a ser acordado ------------
        flag_claude = base / "pendente" / "claude.md"
        flag_kimi = base / "pendente" / "kimi.md"
        flag_codex = base / "pendente" / "codex.md"
        checa(
            "R3 leitor/destinatário recebe flag apontando a retratação",
            flag_claude.exists()
            and "#9" in flag_claude.read_text(encoding="utf-8")
            and "retrata: #7" in flag_claude.read_text(encoding="utf-8"),
        )
        checa(
            "R3 não há eco no autor nem aviso ao cursor anterior ao alvo",
            not flag_codex.exists() and not flag_kimi.exists(),
            f"codex={flag_codex.exists()} kimi={flag_kimi.exists()}",
        )

        # ---- R4: busca da peça marca o erro e aponta a correção -------------
        busca = roda(RETRATAR, env, "search", "e-mail")
        checa(
            "R4 busca marcada devolve original + ponteiro para #9",
            busca.returncode == 0
            and "#7" in busca.stdout
            and "⚠ RETRATADA → #9" in busca.stdout,
            busca.stdout.replace("\n", " | ")[:300],
        )

        # Este caso NASCEU invertido, e a inversão é a história do handoff: o autor da
        # peça o escreveu provando que o `iachat search` nativo NÃO marcava — a
        # integração mora no núcleo, que era fronteira proibida para ele, então ele
        # documentou o gap em vez de mascarar. A orquestradora integrou em 18/08, e o
        # caso virou o oposto: agora ele guarda a integração.
        #
        # Isto importa mais que a marca em si — sem ele, quem procura daqui a uma semana
        # acha a versão errada e a correção lado a lado, sem nada dizendo qual vale.
        busca_nativa = roda(IACHAT, env, "search", "e-mail")
        linha_alvo = next(
            (l for l in busca_nativa.stdout.splitlines() if "#7 " in l), ""
        )
        checa(
            "R4 o search NATIVO marca a mensagem retratada (integração do núcleo)",
            busca_nativa.returncode == 0 and "RETRATADA" in linha_alvo,
            f"a busca nativa devolve a versão errada sem aviso: {linha_alvo.strip()[:110]}",
        )

        # ---- R-RED 1: terceiro contesta, mas NÃO retrata --------------------
        bytes_antes_terceiro = chat.read_bytes()
        terceiro = roda(
            RETRATAR,
            env,
            "post",
            "--de",
            "claude",
            "--msg",
            "7",
            "Eu discordo e tento falar pelo autor.",
        )
        checa(
            "R-RED mensagem de outro autor REPROVA e não escreve",
            terceiro.returncode != 0
            and "só o próprio autor" in terceiro.stderr
            and chat.read_bytes() == bytes_antes_terceiro,
            f"rc={terceiro.returncode}",
        )

        # ---- R-RED 2: decisão do dono é limite material, não conselho -------
        decisao = core.post(
            "claude",
            "[DECISÃO DO DONO]\nO histórico permanece append-only.",
            ["codex"],
        )
        bytes_antes_dono = chat.read_bytes()
        dono = roda(
            RETRATAR,
            env,
            "post",
            "--de",
            "claude",
            "--msg",
            str(decisao["n"]),
            "Tento desfazer a governança do dono.",
        )
        checa(
            "R-RED decisão marcada do dono REPROVA e não escreve",
            dono.returncode != 0
            and "dono não pode ser retratada" in dono.stderr
            and chat.read_bytes() == bytes_antes_dono,
            f"rc={dono.returncode}",
        )

        # Uma retratação também não pode virar alvo e revalidar o erro por ambiguidade.
        retracao_da_retracao = roda(
            RETRATAR,
            env,
            "post",
            "--de",
            "codex",
            "--msg",
            "9",
            "Tento retratar a própria retratação.",
        )
        checa(
            "R-RED retratação de retratação REPROVA",
            retracao_da_retracao.returncode != 0
            and "não é retratável" in retracao_da_retracao.stderr
            and chat.read_bytes() == bytes_antes_dono,
        )

        # ---- R5: correção nova substitui ponteiro, sem apagar a anterior ----
        substituta = roda(
            RETRATAR,
            env,
            "post",
            "--de",
            "codex",
            "--msg",
            "7",
            "A regra vigente é: handles colados exigem validação específica.",
        )
        finais = core.parse(chat.read_text(encoding="utf-8"))
        ultima = finais[-1]
        busca_final = roda(RETRATAR, env, "search", "e-mail")
        checa(
            "R5 nova correção preserva #9 e vira ponteiro vigente #11",
            substituta.returncode == 0
            and ultima["n"] == 11
            and "retrata: #7" in ultima["bruto"]
            and "substitui-retratação: #9" in ultima["bruto"]
            and any(m["n"] == 9 for m in finais)
            and "⚠ RETRATADA → #11" in busca_final.stdout,
            f"rc={substituta.returncode} ultima={ultima['n']}",
        )

        # Nem uma marca publicada pela porta crua pode converter governança em dado vencido.
        core.post(
            "claude",
            f"retrata: #{decisao['n']}\nestado: RETRATADA\n\ncorreção:\nTentativa crua.",
            ["codex"],
        )
        busca_dono = roda(RETRATAR, env, "search", "O histórico permanece append-only")
        checa(
            "R-RED busca ignora retratação crua de decisão do dono",
            busca_dono.returncode == 0
            and f"#{decisao['n']}" in busca_dono.stdout
            and "RETRATADA" not in busca_dono.stdout,
            busca_dono.stdout.replace("\n", " | ")[:260],
        )

        print()
        print("✅ IA-RETRATAR PASSOU" if not falhas else f"❌ IA-RETRATAR REPROVOU: {falhas}")
        return 0 if not falhas else 1
    finally:
        shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
