#!/usr/bin/env python3
"""Bateria do iachat-vacuum — a faxina da sala.

Costuras de isolamento (as mesmas do resto da bateria):
- IACHAT_HOME desvia a sala (iachat_core.py:57-59);
- HOME desvia as pastas de backup (~/.claude, ~/.codex).

Nada aqui toca a sala real nem apaga nada fora de /tmp (contrato i4, ⛔).
O vermelho é testado de propósito: dry-run que não apaga, backup mais recente
que nunca sai, flag de IA na sala que nunca vira lixo.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

FALHAS = 0


def checa(nome: str, condicao: bool, detalhe: str = "") -> None:
    global FALHAS
    if condicao:
        print(f"  ✔ {nome}")
    else:
        FALHAS += 1
        print(f"  ✗ {nome}" + (f" — {detalhe}" if detalhe else ""))


def roda(script: Path, args: list[str], env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True, text=True, env=env,
    )


def monta_sala(tmp: Path) -> tuple[Path, Path, dict]:
    """Sala + HOME falsos em /tmp, com lixo plantado em todas as zonas."""
    home, sala = tmp / "home", tmp / "sala"
    for d in (home / ".claude", home / ".codex", sala / "arquivo", sala / "pendente"):
        d.mkdir(parents=True)

    # 10 backups velhos da MESMA família (acima da cota 8) + 2 de hoje
    carimbo = datetime.now()
    for i in range(10):
        ts = (carimbo - timedelta(days=10 - i)).strftime("%Y%m%d-%H%M%S")
        (home / ".claude" / f"settings.json.bak-iachat-{ts}").write_text(f"backup {i}")
    hoje8 = carimbo.strftime("%Y%m%d")
    (home / ".claude" / f"settings.json.bak-iachat-{hoje8}-235959").write_text("mais novo")
    (home / ".claude" / f"settings.json.bak-iachat-{hoje8}-010101").write_text("de hoje")

    # log do sino com 300 linhas (teto: cauda 200)
    linhas = "\n".join(f"linha {i}" for i in range(300))
    (sala / "ia-bell-claude.log").write_text(linhas + "\n")
    (sala / "ia-bell-codex.out").write_text("x" * 70000)  # acima do teto de 64 KiB

    # .tmp órfão (alvo existe) velho de 2 h; novo; e alvo ausente
    (sala / "chat.md").write_text("alvo presente")
    velho = sala / "chat.md.tmp"
    velho.write_text("lixo")
    os.utime(velho, (time.time() - 7200,) * 2)
    (sala / "estado.json.tmp").write_text("novo")
    sem_alvo = sala / "fantasma.md.tmp"
    sem_alvo.write_text("unico dado")
    os.utime(sem_alvo, (time.time() - 7200,) * 2)
    (sala / "arquivo" / "lixo.md.tmp").write_text("proibido")  # zona proibida

    # pendente/: recado de IA na sala + flag de IA que saiu
    (sala / "pendente" / "claude.md").write_text("recado vivo")
    (sala / "pendente" / "grok.md").write_text("recado do grok")
    (sala / "config.json").write_text(json.dumps({"na_sala": ["claude", "codex", "kimi"]}))

    env = {**os.environ, "IACHAT_HOME": str(sala), "HOME": str(home)}
    return home, sala, env


def main() -> int:
    script = Path(__file__).resolve().parent.parent / "bin" / "iachat-vacuum"
    tmp = Path(tempfile.mkdtemp(prefix="vacuum-teste-"))
    try:
        home, sala, env = monta_sala(tmp)
        hoje8 = datetime.now().strftime("%Y%m%d")
        bak_dir = home / ".claude"
        bak_hoje = bak_dir / f"settings.json.bak-iachat-{hoje8}-235959"
        bak_velho = sorted(p for p in bak_dir.glob("*.bak-iachat-*")
                           if hoje8 not in p.name)[0]

        print("── 1. dry-run é o padrão ──")
        r = roda(script, [], env)
        checa("exit 0 no dry-run", r.returncode == 0, r.stderr.strip()[:200])
        checa("anuncia o plano", "APAGAR" in r.stdout and "backup" in r.stdout)
        checa("NÃO apaga nada", bak_velho.exists() and (sala / "chat.md.tmp").exists())
        checa("NÃO escreve registro em dry-run", not (sala / ".vacuum.log").exists())

        print("── 2. apagar recolhe o lixo ──")
        r = roda(script, ["--apagar"], env)
        checa("exit 0 no --apagar", r.returncode == 0, r.stderr.strip()[:200])
        todos = list((home / ".claude").glob("*.bak-iachat-*"))
        checa("cota respeitada: sobraram 8 de 12 backups", len(todos) == 8,
              f"sobraram {len(todos)}")
        checa("o backup MAIS VELHO foi o recolhido", not bak_velho.exists())
        checa("backup mais recente preservado (regra dura)", bak_hoje.exists())
        log = (sala / "ia-bell-claude.log").read_text()
        checa("log recortado para a cauda de 200 linhas", "linha 299" in log
              and "linha 99" not in log and "linha 100" in log)
        checa(".out acima do teto zerado", (sala / "ia-bell-codex.out").stat().st_size == 0)
        checa(".tmp órfão velho apagado", not (sala / "chat.md.tmp").exists())
        checa(".tmp novo intacto (escrita em curso?)", (sala / "estado.json.tmp").exists())
        checa(".tmp sem alvo intacto (pode ser o único dado)", (sala / "fantasma.md.tmp").exists())
        checa(".tmp dentro de arquivo/ intocado (zona proibida)",
              (sala / "arquivo" / "lixo.md.tmp").exists())
        checa("recorte de arquivo/ intacto", (sala / "arquivo").exists())
        checa("flag de IA na sala preservada (recado não lido)",
              (sala / "pendente" / "claude.md").exists())
        checa("flag de IA fora da sala removida", not (sala / "pendente" / "grok.md").exists())
        registro = (sala / ".vacuum.log").read_text()
        checa("tudo registrado no .vacuum.log", "grok" in registro and "recado do grok" in registro)

        print("── 3. idempotente ──")
        r = roda(script, ["--json"], env)
        saida = json.loads(r.stdout)
        checa("2ª rodada sem ações", saida["acoes"] == [])
        checa("2ª rodada diz quando foi a anterior", bool(saida.get("ultima_rodada")))
        r2 = roda(script, ["--apagar"], env)
        checa("2ª rodada com --apagar é não-evento (exit 0)", r2.returncode == 0)

        print("── 4. vermelho que o gate precisa ver ──")
        # família agora: bak_hoje + bak_hoje2 (hoje) + 6 velhos que sobraram da cota
        bak_hoje2 = bak_dir / f"settings.json.bak-iachat-{hoje8}-010101"
        velho_vivo = sorted(p for p in bak_dir.glob("*.bak-iachat-*")
                            if hoje8 not in p.name)[0]
        r = roda(script, ["--manter", "1"], env)  # dry-run: cota 1, sem incluir hoje
        plano = r.stdout.split("plano:", 1)[-1]
        checa("--manter 1 põe backup velho no plano", velho_vivo.name in plano)
        checa("backup de hoje fora da cota segue protegido sem --incluir-hoje",
              bak_hoje2.name not in plano)
        checa("dry-run NÃO executa", velho_vivo.exists() and bak_hoje2.exists())
        r = roda(script, ["--incluir-hoje", "--manter", "1"], env)
        plano2 = r.stdout.split("plano:", 1)[-1]
        checa("--incluir-hoje libera o backup de hoje fora da cota",
              bak_hoje2.name in plano2)
        checa("o mais recente da família NUNCA entra no plano",
              bak_hoje.name not in r.stdout)
        (sala / "config.json").unlink()  # sem na_sala ninguém julga flag
        r = roda(script, [], env)
        checa("sem config, nenhuma flag julgada (fail-closed)",
              "não li" in r.stdout and (sala / "pendente" / "claude.md").exists())
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"\n{'✔ bateria verde' if FALHAS == 0 else f'✗ {FALHAS} falha(s)'}")
    return 1 if FALHAS else 0


if __name__ == "__main__":
    sys.exit(main())
