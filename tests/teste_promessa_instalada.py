#!/usr/bin/env python3
"""Skill que promete gatilho automático tem que dizer quem arma o gatilho.

Achado por auditoria cruzada em 18/08: a `ia-compactacao` declarava "passiva, no
SessionStart" como se acontecesse sozinha. O `install.sh` copia binário e skill —
e não arma hook nenhum, deliberadamente (editar o `settings.json` de quem instala
é invasivo, e no Codex quebra o `trusted_hash`). Resultado: num clone novo do repo
público, a skill promete e nada acontece.

O gate NÃO exige que o instalador arme o hook. Exige que a promessa e a entrega
digam a mesma coisa — o que se resolve de duas formas legítimas: armando, ou
declarando que não arma e ensinando como. Qualquer uma passa.

Mede mecanismo, não forma: procura a PROMESSA (nome de evento de hook numa skill)
e cobra que exista contrapartida. Uma skill nova que prometa `PreToolUse` cai aqui
do mesmo jeito, sem ninguém precisar acrescentar caso.
"""
from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
EVENTOS = ("SessionStart", "PreCompact", "PostCompact", "PreToolUse", "PostToolUse",
           "UserPromptSubmit", "Stop", "SubagentStop", "Notification")

_ok = 0
_falhou = 0


def checa(nome: str, cond: bool, detalhe: str = "") -> None:
    global _ok, _falhou
    if cond:
        _ok += 1
        print(f"  ✔ {nome}")
    else:
        _falhou += 1
        print(f"  ✗ {nome}" + (f" — {detalhe}" if detalhe else ""))


def skills_que_prometem_hook() -> dict[str, set[str]]:
    """Skill → eventos de hook que o texto dela cita."""
    achadas: dict[str, set[str]] = {}
    for skill in sorted((RAIZ / "skills").glob("*/SKILL.md")):
        texto = skill.read_text(encoding="utf-8")
        eventos = {e for e in EVENTOS if e in texto}
        if eventos:
            achadas[skill.parent.name] = eventos
    return achadas


def main() -> int:
    instalador = (RAIZ / "install.sh").read_text(encoding="utf-8")
    prometem = skills_que_prometem_hook()

    print("— quem promete gatilho —")
    checa("alguma skill fala de hook (senão este gate não está medindo nada)",
          bool(prometem), "nenhuma SKILL.md cita evento de hook: o gate ficou cego")
    for nome, eventos in prometem.items():
        print(f"    · {nome}: {', '.join(sorted(eventos))}")

    print("— promessa e entrega dizem a mesma coisa —")
    for nome, eventos in prometem.items():
        # "Ensinar a armar" é mostrar o nome do binário JUNTO de um evento de hook.
        # Citar o nome solto não conta: o `install.sh` já mencionava `ia-compactacao`
        # num comentário sobre outro assunto, e a primeira versão deste gate passou
        # verde com a ressalva removida. O instrumento frouxo era o meu.
        citada = any(
            nome in linha and any(e in linha for e in eventos)
            for linha in instalador.split("\n")
        ) or any(
            nome in bloco and any(e in bloco for e in eventos)
            for bloco in re.split(r"\n\s*\n", instalador)
        )
        texto = (RAIZ / "skills" / nome / "SKILL.md").read_text(encoding="utf-8")
        # a outra saída legítima: a skill declarar que o gatilho é armado à mão
        declara = bool(re.search(r"(?i)n[ãa]o\s+arma|armar\s+é|gesto seu|na m[ãa]o", texto))
        checa(f"{nome}: o instalador ensina a armar, OU a skill declara que não é automático",
              bool(citada or declara),
              "a skill promete gatilho passivo, o install.sh não fala dele, e a skill "
              "não avisa que é preciso armar — quem clonar não ganha nada")

    print("— o instalador não arma hook por conta própria —")
    # Isto é o outro lado: se um dia ele PASSAR a editar hooks sozinho, quero saber.
    edita = re.search(r"(?i)>\s*[\"']?\$?\{?HOME\}?/\.(claude|codex)/(settings|hooks)\.json", instalador)
    checa("install.sh não escreve no settings.json/hooks.json de ninguém",
          edita is None,
          "editar o arquivo de hooks de quem instala é invasivo e, no Codex, "
          "invalida o trusted_hash em silêncio")

    print(f"\n{_ok} ✔  {_falhou} ✗")
    return 1 if _falhou else 0


if __name__ == "__main__":
    raise SystemExit(main())
