#!/usr/bin/env python3
"""teste_python_sistema.py — o produto tem que rodar no Python que JÁ VEM no Mac.

A promessa do projeto é "zero dependência": quem clona não instala nada. Essa promessa
tem um nome concreto — **`/usr/bin/python3`, que no macOS é o 3.9** — e ninguém a testava.

Por que isso escapa com facilidade: esta máquina tem Python 3.14 no `PATH`, e a bateria
inteira roda nele. Um `match`, um `X | Y` fora de anotação, um `tomllib`, um
`itertools.batched` passariam despercebidos aqui e quebrariam na primeira máquina que só
tem o Python do sistema — que é a maioria dos Macs.

O `lancador.py` do app deixa isso explícito: ele procura o interpretador em ordem e
declara que `/usr/bin/python3` "roda o lançador sem reclamar, porque o repo inteiro é
stdlib pura". Este teste é o que sustenta essa frase.

Se o Python do sistema não existir (Linux, CI), o teste se declara **não aplicável** em
vez de inventar um verde — o terceiro desfecho vale mais que um sucesso falso.
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
APP = RAIZ.parent / "ia-chat-app"
PY_SISTEMA = Path("/usr/bin/python3")

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


print("teste_python_sistema")

if not PY_SISTEMA.is_file():
    print(f"  ⊘ {PY_SISTEMA} não existe — teste não aplicável neste sistema")
    sys.exit(0)

versao = subprocess.run([str(PY_SISTEMA), "--version"], capture_output=True,
                        text=True).stdout.strip() or "?"
print(f"  ({versao}, contra o {sys.version.split()[0]} que roda a bateria)")

# ── 1. compila? ─────────────────────────────────────────────────────────────
# Sintaxe é o primeiro filtro e o mais barato. `match`, `X | Y` fora de anotação e
# f-string aninhada de 3.12 morrem aqui.
alvos = [RAIZ / "bin" / "iachat", RAIZ / "bin" / "iachat_core.py"]
alvos += sorted(RAIZ.glob("bin/iachat-*"))
if APP.is_dir():
    alvos += [APP / "ui" / "servir.py",
              APP / "ia-chat.app" / "Contents" / "Resources" / "servidor.py",
              APP / "ia-chat.app" / "Contents" / "Resources" / "lancador.py"]
else:
    # DIZER que cobriu menos. Sem isto o teste ficava 5 ✔ / 0 ✗ com o repo irmão
    # ausente — o mesmo verde de quando cobre tudo. Todo instrumento tem três
    # desfechos (bom · ruim · não-consegui-olhar) e fundir o terceiro nos outros é
    # onde mora a mentira: alguém lê "5 ✔" e conclui que o app foi conferido no 3.9.
    #
    # Descoberto ao escrever o aviso do CI sobre o irmão ausente: afirmei que os
    # gates se declaravam ⊘, fui provar escondendo o repo, e eles passaram calados.
    print(f"  ⊘ {APP} ausente — os 3 arquivos do app NÃO foram conferidos nesta rodada")

quebrados = []
for f in alvos:
    if not f.is_file():
        continue
    # só arquivos Python: os CLIs do repo misturam .py e shell
    if f.suffix != ".py" and f.read_bytes()[:2] != b"#!" :
        continue
    if f.suffix != ".py" and b"python" not in f.read_bytes()[:80]:
        continue
    r = subprocess.run([str(PY_SISTEMA), "-m", "py_compile", str(f)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        quebrados.append(f"{f.name}: {r.stderr.strip().splitlines()[-1][:70]}")

checa(f"tudo compila no Python do sistema ({len(alvos)} arquivos)", not quebrados,
      "\n      ".join(quebrados))

# ── 2. roda? ────────────────────────────────────────────────────────────────
# Compilar não é rodar: um `import` que só existe no 3.11 passa na compilação e explode
# na primeira execução.
home = Path(tempfile.mkdtemp(prefix="py39-"))
env = dict(os.environ, IACHAT_HOME=str(home / "sala"))

for cmd, espera in (
    (["status"], "teto"),
    (["post", "--de", "claude", "--para", "codex", "mensagem no Python do sistema"], "postada"),
    (["read", "--de", "codex"], "mensagem"),
):
    r = subprocess.run([str(PY_SISTEMA), str(RAIZ / "bin" / "iachat"), *cmd],
                       env=env, capture_output=True, text=True, timeout=60)
    saida = r.stdout + r.stderr
    checa(f"`iachat {cmd[0]}` roda", r.returncode == 0 and espera in saida,
          f"exit={r.returncode} · {saida.strip()[:120]}")

# ── 3. o ciclo fecha ────────────────────────────────────────────────────────
# O gate real: a mensagem postada pelo Python do sistema é legível de volta por ele.
chat = home / "sala" / "iachat.md"
checa("a mensagem foi para o disco", chat.is_file() and
      "Python do sistema" in chat.read_text(errors="replace"))

shutil.rmtree(home, ignore_errors=True)
print(f"\n{_ok} ✔  {_falhou} ✗")
sys.exit(1 if _falhou else 0)
