#!/usr/bin/env python3
"""teste_duas_janelas.py — "nada para você" tem duas causas, e a diferença importa.

O DEFEITO, reproduzido pelo enxame em 18/08: o cursor de leitura é por IA, não por
sessão. Se o dono tem duas janelas do Claude abertas e alguém chama `@claude`, a
**primeira que lê consome a mensagem da outra**. A segunda janela recebe vazio,
idêntico a "ninguém te chamou", e nunca fica sabendo que foi chamada.

A CORREÇÃO ESCOLHIDA, e por que não foi a recomendada. O worker que diagnosticou
recomendou cursor por sessão — e formulou, ele mesmo, o contra-argumento que a derruba:
para o dono, duas janelas do Claude são o mesmo Claude, e multiplicar o estado por
sessão cria um isolamento que não existe no modelo mental dele. Além disso mexeria no
núcleo, onde um erro já apagou a sala inteira uma vez.

O dano real não é o estado compartilhado — é o consumo ser **silencioso**. Então o
conserto é tornar o consumo VISÍVEL, e custa uma linha de saída em vez de uma reforma
de núcleo.
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


def roda(h: Path, *a: str) -> str:
    r = subprocess.run([sys.executable, str(BIN), *a],
                       env=dict(os.environ, IACHAT_HOME=str(h)),
                       capture_output=True, text=True, timeout=40)
    return (r.stdout + r.stderr).strip()


print("teste_duas_janelas")

h = Path(tempfile.mkdtemp(prefix="duasjanelas-"))
for d in ("pendente", "cursor", "arquivo"):
    (h / d).mkdir()
(h / "config.json").write_text(json.dumps({"na_sala": ["claude", "codex"],
                                           "brain": "claude"}))
(h / "iachat.md").write_text("")

roda(h, "post", "--de", "codex", "--para", "claude", "mensagem dirigida ao claude")

janela1 = roda(h, "read", "--de", "claude")
checa("janela 1 recebe a mensagem", "📬" in janela1, janela1[:120])

janela2 = roda(h, "read", "--de", "claude")
checa("janela 2 recebe vazio (o defeito, que continua existindo)",
      "📬" not in janela2, janela2[:120])
checa("mas janela 2 SABE que foi outra sessão",
      "outra sessão" in janela2 and "há" in janela2,
      f"a segunda janela não distingue 'ninguém me chamou' de 'minha outra janela leu':"
      f"\n      {janela2[:160]}")

# O aviso é para leitura RECENTE. Uma sala parada há horas não deve sugerir que a
# mensagem foi roubada por outra janela — isso seria ruído, e ruído mata o aviso.
antigo = json.loads((h / "cursor" / "claude.json").read_text())
antigo["em"] = "2020-01-01T10:00:00-03:00"
(h / "cursor" / "claude.json").write_text(json.dumps(antigo))
velho = roda(h, "read", "--de", "claude")
checa("leitura ANTIGA não acusa outra sessão (senão vira ruído)",
      "outra sessão" not in velho, velho[:140])

shutil.rmtree(h, ignore_errors=True)
print(f"\n{_ok} ✔  {_falhou} ✗")
sys.exit(1 if _falhou else 0)
