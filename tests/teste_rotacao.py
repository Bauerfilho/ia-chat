#!/usr/bin/env python3
"""Gates 6, 7 e 9: rotação, idempotência e o gate de CUSTO da busca.

O gate 9 é o que decide se a fase 5 vale: guardar histórico é fácil, o difícil é
consultá-lo sem pagar o arquivo inteiro. Se a busca custasse o documento todo, o
recorte só teria movido o problema de lugar.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bin"))

falhas: list[str] = []


def checa(nome: str, cond: bool, det: str = "") -> None:
    print(f"{'✔' if cond else '✗'} {nome}" + (f"  → {det}" if det else ""))
    if not cond:
        falhas.append(nome)


def main() -> int:
    base = Path(tempfile.mkdtemp(prefix="iachat-rot-"))
    os.environ["IACHAT_HOME"] = str(base)
    import iachat_core as core

    try:
        core.garantir_estrutura()
        TETO = 20480  # teto pequeno para o teste encher rápido
        core.p_config().write_text(
            json.dumps({"na_sala": ["claude", "codex", "kimi"], "brain": "claude", "teto_bytes": TETO})
            + "\n"
        )

        # ---- G6: encher além do teto ----------------------------------------
        r = core.rotate()
        checa("G6 rotação não roda abaixo do teto", not r["rodou"], r.get("motivo", ""))

        recheio = "conteúdo de teste com palavra-agulha às vezes. " * 12
        for i in range(1, 121):
            marca = "AGULHA-RARA" if i in (3, 27) else "comum"   # 2 agulhas, longe uma da outra
            core.post(
                ["claude", "codex", "kimi"][i % 3],
                f"Mensagem {i:02d} · {marca}\n\n{recheio}\n\nfim {i:02d}",
                ["@all"],
            )
        antes = len(core.p_chat().read_bytes())
        checa("G6 chat passou do teto antes de rotacionar", antes > TETO, f"{antes} B > {TETO} B")

        r = core.rotate()
        depois = len(core.p_chat().read_bytes())
        recortes = list((base / "arquivo").glob("*.md"))
        ativo = core.p_chat().read_text(encoding="utf-8")

        checa("G6 rotação rodou e criou recorte", r["rodou"] and len(recortes) == 1, str(r.get("recorte")))
        checa("G6 ativo voltou a caber no teto", depois <= TETO, f"{antes} B → {depois} B")
        checa(
            "G6 a MARCA ficou no ativo (senão o histórico some do radar)",
            "📦 **Recorte 01**" in ativo and "arquivo/" in ativo,
        )
        faixa = r["faixa"]
        checa(
            "G6 marca declara a faixa certa de mensagens",
            f"msgs #{faixa[0]}–#{faixa[1]}" in ativo,
            f"#{faixa[0]}–#{faixa[1]}",
        )
        cortadas = core.parse((base / "arquivo" / r["recorte"]).read_text(encoding="utf-8"))
        restantes = core.parse(ativo)
        checa(
            "G6 nenhuma mensagem se perdeu no corte",
            len(cortadas) + len(restantes) == 120,
            f"{len(cortadas)} arquivadas + {len(restantes)} no ativo",
        )
        checa(
            "G6 corta de CIMA (as mais antigas vão para o recorte)",
            cortadas[0]["n"] == 1 and restantes[-1]["n"] == 120,
        )

        # ---- G7: idempotência -----------------------------------------------
        r2 = core.rotate()
        checa(
            "G7 segunda rotação não faz nada e diz por quê",
            not r2["rodou"] and len(list((base / "arquivo").glob("*.md"))) == 1,
            r2.get("motivo", ""),
        )

        # ---- G9: o gate de custo --------------------------------------------
        nome = Path(r["recorte"]).stem
        bytes_fonte = len((base / "arquivo" / r["recorte"]).read_bytes())
        b = core.buscar("AGULHA-RARA")
        checa("G9 busca acha as duas agulhas", len(b["achados"]) == 2, str([a["n"] for a in b["achados"]]))

        pg = core.paginar(nome, b["achados"][0]["pagina"])
        custo = len(pg["texto"].encode())
        # Dois critérios, e os dois valem. O RELATIVO só é exigível num arquivo com
        # páginas suficientes (num recorte de 4 páginas, uma página é 25% por
        # construção — o critério mediria o tamanho do teste, não o desenho). Por isso
        # este teste enche até a escala real do plano (recorte ≥40 KB). O ABSOLUTO vale
        # sempre, e é o que garante que uma página nunca estoure a janela de ninguém.
        checa(
            "G9 recorte chegou à escala real (≥40 KB, ≥10 páginas)",
            bytes_fonte >= 40960 and pg["total"] >= 10,
            f"{bytes_fonte} B em {pg['total']} páginas",
        )
        checa(
            "G9-relativo: a resposta cabe em ≤10% do arquivo",
            custo <= bytes_fonte * 0.10,
            f"{custo} B de {bytes_fonte} B = {100*custo/bytes_fonte:.1f}%",
        )
        checa(
            "G9-absoluto: uma página cabe em ~1.200 tokens (≤5 KB)",
            custo <= 5120,
            f"{custo} B ≈ {custo//4} tokens",
        )
        checa(
            "G9 a página devolvida CONTÉM a agulha",
            "AGULHA-RARA" in pg["texto"],
            f"página {pg['pagina']}/{pg['total']}",
        )

        # estabilidade: paginar 2× o mesmo recorte dá os mesmos limites
        a1 = core.paginar(nome, 2)
        a2 = core.paginar(nome, 2)
        checa(
            "G9 paginação estável (recorte é imutável)",
            a1["linhas"] == a2["linhas"] and a1["texto"] == a2["texto"],
            f"linhas {a1['linhas']}",
        )
        checa(
            "G9 página vizinha é outra fatia, não o documento",
            core.paginar(nome, 3)["texto"] != a1["texto"],
        )
        checa(
            "G9 pedir página além do fim devolve a última, não erro",
            core.paginar(nome, 9999)["pagina"] == a1["total"],
        )

        # busca por metadado
        bm = core.buscar("", de="codex")
        checa(
            "G9 busca por remetente sai de graça (--de)",
            bm["achados"] and all(x["de"] == "codex" for x in bm["achados"]),
            f"{len(bm['achados'])} do codex",
        )

        print()
        print("✅ GATES 6, 7 e 9 PASSARAM" if not falhas else f"❌ REPROVOU: {falhas}")
        return 0 if not falhas else 1
    finally:
        shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
