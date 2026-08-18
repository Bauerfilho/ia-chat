#!/usr/bin/env python3
"""Bateria do ia-guard. Duas provas que valem juntas e não separadas:

G-A  CALIBRAÇÃO — as 16 mensagens REAIS de ~/ia-chat-global/iachat.md. Nenhuma
     mensagem que funcionou pode levar achado VERIFICADO (P1). Se levar, a régua
     está errada, não a mensagem.
G-B  CONTROLE NEGATIVO — 7 mensagens sintéticas, uma por defeito que a régua
     promete pegar. Se alguma passar, a régua é decoração.

Sem G-B, G-A é satisfeita por um `return "OK"`. Rode as duas.

    python3 teste_ia_guard.py [caminho/do/iachat.md]
"""
from __future__ import annotations

import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ia_guard  # noqa: E402

CHAT_PADRAO = Path.home() / "ia-chat-global" / "iachat.md"
# A bateria fatia o chat com o próprio regex em vez de importar `iachat_core`.
# Motivo medido: em 17/08 22:15 o núcleo do repositório parou de importar
# (`TETO_PADRAO` usado na linha 42 e definido na 52 → NameError), e isso derrubaria
# uma bateria que não tem nada a ver com aquele defeito. O
# metadado é contrato estável do formato (`bin/iachat_core.py:30-31`); o módulo não.
RE_META = re.compile(r"^<!-- iachat msg=(\d+) de=(\S+) para=(\S*) ts=(\S+) -->$", re.M)

# As 5 que são ping de instrumento, não mensagem — apuradas lendo a sala. Elas não
# são exceção da régua (passam limpas de qualquer jeito): estão aqui só para o
# relatório separar "mensagem boa" de "encanamento".
PINGS = {3, 10, 11, 12, 16}

NEGATIVOS = {
    "N1 caminho digitado de memória":
        ("Arrumei o bug. O patch está em "
         "/Users/bauervieiracesarfilhovieira/Projetos/ia-chat/bin/iachat_bell.py.", "V1"),
    "N2 linha que não existe no arquivo":
        ("O teto está em /Users/bauervieiracesarfilhovieira/Projetos/ia-chat/"
         "bin/iachat_core.py:9999 — muda lá.", "V2"),
    "N3 referência a mensagem inexistente":
        ("Como combinamos na #4242, deixei o daemon parado.", "V3"),
    "N4 deixis sem antecedente":
        ("Resolvi aquele problema do daemon; se voltar é só repetir.", "L1"),
    "N5 aferição sem medida":
        ("Testei e está tudo certo do meu lado, pode seguir.", "L2"),
    "N6 pedido sem o comando":
        ("Preciso de você: instale o hook aí na sua casca e me avisa.", "L3"),
    "N7 defeito acumulado":
        ("Preciso que você conserte aquele bug. O arquivo é /Users/bauervieira"
         "cesarfilhovieira/Projetos/ia-chat/bin/nao_existe.py e vale o que eu "
         "disse na #9999.", "V1"),
}
POSITIVO = (
    "Fechei a fase 5. Prova: `python3 /Users/bauervieiracesarfilhovieira/Projetos/"
    "ia-chat/tests/teste_rotacao.py` → 3 gates verdes; o recorte saiu em "
    "/Users/bauervieiracesarfilhovieira/ia-chat-global/arquivo/ e a função é "
    "`bin/iachat_core.py:427`. Confere do teu lado com `iachat status`."
)


def corpos(chat: Path):
    """Devolve (n, de, corpo) por mensagem. Corpo = sem o metadado e sem o título."""
    texto = chat.read_text(encoding="utf-8")
    achados = list(RE_META.finditer(texto))
    for i, m in enumerate(achados):
        fim = achados[i + 1].start() if i + 1 < len(achados) else len(texto)
        bruto = texto[m.start():fim].rstrip()
        yield int(m.group(1)), m.group(2), "\n".join(bruto.split("\n")[3:]).strip()


def main() -> int:
    chat = Path(sys.argv[1]) if len(sys.argv) > 1 else CHAT_PADRAO
    falhas = 0

    print("G-A · CALIBRAÇÃO nas 16 mensagens reais")
    if not chat.is_file():
        print(f"  ✗ sala não encontrada: {chat}")
        return 1
    msgs = list(corpos(chat))
    ultima = max(n for n, _, _ in msgs)
    for n, de, c in msgs:
        r = ia_guard.avaliar(c, ultima_msg=ultima)
        tag = "ping" if n in PINGS else "msg "
        ach = "; ".join(f"{a['id']}({a['trecho'][:24]})" for a in r["achados"])
        if r["pior"] == "P1":
            falhas += 1
            print(f"  ✗ #{n:>2} {tag} P1 — {ach}   ← RÉGUA ERRADA")
        else:
            print(f"  ✔ #{n:>2} {tag} {de:<7} {r['metricas']['bytes']:>5} B · "
                  f"{r['metricas']['densidade']:>5}/KB · {r['pior']:<3} {ach}")

    print("\nG-B · CONTROLE NEGATIVO (a régua tem que PEGAR)")
    for nome, (txt, esperado) in NEGATIVOS.items():
        r = ia_guard.avaliar(txt, ultima_msg=16)
        ids = [a["id"] for a in r["achados"]]
        ok = esperado in ids
        falhas += 0 if ok else 1
        print(f"  {'✔' if ok else '✗'} {nome:<34} esperava {esperado} · veio {ids or '[]'}")
    r = ia_guard.avaliar(POSITIVO, ultima_msg=16)
    ok = not r["achados"]
    falhas += 0 if ok else 1
    print(f"  {'✔' if ok else '✗'} {'P0 controle positivo (tem que passar)':<34} "
          f"veio {[a['id'] for a in r['achados']] or '[]'}")

    print(f"\n{'✅ BATERIA PASSOU' if not falhas else f'❌ {falhas} FALHA(S)'}")
    return 0 if not falhas else 1


if __name__ == "__main__":
    raise SystemExit(main())
