#!/usr/bin/env python3
"""Gate do confronto de planos feito por ``iachat-comando plan --colher``.

O teste usa somente ``IACHAT_HOME`` temporário. Nenhum byte entra na sala viva e
nenhuma IA é chamada: os dois planos são injetados diretamente no estado da missão.

O T-RED final mutila uma cópia temporária do comando e roda este mesmo gate contra
ela. Assim a bateria prova que realmente fica vermelha quando a divergência some;
um teste que nunca viu o defeito poderia estar verde sem medir nada.
"""
from __future__ import annotations

import json
import os
import runpy
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


RAIZ = Path(__file__).resolve().parent.parent
CMD = Path(os.environ.get("IACHAT_CMD_UNDER_TEST", str(RAIZ / "bin" / "iachat-comando")))
CORE = RAIZ / "bin" / "iachat_core.py"
FALHAS = []


PLANO_CODEX = """<!-- IACHAT-CONFRONTO:INICIO -->
objetivo_id: m-confronto
recomendacao: favoravel
aplicar_agora: nao
tamanho: grande
claims:
- preservar-historico | preservar mensagens no recorte
- superficie-consumidores | sete consumidores precisam mudar
- busca-linear | buscar em todos os recortes cresce linearmente
<!-- IACHAT-CONFRONTO:FIM -->

# Plano codex

SEGREDO_CORPO_CODEX: corpo completo não pode entrar na sala.
"""


# O contrato começa depois de seis linhas não vazias de propósito. Isto reproduz o
# caso real em que o veredito do qwen estava na linha 7 e as três primeiras linhas
# arbitrárias do coletor o esconderam.
PLANO_QWEN = """# Plano qwen
ângulo: custo
premissa: operação deliberada
fonte: núcleo atual
escopo: estimativa inicial
nota: veredito abaixo
<!-- IACHAT-CONFRONTO:INICIO -->
objetivo_id: m-confronto
recomendacao: favoravel
aplicar_agora: nao
tamanho: pequeno
claims:
- preservar-historico | preservar mensagens no recorte
- superficie-consumidores | apenas o núcleo precisa mudar
- recorte-sobrescrita | contar arquivos pode sobrescrever um recorte apagado
<!-- IACHAT-CONFRONTO:FIM -->

SEGREDO_CORPO_QWEN: o resumo não é licença para copiar o corpo.
"""


def checa(nome, condicao, detalhe=""):
    """Registra cada afirmação como gate binário e legível."""
    print("{} {}{}".format("PASS" if condicao else "FAIL", nome,
                            " — " + detalhe if detalhe else ""))
    if not condicao:
        FALHAS.append(nome)


def prepara_home(base, plano_codex, plano_qwen):
    """Monta a menor sala possível para exercitar a porta pública do comando."""
    home = base / "sala"
    missao = home / "comando" / "m-confronto"
    planos = missao / "planos"
    planos.mkdir(parents=True)
    (home / "config.json").write_text(
        json.dumps({"na_sala": ["claude", "codex", "qwen"],
                    "brain": "claude", "teto_bytes": 204800}) + "\n",
        encoding="utf-8",
    )
    p_codex = planos / "codex.md"
    p_qwen = planos / "qwen.md"
    p_codex.write_text(plano_codex, encoding="utf-8")
    p_qwen.write_text(plano_qwen, encoding="utf-8")
    estado = {
        "id": "m-confronto",
        "goal": "decidir se a sala deve ganhar arquivamento deliberado",
        "dir": str(missao),
        "estado": "planejando",
        "de": "claude",
        "workers": {
            "codex": {"plano": str(p_codex)},
            "qwen": {"plano": str(p_qwen)},
        },
    }
    (home / "comando" / "estado.json").write_text(
        json.dumps(estado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return home, p_codex, p_qwen


def executa(plano_codex=PLANO_CODEX, plano_qwen=PLANO_QWEN):
    """Executa ``--colher`` calado; portanto nem a sala temporária recebe post."""
    tmp = tempfile.TemporaryDirectory(prefix="iachat-colher-confronta-")
    base = Path(tmp.name)
    home, p_codex, p_qwen = prepara_home(base, plano_codex, plano_qwen)
    env = os.environ.copy()
    env["IACHAT_HOME"] = str(home)
    proc = subprocess.run(
        [sys.executable, str(CMD), "plan", "--colher", "--calado", "--de", "claude"],
        env=env,
        capture_output=True,
        text=True,
    )
    return tmp, proc, p_codex, p_qwen


def prova_funcional():
    """Dois planos discordam de verdade; a saída tem de tornar isso visível."""
    tmp, proc, p_codex, p_qwen = executa()
    try:
        saida = proc.stdout
        checa("C1 colher conclui", proc.returncode == 0, "rc={}".format(proc.returncode))
        checa("C2 caminhos completos permanecem", str(p_codex) in saida and str(p_qwen) in saida)
        checa("C3 veredito da linha sete aparece", "Veredito qwen" in saida)
        checa(
            "C4 consenso consolidado uma vez",
            "**Concordam**" in saida and saida.count("preservar mensagens no recorte") == 1,
            "ocorrencias={}".format(saida.count("preservar mensagens no recorte")),
        )
        checa(
            "C5 divergência nomeia os dois braços",
            "**Divergem**" in saida and "**codex:** grande" in saida
            and "**qwen:** pequeno" in saida,
        )
        checa(
            "C6 cobertura única não vira ruído",
            "**Cobertura única**" in saida and "só **codex**" in saida
            and "`busca-linear`" in saida and "só **qwen**" in saida
            and "`recorte-sobrescrita`" in saida,
        )
        checa(
            "C7 sala recebe resumo e nunca corpo",
            "SEGREDO_CORPO_CODEX" not in saida and "SEGREDO_CORPO_QWEN" not in saida,
        )
    finally:
        tmp.cleanup()


def prova_nao_comparavel():
    """Um plano vazio não autoriza fabricar concordância com o que sobrou."""
    tmp, proc, _p_codex, _p_qwen = executa(plano_qwen="")
    try:
        checa(
            "C8 plano vazio declara confronto indisponível",
            proc.returncode == 0 and "**Confronto indisponível**" in proc.stdout
            and "não inventei consenso" in proc.stdout and "1 de 2" in proc.stdout,
            "rc={}".format(proc.returncode),
        )
    finally:
        tmp.cleanup()

    outro_tema = PLANO_QWEN.replace(
        "objetivo_id: m-confronto", "objetivo_id: outra-missao", 1
    )
    tmp, proc, _p_codex, _p_qwen = executa(plano_qwen=outro_tema)
    try:
        checa(
            "C9 temas diferentes não fabricam consenso",
            proc.returncode == 0 and "**Confronto indisponível**" in proc.stdout
            and "não corresponde a m-confronto" in proc.stdout,
            "rc={}".format(proc.returncode),
        )
    finally:
        tmp.cleanup()


def prova_prompt():
    """O conserto nasce no pedido: workers novos já escrevem o dado comparável."""
    namespace = runpy.run_path(str(CMD))
    prompt = namespace["prompt_de"](
        "codex",
        {"id": "m-confronto", "goal": "comparar propostas", "dir": "/tmp/m-confronto",
         "de": "claude"},
        "a implementação",
    )
    inicio = prompt.find("<!-- IACHAT-CONFRONTO:INICIO -->")
    prosa = prompt.find("Formato: o que fazer")
    checa(
        "C10 prompt põe contrato antes da prosa",
        inicio >= 0 and prosa > inicio and "objetivo_id: m-confronto" in prompt
        and "claims:" in prompt,
    )


def prova_vermelho():
    """Remove o título de divergência numa cópia e exige que este gate reprove."""
    if os.environ.get("IACHAT_PULAR_ISCA"):
        return
    with tempfile.TemporaryDirectory(prefix="iachat-colher-isca-") as td:
        pasta = Path(td)
        cmd_isca = pasta / "iachat-comando"
        shutil.copy2(CMD, cmd_isca)
        shutil.copy2(CORE, pasta / "iachat_core.py")
        original = cmd_isca.read_text(encoding="utf-8")
        marcador = 'TITULO_DIVERGE = "**Divergem**"'
        mutilado = original.replace(
            marcador, 'TITULO_DIVERGE = "**Divergência escondida**"', 1
        )
        cmd_isca.write_text(mutilado, encoding="utf-8")
        mudou = mutilado != original
        env = os.environ.copy()
        env["IACHAT_CMD_UNDER_TEST"] = str(cmd_isca)
        env["IACHAT_PULAR_ISCA"] = "1"
        vermelho = subprocess.run(
            [sys.executable, str(Path(__file__).resolve())],
            env=env,
            capture_output=True,
            text=True,
        )
        checa(
            "T-RED isca remove divergência e o gate fica vermelho",
            mudou and vermelho.returncode != 0 and "FAIL C5" in vermelho.stdout,
            "arquivo_mudou={} rc={}".format(mudou, vermelho.returncode),
        )


def main():
    prova_funcional()
    prova_nao_comparavel()
    prova_prompt()
    prova_vermelho()
    if FALHAS:
        print("\nVERMELHO: {} falha(s): {}".format(len(FALHAS), ", ".join(FALHAS)))
        return 1
    print("\nVERDE: confronto explícito, compacto e fail-closed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
