#!/usr/bin/env python3
"""teste_erro_ensina.py — mensagem de erro que ensina um caminho que NÃO funciona é pior
que mensagem nenhuma.

O primeiro erro que um usuário novo encontra é sempre o mesmo: instala, abre o app,
tenta enviar, e o núcleo recusa porque ele não está em `na_sala`. Essa é literalmente a
primeira frase que o produto dirige a alguém que acabou de chegar.

Ela dizia: *"Adicione em /caminho/config.json antes de postar."*

Dois problemas. Mandava editar JSON à mão — pior que abrir o terminal, e o app se vende
como "sem terminal". E ignorava que existe `iachat entrar`, um subcomando criado
exatamente para isso. O produto tinha a resposta e apontava para o beco.

Achado da auditoria de pré-publicação (severidade IMPORTANTE), confirmado subindo o app
com um papel fora da sala e lendo o JSON que voltou.

Este gate não testa a redação: testa que **o caminho ensinado leva a algum lugar**.
Roda o fluxo inteiro do usuário novo — tropeça, lê, obedece, consegue.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
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


def roda(env: dict, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(CLI), *args], env=env,
                          capture_output=True, text=True,
                          stdin=subprocess.DEVNULL, timeout=60)


print("teste_erro_ensina")

home = Path(tempfile.mkdtemp(prefix="ensina-")) / "sala"
env = dict(os.environ, IACHAT_HOME=str(home))
roda(env, "status")

# ── 1. o tropeço ────────────────────────────────────────────────────────────
r = roda(env, "post", "--de", "visitante", "--para", "claude", "oi")
erro = r.stdout + r.stderr
checa("postar de fora da sala é recusado", r.returncode != 0, f"exit={r.returncode}")

# ── 2. a mensagem ensina um COMANDO, não um arquivo ─────────────────────────
# O teste que pega a regressão real: se alguém voltar a mandar editar config.json, isto
# fica vermelho. `.json` na mensagem é o cheiro exato do defeito antigo.
checa("a mensagem ensina um comando", "iachat entrar" in erro, erro.strip()[:200])
checa("a mensagem NÃO manda editar JSON à mão", ".json" not in erro.lower(),
      f"voltou a apontar para arquivo de configuração:\n      {erro.strip()[:200]}")

# ── 3. o comando ensinado EXISTE e roda ─────────────────────────────────────
# Extraído da própria mensagem, não digitado aqui: se o texto ensinar um comando
# diferente amanhã, é o novo que é testado. Um gate que testa o comando que ELE lembra,
# em vez do que a mensagem DIZ, valida a si mesmo.
m = re.search(r"iachat entrar (\S+)", erro)
checa("dá para extrair o comando da mensagem", m is not None, erro.strip()[:150])

if m:
    r2 = roda(env, "entrar", m.group(1))
    checa("o comando ensinado roda", r2.returncode in (0, 1),
          f"exit={r2.returncode} · {(r2.stdout + r2.stderr).strip()[:150]}")
    # exit 1 é legítimo: entrou, mas não recebe sozinho. O que não pode é exit 2 (erro).

    # ── 4. e resolve o problema original ────────────────────────────────────
    r3 = roda(env, "post", "--de", m.group(1), "--para", "claude", "oi de novo")
    checa("depois de obedecer, o post PASSA", r3.returncode == 0,
          f"exit={r3.returncode} · {(r3.stdout + r3.stderr).strip()[:150]}")
    chat = home / "iachat.md"
    checa("a mensagem chegou ao disco",
          chat.is_file() and "oi de novo" in chat.read_text(encoding="utf-8"))

    # ── 5. o comando avisa da consequência ──────────────────────────────────
    # Entrar muda quem o `@all` chama, e pode-se entrar sem receber. Um comando que faz
    # isso calado entrega metade e parece inteiro.
    saida2 = r2.stdout + r2.stderr
    checa("o comando avisa que `@all` muda", "@all" in saida2, saida2.strip()[:150])

shutil.rmtree(home.parent, ignore_errors=True)
print(f"\n{_ok} ✔  {_falhou} ✗")
sys.exit(1 if _falhou else 0)
