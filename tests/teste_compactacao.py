#!/usr/bin/env python3
"""Gates da skill de compactação: mapa curto, sino reusado, caso que REPROVA.

Roda em IACHAT_HOME temporário copiado da fixture `sala-v1` (chat pré-existente
com histórico). Achado de 17/08: teste que só cria sala vazia com mkdtemp deixou
passar a mudança que apagou a sala real.
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

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
BIN = RAIZ / "bin" / "ia-compactacao"
FIXTURE = Path.home() / "Projetos" / "ia-chat" / "tests" / "fixtures" / "sala-v1"

_ok = 0
_falhou = 0


def checa(nome: str, cond: bool, detalhe: str = "") -> None:
    global _ok, _falhou
    if cond:
        _ok += 1
        print("  ✔ %s" % nome)
    else:
        _falhou += 1
        print("  ✗ %s" % nome + (("\n      %s" % detalhe) if detalhe else ""))


def sha_chat(base: Path) -> str:
    p = base / "iachat.md"
    return hashlib.sha256(p.read_bytes() if p.is_file() else b"").hexdigest()


def sala_com_historico(notificar: bool, run: Path = None) -> tuple:
    base = Path(tempfile.mkdtemp(prefix="iachat-compact-"))
    if FIXTURE.is_dir():
        shutil.copytree(FIXTURE, base, dirs_exist_ok=True)
    else:
        (base / "pendente").mkdir()
        (base / "cursor").mkdir()
        (base / "iachat.md").write_text(
            "<!-- iachat msg=1 de=claude para=codex ts=2026-08-17T20:00:00 -->\n"
            "histórico pré-existente que NÃO pode sumir\n",
            encoding="utf-8",
        )
    (base / "pendente").mkdir(exist_ok=True)
    cfg = {}
    if (base / "config.json").is_file():
        try:
            cfg = json.loads((base / "config.json").read_text(encoding="utf-8"))
        except Exception:
            cfg = {}
    cfg["na_sala"] = cfg.get("na_sala") or ["claude", "codex", "kimi"]
    cfg["notificar_operador"] = notificar
    (base / "config.json").write_text(json.dumps(cfg) + "\n", encoding="utf-8")
    env = dict(os.environ)
    env["IACHAT_HOME"] = str(base)
    env["IACHAT_TEST"] = "1"
    env["IACHAT_EU"] = "claude"
    env["PYTHON_DONTWRITEBYTECODE"] = "1"
    if run is not None:
        env["IASWARM_RUN"] = str(run)
    return base, env


def run_falso() -> Path:
    d = Path(tempfile.mkdtemp(prefix="iaswarm-run-"))
    (d / "progress").mkdir()
    (d / "resultados").mkdir()
    (d / "painel-porta.txt").write_text("64354\n", encoding="utf-8")
    (d / "MAPA.md").write_text(
        "# MAPA\n\n## O que espera a palavra dele\n\n"
        "1. PENDENTE — publicar os dois repositórios.\n",
        encoding="utf-8",
    )
    (d / "resultados" / "prova.md").write_text(
        "missão: x\nresultado: último passo com prova\n", encoding="utf-8"
    )
    (d / "progress" / "L4-skill-compactacao.jsonl").write_text(
        '{"etapa":1,"de":5,"estado":"rodando","nota":"teste"}\n',
        encoding="utf-8",
    )
    (d / "state.json").write_text(
        json.dumps({
            "workers": [{
                "worker": "L4-skill-compactacao",
                "braco": "grok",
                "feitas": 1,
                "etapas": 5,
                "estado": "rodando",
            }]
        }),
        encoding="utf-8",
    )
    return d


def roda(env: dict, args, stdin: str = "") -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(BIN)] + list(args),
        env=env,
        input=stdin,
        capture_output=True,
        text=True,
        timeout=20,
    )


print("teste_compactacao")

checa("binário presente", BIN.is_file(), str(BIN))

# ── 1. chat pré-existente sobrevive (o caso que os testes velhos não cobriam)
run = run_falso()
base, env = sala_com_historico(True, run)
antes = sha_chat(base)
payload = json.dumps({"trigger": "manual", "session_id": "deadbeef1234"})
r = roda(env, ["--pos"], payload)
depois = sha_chat(base)
mapa = base / "caminho.md"
checa("--pos exit 0", r.returncode == 0, r.stderr)
checa("escreveu caminho.md (isca mudou o disco)", mapa.is_file(),
      "arquivo não criado — teste inválido se a isca não muda nada")
checa("iachat.md do histórico NÃO mudou", antes == depois,
      "o mapa não pode tocar a sala")
ok_txt = mapa.read_text(encoding="utf-8") if mapa.is_file() else ""
checa("mapa tem as 4 seções",
      all(s in ok_txt for s in (
          "## Onde parou", "## Rodando agora", "## Espera decisão", "## 3 links")),
      ok_txt[:400])
checa("mapa cita o run e a porta do painel",
      "64354" in ok_txt and "L4-skill-compactacao" in ok_txt, ok_txt[:500])
checa("mapa NÃO é o resumo longo (sem <analysis>)",
      "<analysis>" not in ok_txt.lower()
      and "primary request and intent" not in ok_txt.lower())
checa("mapa cabe no teto de 12 KB",
      mapa.is_file() and mapa.stat().st_size <= 12000,
      "tamanho %s" % (mapa.stat().st_size if mapa.is_file() else "?"))

# ── 2. sino do dono LIGADO → reusa pendente/ (ia-bell), não cria 2º sistema
flag = base / "pendente" / "claude.md"
checa("sino on: escreveu pendente/claude.md", flag.is_file())
checa("sino on: o aviso se chama compact-bell",
      flag.is_file() and "compact-bell" in flag.read_text(encoding="utf-8"))
checa("sino on: NÃO escreveu pendente/bauer.md (dono ≠ IA compactada)",
      not (base / "pendente" / "bauer.md").is_file())
shutil.rmtree(base, ignore_errors=True)
shutil.rmtree(run, ignore_errors=True)

# ── 3. sino do dono DESLIGADO → silêncio INTEIRO (contrato L1)
run = run_falso()
base, env = sala_com_historico(False, run)
r = roda(env, ["--pre"], '{"trigger":"auto","session_id":"cafef00d"}')
checa("--pre com sino off ainda escreve o mapa", (base / "caminho.md").is_file())
pendentes = list((base / "pendente").glob("*.md"))
checa("sino off: ZERO flag em pendente/ (silêncio total)",
      pendentes == [],
      "escreveu %s — isso acordaria o daemon do ia-bell" % [p.name for p in pendentes])
shutil.rmtree(base, ignore_errors=True)
shutil.rmtree(run, ignore_errors=True)

# ── 4. --inicio injeta o caminho, não reescreve
run = run_falso()
base, env = sala_com_historico(True, run)
roda(env, ["--mapa"])
mtime1 = (base / "caminho.md").stat().st_mtime
r = roda(env, ["--inicio"])
mtime2 = (base / "caminho.md").stat().st_mtime
checa("--inicio exit 0", r.returncode == 0)
checa("--inicio aponta para caminho.md", "caminho.md" in r.stdout)
checa("--inicio NÃO reescreve o mapa", mtime1 == mtime2)
shutil.rmtree(base, ignore_errors=True)
shutil.rmtree(run, ignore_errors=True)

# ── 5. o caso que REPROVA — gate que nunca viu vermelho não é gate
#    (a) mapa sem seção obrigatória
ruim = Path(tempfile.mkdtemp(prefix="mapa-ruim-")) / "ruim.md"
ruim.write_text("# resumo\n\naconteceu muita coisa\n", encoding="utf-8")
r = roda(dict(os.environ, IACHAT_TEST="1"), ["--validar", str(ruim)])
checa("REPROVA: mapa sem as 4 seções sai ✗ (exit 1)",
      r.returncode == 1 and "✗" in r.stdout, r.stdout + r.stderr)
#    (b) mapa que é o resumo da compactação (o defeito que esta peça existe pra matar)
resumo = ruim.parent / "resumo.md"
resumo.write_text(
    "## Onde parou\n\n## Rodando agora\n\n## Espera decisão\n\n## 3 links\n\n"
    "<analysis>\nPrimary Request and Intent\n" + ("bla " * 50) + "\n",
    encoding="utf-8",
)
r = roda(dict(os.environ, IACHAT_TEST="1"), ["--validar", str(resumo)])
checa("REPROVA: texto com <analysis> é resumo, não mapa",
      r.returncode == 1, r.stdout + r.stderr)
#    (c) mapa inchado (a captura de 18/08 tem 45683 B)
gordo = ruim.parent / "gordo.md"
gordo.write_text(
    "## Onde parou\n\n## Rodando agora\n\n## Espera decisão\n\n## 3 links\n\n"
    + ("x" * 13000),
    encoding="utf-8",
)
r = roda(dict(os.environ, IACHAT_TEST="1"), ["--validar", str(gordo)])
checa("REPROVA: mapa > 12 KB (viu o tamanho da captura-resumo)",
      r.returncode == 1 and "grande" in r.stdout, r.stdout)
shutil.rmtree(ruim.parent, ignore_errors=True)

# ── 6. --validar no mapa BOM que o próprio binário gerou
run = run_falso()
base, env = sala_com_historico(True, run)
roda(env, ["--mapa"])
r = roda(env, ["--validar", str(base / "caminho.md")])
checa("PASS: o mapa gerado pelo binário passa no gate",
      r.returncode == 0 and "✔" in r.stdout, r.stdout + r.stderr)
shutil.rmtree(base, ignore_errors=True)
shutil.rmtree(run, ignore_errors=True)

print("\n%d ✔  %d ✗" % (_ok, _falhou))
sys.exit(1 if _falhou else 0)
