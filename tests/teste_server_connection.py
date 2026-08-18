#!/usr/bin/env python3
"""teste_server_connection.py — o sino da infraestrutura, provado nos dois lados.

O que este teste existe para impedir, concretamente: que o vigia que deveria avisar
sobre a queda seja ele próprio silencioso. Um sino que não toca é indistinguível de
"não aconteceu nada" — e foi assim que um worker perdeu 20 minutos em 18/08.

Todos os casos rodam com estado FORJADO em `IACHAT_HOME` temporário: é a única forma de
provar transições (energia caiu, IP mudou) sem esperar a energia cair de verdade.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DAEMON = RAIZ / "bin" / "ia-server-connection-daemon.sh"

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


def sala_nova(estado: dict | None, ias=("claude", "codex", "kimi")) -> Path:
    """Uma sala temporária com estado anterior forjado."""
    home = Path(tempfile.mkdtemp(prefix="netbell-"))
    (home / "pendente").mkdir()
    (home / "rede").mkdir()
    (home / "config.json").write_text(json.dumps({"na_sala": list(ias)}))
    if estado is not None:
        (home / ".rede-estado.json").write_text(json.dumps(estado))
    return home


def roda(home: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ, IACHAT_HOME=str(home))
    return subprocess.run(["bash", str(DAEMON), "--uma-vez"],
                          env=env, capture_output=True, text=True, timeout=30)


def flags(home: Path) -> dict[str, str]:
    return {p.stem: p.read_text() for p in (home / "pendente").glob("*.md")}


def energia_real() -> str:
    r = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True)
    return "tomada" if "AC Power" in r.stdout else "bateria"


def energia_oposta() -> str:
    """O oposto do estado de energia AGORA.

    Transição só existe contra o real: se a máquina está na tomada e eu forjar "tomada"
    como anterior, não há evento nenhum e o caso passa vazio — provando nada. Forjando o
    oposto, o ciclo enxerga uma transição verdadeira e o sino tem que tocar.
    """
    r = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True)
    return "bateria" if "AC Power" in r.stdout else "tomada"


def ip_real() -> str:
    """O IP desta máquina agora.

    Os casos precisam dele para ISOLAR um sino por vez: forjar um IP diferente do real
    dispara o connection-bell junto com o que se queria testar, e aí o caso não prova
    nada sobre a separação dos dois sinos.
    """
    r = subprocess.run(["ipconfig", "getifaddr", "en0"], capture_output=True, text=True)
    return r.stdout.strip() or "-"


print("teste_server_connection")

# ── 1. o executável existe ───────────────────────────────────────────────────
checa("daemon presente e executável", DAEMON.is_file() and os.access(DAEMON, os.X_OK),
      f"não achei {DAEMON}")

# ── 2. primeira execução NÃO toca o sino ─────────────────────────────────────
# Sem estado anterior não há transição. Sino que toca ao nascer treina todo mundo a
# ignorá-lo — e aí, no dia real, ninguém olha.
home = sala_nova(None)
roda(home)
checa("primeira execução não cria flag", flags(home) == {},
      f"criou {list(flags(home))} sem transição nenhuma")
checa("primeira execução grava o estado", (home / ".rede-estado.json").is_file())
shutil.rmtree(home, ignore_errors=True)

# ── 3. energia caiu → avisa TODAS as IAs da sala ─────────────────────────────
home = sala_nova({"energia": energia_oposta(), "ip": ip_real(), "rede": "no-ar"})
roda(home)
f = flags(home)
checa("energia: avisou as 3 IAs da sala", len(f) == 3, f"avisou {list(f)}")
checa("energia: o aviso é do energy-bell, com nome próprio",
      all("energy-bell" in v and "⚡" in v for v in f.values()) if f else False,
      "os dois sinos precisam ser distinguíveis no flag — conduta diferente, nome diferente")
checa("energia: NÃO se disfarça de connection-bell",
      all("connection-bell" not in v for v in f.values()) if f else False)
checa("energia: o dossiê de eventos foi escrito",
      (home / "rede" / "EVENTOS.md").is_file())
shutil.rmtree(home, ignore_errors=True)

# ── 4. IP mudou → avisa, e o aviso carrega o de-para ─────────────────────────
home = sala_nova({"energia": energia_real(), "ip": "10.0.0.99", "rede": "no-ar"})
roda(home)
ev = (home / "rede" / "EVENTOS.md")
texto = ev.read_text() if ev.is_file() else ""
checa("IP: detectou a mudança", "IP MUDOU" in texto, texto[:200])
checa("IP: o aviso mostra o endereço antigo", "10.0.0.99" in texto,
      "sem o de-para, quem lê não sabe qual URL morreu")
shutil.rmtree(home, ignore_errors=True)

# ── 5. O FLAG ACUMULA — este é o caso que REPROVA ────────────────────────────
# Um sino que sobrescreve o chamado anterior faz a IA anunciar o último e perder os
# outros. Já aconteceu de verdade com o flag do Codex: anunciou #15 com 5 pendentes
# atrás. Se alguém trocar o append por escrita, este caso fica vermelho.
home = sala_nova({"energia": energia_real(), "ip": "10.0.0.99", "rede": "no-ar"})
(home / "pendente" / "claude.md").write_text(
    "# 🔔 claude, você foi chamado no ia-chat\n\n## Chamados pendentes\n\n"
    "- #42 de codex — MENSAGEM ANTERIOR QUE NÃO PODE SUMIR\n"
)
roda(home)
depois = (home / "pendente" / "claude.md").read_text()
checa("flag ACUMULA: o chamado anterior sobreviveu",
      "MENSAGEM ANTERIOR QUE NÃO PODE SUMIR" in depois,
      "o aviso de rede sobrescreveu um chamado pendente — sino que apaga é pior que sino nenhum")
checa("flag ACUMULA: o aviso novo também está lá", "-bell" in depois)
shutil.rmtree(home, ignore_errors=True)

# ── 5b. os DOIS sinos são distinguíveis, e o IP é connection ─────────────────
# A premissa do dono: uma skill, DUAS notificações com nomes diferentes, um gatilho.
# Se os dois avisos saírem com o mesmo rótulo, a IA não sabe se tem segundos (energia)
# ou minutos (conexão) — e a conduta é oposta.
home = sala_nova({"energia": energia_real(), "ip": "10.0.0.99", "rede": "no-ar"})
roda(home)
ev = (home / "rede" / "EVENTOS.md").read_text()
checa("IP entra como connection-bell, não energy-bell",
      "connection-bell" in ev and "energy-bell" not in ev, ev[:220])
shutil.rmtree(home, ignore_errors=True)

# ── 5c. no-bell REGISTRA e NÃO acorda ───────────────────────────────────────
# O grupo mais importante do desenho: silêncio MEDIDO é decisão; silêncio não
# registrado é omissão. Uma oscilação de um ciclo fica no dossiê e não cria flag.
home = sala_nova({"energia": "tomada", "ip": "-", "rede": "fora", "falhas": 0})
roda(home)
ev = (home / "rede" / "EVENTOS.md")
texto = ev.read_text() if ev.is_file() else ""
if "no-bell" in texto:
    checa("no-bell: registrou no dossiê", True)
    checa("no-bell: NÃO criou flag para ninguém", flags(home) == {},
          f"acordou {list(flags(home))} numa oscilação de 1 ciclo")
else:
    # A rede real está no ar, então a transição fora→no-ar não gerou no-bell:
    # o caso não se aplica neste ambiente, e dizer isso é melhor que fingir que passou.
    checa("no-bell: caso não exercitado neste ambiente (rede no ar)", True)
    checa("no-bell: sem flag indevido mesmo assim", "energy-bell" not in "".join(flags(home).values()))
shutil.rmtree(home, ignore_errors=True)

# ── 6. sem transição, sem sino (o outro lado do gate) ────────────────────────
# Roda uma vez para capturar o estado REAL, e roda de novo: nada mudou entre as duas,
# então nada pode tocar. Se este caso ficar vermelho, o vigia é um gerador de ruído.
home = sala_nova(None)
roda(home)
roda(home)
checa("estado estável não toca o sino", flags(home) == {},
      f"tocou sem nada mudar: {list(flags(home))}")
shutil.rmtree(home, ignore_errors=True)

# ── 7. sensor mudo não vira 'está tudo bem' ──────────────────────────────────
# O terceiro desfecho ('?') nunca pode ser confundido com um valor bom: uma transição
# de '?' para 'tomada' NÃO é "a energia voltou", é "voltei a enxergar".
home = sala_nova({"energia": "?", "ip": "-", "rede": "?"})
roda(home)
checa("saindo de sensor mudo, não inventa evento", flags(home) == {},
      "tratou 'não consegui olhar' como transição real")
shutil.rmtree(home, ignore_errors=True)

# ── 8 e 9. os dois bugs achados pelo AUDITOR EXTERNO em 18/08 ────────────────
# Achados pelo ollama `kimi-k3`, que não escreveu esta peça — auditor ≠ autor funcionando.
# Ficam aqui para sempre: bug encontrado que não vira teste volta.
#
# Os dois usam sensores FALSOS num PATH temporário. É a única forma de provar o
# comportamento sem esperar a energia cair de verdade ou derrubar a internet do dono.
def com_sensor_falso(estado: dict, binarios: dict[str, str]) -> str:
    """Roda um ciclo com sensores forjados e devolve o dossiê de eventos."""
    home = sala_nova(estado, ias=("claude",))
    fake = home / "fakebin"
    fake.mkdir()
    for nome, corpo in binarios.items():
        (fake / nome).write_text(corpo)
        (fake / nome).chmod(0o755)
    subprocess.run(
        ["bash", str(DAEMON), "--uma-vez"],
        env=dict(os.environ, IACHAT_HOME=str(home), PATH=f"{fake}:{os.environ['PATH']}"),
        capture_output=True, timeout=30,
    )
    ev = home / "rede" / "EVENTOS.md"
    texto = ev.read_text() if ev.is_file() else ""
    shutil.rmtree(home, ignore_errors=True)
    return texto


# BUG 1 — o sensor piscou e a energia caiu de verdade.
# Antes: `ANT_E="?"` bloqueava o sino E virava "bateria" no estado, então a queda ficava
# engolida PARA SEMPRE. O alarme mais importante do sistema, morto por uma leitura falha.
t = com_sensor_falso(
    {"energia": "?", "ip": "-", "rede": "no-ar"},
    {"pmset": "#!/bin/bash\necho \"Now drawing from 'Battery Power'\"\n"},
)
checa("BUG do auditor: '?' → bateria TOCA o energy-bell",
      "energy-bell" in t and "ENERGIA CAIU" in t,
      "a queda de energia foi engolida porque a leitura anterior falhou — "
      "é o pior desfecho possível desta peça")

# BUG 2 — queda SUSTENTADA de conexão.
# Antes o sino exigia `R != ANT_R`, e numa queda contínua só existe UMA borda: o ciclo 1
# dava no-bell e do ciclo 2 em diante `fora == fora`, sem borda. A rede podia ficar fora
# por horas em silêncio absoluto.
t = com_sensor_falso(
    {"energia": "tomada", "ip": "-", "rede": "fora", "falhas": 1},
    {"curl": "#!/bin/bash\nexit 1\n", "ping": "#!/bin/bash\nexit 1\n"},
)
checa("BUG do auditor: 2º ciclo fora TOCA o connection-bell",
      "connection-bell" in t and "CONEXÃO FORA" in t,
      "queda sustentada ficava em silêncio: o sino dependia de borda, e numa queda "
      "contínua não há segunda borda")

# ── 10. intervalo inválido RECUSA, em vez de virar busy-wait ─────────────────
# Medido na máquina do dono em 18/08: o plist do LaunchAgent nasceu com `--help` no
# lugar do intervalo. O script não tratava `--help`, ele caía como valor, `sleep --help`
# falhava a cada volta, e o laço passou a **girar sem pausa** — batendo na API a cada
# iteração por nove minutos e escrevendo 176 KB de "sleep: illegal option" num `.err`
# que ninguém lia.
#
# O que torna este caso obrigatório: **a vigília parecia viva**. `launchctl` mostrava pid
# e exit 0, o `.rede-estado.json` era atualizado, e o instalador tinha dito "✔ no ar".
# Todo sinal apontava saúde. Um vigia que arde em busy-wait enquanto reporta normalidade
# é o defeito que esta peça existe para não deixar acontecer — nela mesma.
for _arg, _esperado in (("abc", 2), ("0", 2), ("-5", 2), ("--help", 0), ("20", None)):
    if _esperado is None:
        continue          # 20 é válido: o daemon entraria no laço e não voltaria
    _r = subprocess.run(["bash", str(DAEMON), _arg],
                        env=dict(os.environ, IACHAT_HOME=str(sala_nova(None))),
                        capture_output=True, text=True, timeout=20)
    checa(f"intervalo {_arg!r} → exit {_esperado}", _r.returncode == _esperado,
          f"saiu {_r.returncode}. Valor não-numérico aceito faz o sleep falhar e o "
          f"laço girar sem pausa, batendo na rede a cada volta.")

print(f"\n{_ok} ✔  {_falhou} ✗")
sys.exit(1 if _falhou else 0)
