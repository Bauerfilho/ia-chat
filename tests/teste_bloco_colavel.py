#!/usr/bin/env python3
"""teste_bloco_colavel.py — o que está num bloco ```bash tem que sobreviver ao copiar-e-colar.

Em **zsh interativo** — que é exatamente onde alguém cola um comando copiado de um
README — a opção `interactive_comments` vem DESLIGADA por padrão. Ou seja: `#` **não**
inicia comentário. O que vem depois dele é lido como mais argumentos, e se tiver
parêntese, colchete ou operador, vira sintaxe.

Medido em 18/08, colando a linha do próprio README:

    iachat rotate    # arquiva o excedente (idempotente)
    zsh: number expected

Três linhas do README quebravam assim. Outras dez passavam `#` e o texto como
ARGUMENTOS do comando — errado sem ser barulhento, que é pior de achar.

Detalhe que quase me fez descartar o achado: `zsh -f -c '<linha>'` **não** reproduz,
porque `-c` não é interativo. Só `zsh -f -i` alimentado por pipe mostra. Testar do jeito
cômodo, e não do jeito que o usuário faz, teria enterrado um defeito verdadeiro.

Este gate vale para os DOIS repositórios: o README do app é o primeiro que um estranho
lê. Achado pelo worker `k1`, seguindo o README como quem nunca viu o projeto.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DOCS = [RAIZ / "README.md", RAIZ / "CONTRIBUTING.md",
        RAIZ.parent / "ia-chat-app" / "README.md",
        RAIZ.parent / "ia-chat-app" / "CONTRIBUTING.md"]
# O que transforma "argumento a mais" em "sintaxe quebrada" no zsh.
PERIGOSOS = "()[]{}<>&|;"

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


def inline(doc: Path) -> list[tuple[str, bool]]:
    """Linhas de bloco ```bash com `#` no meio. bool = quebra a sintaxe."""
    if not doc.is_file():
        return []
    achadas = []
    for bloco in re.findall(r"```bash\n(.*?)```", doc.read_text(encoding="utf-8"), re.S):
        for ln in bloco.splitlines():
            s = ln.strip()
            if not s or s.startswith("#") or "#" not in s:
                continue
            # `#` dentro de aspas é conteúdo, não comentário — e não quebra nada.
            antes = s.split("#", 1)[0]
            if antes.count('"') % 2 or antes.count("'") % 2:
                continue
            depois = s.split("#", 1)[1]
            achadas.append((s, any(c in depois for c in PERIGOSOS)))
    return achadas


print("teste_bloco_colavel")

todas = []
for doc in DOCS:
    if not doc.is_file():
        print(f"  ⊘ {doc.name} de {doc.parent.name} ausente — NÃO conferido")
        continue
    for linha, quebra in inline(doc):
        todas.append((doc, linha, quebra))

quebram = [(d, l) for d, l, q in todas if q]
checa("nenhum comentário inline QUEBRA a sintaxe no zsh interativo", not quebram,
      "\n      ".join(f"{d.parent.name}/{d.name}: {l[:74]}" for d, l in quebram) +
      "\n      Em zsh interativo `#` não é comentário; parêntese vira sintaxe.")

ruido = [(d, l) for d, l, q in todas if not q]
checa("nenhum comentário inline vira ARGUMENTO do comando", not ruido,
      "\n      ".join(f"{d.parent.name}/{d.name}: {l[:74]}" for d, l in ruido) +
      "\n      Não quebra, mas o `#` e o texto entram como argumentos. Use tabela, ou "
      "ponha a explicação FORA do bloco.")

# O detector tem que ver vermelho — senão é enfeite.
import tempfile

with tempfile.TemporaryDirectory() as d:
    isca = Path(d) / "R.md"
    isca.write_text("```bash\niachat rotate   # arquiva (idempotente)\n```\n", encoding="utf-8")
    achou = inline(isca)
    checa("o detector pega o caso real", achou and achou[0][1],
          f"não pegou: {achou}")

    limpo = Path(d) / "L.md"
    limpo.write_text('```bash\niachat post --de claude "texto com # dentro de aspas"\n```\n',
                     encoding="utf-8")
    checa("não acusa `#` dentro de aspas", not inline(limpo),
          f"falso positivo: {inline(limpo)}")

# E a prova viva: se há zsh nesta máquina, cola a isca e confere o erro.
if shutil.which("zsh"):
    r = subprocess.run(["zsh", "-f", "-i"],
                       input='true   # arquiva (idempotente)\nexit\n',
                       capture_output=True, text=True, timeout=30)
    saida = r.stdout + r.stderr
    # Qualquer diagnóstico do zsh serve. A primeira versão listava as mensagens que eu
    # tinha VISTO (`number expected`, `parse error`) e reprovou quando o shell devolveu
    # `unknown file attribute: i` — o texto muda conforme o que vem depois do `#`.
    # Gate que cobra a mensagem exata testa a minha memória, não o mecanismo.
    checa("o zsh desta máquina confirma o mecanismo", "zsh:" in saida,
          f"nenhum erro do zsh — o mecanismo pode ter mudado: {saida.strip()[:120]}")
else:
    print("  ⊘ zsh ausente — o mecanismo NÃO foi confirmado nesta máquina")

print(f"\n{_ok} ✔  {_falhou} ✗")
sys.exit(1 if _falhou else 0)
