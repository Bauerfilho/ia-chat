#!/usr/bin/env python3
"""teste_fronteira_sala.py — a bateria não pode tocar na sala do dono.

POR QUE ESTE TESTE EXISTE, com data e dano: em 18/08, um worker implementando uma peça
precisava de "chat pré-existente com histórico" para testar. Em vez de montar um
`IACHAT_HOME` temporário, ele usou a **sala real** — e deixou lá duas mensagens de
fixture ("Mensagem #1 antiga na sala pré-existente", "#2 antiga…"), assinadas como se
fossem conversa de verdade, entre trabalho real do dono.

Nenhum dos 20 testes pegou, porque cada um só olhava a própria peça. Este olha o que
todos eles fazem JUNTOS, do lado de fora: roda a bateria inteira e compara a sala antes
e depois, byte a byte.

É meta-teste de propósito. A pergunta que ele responde não é "a peça X funciona?" — é
**"a bateria é segura de rodar na máquina do dono?"**. Um repositório cujos testes sujam
a produção é um repositório que ninguém pode rodar sem medo, e medo é o oposto de um
projeto que se quer publicar.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
EU = Path(__file__).name

_ok = 0
_falhou = 0


def checa(nome: str, condicao: bool, detalhe: str = "") -> None:
    global _ok, _falhou
    if condicao:
        _ok += 1
        print(f"  ✔ {nome}")
    else:
        _falhou += 1
        print(f"  ✗ {nome}" + (f"\n      {detalhe}" if detalhe else ""))


def sala_real() -> Path:
    return Path(os.environ.get("IACHAT_HOME", Path.home() / "ia-chat-global"))


def impressao(d: Path) -> dict[str, str]:
    """Hash de tudo que uma bateria descuidada poderia sujar.

    Inclui o `.estado.json` e os flags de `pendente/`: um teste que apenas *lê* já pode
    queimar cursor e apagar chamado — dano invisível que não aparece no `iachat.md`.
    """
    alvos = ["iachat.md", "config.json", ".estado.json"]
    fp: dict[str, str] = {}
    for nome in alvos:
        f = d / nome
        fp[nome] = hashlib.sha256(f.read_bytes()).hexdigest() if f.is_file() else "(ausente)"
    for sub in ("pendente", "cursor"):
        p = d / sub
        fp[sub] = ",".join(sorted(
            f"{x.name}:{hashlib.sha256(x.read_bytes()).hexdigest()[:12]}"
            for x in p.glob("*") if x.is_file()
        )) if p.is_dir() else "(ausente)"
    return fp


print("teste_fronteira_sala")

sala = sala_real()
if not sala.is_dir():
    print(f"  ⊘ sem sala em {sala} — nada a proteger neste ambiente")
    sys.exit(0)

antes = impressao(sala)
outros = sorted(p for p in (RAIZ / "tests").glob("teste_*.py") if p.name != EU)
print(f"  rodando {len(outros)} testes contra a sala viva em {sala}")

quebrados: list[str] = []
for t in outros:
    try:
        # Sem IACHAT_HOME no ambiente: é exatamente assim que o dono roda a bateria, e é
        # nessa configuração que o descuido aparece. Forçar um temporário aqui esconderia
        # o defeito — seria o gate consertando o problema antes de medi-lo.
        subprocess.run([sys.executable, str(t)], capture_output=True, timeout=120)
    except subprocess.TimeoutExpired:
        quebrados.append(f"{t.name} (timeout)")

depois = impressao(sala)

sujos = [k for k in antes if antes[k] != depois[k]]
checa(
    "a bateria inteira NÃO tocou na sala do dono",
    not sujos,
    "mudou: " + ", ".join(sujos) +
    "\n      algum teste está usando a sala real em vez de um IACHAT_HOME temporário."
    "\n      Todo caso que precise de 'chat pré-existente' monta o próprio, com mkdtemp"
    "\n      + fixture — nunca a sala viva.",
)
checa("nenhum teste travou", not quebrados, ", ".join(quebrados))

# ── nenhuma quebra deliberada ficou para trás ────────────────────────────────
# Auditar um gate direito exige QUEBRAR o código e ver o teste ficar vermelho — é o
# protocolo, e é o certo. O risco é a quebra sobreviver ao fim da auditoria: em 18/08 uma
# auditora desarmou o gate de quarentena do `iachat-plan` para prová-lo (`if false;` no
# lugar do `if ! diff -q`) e desfez logo depois, como o contrato mandava. Mas se ela
# tivesse morrido no meio — e três workers morreram naquela mesma noite —, o gate ficaria
# desarmado dentro de um repositório prestes a ser publicado, e nada acusaria.
#
# Este caso é a rede: qualquer marcador de quebra que chegue ao commit reprova a bateria.
marcadores = ("QUEBRA-AUDITORIA", "QUEBRA-TESTE", "DESFAZER-ANTES-DE-COMMITAR")
sujos_quebra: list[str] = []
for p in RAIZ.rglob("*"):
    if not p.is_file() or ".git/" in str(p) or p.suffix not in (".py", ".sh", ".md", ""):
        continue
    try:
        texto = p.read_text(errors="replace")
    except OSError:
        continue
    # O próprio arquivo cita os marcadores para documentá-los; ele não conta.
    if p.name == EU:
        continue
    for n, linha in enumerate(texto.splitlines(), 1):
        if any(m in linha for m in marcadores):
            sujos_quebra.append(f"{p.relative_to(RAIZ)}:{n}")

checa(
    "nenhuma quebra deliberada de auditoria ficou no repositório",
    not sujos_quebra,
    ", ".join(sujos_quebra) +
    "\n      alguém quebrou o código para testar um gate e não desfez. "
    "O gate está DESARMADO.",
)

print(f"\n{_ok} ✔  {_falhou} ✗")
sys.exit(1 if _falhou else 0)
