#!/usr/bin/env python3
"""Gates do iachat-onboard: briefing derivado, cursor intacto, read-only e prova vermelha.

Tudo roda em ``IACHAT_HOME`` temporário, populado a partir da fixture congelada
``tests/fixtures/sala-v1/`` — um CHAT PRÉ-EXISTENTE com 8 mensagens e cursores
reais (claude #8, codex #8, kimi #5). É o achado crítico de 17/08: teste que só
cria sala nova com ``mkdtemp`` deixou passar a mudança que apagou a sala real.

Casos cobertos: IA nova (cursor 0) · IA que já leu · chat pré-existente · sala
grande · DECISOES inflado · decisão sobrevivendo à rotação · ``decidir`` append ·
``--marcar`` ≡ ausência · e o caso que REPROVA (teto abaixo do piso, exit 2).
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ONBOARD = RAIZ / "bin" / "iachat-onboard"
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "sala-v1"
TETO = 4096

falhas: list[str] = []


def checa(nome: str, condicao: bool, detalhe: str = "") -> None:
    print(f"{'✔' if condicao else '✗'} {nome}" + (f"  ‣ {detalhe}" if detalhe else ""))
    if not condicao:
        falhas.append(nome)


def roda(*args: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """Executa a mesma porta pública que uma IA usa no terminal."""
    return subprocess.run(
        [sys.executable, str(ONBOARD), *args],
        env=env,
        capture_output=True,
        text=True,
    )


def nova_base(teto_bytes: int | None = None) -> tuple[Path, dict[str, str]]:
    """Copia a fixture (chat pré-existente) para um IACHAT_HOME temporário."""
    base = Path(tempfile.mkdtemp(prefix="iachat-onboard-teste-"))
    shutil.copytree(FIXTURE, base, dirs_exist_ok=True)
    (base / ".lock").mkdir(exist_ok=True)
    if teto_bytes is not None:
        cfg = json.loads((base / "config.json").read_text(encoding="utf-8"))
        cfg["teto_bytes"] = teto_bytes
        (base / "config.json").write_text(json.dumps(cfg) + "\n", encoding="utf-8")
    env = {
        **os.environ,
        "IACHAT_HOME": str(base),
        "PYTHON_DONTWRITEBYTECODE": "1",
    }
    return base, env


def sha_conteudo(base: Path) -> str:
    """Hash de todo o CONTEÚDO da sala. `.lock/` fica fora: é o mutex de 0 B que
    qualquer comando cria, inclusive um que só lê (iachat_core.py:129-131)."""
    h = hashlib.sha256()
    for p in sorted(base.rglob("*")):
        if p.is_file() and ".lock" not in p.parts:
            h.update(str(p.relative_to(base)).encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def main() -> int:
    bases: list[Path] = []
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(RAIZ / "bin"))

    try:
        # ---- T0: a peça existe e é executável --------------------------------
        checa(
            "T0 CLI iachat-onboard existe e é executável",
            ONBOARD.is_file() and os.access(ONBOARD, os.X_OK),
            str(ONBOARD),
        )

        # ---- T1: IA nova (cursor 0) -------------------------------------------
        base, env = nova_base()
        bases.append(base)
        os.environ["IACHAT_HOME"] = str(base)
        import iachat_core as core

        curso_antes = core.cursor("grok")
        r = roda("briefing", "--de", "grok", env=env)
        n_bytes = len(r.stdout.encode())
        checa(
            "T1 IA nova (cursor 0): briefing diz 'ainda não leu nada', dentro do teto",
            r.returncode == 0
            and "Seu cursor:** #0" in r.stdout
            and "você ainda não leu nada aqui" in r.stdout
            and n_bytes <= TETO,
            f"{n_bytes} B · cursor {curso_antes} → {core.cursor('grok')}",
        )
        checa(
            "T1b cursor da IA nova fica intacto E sem arquivo criado",
            curso_antes == core.cursor("grok") == 0
            and not (base / "cursor" / "grok.json").exists(),
            f"{curso_antes} → {core.cursor('grok')}",
        )

        # ---- T2: IA que já leu (kimi, cursor #5) ------------------------------
        curso_kimi_antes = core.cursor("kimi")
        r = roda("briefing", "--de", "kimi", env=env)
        checa(
            "T2 IA que já leu: mostra o cursor dela, sem 'ainda não leu nada'",
            r.returncode == 0
            and "Seu cursor:** #5" in r.stdout
            and "você ainda não leu nada aqui" not in r.stdout,
            f"cursor {curso_kimi_antes} → {core.cursor('kimi')}",
        )
        checa(
            "T2b fios abertos derivados do grafo de nominação",
            "## Fios abertos" in r.stdout and "#8 claude → kimi" in r.stdout,
        )
        checa(
            "T2c cursor da kimi fica intacto (#5 = #5)",
            curso_kimi_antes == core.cursor("kimi") == 5,
            f"{curso_kimi_antes} → {core.cursor('kimi')}",
        )

        # ---- T3: chat pré-existente — read-only por sha256 --------------------
        antes = sha_conteudo(base)
        cursores_antes = {ia: core.cursor(ia) for ia in ("claude", "codex", "kimi")}
        r = roda("briefing", "--de", "claude", env=env)
        depois = sha_conteudo(base)
        cursores_depois = {ia: core.cursor(ia) for ia in ("claude", "codex", "kimi")}
        checa(
            "T3 chat pré-existente: briefing vê a história (#8) e NÃO escreve na sala",
            r.returncode == 0
            and "#8" in r.stdout
            and "Quem está na sala" in r.stdout
            and antes == depois
            and cursores_antes == cursores_depois,
            f"sha256 {antes[:12]}…={depois[:12]}… · cursores {cursores_antes} → {cursores_depois}",
        )

        # ---- T4: sala grande — o briefing não cresce com a sala ---------------
        base4, env4 = nova_base(teto_bytes=204800)
        bases.append(base4)
        os.environ["IACHAT_HOME"] = str(base4)
        corpo = "Medição autocontida, caminho /Users/bauer/x/y.py:118, número 4096 B. " * 20
        for i in range(45):
            core.post(["claude", "codex", "kimi"][i % 3], f"@kimi Assunto {i}. " + corpo)
        sala_b = (base4 / "iachat.md").stat().st_size
        r = roda("briefing", "--de", "grok", env=env4)
        n_bytes = len(r.stdout.encode())
        checa(
            "T4 sala de ~57 KB e 53 msgs: briefing continua dentro do teto",
            r.returncode == 0 and sala_b > 50000 and n_bytes <= TETO,
            f"sala {sala_b} B → briefing {n_bytes} B",
        )

        # ---- T5: DECISOES.md inflado (60 entradas) -----------------------------
        for i in range(60):
            with (base4 / "DECISOES.md").open("a", encoding="utf-8") as f:
                f.write(
                    f"- [2026-08-18T01:{i % 60:02d} · kimi] Decisão {i:02d} com caminho "
                    f"/Users/bauer/proj/a-{i}.py:{i} e número {i * 137} B, longa o "
                    "bastante para forçar o corte.\n"
                )
        dec_b = (base4 / "DECISOES.md").stat().st_size
        r = roda("briefing", "--de", "grok", env=env4)
        n_bytes = len(r.stdout.encode())
        checa(
            "T5 DECISOES inflado: briefing dentro do teto, corta declarando",
            r.returncode == 0
            and n_bytes <= TETO
            and "… e mais" in r.stdout
            and "Decisão 59" in r.stdout,
            f"DECISOES {dec_b} B → briefing {n_bytes} B",
        )

        # ---- T6: decisão sobrevive à rotação (a mensagem não) ------------------
        base6, env6 = nova_base(teto_bytes=3500)
        bases.append(base6)
        os.environ["IACHAT_HOME"] = str(base6)
        r = roda("decidir", "--de", "claude",
                 "Regra que tem de sobreviver à rotação: o operador tem precedência.",
                 env=env6)
        for i in range(3):
            core.post("codex", f"@kimi Ruído {i} " + "x" * 600, ["kimi"])
        rot = core.rotate()
        ativo = (base6 / "iachat.md").read_text(encoding="utf-8")
        r = roda("briefing", "--de", "grok", env=env6)
        checa(
            "T6 rotação arquivou a msg #1, mas a decisão continua no briefing",
            rot["rodou"]
            and "msg=1 " not in ativo
            and "tem de sobreviver à rotação" in r.stdout,
            f"rot={rot.get('motivo', 'rodou')}",
        )

        # ---- T7: decidir é append-only, cabeçalho uma vez só -------------------
        r1 = roda("decidir", "--de", "kimi", "primeira decisão de teste.", env=env)
        os.environ["IACHAT_HOME"] = str(base)
        r2 = roda("decidir", "--de", "codex", "segunda decisão de teste.", env=env)
        dec = (base / "DECISOES.md").read_text(encoding="utf-8")
        checa(
            "T7 decidir grava as duas linhas, cabeçalho criado uma única vez",
            r1.returncode == 0 and r2.returncode == 0
            and dec.count("# 📌 Decisões da sala") == 1
            and "· kimi] primeira decisão de teste." in dec
            and "· codex] segunda decisão de teste." in dec,
        )

        # ---- T8: --marcar ≡ ausência de cursor (não inventa conceito) ----------
        r = roda("briefing", "--de", "grok", "--marcar", env=env)
        gravado = json.loads((base / "cursor" / "grok.json").read_text())
        checa(
            "T8 --marcar grava cursor #0, indistinguível de ausente (cursor()=0)",
            r.returncode == 0
            and gravado["ultima_lida"] == 0
            and core.cursor("grok") == 0,
            f"arquivo={gravado}",
        )

        # ---- T-RED: teto abaixo do piso REPROVA declarando o piso medido -------
        r = roda("briefing", "--de", "grok", "--teto", "512", env=env)
        checa(
            "T-RED teto de 512 B REPROVA com exit 2 e piso medido no erro",
            r.returncode == 2
            and "não cabe o núcleo" in r.stderr
            and "Piso desta sala/IA" in r.stderr,
            f"rc={r.returncode} · {r.stderr.strip().splitlines()[0][:80] if r.stderr else ''}",
        )

    finally:
        for b in bases:
            shutil.rmtree(b, ignore_errors=True)

    print()
    if falhas:
        print(f"✗ {len(falhas)} falha(s): {', '.join(falhas)}")
        return 1
    print("✔ tudo verde")
    return 0


if __name__ == "__main__":
    sys.exit(main())


# ── onboarding automático pelo HOOK — patch aplicado em 18/08 ────────────────
# Achado da Kimi: uma IA que chega pela primeira vez era INVISÍVEL para a entrega. O
# hook saía quando não havia flag em `pendente/` — e um recém-chegado nunca tem flag,
# porque nominar alguém exige que já soubessem que ele entrou. Ela só descobria a sala
# se um humano contasse.
#
# O bloco tem que valer nos DOIS lados: entregar na primeira vez, e ficar em silêncio
# depois — um hook que repete o briefing a cada evento é pior que o defeito original.
def _hook_onboarding() -> None:
    import json as _json
    import os as _os
    import shutil as _shutil
    import subprocess as _sp
    import tempfile as _tempfile
    from pathlib import Path as _Path

    hook = _Path(__file__).resolve().parent.parent / "bin" / "ia-bell-hook.sh"
    binp = _Path.home() / ".local" / "bin"
    if not hook.is_file() or not (binp / "iachat").is_file():
        checa("hook de onboarding: ambiente sem instalação (pulado)", True)
        return

    h = _Path(_tempfile.mkdtemp(prefix="hookonb-"))
    for d in ("pendente", "cursor", "arquivo"):
        (h / d).mkdir()
    (h / "config.json").write_text(_json.dumps(
        {"na_sala": ["claude", "codex", "novata"], "brain": "claude"}))
    (h / "iachat.md").write_text("")
    env = dict(_os.environ, IACHAT_HOME=str(h), IACHAT_BIN=str(binp))
    for de, txt in (("claude", "primeira decisão da sala"), ("codex", "segunda mensagem")):
        _sp.run([str(binp / "iachat"), "post", "--de", de, "--para", "claude", txt],
                env=env, capture_output=True)

    r1 = _sp.run(["bash", str(hook)], env={**env, "IACHAT_EU": "novata"},
                 capture_output=True, text=True, timeout=40)
    n1 = len((r1.stdout or "").encode())
    checa("hook: IA nova recebe o briefing sem ter sido nominada", n1 > 200,
          f"saíram {n1} B — a IA nova continua invisível para a entrega")
    checa("hook: o cursor da IA nova foi criado",
          (h / "cursor" / "novata.json").is_file())

    r2 = _sp.run(["bash", str(hook)], env={**env, "IACHAT_EU": "novata"},
                 capture_output=True, text=True, timeout=40)
    checa("hook: segunda passada fica em SILÊNCIO (auto-extinguiu)",
          len((r2.stdout or "").encode()) == 0,
          "repetiu o briefing — hook que repete a cada evento é pior que o defeito original")
    _shutil.rmtree(h, ignore_errors=True)


_hook_onboarding()
print(f"\n{_ok} ✔  {_falhou} ✗")
sys.exit(1 if _falhou else 0)
