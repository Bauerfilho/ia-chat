#!/usr/bin/env python3
"""teste_fluxo_completo.py — o produto inteiro, de ponta a ponta, uma vez.

POR QUE ESTE TESTE EXISTE. A bateria tem 24 arquivos e cada um prova **uma peça**. Isso
pega defeito dentro da peça e não pega defeito na **junta** — e é na junta que o produto
vive: alguém posta, o sino toca, o hook entrega dentro da sessão, o flag some, o outro
responde, o cursor anda, a rotação arquiva sem perder ninguém.

Já aconteceu de todas as peças passarem e o conjunto não funcionar: em 17/08, uma
alteração no `RE_META` passou nos 10 gates da época e **apagou 100% da sala real** —
porque nenhum teste lia um chat que já existia.

Este teste faz UMA passada pelo ciclo inteiro, na ordem em que um dia real acontece, com
`IACHAT_HOME` temporário. Não substitui nenhum dos outros: é o que só se enxerga de cima.
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
BIN = Path.home() / ".local" / "bin"
IACHAT = BIN / "iachat" if (BIN / "iachat").is_file() else RAIZ / "bin" / "iachat"
HOOK = RAIZ / "bin" / "ia-bell-hook.sh"

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


h = Path(tempfile.mkdtemp(prefix="fluxo-"))
for d in ("pendente", "cursor", "arquivo"):
    (h / d).mkdir()
(h / "config.json").write_text(json.dumps(
    {"na_sala": ["claude", "codex", "kimi"], "brain": "claude",
     "teto_bytes": 4096, "notificar_operador": False}))
(h / "iachat.md").write_text("")
ENV = dict(os.environ, IACHAT_HOME=str(h), IACHAT_BIN=str(BIN))


def cli(*a: str) -> str:
    r = subprocess.run([sys.executable, str(IACHAT), *a], env=ENV,
                       capture_output=True, text=True, timeout=40)
    return r.stdout + r.stderr


def hook(ia: str) -> str:
    r = subprocess.run(["bash", str(HOOK)], env={**ENV, "IACHAT_EU": ia},
                       capture_output=True, text=True, timeout=40)
    return r.stdout


print("teste_fluxo_completo")

# ── 1. o codex fala com o kimi. o claude NÃO é chamado ───────────────────────
cli("post", "--de", "codex", "--para", "kimi",
    "kimi, o parser quebra em UTF-8 de 3 bytes — vale conferir antes de você seguir")
checa("o flag do destinatário nasce", (h / "pendente" / "kimi.md").is_file())
checa("quem NÃO foi chamado não é incomodado", not (h / "pendente" / "claude.md").is_file(),
      "o claude ganhou flag sem ter sido nominado — é o defeito que o produto existe para evitar")

# ── 2. o hook entrega DENTRO da sessão do kimi, sem ele pedir ────────────────
entregue = hook("kimi")
checa("o hook entrega a mensagem no evento da IA", "UTF-8 de 3 bytes" in entregue,
      f"o hook devolveu {len(entregue.encode())} B e não trouxe o corpo")
checa("e o flag é consumido pela entrega", not (h / "pendente" / "kimi.md").is_file())

# ── 3. o hook do não-chamado: uma vez fala, depois cala ─────────────────────
# Duas coisas convivem aqui, e o teste tem que distinguir as duas — foi este caso que
# pegou a interação entre elas:
#   · o claude nunca esteve na sala, então a PRIMEIRA passada entrega o briefing de
#     onboarding (senão a IA nova fica invisível: ninguém a nomina antes de saber que
#     ela chegou);
#   · a partir daí, sem flag, o hook é MUDO — é o que permite pendurá-lo em todo evento
#     sem custo. Hook que fala sem motivo é o que faz a IA desligar o mecanismo.
primeira = hook("claude")
checa("IA nunca vista recebe o briefing de onboarding", len(primeira.encode()) > 200,
      f"saíram {len(primeira.encode())} B — a IA nova continua invisível para a entrega")
checa("e a partir da segunda passada, sem flag, o hook é MUDO", hook("claude") == "",
      "o onboarding não se auto-extinguiu: repetir o briefing a cada evento é pior que o defeito")

# ── 4. o kimi responde, e agora é o codex que tem recado ─────────────────────
cli("post", "--de", "kimi", "--para", "codex",
    "confirmado, era decode faltando antes do slice. corrigido e com teste.")
checa("a resposta cria flag para o autor original", (h / "pendente" / "codex.md").is_file())
resp = hook("codex")
checa("o autor recebe a resposta dentro da sessão dele", "decode faltando" in resp)

# ── 5. leitura dirigida: o claude não paga pela conversa alheia ──────────────
visao = cli("read", "--de", "claude")
checa("conversa entre terceiros fica OCULTA para quem não foi chamado",
      "UTF-8 de 3 bytes" not in visao and "decode faltando" not in visao,
      "o claude enxergou conversa que não era dele — a leitura dirigida é o coração do produto")

# ── 6. a rotação arquiva sem perder ninguém ─────────────────────────────────
# Teto de 4 KB forjado no config: enche a sala e força o corte de verdade.
for i in range(24):
    cli("post", "--de", "claude", "--para", "codex", f"mensagem de volume {i} " + "x" * 150)
antes_total = json.loads((h / ".estado.json").read_text())["ultima"]
cli("rotate")
recortes = list((h / "arquivo").glob("*.md"))
checa("a rotação criou recorte", bool(recortes), "o teto de 4 KB não disparou o corte")

ativas = (h / "iachat.md").read_text().count("<!-- iachat msg=")
arquivadas = sum(r.read_text().count("<!-- iachat msg=") for r in recortes)
checa("NADA se perde: arquivadas + ativas = total postado",
      ativas + arquivadas == antes_total,
      f"{ativas} ativas + {arquivadas} arquivadas ≠ {antes_total} postadas")
checa("a marca do recorte fica no topo do ativo (o passado não some do radar)",
      "Recorte" in (h / "iachat.md").read_text()[:1500])

# ── 7. depois da rotação, o número da mensagem continua achável ──────────────
achou = cli("search", "UTF-8 de 3 bytes")
checa("a busca acha mensagem que já foi arquivada", "#1" in achou or "recorte" in achou.lower(),
      f"depois de arquivar, a mensagem #1 sumiu do alcance:\n      {achou[:200]}")

shutil.rmtree(h, ignore_errors=True)
print(f"\n{_ok} ✔  {_falhou} ✗")
sys.exit(1 if _falhou else 0)
