#!/usr/bin/env python3
"""Gates do ia-thread: vínculo no corpo, custo, rotação e prova vermelha.

Tudo roda em ``IACHAT_HOME`` temporário. O teste usa a CLI pública em
subprocesso e inclui dois casos ruins que precisam REPROVAR: pai inexistente no
post e vínculo futuro injetado pelo ``iachat`` cru.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


RAIZ = Path(__file__).resolve().parent.parent
THREAD = RAIZ / "bin" / "iachat-thread"
IACHAT = RAIZ / "bin" / "iachat"
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


def primeira_linha_do_corpo(mensagem: dict) -> str:
    partes = mensagem["bruto"].split("\n\n", 1)
    return partes[1].splitlines()[0] if len(partes) == 2 and partes[1] else ""


def todas_as_mensagens(core) -> list[dict]:
    mensagens: list[dict] = []
    for caminho in core._recortes() + [core.p_chat()]:
        mensagens.extend(core.parse(caminho.read_text(encoding="utf-8")))
    return sorted(mensagens, key=lambda item: item["n"])


def main() -> int:
    base = Path(tempfile.mkdtemp(prefix="iachat-thread-teste-"))
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
        checa(
            "T0 CLI iachat-thread existe e é executável",
            THREAD.is_file() and os.access(THREAD, os.X_OK),
            str(THREAD),
        )

        # ---- T1: histórico anterior à peça continua inteiro -----------------
        raiz_1 = core.post("claude", "Assunto legado A. @codex", ["codex"])["n"]
        raiz_2 = core.post("kimi", "Assunto legado B. @claude", ["claude"])["n"]
        falso = core.post(
            "kimi",
            "Primeira linha sem vínculo.\n`re: #1` é exemplo; no meio, re: #1 também não conta.",
            ["claude"],
        )["n"]
        lista_inicial = roda(THREAD, env, "list")
        checa(
            "T1 mensagem antiga sem marcador vira raiz, sem perda",
            lista_inicial.returncode == 0
            and all(f"fio #{numero}" in lista_inicial.stdout for numero in (raiz_1, raiz_2, falso)),
            lista_inicial.stdout.replace("\n", " | ")[:240],
        )
        fio_1_antes = roda(THREAD, env, "ler", str(raiz_1))
        checa(
            "T1 re: #N em crase/no meio NÃO cria falso vínculo",
            fio_1_antes.returncode == 0 and "Primeira linha sem vínculo" not in fio_1_antes.stdout,
        )

        # ---- T2: post canônico e leitura por qualquer descendente -----------
        resposta = roda(
            THREAD,
            env,
            "post",
            "--de",
            "codex",
            "--re",
            str(raiz_1),
            "--para",
            "claude",
            "Medi 27%; devolvo para você, @claude.",
        )
        msgs = todas_as_mensagens(core)
        numero_resposta = msgs[-1]["n"]
        checa(
            "T2 post grava re: #N na PRIMEIRA linha e preserva o parser",
            resposta.returncode == 0
            and primeira_linha_do_corpo(msgs[-1]) == f"re: #{raiz_1}"
            and [m["n"] for m in msgs] == list(range(1, len(msgs) + 1)),
            f"rc={resposta.returncode} primeira={primeira_linha_do_corpo(msgs[-1])!r}",
        )
        ramo = roda(
            THREAD,
            env,
            "post",
            "--de",
            "kimi",
            "--re",
            str(raiz_1),
            "--para",
            "claude",
            "Achei uma segunda evidência.",
        )
        numero_ramo = todas_as_mensagens(core)[-1]["n"]
        lido_pelo_descendente = roda(THREAD, env, "ler", str(numero_resposta))
        checa(
            "T2 ler por descendente devolve raiz e TODAS as ramificações",
            ramo.returncode == 0
            and lido_pelo_descendente.returncode == 0
            and all(
                f"iachat msg={numero}" in lido_pelo_descendente.stdout
                for numero in (raiz_1, numero_resposta, numero_ramo)
            )
            and len(re.findall(r"<!-- iachat msg=", lido_pelo_descendente.stdout)) == 3,
        )
        checa(
            "T3 última nominação deixa fio ABERTO e a bola nomeada",
            "ABERTO" in lido_pelo_descendente.stdout and "bola: @claude" in lido_pelo_descendente.stdout,
        )

        # ---- T4: fechamento explícito vence até uma nominação ---------------
        fechamento = roda(
            THREAD,
            env,
            "post",
            "--de",
            "claude",
            "--re",
            str(numero_ramo),
            "--para",
            "codex",
            "--fecha",
            "Confirmado; o ponto está resolvido.",
        )
        ultima = todas_as_mensagens(core)[-1]
        fechado = roda(THREAD, env, "ler", str(raiz_1))
        checa(
            "T4 --fecha grava a marca explícita e fecha mesmo nominando",
            fechamento.returncode == 0
            and primeira_linha_do_corpo(ultima) == f"re: #{numero_ramo} ✔"
            and "FECHADO" in fechado.stdout
            and "bola: —" in fechado.stdout,
        )

        # ---- T-RED 1: pai inexistente é rejeitado sem append ----------------
        antes_invalido = len(todas_as_mensagens(core))
        invalido = roda(
            THREAD,
            env,
            "post",
            "--de",
            "codex",
            "--re",
            "9999",
            "Isto não pode entrar.",
        )
        depois_invalido = len(todas_as_mensagens(core))
        checa(
            "T-RED pai inexistente é REPROVADO, sem escrever",
            invalido.returncode != 0
            and "não existe mensagem #9999" in invalido.stderr
            and antes_invalido == depois_invalido,
            f"rc={invalido.returncode} mensagens {antes_invalido}→{depois_invalido}",
        )

        # ---- T5/T6: custo e fio partido pela rotação -------------------------
        raiz_longa = core.post("claude", "Fio que atravessará a rotação. @codex", ["codex"])["n"]
        pai = raiz_longa
        for indice in range(4):
            resposta_longa = roda(
                THREAD,
                env,
                "post",
                "--de",
                "codex" if indice % 2 == 0 else "claude",
                "--re",
                str(pai),
                "--para",
                "claude" if indice % 2 == 0 else "codex",
                f"Etapa {indice + 1} do fio; evidência " + ("fio " * 45),
            )
            checa(f"T5 reply encadeada {indice + 1}/4 foi aceita", resposta_longa.returncode == 0)
            pai = todas_as_mensagens(core)[-1]["n"]

        recheio = "conteúdo alheio ao fio para medir custo real " * 14
        for indice in range(40):
            core.post(
                ["claude", "codex", "kimi"][indice % 3],
                f"Assunto paralelo {indice:02d}.\n{recheio}",
                [],
            )

        fio_antes = roda(THREAD, env, "ler", str(raiz_longa))
        sala_inteira = core.ler("kimi", escopo="tudo", avancar=False)["bytes"]
        custo_fio = len(fio_antes.stdout.encode("utf-8"))
        checa(
            "T5 ler um fio custa menos que ler a sala inteira",
            fio_antes.returncode == 0 and custo_fio < sala_inteira,
            f"fio={custo_fio} B · --tudo={sala_inteira} B · {sala_inteira/custo_fio:.1f}x",
        )

        cfg = json.loads(core.p_config().read_text(encoding="utf-8"))
        cfg["teto_bytes"] = 8192
        core.p_config().write_text(json.dumps(cfg) + "\n", encoding="utf-8")
        rotacao = core.rotate()
        fontes_apos_corte = [p.stem for p in core._recortes()]
        checa(
            "T6 rotação realmente arquivou a raiz e o pai",
            rotacao["rodou"]
            and fontes_apos_corte
            and any(m["n"] == raiz_longa for m in core.parse(core._recortes()[0].read_text(encoding="utf-8")))
            and not any(m["n"] == raiz_longa for m in core.parse(core.p_chat().read_text(encoding="utf-8"))),
            f"rodou={rotacao.get('rodou')} fontes={fontes_apos_corte}",
        )

        pos_rotacao = roda(
            THREAD,
            env,
            "post",
            "--de",
            "codex",
            "--re",
            str(pai),
            "--para",
            "claude",
            "Resposta nova ao pai que agora está no recorte.",
        )
        fio_depois = roda(THREAD, env, "ler", str(raiz_longa))
        checa(
            "T6 fio partido volta INTEIRO de recorte + ativo em um comando",
            pos_rotacao.returncode == 0
            and fio_depois.returncode == 0
            and len(re.findall(r"<!-- iachat msg=", fio_depois.stdout)) == 6
            and "recorte-01" in fio_depois.stdout
            and "iachat" in fio_depois.stdout,
            f"msgs={len(re.findall(r'<!-- iachat msg=', fio_depois.stdout))}",
        )
        abertos = roda(THREAD, env, "list", "--abertos")
        checa(
            "T7 list --abertos mostra o fio pendente e omite o fechado",
            abertos.returncode == 0
            and f"fio #{raiz_longa}" in abertos.stdout
            and f"fio #{raiz_1}" not in abertos.stdout,
        )

        # ---- T-RED 2: histórico corrompido precisa deixar o gate vermelho ----
        base_vermelha = Path(tempfile.mkdtemp(prefix="iachat-thread-vermelho-"))
        env_vermelho = {**env, "IACHAT_HOME": str(base_vermelha)}
        try:
            roda(IACHAT, env_vermelho, "status")
            (base_vermelha / "config.json").write_text(
                json.dumps(
                    {"na_sala": ["claude", "codex", "kimi"], "brain": "claude", "teto_bytes": 204800}
                )
                + "\n",
                encoding="utf-8",
            )
            injecao = roda(
                IACHAT,
                env_vermelho,
                "post",
                "--de",
                "claude",
                "re: #99\nVínculo futuro propositalmente inválido.",
            )
            vermelho = roda(THREAD, env_vermelho, "list")
            checa(
                "T-RED vínculo futuro no histórico faz o gate REPROVAR",
                injecao.returncode == 0
                and vermelho.returncode != 0
                and "não aponta para mensagem anterior" in vermelho.stderr,
                f"post={injecao.returncode} gate={vermelho.returncode}",
            )
        finally:
            shutil.rmtree(base_vermelha, ignore_errors=True)

        print()
        print("✅ IA-THREAD PASSOU" if not falhas else f"❌ IA-THREAD REPROVOU: {falhas}")
        return 0 if not falhas else 1
    finally:
        shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
