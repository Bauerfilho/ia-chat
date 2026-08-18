#!/usr/bin/env python3
"""teste_nada_inalcancavel.py — código depois de `sys.exit()` no topo nunca roda.

`teste_onboard.py` tinha 54 linhas — 17% do arquivo — depois de
`if __name__ == "__main__": sys.exit(main())`. Uma função de teste completa, com três
provas do onboarding pelo hook, e a chamada dela. **Nada disso jamais executou.**

O arquivo ficava verde, e o verde parecia cobrir o que aquelas linhas prometiam.

Havia uma segunda camada: o bloco terminava com `print(f"{_ok} ✔ {_falhou} ✗")` e
`sys.exit(1 if _falhou else 0)` — nomes de OUTRO arquivo de teste (aqui a contagem
chama-se `falhas`). Tinha sido colado de lá e emendado no fim. Ou seja, mesmo se
alguém tivesse movido o bloco para um lugar alcançável, ele explodiria com NameError.
**A inalcançabilidade era o que escondia o defeito.** Código morto esconde código
quebrado — e quanto mais tempo passa, mais ele parece confiável só por estar ali.

Movidas para dentro do `main()`, as três provas rodam e passam. Eram boas; estavam no
lugar errado.

Este gate varre a bateria inteira: nenhum arquivo pode ter código executável depois do
`sys.exit(...)` de topo. Achado do worker `codex` na missão m2.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
TESTES = sorted((RAIZ / "tests").glob("teste_*.py"))

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


def apos_saida(caminho: Path) -> list[str]:
    """Nós de topo depois do `if __name__ == "__main__"`.

    Pelo AST, não por regex: `sys.exit` dentro de função ou de string não encerra nada,
    e um grep os confundiria.

    ⚠️ Só conta o `if __name__ == "__main__"`. A primeira versão deste gate marcava
    QUALQUER `sys.exit()` de topo como fim do módulo — e acusou três arquivos que usam
    GUARDA ANTECIPADA: `sys.exit(0)` logo no começo quando o cenário não se aplica (o
    Python do sistema não existe, o bundle não foi montado), com o teste seguindo
    normalmente depois. Isso é o terceiro desfecho da casa — "não consegui olhar" — e é
    padrão correto, não defeito.

    Um gate que grita no lugar errado é pior que gate nenhum: ensina a ignorá-lo, e aí
    ele não serve nem quando acerta.
    """
    try:
        arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    except SyntaxError as e:
        return [f"não compila: {e}"]

    def encerra(no: ast.AST) -> bool:
        if not isinstance(no, ast.If):
            return False
        t = no.test
        if not (isinstance(t, ast.Compare) and isinstance(t.left, ast.Name)
                and t.left.id == "__name__"):
            return False
        return any(isinstance(c, ast.Constant) and c.value == "__main__"
                   for c in t.comparators)

    sobra: list[str] = []
    saiu = False
    for no in arvore.body:
        if saiu:
            # Docstring/constante solta não executa nada — não é o defeito que se caça.
            if isinstance(no, ast.Expr) and isinstance(no.value, ast.Constant):
                continue
            nome = getattr(no, "name", type(no).__name__)
            sobra.append(f"linha {no.lineno}: {nome}")
        elif encerra(no):
            saiu = True
    return sobra


print("teste_nada_inalcancavel")
print(f"  ({len(TESTES)} arquivos na bateria)")

sujos: list[str] = []
for t in TESTES:
    if t.name == Path(__file__).name:
        continue
    for item in apos_saida(t):
        sujos.append(f"{t.name} · {item}")

checa("nenhum código depois do `sys.exit()` de topo", not sujos,
      "\n      ".join(sujos) + "\n      Código ali NUNCA roda, e o verde do arquivo "
      "parece cobrir o que ele promete.")

# O gate tem que enxergar o defeito, senão é enfeite. Um arquivo sintético com o
# mesmo formato do que existia de verdade.
import tempfile

with tempfile.TemporaryDirectory() as d:
    isca = Path(d) / "teste_isca.py"
    isca.write_text(
        "import sys\n"
        "def main():\n    return 0\n"
        'if __name__ == "__main__":\n    sys.exit(main())\n'
        "def orfa():\n    return 1\n"
        "orfa()\n", encoding="utf-8")
    achou = apos_saida(isca)
    checa("o detector vê o defeito quando ele existe", len(achou) >= 2,
          f"achou {achou} — deveria pegar a def e a chamada")

# E não pode acusar quem está certo.
with tempfile.TemporaryDirectory() as d:
    limpo = Path(d) / "teste_limpo.py"
    limpo.write_text(
        "import sys\n"
        "def aux():\n    sys.exit(2)\n"          # sys.exit DENTRO de função não encerra
        "def main():\n    return 0\n"
        'if __name__ == "__main__":\n    sys.exit(main())\n', encoding="utf-8")
    checa("não acusa `sys.exit` dentro de função", not apos_saida(limpo),
          f"falso positivo: {apos_saida(limpo)}")

# GUARDA ANTECIPADA: `sys.exit(0)` no começo quando o cenário não se aplica, e o teste
# seguindo depois. É o terceiro desfecho da casa — "não consegui olhar" — e três
# arquivos reais da bateria usam. A primeira versão deste gate acusou os três; o caso
# fica aqui para o falso positivo não voltar por descuido de quem editar o detector.
with tempfile.TemporaryDirectory() as d:
    guarda = Path(d) / "teste_guarda.py"
    guarda.write_text(
        "import sys\nfrom pathlib import Path\n"
        'if not Path("/nao/existe").is_file():\n'
        '    print("  ⊘ não aplicável")\n    sys.exit(0)\n'
        'print("o teste de verdade roda aqui")\n'
        "sys.exit(0)\n", encoding="utf-8")
    checa("não acusa guarda antecipada (o ⊘ legítimo)", not apos_saida(guarda),
          f"falso positivo: {apos_saida(guarda)} — o padrão ⊘ da casa seria marcado "
          f"como código morto, e o gate viraria ruído")

print(f"\n{_ok} ✔  {_falhou} ✗")
sys.exit(1 if _falhou else 0)
