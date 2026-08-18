#!/usr/bin/env python3
"""Gate da borda ``--via-app`` para alvos IASWARM.

``run`` e ``ia`` atravessam como dados do JSON, nunca como argv. Este teste
prova os dois lados importantes do contrato do CLI: identificadores ruins
morrem antes de qualquer acesso ao run, e identificadores honestos resolvem
somente dentro de ``IASWARM_RAIZ`` sem deixar escrita no modo ``seco``.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


RAIZ = Path(__file__).resolve().parent.parent
COMANDO = RAIZ / "bin" / "iachat-comando"

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


def via_app(env: dict[str, str], comando: str, payload: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(COMANDO), comando, "--via-app"],
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True,
        text=True,
        env=env,
        timeout=20,
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="iachat-via-app-iaswarm-") as td:
        base = Path(td)
        raiz_swarm = base / "runs"
        run = raiz_swarm / "run-seguro"
        for nome in ("logs", "resultados", "progress", "contratos"):
            (run / nome).mkdir(parents=True, exist_ok=True)
        (run / "workers.tsv").write_text(
            "codex\tcodex\t1\tcontratos/codex.md\n", encoding="utf-8"
        )
        (run / "logs" / "codex.pid").write_text("999999\n", encoding="utf-8")
        env = dict(os.environ, IASWARM_RAIZ=str(raiz_swarm))

        print("— identificador é dado fechado, não caminho —")
        ruins = (
            ("parar", {"run": "../fora", "ia": "codex", "seco": True}),
            ("refaz", {"run": "../fora", "ia": "codex", "seco": True}),
            ("parar", {"run": "run-seguro", "ia": "co/dex", "seco": True}),
            ("refaz", {"run": "run-seguro", "ia": "co dex", "seco": True}),
            ("parar", {"run": "r" * 81, "ia": "codex", "seco": True}),
            ("refaz", {"run": "run-seguro", "ia": "i" * 81, "seco": True}),
        )
        for comando, payload in ruins:
            r = via_app(env, comando, payload)
            checa(
                f"REPROVA: {comando} recusa {payload!r}",
                r.returncode == 2 and "identificador" in r.stderr.lower(),
                f"rc={r.returncode} stderr={r.stderr.strip()[:180]}",
            )

        print("— caminho honesto resolve sob a raiz cravada —")
        antes = sorted(str(p.relative_to(run)) for p in run.rglob("*"))
        parar = via_app(
            env, "parar", {"run": "run-seguro", "ia": "codex", "seco": True}
        )
        refaz = via_app(
            env, "refaz", {"run": "run-seguro", "ia": "codex", "seco": True}
        )
        depois = sorted(str(p.relative_to(run)) for p in run.rglob("*"))
        checa(
            "parar seco aceita run/ia honestos pelo JSON",
            parar.returncode == 0 and "codex" in parar.stdout and "seco" in parar.stdout,
            f"rc={parar.returncode} out={parar.stdout[:140]} err={parar.stderr[:140]}",
        )
        checa(
            "refaz seco aceita run/ia honestos pelo JSON",
            refaz.returncode == 0 and "codex" in refaz.stdout and "seco" in refaz.stdout,
            f"rc={refaz.returncode} out={refaz.stdout[:140]} err={refaz.stderr[:140]}",
        )
        checa("os dois secos não escrevem no run", depois == antes, str(depois))

    print()
    print(f"{_ok} ✔  {_falhou} ✗")
    return 1 if _falhou else 0


if __name__ == "__main__":
    raise SystemExit(main())
