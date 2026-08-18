#!/usr/bin/env python3
"""Gate W1 do ia-chat: compatibilidade com histórico escrito por versão anterior.

Por que este gate existe (achado CRÍTICO da auditoria de 18/08): os outros três
testes criam sala nova com tempfile.mkdtemp e apagam no fim — nenhum lê um chat
escrito por uma versão anterior. Consequência provada: uma mudança no RE_META
passou nos 10 gates verdes e, apontada para a sala real, o parser enxergou
0 de 16 mensagens, com status.ultima = 0 — a próxima mensagem seria #1, colidindo
com a #1 existente e zerando todos os cursores. Teste verde que não detecta
destruição de histórico mente com autoridade.

A resposta é a fixture CONGELADA em tests/fixtures/sala-v1/: uma sala escrita à
mão, versionada no repo, que NUNCA é gerada pelo código na hora do teste. Se
fosse gerada, ela acompanharia a mudança e o gate voltaria a mentir — esse é o
ponto inteiro. O teste copia a fixture para um IACHAT_HOME temporário e trabalha
só na cópia; a fixture sai byte-a-byte igual (e o último gate confere isso).

Sub-gates:
  C1 o parser lê TODAS as mensagens da fixture (8/8, números 1..8)
  C2 _ultimo_numero() via .estado.json bate com o maior msg= do arquivo
  C3 _ultimo_numero() SEM .estado.json (fallback pela cauda) idem
  C4 post novo recebe maior+1, sem colisão com o histórico
  C5 cursor pré-existente é respeitado: read dirigido não redevolve o já lido
  C6 rotate sobre a fixture preserva a soma arquivadas+ativas
  C7 a fixture do repo saiu intocada (congelada de verdade)

Prova de fogo (obrigatória para qualquer gate): este arquivo aceita
IACHAT_BIN_DIR apontando para outro núcleo. Rodar
  IACHAT_BIN_DIR=/tmp/iachat-core-quebrado python3 tests/teste_compat.py
contra uma cópia do núcleo com o RE_META alterado TEM que reprovar. Um gate que
nunca viu vermelho não é gate.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "sala-v1"
# Por padrão o gate mira o núcleo real do repo; a prova de fogo mira uma cópia
# quebrada em /tmp. O default (sem env) é sempre o caminho honesto.
BIN_DIR = Path(os.environ.get("IACHAT_BIN_DIR", RAIZ / "bin"))
sys.path.insert(0, str(BIN_DIR))

ESPERADAS = 8  # mensagens da fixture sala-v1, congelada

falhas: list[str] = []


def checa(nome: str, condicao: bool, detalhe: str = "") -> None:
    print(f"{'✔' if condicao else '✗'} {nome}" + (f"  → {detalhe}" if detalhe else ""))
    if not condicao:
        falhas.append(nome)


def fotografa(pasta: Path) -> dict[str, bytes]:
    """Byte a byte de tudo na fixture — para provar no fim que nada a tocou."""
    return {
        str(p.relative_to(pasta)): p.read_bytes()
        for p in sorted(pasta.rglob("*"))
        if p.is_file()
    }


def main() -> int:
    antes = fotografa(FIXTURE)
    checa(
        "C0 fixture existe e tem as 4 peças (chat, config, cursores, estado)",
        {"iachat.md", "config.json", ".estado.json", "cursor/kimi.json"} <= set(antes),
        f"peças={sorted(antes)}",
    )

    base = Path(tempfile.mkdtemp(prefix="iachat-compat-"))
    os.environ["IACHAT_HOME"] = str(base)
    import iachat_core as core

    print(f"núcleo sob teste:  {core.__file__}")
    print(f"fixture congelada: {FIXTURE} ({len(antes['iachat.md'])} B de chat)")
    print(f"cópia de trabalho: {base}\n")

    try:
        shutil.copytree(FIXTURE, base, dirs_exist_ok=True)

        # ---- C1: o parser lê TODAS as mensagens do histórico -----------------
        texto = core.p_chat().read_text(encoding="utf-8")
        msgs = core.parse(texto)
        nums = [m["n"] for m in msgs]
        checa(
            "C1 parser lê TODAS as mensagens da sala antiga",
            len(msgs) == ESPERADAS and nums == list(range(1, ESPERADAS + 1)),
            f"leu {len(msgs)}/{ESPERADAS} nums={nums}",
        )
        st = core.status()
        checa(
            "C1 status.ultima enxerga o histórico (nunca 0)",
            st["mensagens"] == ESPERADAS and st["ultima"] == ESPERADAS,
            f"mensagens={st['mensagens']} ultima={st['ultima']}",
        )

        # ---- C2/C3: _ultimo_numero bate com o maior msg= do arquivo ----------
        maior = max(nums, default=0)
        checa(
            "C2 _ultimo_numero() via .estado.json == maior msg= da fixture",
            core._ultimo_numero() == maior,
            f"estado diz {core._ultimo_numero()} · maior msg= {maior}",
        )
        # Sem o .estado.json, o fallback pela cauda do chat tem que dar o mesmo —
        # foi ESTE caminho que enxergou 0/16 no incidente real.
        estado = core.p_estado()
        bak = base / ".estado.json.bak"
        estado.rename(bak)
        try:
            via_cauda = core._ultimo_numero()
        finally:
            bak.rename(estado)
        checa(
            "C3 _ultimo_numero() SEM .estado (fallback pela cauda) == maior msg=",
            via_cauda == maior and maior == ESPERADAS,
            f"cauda diz {via_cauda} · maior msg= {maior} — 0 aqui = próximo post colide com #1",
        )

        # ---- C5: cursor pré-existente é respeitado ---------------------------
        # Antes do post-sonda (que nominaria o kimi e poluiria a conta). Na
        # fixture, kimi leu até a #5. A #2 era dirigida a ele, mas já lida: não
        # pode voltar. Das não lidas (#6, #7, #8), só #6 e #8 o nominam.
        r1 = core.ler("kimi")
        checa(
            "C5 read dirigido NÃO redevolve o que já estava lido",
            bool(r1["msgs"]) and all(m["n"] > 5 for m in r1["msgs"]),
            f"veio={[m['n'] for m in r1['msgs']]} · cursor era 5 (#2 seria o sinal da quebra)",
        )
        checa(
            "C5 e entrega exatamente as novas dirigidas a ele (#6, #8)",
            [m["n"] for m in r1["msgs"]] == [6, 8] and r1["ocultas"] == 1,
            f"veio={[m['n'] for m in r1['msgs']]} ocultas={r1['ocultas']} (#7 é dos outros)",
        )
        checa(
            "C5 cursor avança só com o que foi entregue (5 → 8) e não redevolve",
            core.cursor("kimi") == 8 and core.ler("kimi")["msgs"] == [],
            f"cursor={core.cursor('kimi')}",
        )

        # ---- C4: post novo recebe maior+1, sem colisão -----------------------
        r = core.post("claude", "Post de sonda do gate de compatibilidade, @kimi.", ["kimi"])
        nums_depois = [m["n"] for m in core.parse(core.p_chat().read_text(encoding="utf-8"))]
        checa(
            "C4 post novo numera maior+1 (sem reiniciar em #1)",
            r["n"] == maior + 1,
            f"novo n={r['n']} · esperado {maior + 1}",
        )
        checa(
            "C4 nenhuma colisão: 1..N sem buraco nem duplicata",
            nums_depois == list(range(1, maior + 2)),
            f"nums={nums_depois}",
        )

        # ---- C6: rotate sobre a fixture preserva arquivadas+ativas -----------
        # Política apertada na CÓPIA (a fixture fica como estava): teto 2 KB
        # força a rotação de uma sala de ~3 KB.
        cfg = json.loads(core.p_config().read_text(encoding="utf-8"))
        cfg["teto_bytes"] = 2048
        core.p_config().write_text(json.dumps(cfg, ensure_ascii=False) + "\n")
        total_antes = len(core.parse(core.p_chat().read_text(encoding="utf-8")))
        rot = core.rotate()
        recortes = list((base / "arquivo").glob("iachat-*-recorte-*.md"))
        if rot["rodou"] and recortes:
            arquivadas = len(core.parse(recortes[0].read_text(encoding="utf-8")))
            ativas = len(core.parse(core.p_chat().read_text(encoding="utf-8")))
        else:
            arquivadas = ativas = -1
        checa(
            "C6 rotate roda sobre sala antiga e NÃO perde mensagem",
            rot["rodou"] and arquivadas + ativas == total_antes,
            f"rodou={rot['rodou']} · {arquivadas} arquivadas + {ativas} ativas = {total_antes}",
        )

        # ---- C7: a fixture saiu intocada -------------------------------------
        depois = fotografa(FIXTURE)
        checa(
            "C7 fixture do repo byte-a-byte igual (o gate não come a referência)",
            antes == depois,
            "" if antes == depois else f"diff em {set(antes.items()) ^ set(depois.items())}",
        )

        print()
        print("✅ GATE W1 (COMPATIBILIDADE) PASSOU" if not falhas else f"❌ REPROVOU: {falhas}")
        return 0 if not falhas else 1
    finally:
        shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
