#!/usr/bin/env python3
"""Gates do ia-digest.

Mede o iachat-digest sob quatro condições essenciais:
1. Mensagem grande destilada cabe no teto e entrega > 50% dos bytes de conteúdo.
2. Mensagem curta (ou que não pode/deve ser destilada) passa inteira.
3. Chat pré-existente com histórico mantido e testado (não só sala recém-criada).
4. O caso que REPROVA: teto estourado reporta ESTOUROU no `ver`, e a entrega
   destilada NUNCA altera o ativo (sha256 antes == depois).

Tudo roda em ``IACHAT_HOME`` temporário, colocado em os.environ ANTES de importar
o core (o core resolve a raiz a cada chamada de home()).
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BIN = RAIZ / "bin"
DIGEST = BIN / "iachat-digest"

TMP = Path(tempfile.mkdtemp(prefix="iachat-digest-test-"))
os.environ["IACHAT_HOME"] = str(TMP)  # antes do import: nenhum teste toca a sala real

sys.path.insert(0, str(BIN))
import iachat_core as core

falhas: list[str] = []
TMP2: Path | None = None


def checa(nome: str, condicao: bool, detalhe: str = "") -> None:
    print(f"{'✔' if condicao else '✗'} {nome}" + (f"  → {detalhe}" if detalhe else ""))
    if not condicao:
        falhas.append(nome)


def roda(env: dict[str, str], *args: str):
    return subprocess.run(
        [sys.executable, str(DIGEST), *args],
        env=env,
        capture_output=True,
        text=True,
    )


def calc_sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    env = os.environ.copy()
    env["IACHAT_HOME"] = str(TMP)

    try:
        # ── Sala com histórico PRÉ-EXISTENTE (achado crítico de 17/08: gate que só
        # testa sala nova não pega o que apaga histórico). Mensagens #1 e #2 antigas,
        # cursor do codex avançado até 2, e a entrega tem que trazer a #1 (dirigida
        # a ele, pré-cursor) + as novas, sem nunca tocar no arquivo.
        core.garantir_estrutura()
        core.post("claude", "Primeira mensagem antiga da sala. `config.json:10`", ["codex"])
        core.post("codex", "Segunda mensagem antiga da sala.", ["claude"])
        core.marca_lida("codex", 2)  # codex já viu #1 e #2: sala pré-existente

        msg_grande1 = (
            "### 💬 Grande Relatório de Teste #1\n\n"
            "Esta é a abertura da mensagem que sempre deve ficar.\n\n"
            "Aqui está uma linha de prosa sem nenhum fato relevante que deve ser cortada no grau 1.\n"
            "Por outro lado, esta linha tem um caminho /Users/bauervieiracesarfilhovieira/file.txt e deve ser preservada!\n"
            "Esta outra linha tem o número 42 medido e deve ficar intacta.\n"
            "E esta linha tem o comando `iachat read` e também fica.\n"
            "Esta linha de prosa pura pode ser eliminada sem problemas.\n"
        )
        msg_grande2 = (
            "### 💬 Grande Relatório de Teste #2\n\n"
            "Abertura da mensagem 2 que também se mantém.\n\n"
            "Prosa irrelevante um. Prosa irrelevante dois.\n"
            'Aqui citamos o dono *\\"faça o teste passar\\"* que não pode sair.\n'
            "Mais prosa pura repetida várias vezes para estourar o teto pequeno de teste.\n"
        ) * 5

        core.post("claude", msg_grande1, ["codex"])
        core.post("claude", msg_grande2, ["codex"])

        ativo = core.p_chat()
        bytes_antes = ativo.stat().st_size
        sha_antes = calc_sha256(ativo)

        # G1 — destilar de verdade, sob teto menor que o pendente
        r = roda(env, "entregar", "--de", "codex", "--teto", "2000")
        checa("G1 iachat-digest entregar roda com sucesso", r.returncode == 0, f"rc={r.returncode}")
        corpo = r.stdout.split("\n\n", 1)[1] if "\n\n" in r.stdout else r.stdout
        checa("G1 entrega atinge a marca de destilado", "🗜️ destilado" in r.stdout)
        checa("G1 entrega destilada respeita o teto", len(corpo.encode()) <= 2000,
              f"corpo={len(corpo.encode())}B")
        checa("G1 ponteiro de volta para a íntegra presente em toda destilada",
              "iachat page ativo" in r.stdout, "comando da íntegra alcançável")
        checa("G1 prosa sem fato é cortada na destilação", "Prosa irrelevante um" not in corpo)

        sha_depois = calc_sha256(ativo)
        checa("G1 sha256 do ativo permanece INTACTO após entrega destilada",
              sha_antes == sha_depois, f"sha={sha_antes[:16]}")
        checa("G1 ativo não cresceu nem encolheu (destilar é leitura, nunca escrita)",
              ativo.stat().st_size == bytes_antes, f"{bytes_antes} B")

        # G2 — fatos protegidos sobrevivem à destilação
        checa("G2 preserva caminho absoluto", "/Users/bauervieiracesarfilhovieira/file.txt" in r.stdout)
        checa("G2 preserva número medido", " 42 " in r.stdout)
        checa("G2 preserva comando em crase", "`iachat read`" in r.stdout)
        checa("G2 preserva citação do dono", '*\\"faça o teste passar\\"*' in r.stdout)

        # G3 — chat pré-existente com histórico: a sala já tinha #1/#2 e cursor avançado
        # ANTES do digest existir. O que o gate prova: a entrega lê o chat real do disco,
        # respeita o cursor (não re-entrega o já lido) e avança só até o que entregou.
        checa("G3 mensagem já lida do histórico NÃO é re-entregue",
              "Primeira mensagem antiga da sala" not in r.stdout)
        checa("G3 sala pré-existente: só as novas (#3, #4) estavam pendentes",
              "Grande Relatório de Teste #1" in r.stdout
              and "Grande Relatório de Teste #2" in r.stdout)
        checa("G3 cursor avançou até a última entregue", core.cursor("codex") == 4,
              f"cursor={core.cursor('codex')}")

        # G3b — sala nova: mensagem curta passa inteira, sem marca 🗜️.
        # home() lê IACHAT_HOME a cada chamada, então basta trocar a env e chamar o core.
        global TMP2
        TMP2 = Path(tempfile.mkdtemp(prefix="iachat-digest-test2-"))
        os.environ["IACHAT_HOME"] = str(TMP2)
        env2 = os.environ.copy()
        core.garantir_estrutura()
        core.post("claude", "Mensagem curta direta.", ["codex"])
        r_curto = roda(env2, "entregar", "--de", "codex", "--teto", "6144")
        checa("G3b mensagem curta passa inteira sem marca 🗜️",
              "🗜️ destilado" not in r_curto.stdout)
        checa("G3b conteúdo curto entregue idêntico", "Mensagem curta direta." in r_curto.stdout)

        # G4 — o caso que REPROVA: teto impossível de caber → o `ver` mede e reporta
        # ESTOUROU em vez de fingir que coube. É o gate vendo vermelho de propósito.
        os.environ["IACHAT_HOME"] = str(TMP)  # volta para a sala com histórico
        core.marca_lida("codex", 2)  # cursor volta antes das grandes, para o ver ter pendente
        r_estouro = roda(env, "ver", "--de", "codex", "--teto", "10")
        checa("G4 estouro de teto reporta ESTOUROU no 'ver'", "ESTOUROU" in r_estouro.stdout)

    finally:
        shutil.rmtree(TMP, ignore_errors=True)
        if TMP2:
            shutil.rmtree(TMP2, ignore_errors=True)

    if falhas:
        print(f"\n❌ {len(falhas)} falha(s): {', '.join(falhas)}", file=sys.stderr)
        return 1
    print("\n✅ IA-DIGEST TESTES PASSARAM")
    return 0


if __name__ == "__main__":
    sys.exit(main())
