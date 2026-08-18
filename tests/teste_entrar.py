#!/usr/bin/env python3
"""teste_entrar.py — pôr uma IA na sala não é o mesmo que ela passar a receber.

POR QUE EXISTE. Entrar na sala era editar `config.json` à mão, e o config aceitava
qualquer nome — dava para inscrever uma casca que a infraestrutura desconhece, **sem
aviso nenhum**. O resultado era um membro fantasma: quem o nominasse ficaria esperando
resposta que nunca vem, sem nada indicando o porquê. Lacuna levantada pelo enxame em
18/08, com prova executável.

O comando `iachat entrar` inscreve E confere a infra, e o código de saída carrega a
diferença: **0 = entrou e recebe · 1 = entrou mas NÃO recebe sozinha.** Um comando que
devolvesse 0 nos dois casos seria pior que o JSON à mão, porque acrescentaria confiança.
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


def checa(nome: str, condicao: bool, detalhe: str = "") -> None:
    global _ok, _falhou
    if condicao:
        _ok += 1
        print(f"  ✔ {nome}")
    else:
        _falhou += 1
        print(f"  ✗ {nome}" + (f"\n      {detalhe}" if detalhe else ""))


def sala() -> Path:
    h = Path(tempfile.mkdtemp(prefix="entrar-"))
    for d in ("pendente", "cursor", "arquivo"):
        (h / d).mkdir()
    (h / "config.json").write_text(json.dumps({"na_sala": ["claude", "codex"],
                                               "brain": "claude"}))
    (h / "iachat.md").write_text("")
    return h


def roda(h: Path, *args: str) -> tuple[int, str]:
    r = subprocess.run([sys.executable, str(BIN), *args],
                       env=dict(os.environ, IACHAT_HOME=str(h)),
                       capture_output=True, text=True, timeout=40)
    return r.returncode, r.stdout + r.stderr


print("teste_entrar")

h = sala()

# 1. entrar de fato altera o config
rc, out = roda(h, "entrar", "qwen")
cfg = json.loads((h / "config.json").read_text())
checa("entrar inscreve a IA no config", "qwen" in cfg["na_sala"], str(cfg["na_sala"]))
checa("entrar avisa que `@all` passa a incluí-la", "@all" in out,
      "entrar na sala muda quem o @all chama — quem não é avisado disso é surpreendido")

# 2. o código de saída DISTINGUE 'entrou' de 'entrou e recebe' — o ponto da peça
checa("código de saída distingue pronta (0) de incompleta (1)", rc in (0, 1),
      f"rc={rc}")
if rc == 1:
    checa("quando incompleta, DIZ o que falta e como resolver",
          "falta" in out.lower() and ("install" in out or "rode:" in out),
          "avisar sem dizer o comando deixa o operador no mesmo lugar")
else:
    checa("quando completa, afirma que ela recebe", "recebe" in out.lower())

# 3. o caso que REPROVA: casca que a infraestrutura não conhece
rc2, out2 = roda(h, "entrar", "casca-que-nao-existe")
checa("casca desconhecida NÃO entra silenciosa", rc2 == 1,
      f"rc={rc2} — inscrever sem infra e devolver sucesso cria membro fantasma")
checa("e o aviso nomeia o problema", "hook" in out2.lower() or "sino" in out2.lower())

# 4. idempotência: entrar duas vezes não duplica
roda(h, "entrar", "qwen")
cfg2 = json.loads((h / "config.json").read_text())
checa("entrar duas vezes não duplica o nome",
      cfg2["na_sala"].count("qwen") == 1, str(cfg2["na_sala"]))

# 5. sair remove do config e NÃO apaga história
rc3, out3 = roda(h, "entrar", "qwen", "--sair")
cfg3 = json.loads((h / "config.json").read_text())
checa("sair remove da sala", "qwen" not in cfg3["na_sala"], str(cfg3["na_sala"]))
checa("sair declara que o histórico fica", "histórico" in out3.lower(),
      "saída que parece apagar mensagem antiga assusta — e não é o que acontece")

# 6. sair de quem não está reprova
rc4, _ = roda(h, "entrar", "ninguem", "--sair")
checa("sair de quem não está na sala reprova", rc4 == 2, f"rc={rc4}")

shutil.rmtree(h, ignore_errors=True)
print(f"\n{_ok} ✔  {_falhou} ✗")
sys.exit(1 if _falhou else 0)
