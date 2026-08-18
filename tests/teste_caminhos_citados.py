#!/usr/bin/env python3
"""teste_caminhos_citados.py — a documentação não pode apontar para o vazio.

POR QUE ESTE TESTE EXISTE, com o caso: em 18/08 dois documentos citavam
`auditorias/2026-08-17-fase6/JA-EXISTE.md` como **leitura obrigatória** do processo. O
arquivo não existia. Seis workers foram instruídos a lê-lo antes de projetar, leram o
nada, e **nenhum reclamou** — trabalharam sem a régua anti-redundância achando que a
tinham. Quem descobriu foi uma auditoria externa, não a bateria.

É a mesma família do defeito que já custou caro aqui: um `<link>` não é uma folha de
estilo, e um caminho escrito não é um arquivo. **Validar a referência não é validar o
alvo.**

O gate: todo caminho relativo do repositório citado em `.md` ou em `SKILL.md` tem que
existir no disco.

Fora de escopo, de propósito:
  · caminhos absolutos (`/Users/...`, `~/...`) — dependem da máquina de quem lê;
  · caminhos dentro de bloco de código de exemplo com placeholder (`<peça>`, `NN`, `*`);
  · URLs.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

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


# Um caminho relativo do repo é: começa por uma pasta conhecida, tem barra, e termina
# numa extensão de arquivo do projeto. Deliberadamente estreito — falso positivo aqui
# vira ruído que faz o gate ser ignorado, e gate ignorado é gate morto.
PASTAS = ("bin", "skills", "tests", "auditorias", "docs")
RE_CAMINHO = re.compile(
    r"(?<![\w/~.-])((?:" + "|".join(PASTAS) + r")/[\w./-]+\.(?:py|sh|md|json|toml|txt))"
)
PLACEHOLDER = re.compile(r"<[^>]+>|\*|\bNN\b|\bN\b|\{|\}")

print("teste_caminhos_citados")

mortos: list[str] = []
conferidos = 0

for doc in sorted(RAIZ.rglob("*.md")):
    if ".git" in doc.parts:
        continue
    # `auditorias/` fica FORA, e é decisão, não omissão: laudo é registro do que o autor
    # viu naquele momento — cita o arquivo que existia então, e a peça pode ter sido
    # renomeada, movida ou substituída depois. Exigir que a história aponte para o disco
    # de hoje transformaria cada laudo antigo em falso positivo, e um gate cheio de
    # falso positivo é um gate que todo mundo aprende a ignorar.
    #
    # O que este gate protege é a documentação VIVA — README, CHANGELOG, JA-EXISTE e as
    # skills —, que é o que ENSINA alguém a usar o produto. Foi exatamente ali que o
    # defeito apareceu.
    if "auditorias" in doc.parts:
        continue
    texto = doc.read_text(errors="replace")
    for n, linha in enumerate(texto.splitlines(), 1):
        for m in RE_CAMINHO.finditer(linha):
            caminho = m.group(1)
            if PLACEHOLDER.search(caminho):
                continue
            conferidos += 1
            if not (RAIZ / caminho).exists():
                mortos.append(f"{doc.relative_to(RAIZ)}:{n} → {caminho}")

checa(
    f"todo caminho citado existe no disco ({conferidos} conferidos)",
    not mortos,
    "\n      ".join(mortos[:12]) +
    (f"\n      … e mais {len(mortos)-12}" if len(mortos) > 12 else "") +
    "\n      documentação que ensina caminho quebrado é pior que documentação nenhuma.",
)

# O gate precisa realmente estar olhando alguma coisa. Um regex que não casa nada passa
# sempre — e passar sempre é o jeito mais silencioso de um gate morrer.
#
# A primeira versão disto contava (`conferidos >= 20`) e reprovou sozinha assim que uma
# citação legítima foi corrigida e o total caiu para 19. Limiar arbitrário é frágil por
# construção: mede o tamanho do corpus, não a saúde do instrumento. O certo é o
# instrumento se auto-testar contra um caso conhecido.
_amostra = "veja bin/iachat_core.py e também skills/ia-bell/SKILL.md para detalhes"
_casou = [m.group(1) for m in RE_CAMINHO.finditer(_amostra)]
checa("o padrão ainda reconhece um caminho conhecido",
      _casou == ["bin/iachat_core.py", "skills/ia-bell/SKILL.md"],
      f"casou {_casou} — o regex parou de funcionar e o gate passaria sempre")
checa("o gate varreu a documentação viva", conferidos > 0,
      "nenhum caminho foi conferido — ou o corpus sumiu, ou o filtro exclui tudo")

# ── âncoras `arquivo:linha` apontam para CÓDIGO, não para o vazio ────────────
# Uma skill que cita `bin/iachat_core.py:38` está prometendo que a constante está ali. A
# âncora envelhece sozinha: basta alguém inserir dez linhas acima e ela passa a apontar
# para outra coisa — sem erro, sem aviso, e continuando plausível.
#
# Foi assim que uma auditoria de 18/08 achou duas âncoras deslizadas numa skill: os
# VALORES citados estavam certos, e as linhas apontavam para comentário. Documentação
# que aponta para o lugar errado é pior que documentação sem âncora, porque quem confere
# lê o comentário e conclui que entendeu.
#
# O gate não tenta adivinhar o símbolo esperado — verifica o que dá para verificar sem
# ambiguidade: **a linha existe e tem código nela**. Âncora que caiu em linha vazia ou em
# comentário puro deslizou.
# ── o README não pode apontar para fora do repositório ──────────────────────
# `[ia-chat](../ia-chat)` resolve perfeitamente no disco de quem tem os dois repos
# clonados lado a lado — e dá **404 no GitHub**, que é onde a primeira dobra é lida por
# quem ainda não clonou nada. Mesma família do resto deste arquivo: a referência existe,
# o alvo não — só que aqui o alvo só some no ambiente que importa.
#
# Placeholder (`<seu-usuario>`) tem o mesmo destino: um `git clone` que não funciona
# copiado-e-colado é pior que nenhum, porque o leitor descobre no erro.
readmes_ruins: list[str] = []
for doc in (RAIZ / "README.md", RAIZ.parent / "ia-chat-app" / "README.md"):
    if not doc.is_file():
        # DIZER que não olhou. O `continue` calado dava o mesmo verde de quem conferiu
        # os dois READMEs — e no CI, sem o repo irmão, isso é falso verde exatamente
        # onde o gate mais importa (o README do app é o que o estranho lê primeiro).
        # "Não consegui olhar" é um terceiro desfecho, e ele só serve se aparecer.
        print(f"  ⊘ {doc} ausente — este README NÃO foi conferido nesta rodada")
        continue
    t = doc.read_text(errors="replace")
    for rel in re.findall(r"\]\((\.\./[^)]+)\)", t):
        readmes_ruins.append(f"{doc.name}: link relativo entre repos `{rel}` → 404 no GitHub")
    # Placeholder de ARGUMENTO (`iachat entrar <ia>`) é a forma padrão de documentar um
    # comando — não é defeito. O que quebra é o placeholder de VALOR que o leitor tinha
    # que ter substituído: `git clone https://github.com/<seu-usuario>/...` sai do
    # copiar-e-colar direto para o erro.
    #
    # A primeira versão deste caso não distinguia os dois e reprovou o `<ia>` legítimo.
    # Gate com falso positivo é gate que todo mundo aprende a ignorar — e aí ele para de
    # valer para os casos verdadeiros.
    for ln in t.splitlines():
        if "github.com/" not in ln and "clone" not in ln:
            continue
        for ph in set(re.findall(r"<[a-z][a-z-]+>", ln)):
            readmes_ruins.append(
                f"{doc.name}: placeholder {ph} num comando de clone/URL — "
                f"o leitor copia, cola e recebe erro")
    # `![img](.../blob/...)` NÃO renderiza no GitHub: `blob` devolve a PÁGINA HTML do
    # arquivo, não os bytes da imagem. O README aparece sem o screenshot — justamente o
    # que decide se alguém rola a página. Para imagem, o caminho é `raw`.
    for img in re.findall(r"!\[[^\]]*\]\((https://github\.com/[^)]*?/blob/[^)]+)\)", t):
        readmes_ruins.append(f"{doc.name}: imagem com /blob/ não renderiza → use /raw/ ({img[:60]})")
    # As imagens locais do README também: o repositório do app é o que tem screenshot na
    # primeira dobra, e ele vive FORA da raiz varrida acima. Uma imagem que não carrega
    # ali custa mais que qualquer outro defeito deste projeto — é a única coisa que a
    # maioria vai ver.
    for img in re.findall(r"!\[[^\]]*\]\((?!https?:)([^)]+)\)", t):
        if not (doc.parent / img).exists():
            readmes_ruins.append(f"{doc.name}: imagem local ausente → {img}")

checa("os READMEs funcionam FORA do disco (no GitHub)", not readmes_ruins,
      "\n      ".join(readmes_ruins))

RE_ANCORA = re.compile(r"`(bin/[\w.-]+):(\d+)`")
deslizadas: list[str] = []
ancoras = 0

for doc in sorted(RAIZ.rglob("SKILL.md")):
    if ".git" in doc.parts or "auditorias" in doc.parts:
        continue
    for n, linha in enumerate(doc.read_text(errors="replace").splitlines(), 1):
        for m in RE_ANCORA.finditer(linha):
            arq, num = m.group(1), int(m.group(2))
            alvo = RAIZ / arq
            if not alvo.is_file():
                continue                      # arquivo inexistente já é pego acima
            ancoras += 1
            linhas = alvo.read_text(errors="replace").splitlines()
            if not (0 < num <= len(linhas)):
                deslizadas.append(f"{doc.relative_to(RAIZ)}:{n} → {arq}:{num} (fora do arquivo)")
                continue
            conteudo = linhas[num - 1].strip()
            if not conteudo or conteudo.startswith("#"):
                deslizadas.append(
                    f"{doc.relative_to(RAIZ)}:{n} → {arq}:{num} "
                    f"({'linha vazia' if not conteudo else 'só comentário'}: {conteudo[:50]})")

checa(
    f"toda âncora arquivo:linha aponta para código ({ancoras} conferidas)",
    not deslizadas,
    "\n      ".join(deslizadas) +
    "\n      a âncora deslizou. Prefira citar o SÍMBOLO (`a constante TETO_PADRAO em "
    "bin/iachat_core.py`) — símbolo sobrevive a inserção de linha; número não.",
)

print(f"\n{_ok} ✔  {_falhou} ✗")
sys.exit(1 if _falhou else 0)
