#!/usr/bin/env python3
"""Gates do iachat-roster: o cadastro que separa visto de ausente de não-consigo-ver.

Roda o binário real em subprocesso, com IACHAT_HOME/HOME/PATH temporários; nunca
toca a sala real. `launchctl` é falsificado no PATH (como o doctor falsifica o
`iachat`) para controlar quais sinos existem; plists são plantados no HOME falso
para controlar para qual sala cada sino aponta.

Casos cobertos (contrato e6): IA presente · IA ausente · IA não-verificável ·
pasta vazia permanecendo vazia · chat PRÉ-EXISTENTE com histórico (a lição de
17/08: gate que só vê sala nova não pega defeito em sala viva) · e o caso que
REPROVA — a reprodução do incidente real (sino ausente + chamado parado 56 min),
que o instrumento é OBRIGADO a alarmar. Um gate que nunca viu vermelho não é gate.
"""
from __future__ import annotations

import json
import os
import plistlib
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

CLI = Path(__file__).resolve().parent.parent / "bin" / "iachat-roster"
falhas: list[str] = []


def checa(nome: str, condicao: bool, detalhe: str = "") -> None:
    print(f"{'✔' if condicao else '✗'} {nome}" + (f"  → {detalhe}" if detalhe else ""))
    if not condicao:
        falhas.append(nome)


def roda(env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    """Executa o binário real, sem importar nada de dentro dele."""
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        env=env, capture_output=True, text=True,
    )


def linha_de(stdout: str, ia: str) -> str:
    """A linha da tabela que começa com o nome da IA (vazio se não existir)."""
    for l in stdout.splitlines():
        if l.startswith(ia):
            return l
    return ""


def agora_iso(delta_s: float = 0.0) -> str:
    return (datetime.now().astimezone() - timedelta(seconds=delta_s)).isoformat()


def monta_sala(base: Path, na_sala: list[str], ultima: int | None = None,
               vocacao: dict | None = None) -> Path:
    """Sala pré-existente (nunca nova demais): config + estrutura + histórico."""
    sala = base / "sala"
    for d in (".lock", "cursor", "pendente", "arquivo"):
        (sala / d).mkdir(parents=True, exist_ok=True)
    # Chat COM histórico, no formato real de iachat.md (meta por mensagem).
    n_msgs = ultima if ultima is not None else 3
    corpo = "".join(
        f"<!-- iachat msg={n} de=claude em=2026-08-17T20:0{n}:00-03:00 -->\n"
        f"## claude · 20:0{n}\n\nmensagem {n}\n\n" for n in range(1, n_msgs + 1)
    )
    (sala / "iachat.md").write_text(corpo, encoding="utf-8")
    cfg: dict = {"na_sala": na_sala, "brain": na_sala[0] if na_sala else "",
                 "teto_bytes": 102400, "notificar_operador": True}
    if vocacao:
        cfg["vocacao"] = vocacao
    (sala / "config.json").write_text(json.dumps(cfg, ensure_ascii=False) + "\n",
                                      encoding="utf-8")
    if ultima is not None:
        (sala / ".estado.json").write_text(
            json.dumps({"ultima": ultima, "em": agora_iso()}) + "\n", encoding="utf-8")
    return sala


def marca_lida(sala: Path, ia: str, n: int, delta_s: float = 0.0) -> None:
    """Mesmo formato de iachat_core.marca_lida (iachat_core.py:355-361)."""
    (sala / "cursor" / f"{ia}.json").write_text(
        json.dumps({"ultima_lida": n, "em": agora_iso(delta_s)}) + "\n",
        encoding="utf-8")


def fake_launchctl(base: Path, labels: dict[str, str]) -> Path:
    """launchctl de mentira: emite a listagem inteira com os labels pedidos."""
    binario = base / "path-bin"
    binario.mkdir(parents=True, exist_ok=True)
    linhas = "".join(f"printf '%s\\t-\\t%s\\n' {pid} {label}\n"
                     for label, pid in labels.items())
    alvo = binario / "launchctl"
    alvo.write_text("#!/bin/sh\n" + linhas, encoding="utf-8")
    alvo.chmod(0o755)
    return binario


def planta_plist(base: Path, label: str, iachat_home: str | None) -> None:
    """plist do LaunchAgent no HOME falso — é daqui que o roster lê IACHAT_HOME."""
    pasta = base / "home" / "Library" / "LaunchAgents"
    pasta.mkdir(parents=True, exist_ok=True)
    d = {"Label": label, "ProgramArguments": ["/bin/sh", "-c", "sleep 1"]}
    if iachat_home is not None:
        d["EnvironmentVariables"] = {"IACHAT_HOME": iachat_home}
    with (pasta / f"{label}.plist").open("wb") as f:
        plistlib.dump(d, f)


def ambiente(base: Path, sala: Path | None, labels: dict[str, str] | None = None
             ) -> dict[str, str]:
    """PATH fechado (só fake + sistema) e HOME falso para os plists."""
    binario = fake_launchctl(base, labels or {})
    home = base / "home"
    home.mkdir(parents=True, exist_ok=True)
    env = {
        **os.environ,
        "PATH": f"{binario}:/usr/bin:/bin",
        "HOME": str(home),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    if sala is not None:
        env["IACHAT_HOME"] = str(sala)
    return env


def foto(d: Path) -> dict[str, tuple[int, int]]:
    """Retrato do que existe: caminho relativo -> (tamanho, mtime em ns)."""
    saida = {}
    for p in sorted(d.rglob("*")):
        if p.is_file():
            st = p.stat()
            saida[str(p.relative_to(d))] = (st.st_size, st.st_mtime_ns)
    return saida


def main() -> int:
    base = Path(tempfile.mkdtemp(prefix="iachat-roster-teste-"))
    try:
        checa("binário novo é executável",
              CLI.is_file() and os.access(CLI, os.X_OK), str(CLI))

        # ---- R1: IA PRESENTE — cursor prova leitura ⇒ visto -----------------
        sala1 = monta_sala(base / "r1", ["claude", "kimi"], ultima=3)
        marca_lida(sala1, "claude", 2)
        planta_plist(base / "r1", "com.bauer.ia-bell-claude", str(sala1))
        r1 = roda(ambiente(base / "r1", sala1,
                           {"com.bauer.ia-bell-claude": "49797"}))
        l1 = linha_de(r1.stdout, "claude")
        checa("R1 IA presente: cursor com leitura ⇒ visto, sino no ar, atraso 1",
              r1.returncode == 0 and "visto" in l1 and "no ar 49797" in l1
              and "há" in l1 and "1" in l1.split() and "última #3" in r1.stdout,
              f"rc={r1.returncode} linha={l1!r}")
        checa("R1 bloco 'não sei dizer' sai até em sala saudável (obrigatório)",
              "não sei dizer" in r1.stdout, "")

        # ---- R2: IA AUSENTE — disco prova que nada a vincula ----------------
        sala2 = monta_sala(base / "r2", ["claude", "grok"], ultima=2)
        marca_lida(sala2, "claude", 2)
        r2 = roda(ambiente(base / "r2", sala2))
        l2 = linha_de(r2.stdout, "grok")
        checa("R2 IA ausente: sem cursor, sem chamado, sem sino ⇒ ausente "
              "(e leu sai '—', nunca zero)",
              r2.returncode == 0 and "ausente" in l2 and "✗ SEM SINO" in l2
              and "não-verificável" not in l2 and " — " in l2,
              f"linha={l2!r}")

        # ---- R3: IA NÃO-VERIFICÁVEL — cursor existe e não parseia -----------
        sala3 = monta_sala(base / "r3", ["claude", "kimi"], ultima=2)
        marca_lida(sala3, "claude", 2)
        (sala3 / "cursor" / "kimi.json").write_text("{isso não é json",
                                                    encoding="utf-8")
        r3 = roda(ambiente(base / "r3", sala3))
        l3 = linha_de(r3.stdout, "kimi")
        checa("R3 IA não-verificável: cursor corrompido não é visto NEM ausente",
              r3.returncode == 0 and "não-verificável" in l3
              and "visto" not in l3.replace("não-verificável", "")
              and "ausente" not in l3,
              f"linha={l3!r}")
        checa("R3 alerta nomeia o cursor ilegível (não-consigo-ver vira texto)",
              "cursor ilegível" in r3.stdout and "kimi" in r3.stdout, "")

        # ---- R4 (REPROVA): sala sem config ⇒ instrumento aborta, não inventa -
        vazia = base / "r4" / "sala-vazia"
        vazia.mkdir(parents=True)
        env4 = ambiente(base / "r4", vazia)
        antes = foto(vazia)
        r4 = roda(env4)
        checa("R4 REPROVA pasta vazia: rc 2 + erro em stderr, tabela nenhuma",
              r4.returncode == 2 and "sala não encontrada" in r4.stderr
              and "desfecho" not in r4.stdout,
              f"rc={r4.returncode}")
        checa("R4 a pasta vazia PERMANECE vazia (perguntar não cria a sala)",
              foto(vazia) == antes and not list(vazia.iterdir()),
              f"antes={len(antes)} depois={len(foto(vazia))}")
        inexistente = base / "r4" / "nem-existe"
        r4b = roda(ambiente(base / "r4b", inexistente))
        checa("R4 caminho inexistente: rc 2 e o caminho não é criado",
              r4b.returncode == 2 and not inexistente.exists(), "")

        # ---- R5 (O CASO QUE REPROVA): reprodução de 17/08, chat pré-existente
        # Sala viva com histórico: codex leu #1 há 2h, sala está na #5, chamado
        # pendente há 56min, sino NUNCA instalado. O instrumento é OBRIGADO a
        # alarmar — se ele ficar calado diante do dano, este gate reprova.
        sala5 = monta_sala(base / "r5", ["claude", "codex", "kimi"], ultima=5)
        marca_lida(sala5, "claude", 5)
        marca_lida(sala5, "kimi", 4, delta_s=30 * 60)
        marca_lida(sala5, "codex", 1, delta_s=2 * 3600)
        flag = sala5 / "pendente" / "codex.md"
        flag.write_text("@codex mensagem #15\n", encoding="utf-8")
        t56 = time.time() - 56 * 60
        os.utime(flag, (t56, t56))
        env5 = ambiente(base / "r5", sala5,
                        {"com.bauer.ia-bell-claude": "49797",
                         "com.bauer.ia-bell-kimi": "49817"})
        planta_plist(base / "r5", "com.bauer.ia-bell-claude", str(sala5))
        planta_plist(base / "r5", "com.bauer.ia-bell-kimi", str(sala5))
        r5 = roda(env5)
        l5 = linha_de(r5.stdout, "codex")
        checa("R5 caso real: chamado parado medido no chat pré-existente (atraso 4)",
              r5.returncode == 0 and "há 56min ⚠" in l5 and "4" in l5.split(),
              f"linha={l5!r}")
        checa("R5 REPROVA se o instrumento ficar calado: alarme de sino ausente "
              "e alarme de chamado parado saem os dois",
              "sino NÃO INSTALADO" in r5.stdout and "ia-bell-codex" in r5.stdout
              and "chamado há 56min e ainda não leu" in r5.stdout
              and "cursor #1" in r5.stdout and "sala #5" in r5.stdout,
              f"alertas={[l for l in r5.stdout.splitlines() if l.startswith('⚠')]}")

        # ---- R6: read-only PROVADO — a sala não muda um byte ----------------
        antes5 = foto(sala5)
        roda(env5)
        roda(env5)
        depois5 = foto(sala5)
        checa("R6 read-only de verdade: duas execuções, zero byte ou mtime mudado",
              antes5 == depois5,
              f"arquivos antes={len(antes5)} depois={len(depois5)}")

        # ---- R7: fora da sala — nunca presença fantasma, nunca 'ausente' ----
        sala7 = monta_sala(base / "r7", ["claude"], ultima=1)
        marca_lida(sala7, "claude", 1)
        r7a = roda(ambiente(base / "r7", sala7), "qwen")
        l7a = linha_de(r7a.stdout, "qwen")
        checa("R7 nome pedido que não está em na_sala ⇒ 'fora da sala', não ausente",
              r7a.returncode == 0 and "fora da sala" in l7a and "ausente" not in l7a,
              f"linha={l7a!r}")
        (sala7 / "cursor" / "zeta.json").write_text(
            json.dumps({"ultima_lida": 1, "em": agora_iso(120)}) + "\n",
            encoding="utf-8")
        r7b = roda(ambiente(base / "r7", sala7))
        l7b = linha_de(r7b.stdout, "zeta")
        checa("R7 artefato órfão de quem saiu da sala ⇒ 'fora da sala' com a "
              "evidência mostrada (não vira visto: não é membro)",
              r7b.returncode == 0 and "fora da sala" in l7b and "há" in l7b
              and "visto" not in l7b.replace("fora da sala", ""),
              f"linha={l7b!r}")

        # ---- R8: sino vigiando OUTRA sala — o verde que mente ---------------
        sala8 = monta_sala(base / "r8", ["claude"], ultima=1)
        marca_lida(sala8, "claude", 1)
        planta_plist(base / "r8", "com.bauer.ia-bell-claude", "/tmp/outra-sala-x")
        r8 = roda(ambiente(base / "r8", sala8,
                           {"com.bauer.ia-bell-claude": "49797"}))
        l8 = linha_de(r8.stdout, "claude")
        checa("R8 sino no ar mas noutra sala ⇒ '⚠ outra sala' + alerta nomeando-a",
              r8.returncode == 0 and "⚠ outra sala" in l8
              and "OUTRA sala (/tmp/outra-sala-x)" in r8.stdout,
              f"linha={l8!r}")

        # ---- R9: sino carregado com plist ilegível — não vira 'no ar' -------
        sala9 = monta_sala(base / "r9", ["kimi"], ultima=1)
        r9 = roda(ambiente(base / "r9", sala9,
                           {"com.bauer.ia-bell-kimi": "51000"}))
        l9 = linha_de(r9.stdout, "kimi")
        checa("R9 plist não abre ⇒ sino incerto, NUNCA 'no ar' por omissão "
              "(defeito do protótipo corrigido)",
              r9.returncode == 0 and "? sala incerta" in l9
              and "no ar" not in l9 and "plist não abre" in r9.stdout,
              f"linha={l9!r}")
        checa("R9 sino sozinho não prova leitura: desfecho fica não-verificável",
              "não-verificável" in l9, f"linha={l9!r}")

        # ---- R10: vocação declarada vs não declarada ------------------------
        sala10 = monta_sala(base / "r10", ["claude", "codex"], ultima=1,
                           vocacao={"codex": {"bom": "código, raciocínio longo"}})
        marca_lida(sala10, "claude", 1)
        marca_lida(sala10, "codex", 1)
        r10 = roda(ambiente(base / "r10", sala10))
        l10c = linha_de(r10.stdout, "codex")
        l10a = linha_de(r10.stdout, "claude")
        checa("R10 vocação declarada aparece; ausente vira '(não declarada)'",
              r10.returncode == 0 and "código, raciocínio longo" in l10c
              and "(não declarada)" in l10a,
              f"codex={l10c!r}")
        checa("R10 vocação ausente também é nomeada no bloco 'não sei dizer'",
              "no que claude é boa" in r10.stdout, "")

        # ---- R11: sala sem .estado.json — atraso vira '—', nunca zero -------
        sala11 = monta_sala(base / "r11", ["claude"], ultima=None)
        marca_lida(sala11, "claude", 2)
        r11 = roda(ambiente(base / "r11", sala11))
        l11 = linha_de(r11.stdout, "claude")
        checa("R11 sem .estado.json: 'última —' e atraso '—' (não zero inventado)",
              r11.returncode == 0 and "última —" in r11.stdout
              and l11.count("—") >= 1 and "visto" in l11,
              f"linha={l11!r}")

        print()
        print("✅ IA-ROSTER PASSOU" if not falhas else f"❌ IA-ROSTER REPROVOU: {falhas}")
        return 0 if not falhas else 1
    finally:
        shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
