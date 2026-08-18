#!/usr/bin/env python3
"""Gate do teste do estranho: o que o instalador e o README ensinam tem que existir
no clone, sem nada da máquina do autor.

Nascido da fase 11 (2026-08-18). Um estranho clonou os dois repositórios públicos,
rodou `./install.sh` com HOME descartável e PATH só `/usr/bin:/bin:/usr/sbin:/sbin`.
A sala funcionou. A interface funcionou. Depois ele copiou a última linha do
instalador — `iachat doctor` — e o CLI recusou:

    invalid choice: 'doctor'

O binário que existe é `iachat-doctor`. Mensagem que ensina um caminho que não
funciona é pior que mensagem nenhuma (mesma classe do teste_erro_ensina).

Este gate NÃO clona de novo (caro, rede). Mede o que o clone publicado entrega
neste disco: o texto que o instalador imprime, os subcomandos do CLI, a conta
das peças do README, e o `.sh` que `entrar` manda rodar sem pôr no PATH.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CLI = RAIZ / "bin" / "iachat"
INSTALL = RAIZ / "install.sh"
README = RAIZ / "README.md"

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


def roda(*args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    e = dict(os.environ)
    if env:
        e.update(env)
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        env=e,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=30,
    )


def roda_doctor(*args: str) -> subprocess.CompletedProcess:
    """Executa o binário irmão que o instalador põe no PATH."""
    doctor = RAIZ / "bin" / "iachat-doctor"
    return subprocess.run(
        [str(doctor), *args],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=30,
    )


def doctor_ensinado_funciona(texto: str) -> tuple[bool, str]:
    """Aceita as duas interfaces do contrato, mas prova a escolhida de verdade.

    A asserção é incondicional: corrigir a linha errada não pode fazer o teste
    desaparecer e transformar um placar 8/8 em um gate menor.
    """
    if re.search(r"\biachat-doctor\b", texto):
        doctor = RAIZ / "bin" / "iachat-doctor"
        if not (doctor.is_file() and os.access(doctor, os.X_OK)):
            return False, f"ensinou iachat-doctor, mas {doctor} não é executável"
        r = roda_doctor("--help")
        return r.returncode == 0, (
            f"iachat-doctor --help saiu {r.returncode}: "
            f"{(r.stderr + r.stdout).strip()[:240]!r}"
        )

    if re.search(r"\biachat doctor\b", texto):
        r = roda("doctor", "--help")
        return r.returncode == 0, (
            f"iachat doctor --help saiu {r.returncode}: "
            f"{(r.stderr + r.stdout).strip()[:240]!r}"
        )

    return False, "não ensinou nem iachat-doctor nem iachat doctor"


def instala_em_sandbox() -> tuple[subprocess.CompletedProcess, Path]:
    """Roda o instalador como um clone novo, sem tocar a instalação do dono."""
    raiz = Path(tempfile.mkdtemp(prefix="iachat-install-limpo-"))
    destino_bin = raiz / "bin"
    e = dict(os.environ)
    e.update(
        {
            "HOME": str(raiz / "home"),
            "IACHAT_SCRIPTS": str(raiz / "scripts"),
            "IACHAT_SKILLS": str(raiz / "skills"),
            "IACHAT_BIN": str(destino_bin),
            "IACHAT_HOME": str(raiz / "sala"),
            "PATH": f"{destino_bin}:{e.get('PATH', '')}",
            "SHELL": "/bin/zsh",
        }
    )
    r = subprocess.run(
        ["/bin/bash", str(INSTALL)],
        env=e,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=60,
    )
    return r, destino_bin


def subcomandos() -> set[str]:
    r = roda("--help")
    texto = r.stdout + r.stderr
    m = re.search(r"\{([^}]+)\}", texto)
    if not m:
        return set()
    return {p.strip() for p in m.group(1).split(",") if p.strip()}


def main() -> int:
    print("teste_clone_limpo — o que o estranho copia tem que existir")

    home = Path(tempfile.mkdtemp(prefix="clone-limpo-")) / "sala"
    env = {"IACHAT_HOME": str(home)}
    roda("status", env=env)  # cria a sala

    cmds = subcomandos()
    checa("iachat --help lista subcomandos", bool(cmds),
          f"stdout/stderr sem {{a,b,c}}: {(roda('--help').stdout + roda('--help').stderr)[:240]!r}")

    # ── 1. o instalador não ensina `iachat X` que o CLI recusa ──────────────
    instalador = INSTALL.read_text(encoding="utf-8")
    ensinados = sorted(set(re.findall(r"\biachat ([a-z][a-z0-9-]*)", instalador)))
    print(f"  · install.sh ensina: {ensinados or '(nenhum subcomando iachat X)'}")
    for nome in ensinados:
        r = roda(nome, "--help", env=env)
        recusa = r.returncode != 0 and "invalid choice" in (r.stderr + r.stdout)
        checa(f"install.sh ensina `iachat {nome}` e o CLI aceita",
              not recusa,
              f"exit={r.returncode} stderr={r.stderr.strip()[:200]!r} — "
              f"o binário irmão é iachat-{nome}; o estranho copia a linha e quebra")

    doctor_ok, doctor_detalhe = doctor_ensinado_funciona(instalador)
    checa("install.sh ensina um comando de doctor que executa",
          doctor_ok,
          doctor_detalhe)

    # a skill da compactação repete a mesma linha errada
    compacta = RAIZ / "skills" / "ia-compactacao" / "SKILL.md"
    compacta_texto = compacta.read_text(encoding="utf-8") if compacta.is_file() else ""
    compacta_ok, compacta_detalhe = doctor_ensinado_funciona(compacta_texto)
    checa("ia-compactacao/SKILL.md ensina um doctor que executa",
          compacta_ok,
          compacta_detalhe)

    # o nome certo tem que existir — senão o conserto vira apagar o diagnóstico
    doctor = RAIZ / "bin" / "iachat-doctor"
    checa("bin/iachat-doctor existe e é executável",
          doctor.is_file() and os.access(doctor, os.X_OK),
          f"{doctor} ausente ou sem +x")

    # ── 2. "As N peças" do README = pastas em skills/ ──────────────────────
    readme = README.read_text(encoding="utf-8")
    m = re.search(r"## As (\d+) peças", readme)
    checa("README tem a seção 'As N peças'", bool(m),
          "não achei o título; o gate ficou cego")
    n_titulo = int(m.group(1)) if m else -1
    skills = sorted(p.name for p in (RAIZ / "skills").iterdir() if p.is_dir())
    secao = readme.split("## As ", 1)[-1].split("##", 1)[0] if m else ""
    citadas = set(re.findall(r"`(ia-[a-z0-9-]+)`", secao))
    extras = sorted(set(skills) - citadas)
    faltam = sorted(citadas - set(skills))
    checa(f"README diz {n_titulo} peças e skills/ tem {len(skills)}",
          n_titulo == len(skills) and not extras and not faltam,
          f"título={n_titulo} disco={len(skills)} extras={extras} faltam={faltam}")

    # ── 3. `entrar` não ensina um .sh que o instalador recusou pôr no PATH ─
    r = roda("entrar", "estranho", env=env)
    saida = r.stdout + r.stderr
    m_sh = re.search(r"rode:\s+(\S*ia-bell-install-daemon\.sh)\b", saida)
    if m_sh:
        ensinado = m_sh.group(1)
        e_script = (ensinado.startswith("/") or ensinado.startswith("~")
                    or "/" in ensinado)
        if e_script:
            alvo = Path(os.path.expanduser(ensinado))
            comando_resolve = alvo.is_file() and os.access(alvo, os.X_OK)
            detalhe = f"ensinou caminho {ensinado!r}, mas ele não é executável"
        else:
            instalacao, destino_bin = instala_em_sandbox()
            alvo = destino_bin / ensinado
            comando_resolve = (instalacao.returncode == 0 and alvo.is_file()
                               and os.access(alvo, os.X_OK))
            detalhe = (
                f"ensinou {ensinado!r}; install exit={instalacao.returncode}; "
                f"alvo={alvo} existe={alvo.is_file()} executável={os.access(alvo, os.X_OK)}; "
                f"stderr={(instalacao.stderr or '').strip()[:180]!r}"
            )
        checa("`entrar` ensina um comando de daemon que resolve após instalar",
              comando_resolve,
              detalhe)
    else:
        checa("`entrar` avisou falta de sino (senão este item não mede)",
              "sino" in saida.lower(),
              f"saída sem 'rode: ia-bell-install-daemon.sh': {saida[:240]!r}")

    print(f"\n{_ok} ✔  {_falhou} ✗")
    return 1 if _falhou else 0


if __name__ == "__main__":
    raise SystemExit(main())
