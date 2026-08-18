#!/usr/bin/env python3
"""Gate do sino do operador: só liga depois de provar o daemon da sala exata."""
from __future__ import annotations

import json
import os
import plistlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
BIN = RAIZ / "bin" / "iachat"
LABEL = "com.bauer.ia-bell-operador"

_ok = 0
_falhou = 0


def checa(nome: str, cond: bool, detalhe: str = "") -> None:
    global _ok, _falhou
    if cond:
        _ok += 1
        print("  ✔ %s" % nome)
    else:
        _falhou += 1
        print("  ✗ %s" % nome + (("\n      %s" % detalhe) if detalhe else ""))


def laboratorio() -> tuple[Path, Path, Path, dict[str, str]]:
    raiz = Path(tempfile.mkdtemp(prefix="iachat-sino-cli-"))
    sala = raiz / "sala"
    casa = raiz / "home"
    bin_fake = raiz / "bin"
    casa.mkdir()
    bin_fake.mkdir()
    env = dict(os.environ)
    env["IACHAT_HOME"] = str(sala)
    env["HOME"] = str(casa)
    env["PATH"] = "%s%s%s" % (bin_fake, os.pathsep, env.get("PATH", ""))
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return raiz, sala, casa, env


def roda(env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(BIN), *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )


def config(sala: Path) -> dict:
    return json.loads((sala / "config.json").read_text(encoding="utf-8"))


def arma_daemon_fake(
    raiz: Path,
    sala: Path,
    casa: Path,
    *,
    sala_vigiada: Optional[Path] = None,
) -> None:
    """Cria plist e launchctl dublês; nunca consulta nem altera o LaunchAgent vivo."""
    plists = casa / "Library" / "LaunchAgents"
    plists.mkdir(parents=True)
    alvo = sala_vigiada or sala
    with (plists / (LABEL + ".plist")).open("wb") as arquivo:
        plistlib.dump(
            {
                "Label": LABEL,
                "ProgramArguments": [
                    "/bin/bash",
                    str(RAIZ / "bin" / "ia-bell-daemon.sh"),
                    "--operador",
                    "15",
                ],
                "EnvironmentVariables": {"IACHAT_HOME": str(alvo)},
                "RunAtLoad": True,
                "KeepAlive": True,
            },
            arquivo,
        )
    launchctl = raiz / "bin" / "launchctl"
    launchctl.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = list ]; then\n"
        "  printf '4242\\t0\\t%s\\n'\n"
        "  exit 0\n"
        "fi\n"
        "exit 1\n" % LABEL,
        encoding="utf-8",
    )
    launchctl.chmod(0o755)


print("teste_sino")
checa("binário presente", BIN.is_file(), str(BIN))

# ── 1. Casa nova sem daemon: não grava consentimento impossível.
raiz, sala, _, env = laboratorio()
r = roda(env, "sino", "on")
cfg = config(sala)
saida = r.stdout + r.stderr
checa("REPROVA: sem daemon, sino on sai não-zero", r.returncode != 0, saida)
checa(
    "REPROVA: sem daemon, config continua false",
    cfg.get("notificar_operador") is False,
    json.dumps(cfg, ensure_ascii=False),
)
checa(
    "sem daemon, ensina o instalador sem executá-lo",
    "ia-bell-install-daemon.sh --operador" in saida,
    saida,
)
shutil.rmtree(raiz, ignore_errors=True)

# ── 2. Daemon carregado e apontando para esta sala: pode gravar true.
raiz, sala, casa, env = laboratorio()
arma_daemon_fake(raiz, sala, casa)
r = roda(env, "sino", "on")
cfg = config(sala)
checa("PASS: daemon da sala exata permite ligar", r.returncode == 0, r.stdout + r.stderr)
checa("PASS: somente depois da prova grava true", cfg.get("notificar_operador") is True)
checa("PASS: saída confirma ligado", "🔔 ligado" in r.stdout, r.stdout)
shutil.rmtree(raiz, ignore_errors=True)

# ── 3. Mesmo label, mas outra sala: é sino inútil para esta e não pode ligar.
raiz, sala, casa, env = laboratorio()
outra = raiz / "outra-sala"
outra.mkdir()
arma_daemon_fake(raiz, sala, casa, sala_vigiada=outra)
r = roda(env, "sino", "on")
cfg = config(sala)
saida = r.stdout + r.stderr
checa("REPROVA: daemon de outra sala não autoriza", r.returncode != 0, saida)
checa(
    "REPROVA: daemon de outra sala mantém false",
    cfg.get("notificar_operador") is False,
    json.dumps(cfg, ensure_ascii=False),
)
checa("outra sala é declarada sem fingir ausência", "outra sala" in saida.lower(), saida)
shutil.rmtree(raiz, ignore_errors=True)

# ── 4. Desligar é sempre seguro e não depende de daemon.
raiz, sala, _, env = laboratorio()
roda(env, "status")
cfg = config(sala)
cfg["notificar_operador"] = True
(sala / "config.json").write_text(
    json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
r = roda(env, "sino", "off")
checa("PASS: sino off não exige daemon", r.returncode == 0, r.stdout + r.stderr)
checa("PASS: sino off grava false", config(sala).get("notificar_operador") is False)
shutil.rmtree(raiz, ignore_errors=True)

print("— o sino mudo NÃO é silêncio do Mac inteiro, e ele precisa saber —")
# Auditoria cruzada de 18/08: três vizinhos chamam a notificação do macOS sem
# consultar `notificar_operador` — o alarme de queda de energia (que ele PEDIU),
# o relay, e o sino próprio de cada IA. Quem lê "🔕 mudo" e vai dormir supõe
# silêncio. O comando não desliga nada: cada um tem consentimento próprio. Só
# mostra o que existe, medido no launchctl.
raiz, sala, _plist, env = laboratorio()
r = roda(env, "sino")
saida = r.stdout + r.stderr
checa("o estado do sino do dono continua sendo a primeira coisa dita",
      "sino do operador:" in saida, saida)
checa("as outras fontes são listadas",
      "outras fontes que podem tocar" in saida,
      "sem esta lista, 'mudo' engana quem confia nele")
checa("cada fonte diz se obedece a este sino",
      "NÃO consulta este sino" in saida or "respeita este sino" in saida, saida)
checa("com o sino mudo, o aviso aparece",
      "🔕 mudo" not in saida or "ainda podem tocar" in saida,
      "dizer 'mudo' e não avisar do resto é a metade que engana")
checa("o comando ensina como silenciar cada uma",
      "🔕 mudo" not in saida or "launchctl unload" in saida)

# A listagem é LEITURA. Se ela desligasse algo, seria pior que o problema.
antes = config(sala).get("notificar_operador")
roda(env, "sino")
checa("listar não muda o estado do sino", config(sala).get("notificar_operador") == antes)
checa("listar não descarrega agente nenhum",
      "unload" not in saida.replace("launchctl unload <plist dela>", ""),
      "a linha de ajuda ensina o comando; o programa não o executa")
shutil.rmtree(raiz, ignore_errors=True)

print("\n%d ✔  %d ✗" % (_ok, _falhou))
sys.exit(1 if _falhou else 0)
