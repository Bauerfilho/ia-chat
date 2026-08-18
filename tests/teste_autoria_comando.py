#!/usr/bin/env python3
"""teste_autoria_comando.py — o dono só assina o que ele digitou.

Os comandos de `iachat-comando` são DELE: `--de` tem padrão `bauer` para que ele não
precise se identificar na própria máquina. O buraco aparece quando uma IA dispara o
mesmo comando: sem `--de`, a mensagem sai assinada por ele — e as outras IAs leem a
sala e OBEDECEM. Esta casa já teve uma mensagem-fantasma assinada `bauer` que ele não
escreveu.

Três defeitos da MESMA classe, achados em 18/08 pelo worker `g2-ciclo-comandos` numa
rodada com o dono dormindo:

  A. `prompt_de` dizia "O DONO da máquina definiu este objetivo" mesmo quando o goal
     era de outra pessoa — o estado já gravava `"de"`, e o template ignorava.
  B. o alvo padrão do `/plan` era `na_sala` menos o brain; com `bauer` na sala (ele
     entrou pelo app), o comando tentaria despachar o HUMANO como worker.
  C. `--de` tinha default `bauer`: assinar como ele estava a um flag de distância.

O que os três têm em comum: o comando assumia que quem dispara é o dono. Era verdade
quando `bauer` não estava em `na_sala`. Deixou de ser, e o código não soube.

Este gate roda em `IACHAT_HOME` temporário: a sala viva nunca é tocada.
"""
from __future__ import annotations

import json
import os
import pty
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CMD = RAIZ / "bin" / "iachat-comando"

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


def sala_nova() -> tuple[Path, dict]:
    """Sala descartável. Nunca a viva."""
    home = Path(tempfile.mkdtemp(prefix="autoria-")) / "sala"
    return home, dict(os.environ, IACHAT_HOME=str(home))


def roda(env: dict, *args: str) -> tuple[int, str]:
    """Sem TTY — é assim que uma IA dispara: subprocesso, stdin fechado."""
    r = subprocess.run([sys.executable, str(CMD), *args], env=env,
                       capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=60)
    return r.returncode, r.stdout + r.stderr


def roda_com_tty(env: dict, *args: str) -> tuple[int, str]:
    """COM TTY — é assim que ELE dispara: digitando no terminal.

    `pty.openpty()` em vez de `script(1)`: o `script` do macOS falha com
    "tcgetattr/ioctl: Operation not supported on socket" quando o processo pai já não
    tem terminal — que é exatamente o caso de qualquer agente rodando isto. Um teste
    que não roda no ambiente onde precisa rodar não é teste.
    """
    mestre, escravo = pty.openpty()
    try:
        r = subprocess.run([sys.executable, str(CMD), *args], env=env,
                           capture_output=True, text=True, stdin=escravo, timeout=60)
        return r.returncode, r.stdout + r.stderr
    finally:
        os.close(mestre)
        os.close(escravo)


def autor_gravado(home: Path) -> str:
    p = home / "comando" / "estado.json"
    if not p.is_file():
        return "(sem estado)"
    return json.loads(p.read_text(encoding="utf-8")).get("de", "(sem campo)")


print("teste_autoria_comando")

# ── C. o guarda-corpo do `--de` ─────────────────────────────────────────────
# A prova que importa: sem terminal e sem `--de`, o comando RECUSA em vez de assinar
# como ele. É a diferença entre um gate e um adorno.
home, env = sala_nova()
código, saída = roda(env, "goal", "objetivo qualquer", "--calado")
checa("sem TTY e sem --de: RECUSA", código != 0 and "sem terminal" in saída,
      f"exit={código} · {saída.strip()[:150]}")
checa("a recusa ensina o conserto", "--de claude" in saída,
      f"a mensagem não mostra a saída: {saída.strip()[:120]}")
checa("nada foi gravado na recusa", not (home / "comando" / "estado.json").is_file(),
      "recusou mas gravou estado — a recusa tem que ser total")

# Com `--de` explícito, passa e assina quem falou.
código, saída = roda(env, "goal", "objetivo da orquestradora", "--de", "claude", "--calado")
checa("sem TTY e com --de: PASSA", código == 0, f"exit={código} · {saída.strip()[:150]}")
checa("assina quem falou, não o dono", autor_gravado(home) == "claude",
      f"gravou {autor_gravado(home)!r}")

# Com TTY — ele, no terminal dele — o padrão `bauer` continua valendo. Sem isto o
# conserto viraria um estorvo para o dono: ele teria que digitar `--de bauer` na
# própria máquina, e um gate que atrapalha o usuário legítimo é trocar um defeito
# por outro.
home2, env2 = sala_nova()
código, saída = roda_com_tty(env2, "goal", "objetivo dele", "--calado")
checa("COM TTY e sem --de: PASSA (é ele digitando)", código == 0,
      f"exit={código} · {saída.strip()[:150]}")
checa("COM TTY o padrão continua sendo o dono", autor_gravado(home2) == "bauer",
      f"gravou {autor_gravado(home2)!r} — o padrão do dono foi perdido")

# `decidi` é o pior caso da classe: registra decisão que TODAS obedecem.
home3, env3 = sala_nova()
código, saída = roda(env3, "decidi", "uma decisão qualquer", "--porque", "prova")
checa("`decidi` sem TTY e sem --de: RECUSA", código != 0 and "sem terminal" in saída,
      f"exit={código} · {saída.strip()[:150]}")

# ── A. o template não põe palavra na boca dele ──────────────────────────────
# Sem subprocesso: importa o módulo e chama a função. O template é string pura, e
# testá-lo por dentro é mais barato e mais direto que despachar braço de verdade.
sys.path.insert(0, str(RAIZ / "bin"))
import importlib.machinery
import importlib.util

spec = importlib.util.spec_from_loader(
    "iachat_comando", importlib.machinery.SourceFileLoader("iachat_comando", str(CMD)))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

e_dono = {"id": "m1", "goal": "G", "dir": str(home), "de": "bauer"}
e_ia = {"id": "m1", "goal": "G", "dir": str(home), "de": "claude"}

p_dono = mod.prompt_de("codex", e_dono, "papel")
p_ia = mod.prompt_de("codex", e_ia, "papel")

checa("goal DO DONO: o worker lê que é do dono", "O DONO da máquina definiu" in p_dono,
      p_dono[:160])
checa("goal DE UMA IA: o worker NÃO lê que é do dono",
      "O DONO da máquina definiu" not in p_ia, p_ia[:160])
checa("goal DE UMA IA: a procedência é declarada",
      "claude PROPÔS" in p_ia and "NÃO é ordem do dono" in p_ia, p_ia[:200])

# ── B. o dono não é operário ────────────────────────────────────────────────
# `na_sala` com ele dentro (o estado real desde que entrou pelo app).
home4, env4 = sala_nova()
# Quem cria a estrutura da sala é o `iachat`, não o `iachat-comando`: o comando trabalha
# numa sala que já existe. Sem este passo o `config.json` não nasce e o teste morre com
# FileNotFoundError — que é falha do TESTE, não do produto.
subprocess.run([sys.executable, str(RAIZ / "bin" / "iachat"), "status"],
               env=env4, capture_output=True, stdin=subprocess.DEVNULL, timeout=60)
subprocess.run([sys.executable, str(CMD), "goal", "g", "--de", "claude", "--calado"],
               env=env4, capture_output=True, stdin=subprocess.DEVNULL, timeout=60)
cfg = home4 / "config.json"
c = json.loads(cfg.read_text(encoding="utf-8"))
c["na_sala"] = ["claude", "codex", "kimi", "bauer"]
c["brain"] = "claude"
cfg.write_text(json.dumps(c, ensure_ascii=False, indent=2), encoding="utf-8")

código, saída = roda(env4, "plan", "--de", "claude", "--seco")
checa("`plan --seco` roda com o dono na sala", código == 0, f"exit={código} · {saída[:150]}")
checa("o dono NÃO entra como worker", "bauer" not in saída.lower(),
      f"o humano foi despachado como IA:\n      {saída.strip()[:200]}")
checa("as IAs entram", "codex" in saída and "kimi" in saída, saída.strip()[:150])

# ── M1. os OUTROS pontos de assinatura ──────────────────────────────────────
# A auditoria h2 provou que este gate ficava 14 ✔ com o `cmd_concluir` INTEIRO
# revertido ao pré-fix: cobria `goal` e `decidi` e deixava `concluir`, `parar` e
# `colher` sem um único caso. `concluir` é o pior lugar para essa cegueira — é o
# comando que AUTORIZA APLICAR, o único que muda o mundo.
#
# Exercitar de verdade custa montar o cenário: `concluir` recusa antes de assinar se
# não houver plano no disco. Um teste que se contentasse com essa recusa mediria a
# validação de plano, não a autoria — verde pelo motivo errado.
home5, env5 = sala_nova()
subprocess.run([sys.executable, str(RAIZ / "bin" / "iachat"), "status"],
               env=env5, capture_output=True, stdin=subprocess.DEVNULL, timeout=60)
roda(env5, "goal", "objetivo para autorizar", "--de", "claude", "--calado")

est = home5 / "comando" / "estado.json"
e = json.loads(est.read_text(encoding="utf-8"))
plano = Path(e["dir"]) / "planos" / "codex.md"
plano.parent.mkdir(parents=True, exist_ok=True)
plano.write_text("# plano de mentira, com corpo\n", encoding="utf-8")
e["workers"] = {"codex": {"plano": str(plano), "estado": "entregue"}}
est.write_text(json.dumps(e, ensure_ascii=False, indent=2), encoding="utf-8")

código, saída = roda(env5, "concluir", "--calado")
checa("`concluir` sem TTY e sem --de: RECUSA", código != 0 and "sem terminal" in saída,
      f"exit={código} · {saída.strip()[:150]}")
checa("`concluir` recusado não autoriza nada",
      json.loads(est.read_text(encoding="utf-8")).get("estado") != "autorizada",
      "recusou a assinatura mas autorizou assim mesmo — o pior desfecho deste comando")

código, saída = roda(env5, "concluir", "--de", "claude", "--calado")
por = json.loads(est.read_text(encoding="utf-8")).get("autorizado", {}).get("por")
checa("`concluir` com --de: autoriza e registra quem", código == 0 and por == "claude",
      f"exit={código} · por={por!r}")

# `parar`: mata processo, então assina um aviso de aborto na sala.
home6, env6 = sala_nova()
subprocess.run([sys.executable, str(RAIZ / "bin" / "iachat"), "status"],
               env=env6, capture_output=True, stdin=subprocess.DEVNULL, timeout=60)
roda(env6, "goal", "objetivo para abortar", "--de", "claude", "--calado")
código, saída = roda(env6, "parar")
checa("`parar` sem TTY e sem --de não assina pelo dono",
      "sem terminal" in saída or "bauer" not in saída.lower(),
      f"exit={código} · {saída.strip()[:150]}")

# `--de ""` — achado B2: gravava autor VAZIO, mensagem sem dono nenhum.
home7, env7 = sala_nova()
código, saída = roda(env7, "goal", "x", "--de", "", "--calado")
checa("`--de \"\"` é recusado (autor vazio não identifica ninguém)",
      código != 0 and "vazio" in saída.lower(),
      f"exit={código} · {saída.strip()[:150]}")

for h in (home, home2, home3, home4, home5, home6, home7):
    shutil.rmtree(h.parent, ignore_errors=True)

print(f"\n{_ok} ✔  {_falhou} ✗")
sys.exit(1 if _falhou else 0)
