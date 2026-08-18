#!/usr/bin/env python3
"""Gates do iachat-plan.

Mede o iachat-plan sob cinco condições essenciais:
1. Modo seco por padrão: sem --executar não gasta e não aciona ninguém.
2. --executar exigido para acionar a casca.
3. Plano que volta não escreve nada no repositório do projeto.
4. Chat pré-existente com histórico mantido e testado (não só sala nova).
5. O caso que REPROVA (gate de reprovação): se a casca alterar o disco em modo plano,
   o plano vai para quarentena, não é entregue e o comando sai com código 3.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BIN = RAIZ / "bin"
PLAN = BIN / "iachat-plan"
sys.path.insert(0, str(BIN))
import iachat_core as core

falhas: list[str] = []


def checa(nome: str, condicao: bool, detalhe: str = "") -> None:
    print(f"{'✔' if condicao else '✗'} {nome}" + (f"  → {detalhe}" if detalhe else ""))
    if not condicao:
        falhas.append(nome)


def roda(env: dict[str, str], *args: str):
    return subprocess.run(
        [str(PLAN), *args],
        env=env,
        capture_output=True,
        text=True,
    )


def cria_script_mock(caminho: Path, conteudo: str) -> None:
    caminho.write_text(conteudo, encoding="utf-8")
    caminho.chmod(0o755)


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="iachat-plan-test-"))
    sala = tmp / "sala"
    repo_teste = tmp / "repo"
    repo_teste.mkdir(parents=True, exist_ok=True)
    (repo_teste / "README.md").write_text("# Repo Teste\n", encoding="utf-8")

    bin_mock = tmp / "mock_bin"
    bin_mock.mkdir(parents=True, exist_ok=True)

    # Mock casca obediente (kimi): apenas imprime o plano e registra chamada
    log_obediente = tmp / "obediente.log"
    cria_script_mock(
        bin_mock / "kimi",
        f"#!/bin/sh\necho 'chamado' >> '{log_obediente}'\n"
        "echo '## Objetivo — Testar o plano'\n"
        "echo '## O que eu li — README.md:1'\n"
        "echo '## Passos — 1. Passo teste'\n"
        "echo '## Riscos — Nenhum'\n"
        "echo '## O que eu não sei — Nada'\n"
    )

    # Mock casca maliciosa (codex): altera o disco E imprime plano
    cria_script_mock(
        bin_mock / "codex",
        "#!/bin/sh\n"
        f"echo 'invadido' > '{repo_teste}/arquivo_sujo.txt'\n"
        "echo '## Objetivo — Plano com invasão'\n"
        "echo '## O que eu li — README.md:1'\n"
        "echo '## Passos — 1. Criar arquivo'\n"
    )

    os.environ["IACHAT_HOME"] = str(sala)
    os.environ["IACHAT_BIN"] = str(BIN)

    env = os.environ.copy()
    env["PATH"] = f"{bin_mock}:{env.get('PATH', '')}"

    try:
        # G0: Executável existe
        checa("G0 iachat-plan existe e é executável", PLAN.is_file() and os.access(PLAN, os.X_OK))

        # G1: Modo seco por padrão (sem --executar)
        r_seco = roda(env, "kimi", "Refatorar módulo teste", "--repo", str(repo_teste))
        checa("G1 modo seco sai com código 0", r_seco.returncode == 0, f"rc={r_seco.returncode}")
        checa("G1 modo seco imprime cabeçalho de MODO SECO", "MODO SECO" in r_seco.stdout)
        checa("G1 modo seco não aciona a casca (mock não rodou)", not log_obediente.exists())
        checa("G1 modo seco mostra custo medido do prompt em bytes", "Prompt total medido:" in r_seco.stdout or "total medidos" in r_seco.stdout)

        # Prepara sala pré-existente com histórico real
        core.garantir_estrutura()
        core.post("claude", "Mensagem #1 antiga na sala pré-existente.", ["codex"])
        core.post("codex", "Mensagem #2 antiga na sala pré-existente.", ["claude"])
        core.marca_lida("codex", 2)

        # G2: Disparo real com --executar e casca obediente (kimi)
        r_exec = roda(env, "kimi", "Criar novo plano de arquitetura", "--repo", str(repo_teste), "--de", "claude", "--executar")
        checa("G2 disparo real com --executar sai com código 0", r_exec.returncode == 0, f"rc={r_exec.returncode}")
        checa("G2 mock obediente foi efetivamente acionado", log_obediente.exists())

        planos = list((sala / "planos").glob("*.md"))
        checa("G2 arquivo de plano gerado em ~/ia-chat-global/planos/", len(planos) == 1, f"planos={len(planos)}")

        # Verifica histórico mantido no chat pré-existente e ponteiro adicionado
        chat_depois = (sala / "iachat.md").read_text(encoding="utf-8")
        checa("G2 histórico pré-existente mantido intacto", "Mensagem #1 antiga" in chat_depois and "Mensagem #2 antiga" in chat_depois)
        checa("G2 ponteiro do plano postado na sala", "plano pronto:" in chat_depois or "gate do disco INTACTO" in chat_depois)
        checa("G2 disco do repositório permaneceu intacto sem edições", not (repo_teste / "arquivo_sujo.txt").exists())

        # G3: O CASO QUE REPROVA (GATE DE REPROVAÇÃO - Casca altera o disco)
        r_mal = roda(env, "codex", "Alterar disco indevidamente", "--repo", str(repo_teste), "--de", "claude", "--executar")
        checa("G3 casca maliciosa reprova no gate com código 3", r_mal.returncode == 3, f"rc={r_mal.returncode}")
        checa("G3 stderr alerta que a casca alterou o disco", "alterou o disco" in r_mal.stderr or "GATE REPROVOU" in r_mal.stderr)

        quarentenas = list((sala / "planos").glob("*.QUARENTENA.md"))
        checa("G3 plano violador movido para quarentena (.QUARENTENA.md)", len(quarentenas) == 1, f"quarentenas={len(quarentenas)}")

        chat_quarentena = (sala / "iachat.md").read_text(encoding="utf-8")
        checa("G3 aviso de quarentena enviado para a sala sem entregar o plano", "iachat-plan REPROVADO" in chat_quarentena)

        # G4: Suporte a casca sem adaptador (código 2)
        r_invalida = roda(env, "casca_inexistente", "Minha tarefa", "--repo", str(repo_teste))
        checa("G4 casca sem adaptador retorna código 2", r_invalida.returncode == 2, f"rc={r_invalida.returncode}")

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if falhas:
        print(f"\n❌ {len(falhas)} falha(s): {', '.join(falhas)}", file=sys.stderr)
        return 1
    print("\n✅ IA-PLAN TESTES PASSARAM")
    return 0


if __name__ == "__main__":
    sys.exit(main())
