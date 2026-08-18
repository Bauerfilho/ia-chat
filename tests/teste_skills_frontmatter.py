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


def parse_frontmatter(bloco: str) -> dict:
    """Parseia o YAML do frontmatter de verdade — não só o regex de name/description.

    O teste antigo passava em `ia-roster` com `"na_sala: x, y, z"` no meio de um
    escalar não-citado. Parsers estritos (PyYAML, js-yaml das cascas) recusam
    isso com ScannerError e a skill some em silêncio. Sem parse real, o defeito
    volta.

    Preferência: yaml.safe_load, que é o que as cascas usam. Sem PyYAML (Python
    3.9 de sistema, zero dep): recusa o mesmo caso (`: ` em escalar não-citado)
    e monta o dict.
    """
    try:
        import yaml  # type: ignore
    except ImportError:
        yaml = None
    if yaml is not None:
        data = yaml.safe_load(bloco)
        if not isinstance(data, dict):
            raise ValueError("frontmatter não é um mapeamento YAML")
        return data
    return _parse_frontmatter_sem_pyyaml(bloco)


def _parse_frontmatter_sem_pyyaml(bloco: str) -> dict:
    out: dict[str, str] = {}
    for raw in bloco.splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"linha sem chave YAML: {line[:80]}")
        chave, _sep, resto = line.partition(":")
        chave = chave.strip()
        if not chave or any(c.isspace() for c in chave):
            raise ValueError(f"chave YAML inválida: {chave!r}")
        valor = resto.strip()
        if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in ("'", '"'):
            if valor[0] == "'":
                out[chave] = valor[1:-1].replace("''", "'")
            else:
                out[chave] = valor[1:-1]
            continue
        if ": " in valor:
            raise ValueError(
                f"{chave}: ': ' em escalar não-citado "
                "(parsers estritos recusam; a skill some em silêncio)"
            )
        out[chave] = valor
    if not out:
        raise ValueError("frontmatter vazio")
    return out


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

# ── YAML de verdade ────────────────────────────────────────────────────────
# O regex acima aceita qualquer texto depois de `description:`. Este bloco
# parseia. O fixture é o defeito medido em ia-roster (18/08): aspas cruas
# com `: ` no meio de um escalar não-citado.
fixture_quebrado = (
    "name: ia-roster\n"
    "description: texto disser \"na_sala: x, y, z\" e segue\n"
)
reprovou = False
try:
    parse_frontmatter(fixture_quebrado)
except Exception:
    reprovou = True
checa("YAML com ': ' em escalar não-citado é REPROVADO", reprovou,
      "o parser aceitou o fixture quebrado — o defeito do ia-roster volta")

yaml_vivo: list[str] = []
for s in skills:
    t = s.read_text(errors="replace")
    if not t.startswith("---") or t.count("---") < 2:
        continue
    bloco = t.split("---", 2)[1]
    try:
        parse_frontmatter(bloco)
    except Exception as e:
        yaml_vivo.append(f"{s.parent.name}: {type(e).__name__}")

roster = RAIZ / "skills" / "ia-roster" / "SKILL.md"
roster_ok = False
roster_detalhe = "arquivo ausente"
if roster.is_file():
    rt = roster.read_text(errors="replace")
    if rt.startswith("---") and rt.count("---") >= 2:
        try:
            data = parse_frontmatter(rt.split("---", 2)[1])
            roster_ok = isinstance(data, dict) and data.get("name") == "ia-roster"
            roster_detalhe = f"name={data.get('name')!r}" if roster_ok else repr(data)
        except Exception as e:
            roster_detalhe = f"{type(e).__name__}: {e}"
checa("ia-roster/SKILL.md carrega como YAML", roster_ok, roster_detalhe)

# Os outros SKILL.md com o mesmo cheiro (ia-doctor, ia-onboard, ia-plan) estão
# fora da fronteira desta missão. Sinalizo, não barro — senão a bateria fica
# vermelha por arquivo que este worker não pode editar.
outros = [x for x in yaml_vivo if not x.startswith("ia-roster:")]
if outros:
    print("  · YAML inválido fora desta fronteira (só sinal): " + "; ".join(outros))

print(f"\n{_ok} ✔  {_falhou} ✗")
sys.exit(1 if _falhou else 0)
