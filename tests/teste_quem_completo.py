#!/usr/bin/env python3
"""teste_quem_completo.py — `/quem` mostra QUEM ESTÁ TRABALHANDO, não quem mora na sala.

`/quem` existe para uma pergunta só: quem está vivo, fazendo o quê, há quanto tempo.
Ele percorria `na_sala` — e vários braços da frota planejam sem morar na sala (`qwen`,
`grok`, `agy`, `qwclaude`). Um worker despachado para um deles ficava **invisível no
comando cuja única função é dizer quem está vivo.**

Medido em 18/08, na missão m2: `qwen` rodando com pid 34029 e ausente da listagem. O
dano não é cosmético — quem olha um painel que esconde metade da frota conclui que ela
morreu e redispara em cima de trabalho vivo, que é como se perde o que já estava pronto.

O teste força o cenário: um worker de braço que NÃO está em `na_sala`.
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
CMD = RAIZ / "bin" / "iachat-comando"
CLI = RAIZ / "bin" / "iachat"

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


def roda(env, prog, *args):
    return subprocess.run([sys.executable, str(prog), *args], env=env,
                          capture_output=True, text=True,
                          stdin=subprocess.DEVNULL, timeout=60)


print("teste_quem_completo")

home = Path(tempfile.mkdtemp(prefix="quem-")) / "sala"
env = dict(os.environ, IACHAT_HOME=str(home))
roda(env, CLI, "status")
roda(env, CMD, "goal", "objetivo qualquer", "--de", "claude", "--calado")

cfg = json.loads((home / "config.json").read_text(encoding="utf-8"))
na_sala = cfg.get("na_sala", [])
checa("cenário: `qwen` NÃO está em na_sala", "qwen" not in na_sala, f"na_sala={na_sala}")

# Worker de braço de fora, com o processo deste teste como pid — vivo de verdade, para
# o `confere_dono` ter o que conferir. Um pid inventado seria classificado como morto e
# o teste mediria outra coisa.
est = home / "comando" / "estado.json"
e = json.loads(est.read_text(encoding="utf-8"))
plano = Path(e["dir"]) / "planos" / "qwen.md"
plano.parent.mkdir(parents=True, exist_ok=True)
eu = os.getpid()
lstart = subprocess.run(["ps", "-o", "lstart=", "-p", str(eu)],
                        capture_output=True, text=True).stdout.strip()
e["workers"] = {"qwen": {"plano": str(plano), "estado": "rodando", "pid": eu,
                         "lstart": lstart, "papel": "o custo e o risco",
                         "prompt": str(Path(e["dir"]) / "logs" / "qwen.prompt.txt"),
                         "braco": "qwen"}}
est.write_text(json.dumps(e, ensure_ascii=False, indent=2), encoding="utf-8")

r = roda(env, CMD, "quem")
saida = r.stdout + r.stderr

checa("`quem` roda", r.returncode == 0, f"exit={r.returncode} · {saida[:150]}")
checa("o worker de FORA da sala aparece", "qwen" in saida,
      f"a frota some do painel que existe para mostrá-la:\n      {saida.strip()[:300]}")
# Não checo o PAPEL: ele só é impresso quando `confere_dono` dá o worker por vivo, e
# isso exige pid + lstart + o caminho do prompt na linha de comando do processo. Forjar
# isso pediria subir um processo de verdade só para ler uma coluna. O que este gate
# protege é a VISIBILIDADE — que era o defeito. Medir menos e medir certo vale mais que
# um caso frágil que quebra por motivo alheio ao que ele deveria vigiar.
checa("aparece classificado, não em branco",
      any(m in saida for m in ("🟢", "🔴", "✅", "⚪")), saida.strip()[:250])
checa("quem está na sala continua aparecendo",
      all(x in saida for x in na_sala if x), f"na_sala={na_sala} · {saida.strip()[:200]}")
# Sem duplicar: quem está na sala E é worker aparece uma vez só.
checa("ninguém aparece duas vezes", saida.count("qwen ") <= 2, saida.strip()[:250])

shutil.rmtree(home.parent, ignore_errors=True)
print(f"\n{_ok} ✔  {_falhou} ✗")
sys.exit(1 if _falhou else 0)
