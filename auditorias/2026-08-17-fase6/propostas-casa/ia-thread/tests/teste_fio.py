#!/usr/bin/env python3
"""Gates do ia-thread. Cada um existe por um risco medido, não por simetria.

  F1 compatibilidade  — o repo não muda: as 3 baterias já verdes continuam verdes,
                        e uma sala escrita ANTES do iafio é lida sem perda
  F2 ancoragem        — só a PRIMEIRA linha vincula (`↳ #7` no meio ou em crases
                        é exemplo, igual ao `@codex` em backticks de 17/08)
  F3 rotação          — fio partido entre recorte e ativo volta INTEIRO
  F4 custo            — ler o fio é mais barato que a única rota que hoje o monta
  F6 pós-rotação      — `read --tudo` perde a metade arquivada; o fio não
  F5 estado           — ABERTO/FECHADO é mecânico; órfão não derruba nada
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from importlib.machinery import SourceFileLoader
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
# IACHAT_BIN só é preciso enquanto o iafio mora fora do repo; instalado em
# `bin/` junto do iachat_core.py, o default já resolve.
sys.path.insert(0, os.environ.get("IACHAT_BIN", str(RAIZ / "bin")))

falhas: list[str] = []


def checa(nome: str, cond: bool, detalhe: str = "") -> None:
    print(f"{'✔' if cond else '✗'} {nome}" + (f"  → {detalhe}" if detalhe else ""))
    if not cond:
        falhas.append(nome)


def main() -> int:
    base = Path(tempfile.mkdtemp(prefix="iachat-fio-"))
    os.environ["IACHAT_HOME"] = str(base)
    import iachat_core as core

    iafio = SourceFileLoader("iafio", str(RAIZ / "bin" / "iafio")).load_module()

    core.garantir_estrutura()
    core.p_config().write_text(
        json.dumps({"na_sala": ["claude", "codex", "kimi"], "brain": "claude",
                    "teto_bytes": 8192}) + "\n"
    )

    # ---- F1: mensagem SEM marcador (o passado) é raiz, não erro ---------------
    core.post("claude", "Sala antiga, escrita antes do fio existir. @codex")
    core.post("codex", "Também antiga. @claude")
    f = iafio.fios(iafio.universo())
    checa("F1 sala escrita antes do iafio: cada msg vira raiz, nada se perde",
          sorted(f) == [1, 2], f"raízes={sorted(f)}")

    # ---- F2: ancoragem posicional -------------------------------------------
    core.post("claude", "↳ #1\n\nEsta responde a #1 de verdade. @codex")
    core.post("kimi", "Uso `↳ #1` na primeira linha.\n↳ #1 no meio é exemplo. @claude")
    f = iafio.fios(iafio.universo())
    checa("F2 marcador na 1ª linha vincula", 3 in f.get(1, []) or any(m["n"] == 3 for m in f.get(1, [])),
          f"fio #1 = {[m['n'] for m in f.get(1, [])]}")
    checa("F2 `↳ #1` em crase/no meio do corpo NÃO vincula (sem falso-positivo)",
          4 not in [m["n"] for m in f.get(1, [])],
          f"fio #1 = {[m['n'] for m in f.get(1, [])]}")

    # ---- F5: estado mecânico -------------------------------------------------
    est, bola = iafio.estado(f[1])
    checa("F5 fio cuja última nomina alguém = ABERTO, com a bola nomeada",
          est == "ABERTO" and bola == ["codex"], f"{est} bola={bola}")
    core.post("codex", "↳ #3 ✔\n\nResolvido, não preciso de mais nada.")
    f = iafio.fios(iafio.universo())
    est, bola = iafio.estado(f[1])
    checa("F5 `↳ #N ✔` fecha o fio", est == "FECHADO" and bola == [], f"{est} bola={bola}")

    core.post("kimi", "↳ #4096\n\nPai que nunca existiu. @claude")
    f = iafio.fios(iafio.universo())
    checa("F5 órfão (pai inexistente) vira raiz própria, não quebra o grafo",
          6 in f, f"raízes={sorted(f)}")

    # ---- F4: custo, com a sala ainda inteira (fio ≠ sala) --------------------
    for i in range(6):                       # um segundo assunto, para o fio não ser a sala
        core.post("kimi", f"outro assunto {i} " + "y" * 300 + " @claude")
    f = iafio.fios(iafio.universo())
    fio_b = sum(len(m["bruto"].encode()) for m in f[1])
    core.marca_lida("kimi", 0)
    tudo_b = core.ler("kimi", escopo="tudo", avancar=False)["bytes"]
    checa("F4 ler UM fio custa menos que `read --tudo`, a única rota que hoje o monta",
          fio_b < tudo_b, f"fio #1={fio_b} B · read --tudo={tudo_b} B "
                          f"({tudo_b/max(fio_b,1):.1f}x mais barato)")

    # ---- F3: rotação ---------------------------------------------------------
    for i in range(12):
        core.post("claude", "↳ #1\n\n" + f"engorda {i} " + "x" * 700 + " @codex")
    antes = [m["n"] for m in iafio.fios(iafio.universo())[1]]
    r = core.rotate()
    f = iafio.fios(iafio.universo())
    depois = [m["n"] for m in f[1]]
    fontes = {m["fonte"] for m in f[1]}
    checa("F3 a rotação de fato partiu o fio entre recorte e ativo",
          r["rodou"] and len(fontes) > 1, f"rodou={r['rodou']} fontes={sorted(fontes)}")
    checa("F3 fio partido volta INTEIRO num comando só (mesma lista de antes)",
          antes == depois, f"{len(antes)} antes → {len(depois)} depois")

    # ---- F6: o que a rotação tira do `read` — e o fio não perde --------------
    core.marca_lida("kimi", 0)
    visiveis = {m["n"] for m in core.ler("kimi", escopo="tudo", avancar=False)["msgs"]}
    perdidas = [n for n in depois if n not in visiveis]
    checa("F6 depois da rotação `read --tudo` já NÃO enxerga o fio inteiro",
          bool(perdidas), f"{len(perdidas)} msg(s) do fio ficaram fora do `read`: {perdidas[:6]}…")
    checa("F6 `iafio ler` continua enxergando as arquivadas (varre recorte+ativo, como o search)",
          all(n in depois for n in perdidas), f"fio tem {len(depois)}, read tem {len(visiveis)}")

    print()
    if falhas:
        print(f"❌ {len(falhas)} GATE(S) DE FIO FALHARAM: {falhas}")
        return 1
    print("✅ GATES DE FIO (F1-F6) PASSARAM")
    return 0


if __name__ == "__main__":
    sys.exit(main())
