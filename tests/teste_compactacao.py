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
import time
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


def mapa_minimo(*, rodando: str = "- (nenhum)", espera: str = "- (nenhuma)",
                link: str = "- (nenhum)") -> str:
    return (
        "## Onde parou\n\n- (nenhuma prova)\n\n"
        "## Rodando agora\n\n%s\n\n"
        "## Espera decisão\n\n%s\n\n"
        "## 3 links\n\n%s\n" % (rodando, espera, link)
    )


def roda(env: dict, args, stdin: str = "", cwd: Path = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(BIN)] + list(args),
        env=env,
        input=stdin,
        capture_output=True,
        text=True,
        timeout=20,
        cwd=str(cwd) if cwd is not None else None,
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

# ── 3b. tipo estrito: strings parecidas com falso continuam DESLIGADAS
for valor_ruim in ("false", "0"):
    run = run_falso()
    base, env = sala_com_historico(False, run)
    cfg = json.loads((base / "config.json").read_text(encoding="utf-8"))
    cfg["notificar_operador"] = valor_ruim
    (base / "config.json").write_text(json.dumps(cfg) + "\n", encoding="utf-8")
    roda(env, ["--pre"], '{"trigger":"auto","session_id":"tipo-ruim"}')
    pendentes = list((base / "pendente").glob("*.md"))
    checa('REPROVA: string %r não liga o sino' % valor_ruim,
          pendentes == [],
          "escreveu %s — somente o booleano true pode ligar" % [p.name for p in pendentes])
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

# ── 6b. Verdade do mapa: progresso sem processo não vira worker vivo.
run = run_falso()
base, env = sala_com_historico(False, run)
roda(env, ["--mapa"])
mapa_fantasma = (base / "caminho.md").read_text(encoding="utf-8")
checa(
    "REPROVA: progresso sem PID declara que não confirmou vida",
    "L4-skill-compactacao" in mapa_fantasma
    and "não consegui confirmar se está vivo" in mapa_fantasma,
    mapa_fantasma,
)
ruim_vivo = base / "mapa-mente-vida.md"
ruim_vivo.write_text(
    mapa_minimo(rodando="- **fantasma** · etapa 4/5 · rodando"),
    encoding="utf-8",
)
r = roda(env, ["--validar", str(ruim_vivo)])
checa(
    "REPROVA: gate recusa rodando sem prova nem incerteza",
    r.returncode == 1 and "vida" in r.stdout.lower(),
    r.stdout + r.stderr,
)
shutil.rmtree(base, ignore_errors=True)
shutil.rmtree(run, ignore_errors=True)

# ── 6c. O lado bom da vida: processo real, PID exato e comando ancorado no worker.
run = run_falso()
(run / "logs").mkdir()
worker = "L4-skill-compactacao"
processo = subprocess.Popen(
    [sys.executable, "-c", "import time; time.sleep(30)", str(run), worker],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
try:
    (run / "logs" / (worker + ".pid")).write_text(
        str(processo.pid) + "\n", encoding="utf-8"
    )
    time.sleep(0.05)
    base, env = sala_com_historico(False, run)
    roda(env, ["--mapa"])
    mapa_vivo = (base / "caminho.md").read_text(encoding="utf-8")
    r = roda(env, ["--validar", str(base / "caminho.md")])
    checa(
        "PASS: processo ancorado aparece vivo com PID",
        ("processo vivo PID %d" % processo.pid) in mapa_vivo,
        mapa_vivo,
    )
    checa("PASS: mapa com processo provado passa", r.returncode == 0, r.stdout + r.stderr)
finally:
    processo.terminate()
    try:
        processo.wait(timeout=5)
    except subprocess.TimeoutExpired:
        processo.kill()
        processo.wait(timeout=5)
    shutil.rmtree(base, ignore_errors=True)
    shutil.rmtree(run, ignore_errors=True)

# ── 6d. Caminho citado precisa existir; ausência vira declaração, não link falso.
run = run_falso()
shutil.rmtree(run / "resultados")
base, env = sala_com_historico(False, run)
roda(env, ["--mapa"])
mapa_sem_resultados = (base / "caminho.md").read_text(encoding="utf-8")
checa(
    "REPROVA: resultados ausente não é citado como caminho existente",
    ("`%s`" % (run / "resultados")) not in mapa_sem_resultados
    and "pasta de resultados ausente" in mapa_sem_resultados,
    mapa_sem_resultados,
)
ruim_path = base / "mapa-mente-path.md"
path_inexistente = run / "nao-existe"
ruim_path.write_text(
    mapa_minimo(link="- **relatórios** — `%s`" % path_inexistente),
    encoding="utf-8",
)
r = roda(env, ["--validar", str(ruim_path)])
checa(
    "REPROVA: gate recusa caminho absoluto inexistente",
    r.returncode == 1 and "caminho" in r.stdout.lower(),
    r.stdout + r.stderr,
)
shutil.rmtree(base, ignore_errors=True)
shutil.rmtree(run, ignore_errors=True)

# ── 6e. Item concluído não volta do disco fantasiado de decisão pendente.
run = run_falso()
(run / "MAPA.md").write_text(
    "# MAPA\n\n## O que espera a palavra dele\n\n"
    "1. ✅ Publicar — FEITO às 07:18\n"
    "2. PENDENTE — escolher a versão de publicação.\n",
    encoding="utf-8",
)
base, env = sala_com_historico(False, run)
roda(env, ["--mapa"])
mapa_decisao = (base / "caminho.md").read_text(encoding="utf-8")
checa(
    "REPROVA: decisão concluída some e pendência real permanece",
    "✅ Publicar" not in mapa_decisao
    and "FEITO às 07:18" not in mapa_decisao
    and "escolher a versão" in mapa_decisao,
    mapa_decisao,
)
ruim_feito = base / "mapa-mente-pendencia.md"
ruim_feito.write_text(
    mapa_minimo(espera="- ✅ Publicar — FEITO às 07:18"),
    encoding="utf-8",
)
r = roda(env, ["--validar", str(ruim_feito)])
checa(
    "REPROVA: gate recusa concluído em Espera decisão",
    r.returncode == 1 and "concluído" in r.stdout.lower(),
    r.stdout + r.stderr,
)
shutil.rmtree(base, ignore_errors=True)
shutil.rmtree(run, ignore_errors=True)

# ── 7. seleção do run: ambiente > cwd > fallback de mtime declarado
laboratorio = Path(tempfile.mkdtemp(prefix="compact-run-cwd-"))
home_teste = laboratorio / "home"
raiz_runs = home_teste / ".claude" / "iaswarm-runs"
run_cwd = raiz_runs / "run-do-cwd"
run_novo = raiz_runs / "run-mais-novo"
(run_cwd / "progress").mkdir(parents=True)
(run_novo / "progress").mkdir(parents=True)
(run_cwd / "resultados").mkdir()
(run_novo / "resultados").mkdir()
(run_cwd / "subpasta" / "profunda").mkdir(parents=True)
(run_cwd / "state.json").write_text('{"workers": []}\n', encoding="utf-8")
(run_novo / "state.json").write_text('{"workers": []}\n', encoding="utf-8")
os.utime(run_cwd / "state.json", (1700000000, 1700000000))
os.utime(run_novo / "state.json", (1800000000, 1800000000))

base, env = sala_com_historico(False)
env.pop("IASWARM_RUN", None)
env["HOME"] = str(home_teste)
env["PWD"] = str(run_novo)  # isca: variável stale não pode vencer o cwd real
r = roda(env, ["--mapa"], cwd=run_cwd / "subpasta" / "profunda")
mapa_cwd = (base / "caminho.md").read_text(encoding="utf-8")
checa("cwd dentro de run vence o mtime global",
      r.returncode == 0 and ("- run `%s`" % run_cwd) in mapa_cwd
      and ("- run `%s`" % run_novo) not in mapa_cwd,
      mapa_cwd[:700])
shutil.rmtree(base, ignore_errors=True)

fora = laboratorio / "fora-de-run"
fora.mkdir()
base, env = sala_com_historico(False)
env.pop("IASWARM_RUN", None)
env["HOME"] = str(home_teste)
env["PWD"] = str(run_cwd)  # isca: PWD stale não transforma cwd externo em run
r = roda(env, ["--mapa"], cwd=fora)
mapa_chutado = (base / "caminho.md").read_text(encoding="utf-8")
checa("fallback escolhe o run de mtime mais recente",
      r.returncode == 0 and ("- run `%s`" % run_novo) in mapa_chutado,
      mapa_chutado[:700])
checa("fallback declara na cara que adivinhou por mtime",
      "Run adivinhado pelo mtime mais recente" in mapa_chutado,
      mapa_chutado[:700])
shutil.rmtree(base, ignore_errors=True)
shutil.rmtree(laboratorio, ignore_errors=True)

print("\n%d ✔  %d ✗" % (_ok, _falhou))
sys.exit(1 if _falhou else 0)
