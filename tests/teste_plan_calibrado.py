#!/usr/bin/env python3
"""Gates do /plan calibrado por nível.

REPROVA no código antigo (despacha a sala inteira, sem --nivel/--todas) e passa
depois da calibração. IACHAT_HOME temporário: a sala viva não é tocada.
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
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


def carrega_modulo():
    spec = importlib.util.spec_from_loader(
        "iachat_comando",
        importlib.machinery.SourceFileLoader("iachat_comando", str(CMD)),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sala_nova() -> tuple[Path, dict]:
    home = Path(tempfile.mkdtemp(prefix="plan-calibrado-")) / "sala"
    env = dict(os.environ, IACHAT_HOME=str(home), PYTHON_DONTWRITEBYTECODE="1")
    return home, env


def prepara(home: Path, env: dict, ias: list[str], brain: str = "claude") -> None:
    subprocess.run(
        [sys.executable, str(RAIZ / "bin" / "iachat"), "status"],
        env=env, capture_output=True, stdin=subprocess.DEVNULL, timeout=60,
    )
    cfg = home / "config.json"
    c = json.loads(cfg.read_text(encoding="utf-8")) if cfg.is_file() else {}
    c["na_sala"] = ias
    c["brain"] = brain
    cfg.write_text(json.dumps(c, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def roda(env: dict, *args: str) -> subprocess.CompletedProcess[str]:
    argv = list(args)
    if argv and argv[0] == "plan" and "--de" not in argv:
        argv += ["--de", "claude"]
    if argv and argv[0] == "goal" and "--de" not in argv:
        argv += ["--de", "claude"]
    return subprocess.run(
        [sys.executable, str(CMD), *argv],
        env=env, capture_output=True, text=True, timeout=60,
    )


def escolhidas(stdout: str) -> list[str]:
    """IAs que o --seco anunciou como despacho, não as 'de fora'."""
    nomes, fora = [], False
    for ln in stdout.splitlines():
        s = ln.strip()
        if s.startswith("de fora"):
            fora = True
            continue
        if fora or s.startswith("recusadas") or s.startswith("🧪") or s.startswith("seco"):
            continue
        tok = s.split()
        if tok and tok[0] in ("codex", "kimi", "qwen", "grok", "agy",
                               "qwclaude", "dsclaude", "claude", "bauer"):
            nomes.append(tok[0])
    return nomes


def main() -> int:
    print("teste_plan_calibrado")
    mod = carrega_modulo()
    candidatas = ["codex", "kimi", "qwen", "grok", "agy", "qwclaude", "dsclaude"]

    # ---- unidade: nível 1 escolhe uma só -----------------------------------
    cal1 = mod.calibra_plan(
        "renomear a variável X neste arquivo", candidatas)
    checa(
        "nível 1 escolhe uma só",
        cal1["nivel"] == 1 and len(cal1["alvos"]) == 1 and cal1["alvos"] == ["codex"],
        f"nivel={cal1['nivel']} alvos={cal1['alvos']} criterio={cal1['criterio']}",
    )
    checa(
        "nível 1 declara que estimou e cita a palavra",
        cal1["origem"] == "estimado" and cal1["criterio"].startswith("estimei")
        and cal1["casadas"] and cal1["casadas"][0]["palavra"] == "renomear",
        f"casadas={cal1['casadas']}",
    )

    # ---- unidade: nível 3 escolhe várias -----------------------------------
    cal3 = mod.calibra_plan(
        "varrer todos os arquivos, auditar a implementação e provar que a migração ficou pronta",
        candidatas,
    )
    checa(
        "nível 3 escolhe várias",
        cal3["nivel"] == 3 and len(cal3["alvos"]) >= 2 and "kimi" in cal3["alvos"],
        f"nivel={cal3['nivel']} alvos={cal3['alvos']} criterio={cal3['criterio']}",
    )

    # ---- unidade: --ias vence a estimativa ---------------------------------
    cal_ias = mod.calibra_plan(
        "renomear a variável X neste arquivo", candidatas, ias=["kimi"])
    checa(
        "--ias vence a estimativa",
        cal_ias["origem"] == "ias" and cal_ias["alvos"] == ["kimi"]
        and "soberano" in cal_ias["criterio"],
        f"origem={cal_ias['origem']} alvos={cal_ias['alvos']}",
    )

    # ---- unidade: --nivel vence a estimativa --------------------------------
    cal_n = mod.calibra_plan(
        "varrer todos os arquivos e auditar cada arquivo",
        candidatas, nivel=1,
    )
    checa(
        "--nivel vence a estimativa",
        cal_n["origem"] == "cravado" and cal_n["nivel"] == 1
        and len(cal_n["alvos"]) == 1 and "estimativa calada" in cal_n["criterio"],
        f"origem={cal_n['origem']} alvos={cal_n['alvos']}",
    )

    # ---- unidade: irreconhecível cai em 3 e declara ------------------------
    cal_x = mod.calibra_plan("xyzzy plugh 42", candidatas)
    checa(
        "enunciado irreconhecível cai em 3 e declara",
        cal_x["nivel"] == 3 and cal_x["reconheceu"] is False
        and "não reconheci" in cal_x["criterio"]
        and set(cal_x["alvos"]) == set(candidatas),
        f"nivel={cal_x['nivel']} criterio={cal_x['criterio']} alvos={cal_x['alvos']}",
    )

    # ---- unidade: dono e brain nunca entram --------------------------------
    cal_d = mod.calibra_plan(
        "xyzzy plugh 42", ["codex", "kimi"],
        ias=["bauer", "claude", "codex"], brain="claude")
    checa(
        "dono e brain nunca entram mesmo no --ias",
        "bauer" not in cal_d["alvos"] and "claude" not in cal_d["alvos"]
        and cal_d["alvos"] == ["codex"]
        and "bauer" in cal_d["recusadas"] and "claude" in cal_d["recusadas"],
        f"alvos={cal_d['alvos']} recusadas={cal_d['recusadas']}",
    )

    # ---- CLI: o --seco mostra o critério e quem ficou de fora --------------
    homes: list[Path] = []
    try:
        home, env = sala_nova()
        homes.append(home)
        prepara(home, env, ["claude", "codex", "kimi", "grok", "agy", "bauer"], "claude")
        g = roda(env, "goal", "--calado", "renomear a variável X neste arquivo")
        checa("goal abre a missão para o --seco", g.returncode == 0, g.stderr[:160])

        s1 = roda(env, "plan", "--seco")
        quem1 = escolhidas(s1.stdout)
        checa(
            "CLI nível 1 despacha uma só e não gasta",
            s1.returncode == 0 and quem1 == ["codex"]
            and "estimei nível 1" in s1.stdout
            and "de fora:" in s1.stdout
            and "kimi" in s1.stdout
            and not (home / "comando" / "estado.json").read_text().count('"pid"'),
            f"rc={s1.returncode} quem={quem1}\n{s1.stdout[:400]}",
        )
        checa(
            "CLI --seco não cita o dono nem o brain como alvo",
            "bauer" not in s1.stdout.lower() and "claude" not in s1.stdout,
            s1.stdout[:300],
        )

        s_ias = roda(env, "plan", "--seco", "--ias", "agy")
        checa(
            "CLI --ias soberano ignora a estimativa",
            s_ias.returncode == 0 and escolhidas(s_ias.stdout) == ["agy"]
            and "soberano" in s_ias.stdout,
            s_ias.stdout[:300],
        )

        s_n = roda(env, "plan", "--seco", "--nivel", "3")
        quem_n = escolhidas(s_n.stdout)
        checa(
            "CLI --nivel 3 crava e a estimativa cala",
            s_n.returncode == 0 and len(quem_n) >= 2
            and "cravado por --nivel" in s_n.stdout,
            f"quem={quem_n}\n{s_n.stdout[:300]}",
        )

        s_t = roda(env, "plan", "--seco", "--todas")
        quem_t = escolhidas(s_t.stdout)
        checa(
            "CLI --todas é a sala menos brain e dono",
            s_t.returncode == 0 and set(quem_t) == {"codex", "kimi", "grok", "agy"}
            and "bauer" not in s_t.stdout.lower() and "claude" not in s_t.stdout,
            f"quem={quem_t}\n{s_t.stdout[:300]}",
        )

        home2, env2 = sala_nova()
        homes.append(home2)
        prepara(home2, env2, ["claude", "codex", "kimi", "bauer"], "claude")
        roda(env2, "goal", "--calado", "xyzzy plugh 42")
        sx = roda(env2, "plan", "--seco")
        quem_x = escolhidas(sx.stdout)
        checa(
            "CLI irreconhecível cai em 3, declara, e não inclui dono/brain",
            sx.returncode == 0 and "não reconheci" in sx.stdout
            and set(quem_x) == {"codex", "kimi"}
            and "bauer" not in sx.stdout.lower() and "claude" not in sx.stdout,
            f"quem={quem_x}\n{sx.stdout[:400]}",
        )
    finally:
        for h in homes:
            shutil.rmtree(h.parent, ignore_errors=True)

    print(f"\n{_ok} ✔  {_falhou} ✗")
    return 1 if _falhou else 0


if __name__ == "__main__":
    sys.exit(main())
