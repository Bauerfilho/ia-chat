#!/usr/bin/env python3
"""Gates do ia-report: camada mecânica para o dono — sem IA aberta, sem mentira.
Roda a CLI em subprocesso com ``IACHAT_HOME`` temporário; nunca toca a sala real.
A prova vermelha: sala com bytes mas sem metadado NÃO pode virar "Sala vazia" —
o relatório falha em vez de mentir.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

CLI = Path(__file__).resolve().parent.parent / "bin" / "iachat-report"

falhas: list[str] = []


def checa(nome: str, condicao: bool, detalhe: str = "") -> None:
    print(f"{'✔' if condicao else '✗'} {nome}" + (f"  → {detalhe}" if detalhe else ""))
    if not condicao:
        falhas.append(nome)


def roda(env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        env=env,
        capture_output=True,
        text=True,
    )


def nova_sala() -> tuple[dict[str, str], Path]:
    tmp = tempfile.mkdtemp(prefix="ia-report-teste-")
    env = dict(os.environ, IACHAT_HOME=tmp)
    return env, Path(tmp) / "iachat.md"


def meta(n: int, de: str, para: str, ts: str) -> str:
    return f"<!-- iachat msg={n} de={de} para={para} ts={ts} -->"


def corpo(n: int, de: str, para: str, ts: str, texto: str) -> str:
    alvo = "@" + para if para != "-" else "a sala"
    return (
        meta(n, de, para, ts)
        + f"\n### 💬 #{n} · **{de}** → {alvo} · {ts[11:16]}\n\n{texto}\n"
    )


def agora_iso(minutos_atras: int = 0) -> str:
    dt = datetime.now().astimezone() - timedelta(minutes=minutos_atras)
    return dt.isoformat(timespec="seconds")


# ── Sala do cenário principal ───────────────────────────────────────────────
def sala_exemplo(chat: Path) -> None:
    msgs = [
        corpo(1, "claude", "codex", agora_iso(90), "Comecei a fase 6. Codex, olha o hook."),
        corpo(2, "codex", "-", agora_iso(80), "DECIDIDO: hook roda no boot."),
        corpo(3, "kimi", "bauer", agora_iso(70), "Preciso da palavra do dono sobre o caminho do sync."),
        corpo(4, "claude", "kimi", agora_iso(10), "Kimi, reescreve o teste no estilo novo."),
    ]
    chat.write_text(
        "# 💬 IA-CHAT\n\n" + "".join(msgs), encoding="utf-8"
    )


def main() -> int:
    # 1. Cenário principal: laço aberto, marca, endereçada ao dono.
    env, chat = nova_sala()
    sala_exemplo(chat)
    r = roda(env)
    checa("roda sem IA aberta (exit 0)", r.returncode == 0, r.stderr[:120])
    checa(
        "laço aberto detectado (kimi chamada na #4, sem resposta)",
        "**kimi**" in r.stdout and "#4" in r.stdout and "sem responder" in r.stdout,
    )
    checa(
        "estado do laço diz se o sino está tocando",
        "nem leu (sino tocando)" in r.stdout or "leu até #" in r.stdout,
    )
    checa(
        "marca DECIDIDO extraída",
        "**DECIDIDO**" in r.stdout and "hook roda no boot" in r.stdout,
    )
    checa(
        "endereçada ao dono listada",
        "Endereçado a você" in r.stdout and "#3" in r.stdout,
    )
    checa(
        "fio lista cada mensagem com autor e alvo",
        all(f"`#{n:>3}`" in r.stdout for n in (1, 2, 3, 4)),
    )
    checa(
        "declara o que NÃO julgou",
        "NÃO julgou" in r.stdout,
    )

    # 2. --desde: janela exclui o que ficou para trás (exclusivo: n > desde).
    r = roda(env, "--desde", "2")
    checa(
        "--desde 2 tira #1 e #2 do período",
        "`#  1`" not in r.stdout and "`#  2`" not in r.stdout and "`#  3`" in r.stdout,
    )
    secao = r.stdout.split("Parado esperando alguém")[1].split("\n##")[0]
    checa(
        "--desde: pendência é só a nominação DENTRO da janela",
        "**kimi**" in secao and "**codex**" not in secao,
    )

    # 3. --saida: arquivo para o celular/offline é escrito.
    saida = chat.parent / "relatorio.md"
    r = roda(env, "--saida", str(saida))
    checa(
        "--saida grava arquivo igual ao stdout (offline/celular)",
        saida.exists() and saida.read_text(encoding="utf-8") == r.stdout,
    )

    # 4. Sala vazia de verdade.
    env2, chat2 = nova_sala()
    r = roda(env2)
    checa("sala sem arquivo → sala vazia, exit 0", r.returncode == 0 and "Sala vazia" in r.stdout)

    # 5. PROVA VERMELHA — o caso que REPROVA se o relatório mentir:
    # sala com bytes mas nenhuma mensagem parseável NÃO pode virar "Sala vazia".
    env3, chat3 = nova_sala()
    chat3.write_text("# 💬 IA-CHAT\n\ntexto solto sem nenhum metadado\n", encoding="utf-8")
    r = roda(env3)
    checa(
        "REPROVA-SE MENTIR: bytes sem metadado → erro (exit 1), não 'Sala vazia'",
        r.returncode == 1 and "Sala vazia" not in r.stdout and r.stderr.strip() != "",
        f"exit={r.returncode}",
    )

    # 6. Marcador inline `#7` sobrevive à limpeza da primeira frase
    # (regressão do defeito histórico: regex comia o # de referência).
    env4, chat4 = nova_sala()
    chat4.write_text(
        "# 💬 IA-CHAT\n\n"
        + corpo(1, "claude", "codex", agora_iso(5), "Olha a minha #7 antes de mexer."),
        encoding="utf-8",
    )
    r = roda(env4)
    checa("referência #7 sobrevive no resumo", "#7" in r.stdout)

    print()
    if falhas:
        print(f"✗ {len(falhas)} gate(s) falharam: {', '.join(falhas)}")
        return 1
    print("✔ todos os gates passaram.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
