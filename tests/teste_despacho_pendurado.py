#!/usr/bin/env python3
"""Gates do teto CPU+escrita do iachat-despacho.

O PID vivo enganou o /plan: um worker a 0% CPU sem escrever o plano travou o
comando do dono. Este arquivo prova o detector — e tem o caso que REPROVA.

Nada da sala viva, nenhum worker real: tudo em mkdtemp. Missões `kpend-*`.
Não usa o comando `timeout` (não existe no macOS).
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DESPACHO = RAIZ / "bin" / "iachat-despacho.sh"

falhas: list[str] = []
faxina_pids: list[int] = []
faxina_sessoes: list[str] = []


def checa(nome: str, condicao: bool, detalhe: str = "") -> None:
    print(f"{'✔' if condicao else '✗'} {nome}" + (f"  ‣ {detalhe}" if detalhe else ""))
    if not condicao:
        falhas.append(nome)


def vivo_no_so(pid: int) -> bool:
    r = subprocess.run(
        ["ps", "-o", "state=", "-p", str(pid)], capture_output=True, text=True
    )
    est = r.stdout.strip()
    return r.returncode == 0 and est != "" and not est.startswith("Z")


def mata(pid: int) -> None:
    if pid <= 1:
        return
    try:
        os.kill(pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        pass


def cpu_de(pid: int) -> float:
    r = subprocess.run(
        ["ps", "-p", str(pid), "-o", "pcpu="], capture_output=True, text=True
    )
    bruto = (r.stdout or "0").strip().replace(",", ".")
    try:
        return float(bruto)
    except ValueError:
        return -1.0


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="iachat-pendurado-"))
    plano = tmp / "plano.md"
    log = tmp / "worker.log"
    env = {
        **os.environ,
        "IACHAT_PENDURADO_SEG": "3",
        "IACHAT_PENDURADO_AVISO_SEG": "2",
        "IACHAT_PENDURADO_CPU": "1.0",
        "PYTHON_DONTWRITEBYTECODE": "1",
    }

    try:
        checa(
            "G0 iachat-despacho.sh existe e é executável",
            DESPACHO.is_file() and os.access(DESPACHO, os.X_OK),
        )
        texto = DESPACHO.read_text(encoding="utf-8")
        checa(
            "G0b a Kimi sobe com --auto (não com kimi -p)",
            '"$KIMI_CMD" --auto' in texto or "kimi --auto" in texto,
            "adaptador kimi sem --auto",
        )
        checa(
            "G0c trap EXIT mata a sessão tmux",
            "trap" in texto and "kill-session" in texto,
        )

        # ---- T-RED: worker forjado sem CPU e sem escrita TEM que ser detectado
        sono = subprocess.Popen(
            ["sleep", "120"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        faxina_pids.append(sono.pid)
        time.sleep(1.2)
        cpu_sono = cpu_de(sono.pid)
        checa(
            "T-RED prep: o sleep está vivo e sem CPU (o sinal que enganou o gate)",
            vivo_no_so(sono.pid) and 0.0 <= cpu_sono < 1.0,
            f"pid={sono.pid} cpu={cpu_sono}",
        )
        t0 = time.time()
        det = subprocess.run(
            [str(DESPACHO), "--vigiar", str(sono.pid), str(plano), str(log)],
            env=env,
            capture_output=True,
            text=True,
            timeout=15,
        )
        durou = time.time() - t0
        vigia = Path(str(log).removesuffix(".log") + ".vigia")
        if not vigia.exists():
            vigia = tmp / "worker.vigia"
        corpo_vigia = vigia.read_text(encoding="utf-8") if vigia.exists() else det.stderr
        checa(
            "T-RED worker sem CPU e sem escrita é detectado (exit 4, não espera 1800s)",
            det.returncode == 4 and durou < 12 and "PENDURADO" in (corpo_vigia + det.stderr + det.stdout),
            f"rc={det.returncode} durou={durou:.1f}s stderr={det.stderr[:160]!r}",
        )

        # ---- quem ESCREVE o plano não é pendurado
        sono2 = subprocess.Popen(
            ["sleep", "20"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        faxina_pids.append(sono2.pid)
        plano_ok = tmp / "plano-ok.md"
        log_ok = tmp / "ok.log"

        def escreve_depois() -> None:
            time.sleep(0.8)
            plano_ok.write_text("plano de verdade\n", encoding="utf-8")

        import threading
        threading.Thread(target=escreve_depois, daemon=True).start()
        t1 = time.time()
        livre = subprocess.run(
            [str(DESPACHO), "--vigiar", str(sono2.pid), str(plano_ok), str(log_ok)],
            env=env,
            capture_output=True,
            text=True,
            timeout=15,
        )
        checa(
            "quem escreve o plano NÃO é declarado pendurado",
            livre.returncode == 0 and (time.time() - t1) < 8 and vivo_no_so(sono2.pid),
            f"rc={livre.returncode} vivo={vivo_no_so(sono2.pid)}",
        )
        mata(sono2.pid)

        # ---- quem QUEIMA CPU não toma o tiro (pode estar pensando)
        # `yes` é 90%+ CPU no ps desta máquina (medido). Espera o ps acusar
        # antes de vigiar — o %cpu do macOS atrasa no primeiro instante.
        busy = subprocess.Popen(
            ["yes"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        faxina_pids.append(busy.pid)
        cpu_b = 0.0
        for _ in range(15):
            time.sleep(0.2)
            cpu_b = cpu_de(busy.pid)
            if cpu_b >= 5.0:
                break
        checa(
            "prep: yes já queima CPU antes do vigia",
            vivo_no_so(busy.pid) and cpu_b >= 5.0,
            f"pid={busy.pid} cpu={cpu_b}",
        )
        env_curto = {**env, "IACHAT_PENDURADO_SEG": "3", "IACHAT_PENDURADO_AVISO_SEG": "2"}
        plano_b = tmp / "busy.md"
        log_b = tmp / "busy.log"
        try:
            pensante = subprocess.run(
                [str(DESPACHO), "--vigiar", str(busy.pid), str(plano_b), str(log_b)],
                env=env_curto,
                capture_output=True,
                text=True,
                timeout=8,
            )
            rc_busy = pensante.returncode
        except subprocess.TimeoutExpired:
            # ainda vigiando quem queima CPU: não saiu 4 no teto curto.
            rc_busy = 0
        checa(
            "quem queima CPU não é pendurado no teto curto",
            rc_busy != 4 and vivo_no_so(busy.pid),
            f"rc={rc_busy} cpu={cpu_de(busy.pid)}",
        )
        mata(busy.pid)

        # ---- integração: mock kimi que só dorme → despacho sai e a sessão morre
        mock = tmp / "kimi-mock"
        mock.write_text(
            "#!/bin/sh\necho \"$@\" > \"{}/argv\"\nsleep 120\n".format(tmp),
            encoding="utf-8",
        )
        mock.chmod(0o755)
        prompt = tmp / "prompt.txt"
        prompt.write_text("escreva o plano e saia\n", encoding="utf-8")
        missao = f"kpend{os.getpid()}"
        faxina_sessoes.append(f"iacmd-{missao}")
        plano_i = tmp / "plano-int.md"
        log_i = tmp / "int.log"
        env_i = {
            **env,
            "IACHAT_KIMI": str(mock),
            "IACHAT_KIMI_BOOT_SEG": "0",
            "IACHAT_KIMI_POLL_SEG": "1",
        }
        t2 = time.time()
        try:
            inte = subprocess.run(
                [str(DESPACHO), "kimi", missao, str(prompt), str(log_i), str(plano_i)],
                env=env_i,
                capture_output=True,
                text=True,
                timeout=20,
            )
        except subprocess.TimeoutExpired as ex:
            inte = subprocess.CompletedProcess(
                args=ex.cmd, returncode=99, stdout=ex.stdout or "", stderr=ex.stderr or "TIMEOUT"
            )
        durou_i = time.time() - t2
        sess = subprocess.run(
            ["tmux", "has-session", "-t", f"iacmd-{missao}"],
            capture_output=True,
        )
        argv = (tmp / "argv").read_text(encoding="utf-8") if (tmp / "argv").exists() else ""
        checa(
            "integração: mock sem escrita cai no teto, sessão tmux morre, --auto foi passado",
            inte.returncode == 4
            and durou_i < 15
            and sess.returncode != 0
            and "--auto" in argv,
            f"rc={inte.returncode} durou={durou_i:.1f}s tmux={sess.returncode} argv={argv!r}",
        )

    finally:
        for pid in faxina_pids:
            mata(pid)
        for s in faxina_sessoes:
            subprocess.run(
                ["tmux", "kill-session", "-t", s],
                capture_output=True,
            )

    if falhas:
        print(f"\n❌ {len(falhas)} falha(s): {', '.join(falhas)}", file=sys.stderr)
        return 1
    print("\n✅ DESPACHO PENDURADO — testes passaram")
    return 0


if __name__ == "__main__":
    sys.exit(main())
