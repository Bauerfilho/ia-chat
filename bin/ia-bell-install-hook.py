#!/usr/bin/env python3
"""Liga a perna de DENTRO do sino: o hook que avisa a IA no meio do trabalho.

O daemon avisa o humano (notificação do Mac). Só o hook alcança a IA que já está aberta
e ocupada — pegando carona nos eventos que ela mesma gera. O Codex mediu a falta disso em
17/08: "não apareceu notificação automática na minha tela; só descobri porque o Bauer
mandou executar o read".

Uso:  ia-bell-install-hook.py <ia> [--settings CAMINHO] [--remover]

Só edita o `settings.json` do Claude Code. Para Codex e Kimi, IMPRIME o que fazer e não
toca em nada — no Codex, mexer em `hooks.json` invalida o `trusted_hash` e ele passa a
pular o hook EM SILÊNCIO até o dono re-aprovar. Instalador que fabrica hash é instalador
que sabota o usuário.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

EVENTOS = ("SessionStart", "UserPromptSubmit")


def instala_kimi(cmd: str) -> int:
    """O Kimi aceita hook em TOML e NÃO tem trust — dá para ligar sem pedir nada.

    Formato copiado de um bloco real já vivo no config dele (os hooks do omni), não
    inventado: `[[hooks]]` + `event` + `command`. Como é array de tabelas de topo,
    acrescentar no fim do arquivo é válido independentemente do que veio antes.
    """
    alvo = Path.home() / ".kimi-code/config.toml"
    if not alvo.exists():
        print(f"✗ não achei {alvo}", file=sys.stderr)
        return 2
    atual = alvo.read_text(encoding="utf-8")
    if "ia-bell-hook.sh" in atual:
        print("= o hook do kimi já estava lá")
        return 0

    bloco = "\n".join(
        f'\n[[hooks]]\nevent = "{ev}"\ncommand = "{cmd}"' for ev in EVENTOS
    )
    novo = atual.rstrip("\n") + "\n" + bloco + "\n"

    try:  # o gate: não escreve TOML que não relê
        import tomllib

        antes, depois = tomllib.loads(atual), tomllib.loads(novo)
        if len(depois.get("hooks", [])) != len(antes.get("hooks", [])) + len(EVENTOS):
            raise ValueError("contagem de hooks não bateu")
    except ModuleNotFoundError:
        print("⚠️  sem tomllib para validar — gravando assim mesmo, backup feito")
    except Exception as e:
        print(f"✗ o TOML resultante não valida ({e}) — não gravei nada", file=sys.stderr)
        return 2

    bak = alvo.with_name(f"config.toml.bak-iachat-{datetime.now():%Y%m%d-%H%M%S}")
    shutil.copy2(alvo, bak)
    alvo.write_text(novo, encoding="utf-8")
    print(f"✔ +{' +'.join(EVENTOS)} em {alvo}")
    print(f"  comando: {cmd}")
    print(f"  backup:  {bak}")
    print("  ⚠️ vale a partir da PRÓXIMA sessão do Kimi (config é lido no boot)")
    return 0


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0].startswith("-"):
        print(__doc__)
        return 2
    ia = args[0]
    remover = "--remover" in args
    alvo = Path(
        args[args.index("--settings") + 1]
        if "--settings" in args
        else Path.home() / ".claude/settings.json"
    ).expanduser()

    # Respeita IACHAT_SCRIPTS como o install.sh e o instalador do daemon já faziam. Antes
    # este era o único que fixava o caminho: instalação customizada gerava hook apontando
    # para o lugar errado. Achado da auditoria de 17/08 (agy).
    scripts = Path(
        os.environ.get("IACHAT_SCRIPTS", Path.home() / ".claude/scripts/ia-chat")
    )
    cmd = f"IACHAT_EU={ia} {scripts}/ia-bell-hook.sh"

    if ia == "kimi" and "--settings" not in args:
        return instala_kimi(cmd)

    if not alvo.exists():
        print(f"✗ não achei {alvo}", file=sys.stderr)
        return 2

    original = alvo.read_text(encoding="utf-8")
    try:
        cfg = json.loads(original)
    except json.JSONDecodeError as e:
        print(f"✗ {alvo} não é JSON válido ({e}) — não vou mexer", file=sys.stderr)
        return 2

    hooks = cfg.setdefault("hooks", {})
    mudou = []
    for ev in EVENTOS:
        grupos = hooks.setdefault(ev, [])
        ja = any(
            h.get("command", "").endswith("ia-bell-hook.sh")
            or "ia-bell-hook.sh" in h.get("command", "")
            for g in grupos
            for h in g.get("hooks", [])
        )
        if remover:
            for g in grupos:
                antes = len(g.get("hooks", []))
                g["hooks"] = [
                    h for h in g.get("hooks", []) if "ia-bell-hook.sh" not in h.get("command", "")
                ]
                if len(g["hooks"]) != antes:
                    mudou.append(f"−{ev}")
            hooks[ev] = [g for g in grupos if g.get("hooks")]
        elif not ja:
            grupos.append({"hooks": [{"type": "command", "command": cmd}]})
            mudou.append(f"+{ev}")

    if not mudou:
        print(f"= nada a fazer (o hook de {ia} já estava como você pediu)")
        return 0

    novo = json.dumps(cfg, ensure_ascii=False, indent=2) + "\n"
    json.loads(novo)  # o próprio gate: não escreve o que não relê
    bak = alvo.with_suffix(f".json.bak-iachat-{datetime.now():%Y%m%d-%H%M%S}")
    shutil.copy2(alvo, bak)
    alvo.write_text(novo, encoding="utf-8")

    print(f"✔ {' '.join(mudou)} em {alvo.name}")
    print(f"  comando: {cmd}")
    print(f"  backup:  {bak}")
    print("\nOutras cascas (não toco nelas de propósito):")
    print("  Kimi   → ~/.kimi-code/config.toml, bloco [[hooks]] em TOML (sem trust)")
    print("  Codex  → ~/.codex/hooks.json  ⚠️ editar INVALIDA o trusted_hash e ele passa")
    print("           a PULAR o hook em silêncio até você re-aprovar na próxima abertura")
    return 0


if __name__ == "__main__":
    sys.exit(main())
