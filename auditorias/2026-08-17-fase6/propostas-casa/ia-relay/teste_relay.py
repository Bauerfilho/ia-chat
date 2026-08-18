"""Bateria do ia-relay: cada ramo de decisão, provado numa sala limpa."""
import json, os, shutil, sys, importlib.util
from datetime import datetime, timedelta
from importlib.machinery import SourceFileLoader
from pathlib import Path

BIN = Path.home() / ".claude/iaswarm-runs/ia-chat-fase6/batch/ia-relay/bin"
H = Path("/private/tmp/claude-501/-Users-bauervieiracesarfilhovieira/2073ef4a-6581-4ab8-8472-bc3db3134e02/scratchpad/relay-teste")
os.environ["IACHAT_HOME"] = str(H)
sys.path.insert(0, str(BIN))

spec = importlib.util.spec_from_loader("relay", SourceFileLoader("relay", str(BIN / "iachat-relay")))
relay = importlib.util.module_from_spec(spec); spec.loader.exec_module(relay)
core = relay.core

OK = FALHOU = 0
def gate(nome, cond, detalhe=""):
    global OK, FALHOU
    if cond: OK += 1; print(f"  ✔ {nome} {detalhe}")
    else:    FALHOU += 1; print(f"  ✘ {nome} {detalhe}")

def sala_limpa(**relay_cfg):
    shutil.rmtree(H, ignore_errors=True)
    core.garantir_estrutura()
    cfg = json.loads(core.p_config().read_text())
    cfg["na_sala"] = ["claude", "codex", "kimi"]
    cfg["relay"] = {
        "prazo_min": 15,
        "vocacao": {"claude": "cerebro", "codex": "codigo", "kimi": "construcao"},
        "irmas": {"codigo": ["codex", "qwen", "kimi"], "construcao": ["kimi", "grok", "codex"],
                  "cerebro": ["claude"]},
        **relay_cfg,
    }
    core.p_config().write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n")
    relay._CFG = None

def daqui(min_): return datetime.now().astimezone() + timedelta(minutes=min_)

print("\n[G1] dentro do prazo → NÃO repassa")
sala_limpa()
core.post("claude", "@codex roda o teste de rotacao e me diz o exit code")
a = relay.varrer(agora=daqui(14))["achados"][0]
gate("14 min não vence", a["vence"] is False, f"(idade {a['idade_min']} min)")
a = relay.varrer(agora=daqui(16))["achados"][0]
gate("16 min vence", a["vence"] is True, f"(idade {a['idade_min']} min, irmã @{a['irma']})")

print("\n[G2] IA viva (postou depois) → NÃO repassa, mesmo vencida")
sala_limpa()
core.post("claude", "@codex roda o teste de rotacao")
core.post("codex", "estou no meio de outra coisa, ja volto")   # posta sem ler
gate("cursor do codex continua 0 (post não avança)", core.cursor("codex") == 0)
a = relay.varrer(agora=daqui(90))["achados"][0]
gate("90 min sem leitura + postou = viva, não vence", a["vence"] is False and a["viva"] is True)

print("\n[G3] vencida com irmã → repassa uma vez só")
sala_limpa()
core.post("claude", "@codex roda o teste de rotacao e me diz o exit code")
a = relay.varrer(agora=daqui(20))["achados"][0]
r1 = relay.repassar(a)
msgs = core.parse(core.p_chat().read_text())
rep = [m for m in msgs if m["n"] == r1["n"]][0]
gate("repasse nomina a irmã", "kimi" in rep["para"], f"para={rep['para']}")
gate("repasse nomina a original também", "codex" in rep["para"])
gate("repasse é postado em nome do remetente", rep["de"] == "claude")
gate("sino da irmã tocou", core.p_pendente("kimi").exists())
seg = relay.varrer(agora=daqui(40))
gate("2ª passada não repassa de novo", not any(x["vence"] for x in seg["achados"]),
     str([(x["n"], x["ia"], x["vence"]) for x in seg["achados"]]))
volta = [x for x in seg["achados"] if x["ia"] == "kimi"][0]
gate("o repasse NÃO volta em loop para quem estava mudo", volta["vence"] is False)
tarde = [x for x in relay.varrer(agora=daqui(31))["achados"] if x["ia"] == "kimi"][0]
gate("irmã muda além de 2× o prazo vira chamado ao operador", tarde["irma_muda"] is True)

print("\n[G4] a original acorda depois → vê o repasse ANTES de trabalhar")
lido = core.ler("codex", escopo="meu", avancar=False)
ns = [m["n"] for m in lido["msgs"]]
gate("recebe o pedido e o repasse na mesma leitura", ns == [1, 2], f"msgs={ns}")
gate("o repasse diz para não refazer", "não refaça" in lido["msgs"][-1]["bruto"])

print("\n[G5] sem irmã declarada → fail-closed, não inventa destino")
sala_limpa(vocacao={}, irmas={})
core.post("claude", "@codex roda o teste")
a = relay.varrer(agora=daqui(20))["achados"][0]
gate("vence mas sem irmã", a["vence"] is True and a["irma"] is None, f"({a['sem_irma']})")
antes = len(core.parse(core.p_chat().read_text()))
relay.sem_destino(a)
gate("não postou nada na sala", len(core.parse(core.p_chat().read_text())) == antes)
gate("registrou no ledger", "1" in relay.ledger().get("sem_destino", {}))

print("\n[G6] a tabela reclama sozinha (anti-configuração morta)")
sala_limpa(vocacao={"claude": "cerebro"})
av = relay.varrer()["avisos"]
gate("acusa IA sem vocação", any("codex" in x for x in av) and any("kimi" in x for x in av),
     f"({len(av)} aviso(s))")
sala_limpa()
core.post("claude", "@codex teste")
av = relay.varrer()["avisos"]
gate("cala quando está tudo declarado", av == [], f"avisos={av}")

print("\n[G7] mensagem grande → repassa por referência, não por cópia")
sala_limpa()
core.post("claude", "@codex " + ("linha de contexto que ninguem quer pagar duas vezes\n" * 60))
a = relay.varrer(agora=daqui(20))["achados"][0]
r = relay.repassar(a)
orig = [m for m in core.parse(core.p_chat().read_text()) if m["n"] == 1][0]
novo = [m for m in core.parse(core.p_chat().read_text()) if m["n"] == r["n"]][0]
b_o, b_n = len(orig["bruto"].encode()), len(novo["bruto"].encode())
gate("repasse menor que o original", b_n < b_o, f"({b_n} B vs {b_o} B, {100-100*b_n//b_o}% menor)")
gate("repasse leva ponteiro para a íntegra", "iachat search" in novo["bruto"])

print("\n[G8] nominação já lida → não é silêncio")
sala_limpa()
core.post("claude", "@codex teste")
core.ler("codex")
r = relay.varrer(agora=daqui(60))
gate("60 min depois de lida, nada a repassar", r["achados"] == [], f"achados={r['achados']}")
gate("basta UMA IA com cursor atrasado para a varredura acordar",
     relay.varrer()["ocioso"] is False, "(kimi nunca leu, mesmo sem nominação para ela)")
core.ler("claude"); core.ler("kimi")   # sala inteira em dia
r = relay.varrer(agora=daqui(60))
gate("sala toda em dia = varredura ociosa, chat intocado",
     r["ocioso"] is True and r["lido_bytes"] == 0)

print(f"\n{'='*54}\n  {OK} passaram · {FALHOU} falharam\n{'='*54}")
sys.exit(1 if FALHOU else 0)
