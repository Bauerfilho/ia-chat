#!/usr/bin/env python3
"""Gate do ia-ack — binário, fail-closed. Roda sobre uma RÉPLICA das 16 mensagens reais.

Nunca toca `~/ia-chat-global`: copia o `iachat.md` e os cursores para um IACHAT_HOME
temporário e mede lá. Um gate vermelho reprova a peça inteira.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ACK = AQUI.parent / "bin" / "iachat-ack"
REAL = Path("~/ia-chat-global").expanduser()
REPO = Path("~/Projetos/ia-chat").expanduser()

falhas = []


def ok(nome: str, cond: bool, detalhe: str = "") -> None:
    print(f"  {'✔' if cond else '✗'} {nome}" + (f"  · {detalhe}" if detalhe else ""))
    if not cond:
        falhas.append(nome)


def roda(*args, home: str) -> tuple[int, str]:
    # O core vem do repositório por PYTHONPATH — não se copia nada para dentro da peça.
    env = dict(os.environ, IACHAT_HOME=home, PYTHONPATH=str(REPO / "bin"))
    p = subprocess.run([sys.executable, str(ACK), *args], capture_output=True, text=True, env=env)
    return p.returncode, p.stdout + p.stderr


def monta(dst: Path) -> None:
    for sub in ("cursor", "pendente", "arquivo", ".lock", "ack"):
        (dst / sub).mkdir(parents=True, exist_ok=True)
    for f in ("iachat.md", "config.json", ".estado.json"):
        shutil.copy(REAL / f, dst / f)
    for c in (REAL / "cursor").glob("*.json"):
        shutil.copy(c, dst / "cursor" / c.name)


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="ia-ack-gate-"))
    home = str(tmp)
    monta(tmp)
    chat = tmp / "iachat.md"
    antes = chat.stat().st_size
    sinos_antes = sorted(p.name for p in (tmp / "pendente").glob("*"))

    # A unidade é o PAR (mensagem, destinatário), não a mensagem: #5 foi para `kimi,codex`,
    # o kimi respondeu e o codex não — meia mensagem respondida. As 16 mensagens reais
    # valem 17 pares: 9 respondidos, 5 mudos (codex nunca leu), 3 lidos-e-parados (claude).
    RESPONDIDOS = {(1, "codex"), (2, "claude"), (3, "claude"), (5, "kimi"), (6, "kimi"),
                   (7, "claude"), (8, "claude"), (9, "kimi"), (12, "kimi")}

    def pares(saida: str) -> set:
        r = set()
        for l in saida.splitlines():
            if l[:4] in ("mudo", "leu "):
                r.add((int(l.split("#")[1].split()[0]), l.split("→")[1].split()[0]))
        return r

    print("G1 · classifica os 8 silêncios reais em DOIS tipos distintos")
    rc, out = roda("pendentes", "--minutos", "15", home=home)
    mudo = [l for l in out.splitlines() if l.startswith("mudo")]
    leu = [l for l in out.splitlines() if l.startswith("leu")]
    ok("5 mudos por NÃO-LEITURA (codex, cursor #1)", len(mudo) == 5, f"achou {len(mudo)}")
    ok("3 mudos por NÃO-AÇÃO (claude, cursor #16)", len(leu) == 3, f"achou {len(leu)}")
    ok("os 5 mudos apontam o codex", all("codex" in l for l in mudo))
    ok("as 3 não-ações apontam a claude", all("claude" in l for l in leu))

    print("G2 · zero falso positivo: nenhum dos 9 pares respondidos aparece como aberto")
    ok("nenhum respondido listado", not (pares(out) & RESPONDIDOS),
       f"interseção {pares(out) & RESPONDIDOS}")

    print("G3 · timeout calibrado pela medida (resposta máxima real = 5,9 min)")
    rc6, out6 = roda("pendentes", "--minutos", "6", home=home)
    ok("com --minutos 6 ainda não pega respondido", not (pares(out6) & RESPONDIDOS),
       f"interseção {pares(out6) & RESPONDIDOS}")

    print("G4 · `recuso` sem motivo é recusado")
    rc, out = roda("marcar", "--de", "claude", "--msg", "13", "--estado", "recuso", home=home)
    ok("exit 2 e mensagem explícita", rc == 2 and "exige --nota" in out)

    print("G5 · confirmar não escreve na sala e não toca sino de ninguém")
    for n, e, nota in ((13, "fazendo", "rodando"), (14, "feito", "gate ok"), (16, "recuso", "fora do escopo")):
        rc, out = roda("marcar", "--de", "claude", "--msg", str(n), "--estado", e, "--nota", nota, home=home)
        ok(f"#{n} → {e}", rc == 0)
    ok("iachat.md inalterado", chat.stat().st_size == antes, f"{antes} → {chat.stat().st_size} B")
    ok("nenhum sino novo", sorted(p.name for p in (tmp / "pendente").glob("*")) == sinos_antes)

    print("G6 · `feito`/`recuso` fecham; `fazendo` continua aberto")
    rc, out = roda("linha", "--de", "kimi", home=home)
    ok("#13 (fazendo) continua na linha", "#13" in out)
    ok("#14 (feito) saiu", "#14" not in out)
    ok("#16 (recuso) saiu", "#16" not in out)

    print("G7 · calado quando não há o que dizer (o anti-spam)")
    rc, out = roda("linha", "--de", "codex", home=home)
    ok("saída vazia e exit 0", rc == 0 and out.strip() == "", repr(out[:60]))

    print("G8 · não aceita ack de quem não foi nominado nem de mensagem inexistente")
    rc, _ = roda("marcar", "--de", "codex", "--msg", "13", "--estado", "feito", home=home)
    ok("codex não pode confirmar #13 (kimi→claude)", rc == 2)
    rc, _ = roda("marcar", "--de", "claude", "--msg", "999", "--estado", "feito", home=home)
    ok("mensagem inexistente recusada", rc == 2)

    print("G9 · custo na janela da IA fica abaixo de 1 linha de mensagem (135 B de bloco × 2)")
    _, out = roda("linha", "--de", "claude", home=home)
    ok("≤ 300 B", len(out.encode()) <= 300, f"{len(out.encode())} B")

    shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{'TODOS OS GATES VERDES' if not falhas else 'REPROVADO: ' + ', '.join(falhas)}")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
