#!/usr/bin/env python3
"""teste_corpo_util.py — mensagem que só tem pontuação toca o sino por nada.

DE ONDE VEIO ESTE TESTE, e vale registrar: não fui eu que achei, nem outro teste. Foi
**outra IA lendo a sala pelo próprio produto**.

Em 18/08, a Kimi foi acionada para ler o ia-chat e responder pela própria sala. Ela leu o
histórico, entendeu o estado do projeto, e reparou numa coisa que eu não tinha visto:

> *"a #27 saiu para o codex com corpo literal `...` — mensagem vazia tocou o sino dele e
> queimou contexto da frota à toa. Eu faria o `iachat post` falhar fechado em corpo vazio
> ou só-espaços: sem corpo, sem post."*

Ela estava certa na substância. O gate de corpo vazio **já existia** e barrava `""` e
`"   "` — mas `...` passava, e fui **eu** que postei aquilo.

O custo de uma mensagem inútil não é o byte: é a **atenção de quem foi nominado**. Numa
ferramenta cujo propósito é não interromper quem não precisa ser interrompido, interromper
alguém com três pontos é o defeito mais contrário ao produto que existe.

O critério NÃO pode ser tamanho — `ok` tem dois caracteres e é resposta legítima. É ter
**algo além de pontuação**: pelo menos uma letra ou um dígito.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BIN = Path.home() / ".local" / "bin" / "iachat"
if not BIN.is_file():
    BIN = Path(__file__).resolve().parent.parent / "bin" / "iachat"

_ok = 0
_falhou = 0


def checa(nome: str, cond: bool, detalhe: str = "") -> None:
    global _ok, _falhou
    if cond:
        _ok += 1
        print(f"  ✔ {nome}")
    else:
        _falhou += 1
        print(f"  ✗ {nome}" + (f"\n      {detalhe}" if detalhe else ""))


print("teste_corpo_util")

h = Path(tempfile.mkdtemp(prefix="corpo-"))
for d in ("pendente", "cursor", "arquivo"):
    (h / d).mkdir()
(h / "config.json").write_text(json.dumps({"na_sala": ["claude", "codex"],
                                           "brain": "claude"}))
(h / "iachat.md").write_text("")
env = dict(os.environ, IACHAT_HOME=str(h))

CASOS = [
    ("...", True, "o caso real: três pontos interromperam o Codex"),
    ("---", True, ""),
    ("???", True, ""),
    ("!!", True, ""),
    ("   ", True, "só espaço — já era barrado antes"),
    ("ok", False, "duas letras, resposta legítima: o critério não é tamanho"),
    ("sim", False, ""),
    ("#42", False, "dígito conta como conteúdo"),
    ("👍 feito", False, "emoji + palavra"),
]

for corpo, deve_reprovar, nota in CASOS:
    r = subprocess.run([sys.executable, str(BIN), "post", "--de", "claude",
                        "--para", "codex", corpo],
                       env=env, capture_output=True, text=True, timeout=30, input="")
    reprovou = r.returncode != 0
    rotulo = f"{corpo!r} {'REPROVA' if deve_reprovar else 'passa'}"
    if nota:
        rotulo += f"  ({nota})"
    checa(rotulo, reprovou == deve_reprovar,
          f"exit={r.returncode} · "
          + ("passou e tocaria o sino por nada" if deve_reprovar
             else "bloqueou conteúdo legítimo"))

# O outro lado do gate: o que passou tem que ter chegado mesmo.
achou = subprocess.run([sys.executable, str(BIN), "read", "--de", "codex"],
                       env=env, capture_output=True, text=True, timeout=30)
checa("o que passou foi realmente entregue", "ok" in achou.stdout,
      "as mensagens legítimas não chegaram ao destinatário")

shutil.rmtree(h, ignore_errors=True)
print(f"\n{_ok} ✔  {_falhou} ✗")
sys.exit(1 if _falhou else 0)
