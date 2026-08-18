#!/usr/bin/env python3
"""Bateria do iachat-relay — a mensagem nominada não fica parada para sempre.

Cada ramo de decisão do relay, provado numa sala limpa em /tmp (IACHAT_HOME desviado;
nada toca a sala real). Inclui o caso que REPROVA de propósito: ledger corrompido —
o `run` não pode morrer nem inventar repasse por causa disso.

Duas expectativas da proposta (auditorias/.../propostas-casa/ia-relay/teste_relay.py)
foram corrigidas aqui, ambas pela MESMA causa raiz medida agora: **autor puro nunca
avança cursor** — `post` não avança o autor (iachat_core.py:325-329) e `ler` só avança
destinatário (iachat_core.py:389-397).
  1. Proposta G6 "cala quando está tudo declarado": com sala completa e tabela
     completa, os cursores 0 de quem só postou deixam a varredura NÃO-ociosa e o
     cache de varredura registra achados vazios — o teste da proposta falharia no
     `av == []` só se os avisos mudassem; aqui o gate é direto: avisos == [] com a
     tabela completa, e 3 avisos com a tabela furada.
  2. Proposta G8 "sala toda em dia = varredura ociosa": `core.ler("claude")` de quem
     só postou NÃO avança o cursor, então a sala nunca fica "em dia" por esse caminho.
     O gate aqui usa `marca_lida` para simular leitura real de todos.
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BIN = RAIZ / "bin"
RELAY = BIN / "iachat-relay"
H = Path(tempfile.mkdtemp(prefix="iachat-relay-teste-"))
os.environ["IACHAT_HOME"] = str(H)
sys.path.insert(0, str(BIN))

loader = importlib.machinery.SourceFileLoader("iachat_relay", str(RELAY))
spec = importlib.util.spec_from_loader("iachat_relay", loader)
relay = importlib.util.module_from_spec(spec)
loader.exec_module(relay)
core = relay.core

FALHAS = 0


def checa(nome: str, condicao: bool, detalhe: str = "") -> None:
    global FALHAS
    if condicao:
        print(f"  ✔ {nome}" + (f"  → {detalhe}" if detalhe else ""))
    else:
        FALHAS += 1
        print(f"  ✗ {nome}" + (f"  → {detalhe}" if detalhe else ""))


def daqui(min_: int) -> datetime:
    return datetime.now().astimezone() + timedelta(minutes=min_)


def envelhece(min_: int) -> None:
    """Reescreve o `ts=` das mensagens na cópia de teste, para o `run` (que usa o
    relógio real) enxergar idade. Necessário só nos gates que exercem a CLI."""
    import re
    velho = (datetime.now().astimezone() - timedelta(minutes=min_)).isoformat(timespec="seconds")
    texto = core.p_chat().read_text()
    texto = re.sub(r"ts=\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+\-]\d{2}:\d{2}", f"ts={velho}", texto)
    core.p_chat().write_text(texto)


def sala_limpa(relay_extra: dict | None = None) -> None:
    """Sala nova em /tmp; reset do cache de config do relay (ele lê 1×/processo)."""
    shutil.rmtree(H, ignore_errors=True)
    H.mkdir(parents=True)
    core.garantir_estrutura()
    cfg = json.loads(core.p_config().read_text())
    cfg["na_sala"] = ["claude", "codex", "kimi"]
    relay_cfg = {
        "prazo_min": 15,
        "vocacao": {"claude": "cerebro", "codex": "codigo", "kimi": "construcao"},
        "irmas": {"codigo": ["codex", "qwen", "kimi"], "construcao": ["kimi", "grok", "codex"],
                  "cerebro": ["claude"]},
    }
    if relay_extra:
        relay_cfg.update(relay_extra)
    cfg["relay"] = relay_cfg
    core.p_config().write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n")
    relay._CFG = None


print("\n[G1] dentro do prazo → NÃO repassa; fora, vence e aponta irmã")
sala_limpa()
core.post("claude", "@codex roda o teste de rotacao e me diz o exit code")
a = relay.varrer(agora=daqui(14))["achados"][0]
checa("14 min não vence", a["vence"] is False, f"(idade {a['idade_min']} min)")
a = relay.varrer(agora=daqui(16))["achados"][0]
checa("16 min vence", a["vence"] is True, f"(idade {a['idade_min']} min)")
checa("irmã declarada na fila é @kimi", a.get("irma") == "kimi", f"(fila codigo: codex,qwen,kimi; qwen fora da sala)")

print("\n[G2] IA viva (postou depois da nominação) → NÃO repassa, mesmo vencida")
sala_limpa()
core.post("claude", "@codex roda o teste de rotacao")
core.post("codex", "estou no meio de outra coisa, ja volto")   # posta sem ler
checa("cursor do codex continua 0 (post não avança autor)", core.cursor("codex") == 0)
a = relay.varrer(agora=daqui(90))["achados"][0]
checa("90 min sem leitura + postou = viva, não vence",
      a["vence"] is False and a["viva"] is True)

print("\n[G3] vencida com irmã → repassa uma vez só, sem loop")
sala_limpa()
core.post("claude", "@codex roda o teste de rotacao e me diz o exit code")
a = relay.varrer(agora=daqui(20))["achados"][0]
r1 = relay.repassar(a)
msgs = core.parse(core.p_chat().read_text())
rep = [m for m in msgs if m["n"] == r1["n"]][0]
checa("repasse nomina a irmã", "kimi" in rep["para"], f"para={rep['para']}")
checa("repasse nomina a original também", "codex" in rep["para"])
checa("repasse é postado em nome do remetente", rep["de"] == "claude")
checa("sino da irmã tocou", core.p_pendente("kimi").exists())
seg = relay.varrer(agora=daqui(40))
checa("2ª passada não repassa de novo", not any(x["vence"] for x in seg["achados"]),
      str([(x["n"], x["ia"], x["vence"]) for x in seg["achados"]]))
checa("o repasse NÃO volta em loop para quem estava mudo",
      all(not (x["ia"] == "codex" and x["vence"]) for x in seg["achados"]))
tarde = [x for x in relay.varrer(agora=daqui(31))["achados"] if x["ia"] == "kimi"][0]
checa("irmã muda além de 2× o prazo vira chamado ao operador", tarde["irma_muda"] is True)

print("\n[G4] a original acorda depois → vê o repasse ANTES de trabalhar")
lido = core.ler("codex", escopo="meu", avancar=False)
ns = [m["n"] for m in lido["msgs"]]
checa("recebe o pedido e o repasse na mesma leitura", ns == [1, 2], f"msgs={ns}")
checa("o repasse diz para não refazer", "não refaça" in lido["msgs"][-1]["bruto"])

print("\n[G5] sem irmã declarada → fail-closed, não inventa destino")
sala_limpa(relay_extra={"vocacao": {}, "irmas": {}})
core.post("claude", "@codex roda o teste")
a = relay.varrer(agora=daqui(20))["achados"][0]
checa("vence mas sem irmã", a["vence"] is True and a.get("irma") is None,
      f"({a['sem_irma']})")
antes = len(core.parse(core.p_chat().read_text()))
checa("sem_destino notificou", relay.sem_destino(a) is True)
checa("não postou nada na sala", len(core.parse(core.p_chat().read_text())) == antes)
checa("registrou no ledger", "1" in relay.ledger().get("sem_destino", {}))
checa("cooldown: não re-notifica na mesma hora", relay.sem_destino(a) is False)

print("\n[G6] a tabela reclama sozinha (anti-configuração morta)")
sala_limpa(relay_extra={
    "vocacao": {"claude": "cerebro"},
    "irmas": {"codigo": ["codex", "qwen", "kimi"], "construcao": ["kimi", "grok", "codex"],
              "cerebro": ["claude"], "visual": ["agy"]},
})
av = relay.varrer()["avisos"]
checa("acusa IA sem vocação (codex e kimi)",
      any("codex" in x for x in av) and any("kimi" in x for x in av), f"({len(av)} aviso(s))")
checa("acusa fila inteira fora da sala (visual→agy)", any("visual" in x for x in av))
sala_limpa()
core.post("claude", "@codex teste")
av = relay.varrer()["avisos"]
checa("cala quando está tudo declarado", av == [], f"avisos={av}")
sala_limpa(relay_extra={
    "vocacao": {"claude": "cerebro", "codex": "construção", "kimi": "construcao"},
    "irmas": {"construcao": ["kimi", "codex"], "cerebro": ["claude"]},
})
core.post("claude", "@codex teste")
a = relay.varrer(agora=daqui(20))["achados"][0]
checa("vocação com acento casa com a fila sem acento", a.get("irma") == "kimi",
      f"(vocação 'construção' → fila 'construcao', irmã {a.get('irma')})")

print("\n[G7] mensagem grande → repasse por referência, não por cópia")
sala_limpa()
core.post("claude", "@codex " + ("linha de contexto que ninguem quer pagar duas vezes\n" * 60))
a = relay.varrer(agora=daqui(20))["achados"][0]
r = relay.repassar(a)
orig = [m for m in core.parse(core.p_chat().read_text()) if m["n"] == 1][0]
novo = [m for m in core.parse(core.p_chat().read_text()) if m["n"] == r["n"]][0]
b_o, b_n = len(orig["bruto"].encode()), len(novo["bruto"].encode())
checa("repasse menor que o original", b_n < b_o, f"({b_n} B vs {b_o} B, {100-100*b_n//b_o}% menor)")
checa("repasse leva ponteiro para a íntegra", "iachat search" in novo["bruto"])

print("\n[G8] nominação já lida → não é silêncio; sala em dia = ocioso")
sala_limpa()
core.post("claude", "@codex teste")
core.ler("codex")
r = relay.varrer(agora=daqui(60))
checa("60 min depois de lida, nada a repassar", r["achados"] == [], f"achados={r['achados']}")
checa("correção da proposta: cursor 0 de autor puro deixa a varredura acordada",
      relay.varrer(agora=daqui(60))["ocioso"] is False,
      "(claude/kimi só postaram — post não avança autor, iachat_core.py:325-329)")
for ia in ("claude", "codex", "kimi"):
    core.marca_lida(ia, 1)   # simula leitura real de todos
r = relay.varrer(agora=daqui(60))
checa("todos com cursor em dia = varredura ociosa, chat intocado",
      r["ocioso"] is True and r["lido_bytes"] == 0)

print("\n[G9] REPROVA de propósito: ledger corrompido não derruba o run nem inventa repasse")
sala_limpa()
core.post("claude", "@codex teste")
envelhece(30)
relay.p_ledger().write_text("{ isto não é json")
antes = len(core.parse(core.p_chat().read_text()))
p = subprocess.run([sys.executable, str(RELAY), "run"], capture_output=True, text=True,
                   env={**os.environ, "IACHAT_HOME": str(H)})
checa("run com ledger corrompido sai 0", p.returncode == 0, f"(stderr: {p.stderr.strip()[:80]})")
depois = len(core.parse(core.p_chat().read_text()))
checa("repasse aconteceu UMA vez apesar do ledger zerado (sem crash)", depois == antes + 1,
      f"({antes} → {depois} msgs)")
p2 = subprocess.run([sys.executable, str(RELAY), "run"], capture_output=True, text=True,
                    env={**os.environ, "IACHAT_HOME": str(H)})
checa("run de novo não repassa duas vezes",
      len(core.parse(core.p_chat().read_text())) == depois, f"(exit {p2.returncode})")
p3 = subprocess.run([sys.executable, str(RELAY), "check"], capture_output=True, text=True,
                    env={**os.environ, "IACHAT_HOME": str(H)})
checa("check é read-only e sai 0", p3.returncode == 0 and
      len(core.parse(core.p_chat().read_text())) == depois)

print(f"\n{'='*54}\n  {FALHAS} falharam\n{'='*54}")
sys.exit(1 if FALHAS else 0)
