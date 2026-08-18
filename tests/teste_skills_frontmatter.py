#!/usr/bin/env python3
"""teste_skills_frontmatter.py — o cartão de visita de cada skill tem que estar certo.

Uma skill é descoberta pelo frontmatter. Se o `name` diverge da pasta, o loader que casa
os dois não a encontra — e a falha é **silenciosa**: a skill existe no disco, aparece na
listagem de arquivos, e simplesmente nunca é invocada.

Achado em 18/08 com 26 skills no repositório: `ia-vacuum` declarava `name: iachat-vacuum`
(o nome do CLI, não o da skill). Nenhum teste pegava, porque cada bateria olhava o
comportamento da própria peça, e o frontmatter não é comportamento — é catálogo.

O `description` também importa mais do que parece: é por ele que a IA decide **quando**
usar a skill. Descrição vazia é skill que nunca é escolhida.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

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


print("teste_skills_frontmatter")

skills = sorted(RAIZ.glob("skills/*/SKILL.md"))
sem_abertura, sem_nome, sem_desc, nome_divergente, desc_curta = [], [], [], [], []

for s in skills:
    pasta = s.parent.name
    t = s.read_text(errors="replace")
    if not t.startswith("---"):
        sem_abertura.append(pasta)
        continue
    bloco = t.split("---", 2)[1] if t.count("---") >= 2 else ""

    m = re.search(r"^name:\s*(\S+)", bloco, re.M)
    if not m:
        sem_nome.append(pasta)
    elif m.group(1) != pasta:
        nome_divergente.append(f"{pasta} → declara '{m.group(1)}'")

    d = re.search(r"^description:\s*(.+)", bloco, re.M)
    if not d:
        sem_desc.append(pasta)
    elif len(d.group(1).strip()) < 40:
        # É pela descrição que a IA decide QUANDO usar a skill. Uma linha de 20
        # caracteres não distingue esta peça das outras 25.
        desc_curta.append(f"{pasta} ({len(d.group(1).strip())} chars)")

checa(f"há skills para conferir ({len(skills)})", bool(skills))
checa("toda skill abre com frontmatter", not sem_abertura, ", ".join(sem_abertura))
checa("toda skill declara `name`", not sem_nome, ", ".join(sem_nome))
checa("toda skill declara `description`", not sem_desc, ", ".join(sem_desc))
checa("o `name` bate com o nome da PASTA", not nome_divergente,
      ", ".join(nome_divergente) +
      "\n      loader que casa nome×pasta não acha a skill, e a falha é silenciosa: "
      "ela existe no disco e nunca é invocada.")
checa("nenhuma `description` é curta demais para escolher", not desc_curta,
      ", ".join(desc_curta) +
      "\n      é pela description que a IA decide QUANDO usar a peça.")

print(f"\n{_ok} ✔  {_falhou} ✗")
sys.exit(1 if _falhou else 0)
