#!/usr/bin/env python3
"""A telemetria precisa poder ficar ligada sem alguém lembrar de exportar variável.

A barra de contexto do groupchat só tem número se algo escrever o sidecar. Ela nasceu
ligada **só** por `IACHAT_TELEMETRIA=1` — e variável de ambiente some entre sessões e é
diferente em cada braço da frota. Na prática ninguém ligava, e a barra ficava
permanentemente `desconhecido`: a tela era honesta e vazia. Funcionalidade que depende de
alguém lembrar de exportar uma variável é funcionalidade morta.

A regra que este teste trava:

  1. a variável de ambiente MANDA — é o escape para ligar ou desligar num comando só;
  2. sem ela, vale o `telemetria` do `config.json` da sala, que é onde moram as decisões
     que persistem (`na_sala`, `brain`, `teto_bytes`);
  3. o default continua DESLIGADO — quem não pediu não paga o custo de ler rollout a cada
     post;
  4. config ilegível não liga nada por conta própria.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

BIN = Path(__file__).resolve().parent.parent / "bin"

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


def pergunta(env_valor: str | None, cfg_valor, *, config_quebrada: bool = False) -> str:
    """Monta uma sala descartável e pergunta ao próprio `iachat` se a telemetria está ligada."""
    with tempfile.TemporaryDirectory() as d:
        cfg = {"na_sala": ["claude"], "brain": "claude", "teto_bytes": 204800}
        if cfg_valor is not None:
            cfg["telemetria"] = cfg_valor
        alvo = Path(d) / "config.json"
        alvo.write_text("{ isto não é json" if config_quebrada
                        else json.dumps(cfg, ensure_ascii=False), encoding="utf-8")

        env = {k: v for k, v in os.environ.items() if k != "IACHAT_TELEMETRIA"}
        env["IACHAT_HOME"] = d
        if env_valor is not None:
            env["IACHAT_TELEMETRIA"] = env_valor

        codigo = (
            "import runpy, sys, types\n"
            f"sys.path.insert(0, {str(BIN)!r})\n"
            "mod = runpy.run_path("
            f"{str(BIN / 'iachat')!r}, run_name='__nao_main__')\n"
            "print(mod['telemetria_ligada']())\n"
        )
        r = subprocess.run([sys.executable, "-c", codigo],
                           capture_output=True, text=True, env=env, timeout=60)
        return (r.stdout.strip() or f"ERRO: {r.stderr.strip()[:120]}")


def main() -> int:
    print("— sem variável de ambiente, quem manda é a config —")
    checa("config sem a chave → desligado", pergunta(None, None) == "False",
          f"veio {pergunta(None, None)!r} — o default não pode ligar sozinho")
    checa("config com telemetria=true → ligado", pergunta(None, True) == "True",
          "é isto que faz a barra ter número sem ninguém exportar nada")
    checa("config com telemetria=false → desligado", pergunta(None, False) == "False")

    print("— a variável de ambiente manda sobre a config —")
    checa("env=1 vence config=false", pergunta("1", False) == "True")
    checa("env=0 vence config=true", pergunta("0", True) == "False",
          "sem este escape, não há como desligar num comando só")
    for forma in ("true", "on", "sim"):
        checa(f"env={forma!r} liga", pergunta(forma, False) == "True")
    for forma in ("false", "off", "nao"):
        checa(f"env={forma!r} desliga", pergunta(forma, True) == "False")

    print("— e o que não dá para ler não liga nada —")
    checa("config ilegível → desligado",
          pergunta(None, None, config_quebrada=True) == "False",
          "na dúvida, fica desligado: ligar por acidente gasta leitura de rollout a cada post")

    print(f"\n{_ok} ✔  {_falhou} ✗")
    return 1 if _falhou else 0


if __name__ == "__main__":
    raise SystemExit(main())
