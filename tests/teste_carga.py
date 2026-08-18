#!/usr/bin/env python3
"""Carga real do ia-chat: 20 IAs, lock, escala, rotação sob escrita.

Por que este teste existe: `teste_concorrencia.py` cobre 5 IAs. O dono roda 7
braços com frequência e o produto vai ser publicado para salas maiores. Ninguém
tinha medido 20/50, o custo vs tamanho, o lock sob pressão, nem a rotação
disparando enquanto alguém posta.

Gate (default, vira permanente):
  G-C1  20 IAs postando em paralelo sobre chat que JÁ EXISTE com histórico
  G-C2  numeração 1..N sem buraco/duplicata; `.estado.json` bate com o chat
  G-C3  corpos íntegros (marca INICIO/FIM uma vez cada)
  G-C4  `rotate` no meio de uma fila de `post` — nada cai no vão
  G-C5  o oráculo REPROVA de propósito num chat corrompido
        (buraco + estado mentiroso). Gate que nunca viu vermelho não é gate.

`--medir`: 3 corridas das 5 perguntas do contrato d2 (números no stdout).
Tudo em IACHAT_HOME temporário. Nunca toca ~/ia-chat-global.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
IACHAT = RAIZ / "bin" / "iachat"
BIN = RAIZ / "bin"

# Placeholder para o import: home() lê o env a cada chamada, mas o módulo
# precisa existir sem apontar para a sala viva.
_PH = Path(tempfile.mkdtemp(prefix="iachat-carga-ph-"))
os.environ["IACHAT_HOME"] = str(_PH)
sys.path.insert(0, str(BIN))
import iachat_core as core  # noqa: E402

RE_META = re.compile(
    r"^<!-- iachat msg=(\d+) de=(\S+) para=(\S*) ts=\S+ -->$", re.M
)
N_IAS = 20
POR_IA = 5
IAS = [f"ia{i:02d}" for i in range(N_IAS)]
RECHEIO = ("linha de recheio para passar de 512 bytes (PIPE_BUF) " * 18).strip()

falhas: list[str] = []


def checa(nome: str, cond: bool, det: str = "") -> None:
    print(f"{'✔' if cond else '✗'} {nome}" + (f"  → {det}" if det else ""))
    if not cond:
        falhas.append(nome)


def cli(env: dict, *args: str, timeout: float = 90) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(IACHAT), *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def sala(
    ias: list[str] | None = None,
    teto: int = 2_000_000,
    historico: int = 12,
) -> tuple[Path, dict]:
    """Sala TEMPORÁRIA com chat pré-existente. O achado de 17/08: teste em
    sala nova não pega o bug que apaga histórico."""
    ias = ias or IAS
    base = Path(tempfile.mkdtemp(prefix="iachat-carga-"))
    env = {**os.environ, "IACHAT_HOME": str(base)}
    os.environ["IACHAT_HOME"] = str(base)
    core.garantir_estrutura()
    (base / "config.json").write_text(
        json.dumps(
            {
                "na_sala": ias,
                "brain": ias[0],
                "teto_bytes": teto,
                "notificar_operador": False,
            }
        )
        + "\n"
    )
    for i in range(1, historico + 1):
        core.post(
            ias[0],
            f"HISTORICO-PREEXISTENTE-{i:02d}\n\nseed de sala que já existia.\nfim-seed-{i:02d}",
            [ias[1]] if len(ias) > 1 else None,
        )
    return base, env


def limpa(*bases: Path) -> None:
    for b in bases:
        shutil.rmtree(b, ignore_errors=True)
    shutil.rmtree(_PH, ignore_errors=True)


def msgs_disco(base: Path) -> list[dict]:
    os.environ["IACHAT_HOME"] = str(base)
    achados: list[dict] = []
    for p in [core.p_chat(), *core._recortes()]:
        if p.exists():
            achados.extend(core.parse(p.read_text(encoding="utf-8")))
    achados.sort(key=lambda m: m["n"])
    return achados


def auditar(base: Path) -> dict:
    msgs = msgs_disco(base)
    nums = [m["n"] for m in msgs]
    visto: dict[int, int] = {}
    for n in nums:
        visto[n] = visto.get(n, 0) + 1
    dups = sorted(n for n, c in visto.items() if c > 1)
    maxn = max(nums) if nums else 0
    buracos = [i for i in range(1, maxn + 1) if i not in visto]
    estado_n = None
    ep = base / ".estado.json"
    if ep.exists():
        try:
            estado_n = int(json.loads(ep.read_text())["ultima"])
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            estado_n = None
    return {
        "n": len(msgs),
        "nums": nums,
        "dups": dups,
        "buracos": buracos,
        "estado": estado_n,
        "maxn": maxn,
        "ok": (
            not dups
            and not buracos
            and estado_n == maxn
            and nums == list(range(1, maxn + 1))
        ),
    }


def postar(env: dict, ia: str, i: int, marca: str) -> tuple[int, float, str]:
    corpo = (
        f"INICIO-{marca}-{ia}-{i:02d}\n\n"
        f"{RECHEIO}\n\n"
        f"Mensagem autocontida de carga.\n"
        f"FIM-{marca}-{ia}-{i:02d}"
    )
    t0 = time.perf_counter()
    r = cli(env, "post", "--de", ia, "--para", "@all", corpo)
    dt = time.perf_counter() - t0
    return r.returncode, dt, (r.stdout + r.stderr).strip()


# ─────────────────────────────────────────────────────────────────────────────
# GATE
# ─────────────────────────────────────────────────────────────────────────────


def gate_concorrencia() -> None:
    print("\n── G-C1/C2/C3  20 IAs × 5 posts sobre chat pré-existente ──")
    base, env = sala(historico=12)
    try:
        historico_txt = (base / "iachat.md").read_text(encoding="utf-8")
        checa(
            "G-C1 sala JÁ TINHA histórico antes da tempestade",
            historico_txt.count("HISTORICO-PREEXISTENTE-") == 12,
            f"{historico_txt.count('HISTORICO-PREEXISTENTE-')} seeds",
        )
        alvos = [(ia, i) for ia in IAS for i in range(1, POR_IA + 1)]
        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=N_IAS) as ex:
            res = list(ex.map(lambda t: postar(env, t[0], t[1], "C1"), alvos))
        parede = time.perf_counter() - t0
        falhou = [o for c, _, o in res if c != 0]
        lats = [dt for _, dt, _ in res]
        texto = (base / "iachat.md").read_text(encoding="utf-8")
        au = auditar(base)
        esperado = 12 + len(alvos)
        trunc = [
            f"{ia}-{i:02d}"
            for ia, i in alvos
            if texto.count(f"INICIO-C1-{ia}-{i:02d}") != 1
            or texto.count(f"FIM-C1-{ia}-{i:02d}") != 1
        ]
        seeds = sum(
            1
            for i in range(1, 13)
            if "HISTORICO-PREEXISTENTE-%02d" % i in texto
            or any(
                "HISTORICO-PREEXISTENTE-%02d" % i in m["bruto"]
                for m in msgs_disco(base)
            )
        )
        print(
            f"    tentadas={len(alvos)} falhas_cli={len(falhou)} "
            f"msgs={au['n']} (esperado {esperado}) "
            f"dups={au['dups'][:6]} buracos={au['buracos'][:6]} "
            f"estado={au['estado']} parede={parede:.3f}s "
            f"lat_max={max(lats):.3f}s lat_med={statistics.mean(lats):.3f}s "
            f"posts_s={len(alvos)/parede:.2f}"
        )
        checa("G-C1 nenhum post CLI falhou", not falhou, str(falhou[:2]))
        checa(
            "G-C1 contagem bate (histórico + novos)",
            au["n"] == esperado,
            f"{au['n']} != {esperado}",
        )
        checa("G-C2 sem números duplicados", not au["dups"], str(au["dups"][:8]))
        checa("G-C2 sem buracos", not au["buracos"], str(au["buracos"][:8]))
        checa(
            "G-C2 .estado.json == último n do disco",
            au["estado"] == au["maxn"],
            f"estado={au['estado']} maxn={au['maxn']}",
        )
        checa("G-C3 corpos sem truncar", not trunc, str(trunc[:5]))
        checa(
            "G-C3 as 12 mensagens pré-existentes sobreviveram",
            seeds == 12,
            f"{seeds}/12",
        )
    finally:
        limpa(base)


def gate_rotacao_sob_escrita() -> None:
    print("\n── G-C4  rotate enquanto posts esperam o lock ──")
    # Teto baixo para a rotação ter o que cortar. Histórico já empurra o ativo.
    base, env = sala(teto=8_192, historico=16)
    try:
        alvos = [(ia, i) for ia in IAS[:10] for i in range(1, 4)]  # 30 posts
        esperado = 16 + len(alvos)

        def _rot() -> tuple[str, float]:
            time.sleep(0.05)  # deixa a fila de post começar
            t0 = time.perf_counter()
            r = cli(env, "rotate", "--forcar")
            return (r.stdout + r.stderr).strip(), time.perf_counter() - t0

        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=12) as ex:
            futs = [ex.submit(postar, env, ia, i, "C4") for ia, i in alvos]
            fut_r = ex.submit(_rot)
            res = [f.result() for f in futs]
            out_r, dt_r = fut_r.result()
        parede = time.perf_counter() - t0
        falhou = [o for c, _, o in res if c != 0]
        au = auditar(base)
        recortes = list((base / "arquivo").glob("*.md"))
        ativo = (base / "iachat.md").read_text(encoding="utf-8")
        nos_recortes = 0
        for p in recortes:
            nos_recortes += len(core.parse(p.read_text(encoding="utf-8")))
        no_ativo = len(core.parse(ativo))
        print(
            f"    rotate={out_r.splitlines()[0] if out_r else '?'} "
            f"dt_rotate={dt_r:.3f}s parede={parede:.3f}s "
            f"recortes={len(recortes)} ativo_msgs={no_ativo} "
            f"recorte_msgs={nos_recortes} total={au['n']} "
            f"esperado={esperado} dups={au['dups'][:4]} buracos={au['buracos'][:4]}"
        )
        checa("G-C4 nenhum post falhou durante a rotação", not falhou, str(falhou[:2]))
        checa(
            "G-C4 nenhuma mensagem caiu no vão (ativo+recorte == esperado)",
            au["n"] == esperado,
            f"{au['n']} != {esperado} ativo={no_ativo} recorte={nos_recortes}",
        )
        checa("G-C4 sem duplicata após rotate+post", not au["dups"], str(au["dups"][:8]))
        checa("G-C4 sem buraco após rotate+post", not au["buracos"], str(au["buracos"][:8]))
        checa(
            "G-C4 .estado.json ainda bate",
            au["estado"] == au["maxn"],
            f"estado={au['estado']} maxn={au['maxn']}",
        )
        checa(
            "G-C4 rotação de fato criou recorte ou justificou",
            bool(recortes) or "sem rotação" in out_r or "nada" in out_r.lower(),
            out_r[:160],
        )
    finally:
        limpa(base)


def gate_oraculo_vermelho() -> None:
    print("\n── G-C5  oráculo que TEM que reprovar ──")
    base, env = sala(historico=8)
    try:
        au_ok = auditar(base)
        checa("G-C5-pre chat sadio passa no oráculo", au_ok["ok"], str(au_ok))

        # Corrompe: apaga a mensagem #3 do texto e mente no estado.
        txt = (base / "iachat.md").read_text(encoding="utf-8")
        msgs = list(RE_META.finditer(txt))
        checa("G-C5-pre há o que corromper", len(msgs) >= 4, f"{len(msgs)} metas")
        a, b = msgs[2].start(), (msgs[3].start() if len(msgs) > 3 else len(txt))
        (base / "iachat.md").write_text(txt[:a] + txt[b:])
        (base / ".estado.json").write_text(
            json.dumps({"ultima": 999, "em": "corrupto"}) + "\n"
        )
        au_bad = auditar(base)
        print(
            f"    após corrupção: n={au_bad['n']} dups={au_bad['dups']} "
            f"buracos={au_bad['buracos']} estado={au_bad['estado']} "
            f"ok={au_bad['ok']}"
        )
        checa(
            "G-C5 oráculo REPROVA chat com buraco + estado mentiroso",
            (not au_bad["ok"]) and 3 in au_bad["buracos"] and au_bad["estado"] != au_bad["maxn"],
            f"ok={au_bad['ok']} buracos={au_bad['buracos']} estado={au_bad['estado']}",
        )
    finally:
        limpa(base)


# ─────────────────────────────────────────────────────────────────────────────
# MEDIÇÃO (contrato d2 — 5 perguntas, média de ≥3)
# ─────────────────────────────────────────────────────────────────────────────


def encher_ate(base: Path, alvo: int, agulha: str = "AGULHA-CARGA") -> int:
    """Enche o ativo até ≥alvo bytes com posts REAIS (append+lock+estado)."""
    os.environ["IACHAT_HOME"] = str(base)
    n = 0
    pad = "p" * min(8000, max(700, alvo // 40))
    while (base / "iachat.md").stat().st_size < alvo:
        n += 1
        marca = agulha if n == 3 else "comum"
        core.post("ia00", f"enchente {n} {marca}\n{pad}", None)
        if n > 8000:
            break
    return n


def cronometrar(fn, vezes: int = 3) -> list[float]:
    xs = []
    for _ in range(vezes):
        t0 = time.perf_counter()
        fn()
        xs.append(time.perf_counter() - t0)
    return xs


def fmt(xs: list[float]) -> str:
    return (
        f"med={statistics.mean(xs)*1000:.1f}ms "
        f"min={min(xs)*1000:.1f}ms "
        f"max={max(xs)*1000:.1f}ms "
        f"n={len(xs)}"
    )


def medir_q2() -> None:
    print("\n══ Q2  custo × tamanho (10 KB / 100 KB / 1 MB) ══")
    alvos = [("10KB", 10_000), ("100KB", 100_000), ("1MB", 1_000_000)]
    for nome, alvo in alvos:
        base, env = sala(teto=4_000_000, historico=4)
        try:
            encher_ate(base, alvo)
            tam = (base / "iachat.md").stat().st_size
            # cursor no fim para o caso "tem coisa nova?" (caminho quente)
            maxn = auditar(base)["maxn"]
            core.marca_lida("ia01", maxn)
            # uma dirigida pendente para entregar/read ter o que fazer
            rpend = core.post("ia00", f"PENDENTE-Q2-{nome} para @ia01", ["ia01"])
            n_pend = int(rpend["n"])

            def p():
                cli(env, "post", "--de", "ia02", "--para", "ia03", f"probe-{nome}-{time.time()}")

            def rd():
                cli(env, "read", "--de", "ia01", "--sem-avancar")

            def rd_tudo():
                cli(env, "read", "--de", "ia01", "--tudo", "--sem-avancar")

            def ent():
                # repor o cursor para cada amostra ser o mesmo trabalho
                core.marca_lida("ia01", n_pend - 1)
                cli(env, "entregar", "--de", "ia01")

            def st():
                cli(env, "status")

            def se():
                cli(env, "search", "AGULHA-CARGA")

            print(f"  {nome} arquivo={tam} B")
            print(f"    post       {fmt(cronometrar(p))}")
            print(f"    read       {fmt(cronometrar(rd))}")
            print(f"    read --tudo {fmt(cronometrar(rd_tudo))}")
            print(f"    entregar   {fmt(cronometrar(ent))}")
            print(f"    status     {fmt(cronometrar(st))}")
            print(f"    search     {fmt(cronometrar(se))}")
        finally:
            limpa(base)


def medir_q3() -> None:
    print("\n══ Q3  lock sob pressão (1/5/10/20/50 IAs, 1 post cada) ══")
    for n in (1, 5, 10, 20, 50):
        nomes = [f"w{i:02d}" for i in range(n)]
        amostras_parede: list[float] = []
        amostras_max: list[float] = []
        amostras_med: list[float] = []
        for _run in range(3):
            base, env = sala(ias=nomes, historico=6)
            try:
                t0 = time.perf_counter()
                with ThreadPoolExecutor(max_workers=n) as ex:
                    res = list(
                        ex.map(lambda ia: postar(env, ia, 1, f"Q3n{n}"), nomes)
                    )
                parede = time.perf_counter() - t0
                lats = [dt for _, dt, _ in res]
                amostras_parede.append(parede)
                amostras_max.append(max(lats))
                amostras_med.append(statistics.mean(lats))
            finally:
                limpa(base)
        thr = [n / p for p in amostras_parede]
        print(
            f"  N={n:2d}  parede {fmt(amostras_parede)}  "
            f"lat_max {fmt(amostras_max)}  lat_med {fmt(amostras_med)}  "
            f"posts/s med={statistics.mean(thr):.2f} "
            f"min={min(thr):.2f} max={max(thr):.2f}"
        )


def medir_q1_extra() -> None:
    print("\n══ Q1  20 IAs × 5 (3 corridas, CLI real) ══")
    paredes, maxs, oks = [], [], []
    for run in range(3):
        base, env = sala(historico=12)
        try:
            alvos = [(ia, i) for ia in IAS for i in range(1, POR_IA + 1)]
            t0 = time.perf_counter()
            with ThreadPoolExecutor(max_workers=N_IAS) as ex:
                res = list(ex.map(lambda t: postar(env, t[0], t[1], f"Q1r{run}"), alvos))
            parede = time.perf_counter() - t0
            au = auditar(base)
            falhou = sum(1 for c, _, _ in res if c != 0)
            lats = [dt for _, dt, _ in res]
            paredes.append(parede)
            maxs.append(max(lats))
            ok = au["ok"] and au["n"] == 12 + len(alvos) and falhou == 0
            oks.append(ok)
            print(
                f"  run{run+1} ok={ok} msgs={au['n']} dups={au['dups']} "
                f"buracos={au['buracos']} estado={au['estado']} "
                f"parede={parede:.3f}s lat_max={max(lats):.3f}s "
                f"posts/s={len(alvos)/parede:.2f} cli_fail={falhou}"
            )
        finally:
            limpa(base)
    print(
        f"  resumo  3/3 íntegros={all(oks)}  parede {fmt(paredes)}  "
        f"lat_max {fmt(maxs)}"
    )


def medir_q5() -> None:
    print("\n══ Q5  status com 20 flags pendentes ══")
    base, env = sala(historico=8)
    try:
        # 20 IAs, cada uma posta @all → 19 flags por post, todos têm flag
        for ia in IAS:
            core.post(ia, f"chamado geral de {ia} @all", ["@all"])
        n_flags = len(list((base / "pendente").glob("*.md")))
        bytes_pend = sum(p.stat().st_size for p in (base / "pendente").glob("*.md"))
        tam = (base / "iachat.md").stat().st_size

        def st():
            cli(env, "status")

        xs = cronometrar(st, 5)
        # Controle: apaga flags, mede de novo (mesmo tamanho de chat)
        for p in (base / "pendente").glob("*.md"):
            p.unlink()
        ys = cronometrar(st, 5)
        print(
            f"  flags={n_flags} bytes_pendente={bytes_pend} chat={tam} B"
        )
        print(f"  status COM  flags  {fmt(xs)}")
        print(f"  status SEM  flags  {fmt(ys)}")
        print(
            f"  delta med={(statistics.mean(xs)-statistics.mean(ys))*1000:.1f}ms "
            f"(pendente/ é o gargalo? {'sim' if statistics.mean(xs) > 1.5*statistics.mean(ys) else 'não'})"
        )
    finally:
        limpa(base)


def medir_q4_repetido() -> None:
    print("\n══ Q4  rotação sob escrita (3 corridas) ══")
    for run in range(3):
        base, env = sala(teto=8_192, historico=16)
        try:
            alvos = [(ia, i) for ia in IAS[:12] for i in range(1, 4)]  # 36

            def _rot() -> str:
                time.sleep(0.02)
                return cli(env, "rotate", "--forcar").stdout.strip()

            with ThreadPoolExecutor(max_workers=14) as ex:
                futs = [ex.submit(postar, env, ia, i, f"Q4r{run}") for ia, i in alvos]
                fr = ex.submit(_rot)
                res = [f.result() for f in futs]
                out_r = fr.result()
            au = auditar(base)
            rec = list((base / "arquivo").glob("*.md"))
            falhou = sum(1 for c, _, _ in res if c != 0)
            print(
                f"  run{run+1} ok={au['ok'] and au['n']==16+len(alvos) and falhou==0} "
                f"total={au['n']} esperado={16+len(alvos)} recortes={len(rec)} "
                f"dups={au['dups']} buracos={au['buracos']} "
                f"estado={au['estado']} rotate={out_r.splitlines()[0] if out_r else '?'}"
            )
        finally:
            limpa(base)


def sonda_threads_mesmo_processo() -> None:
    """fcntl.flock é por processo. Threads no mesmo PID NÃO se serializam.
    Isto NÃO é o caminho publicado (cada IA é um processo), mas o app ou um
    hook futuro que importe o core em threads quebraria a numeração."""
    print("\n══ sonda  core.post em threads no MESMO processo ══")
    nomes = [f"t{i:02d}" for i in range(8)]
    base, env = sala(ias=nomes, historico=4)
    try:
        erros: list[str] = []

        def _p(ia: str, i: int) -> None:
            try:
                core.post(ia, f"THREAD-{ia}-{i} corpo de sonda", ["@all"])
            except Exception as e:  # noqa: BLE001 — queremos ver o que vaza
                erros.append(f"{ia}-{i}:{type(e).__name__}:{e}")

        with ThreadPoolExecutor(max_workers=8) as ex:
            futs = [ex.submit(_p, ia, i) for ia in nomes for i in range(4)]
            for f in as_completed(futs):
                f.result()
        au = auditar(base)
        print(
            f"  posts=32+4seed msgs={au['n']} dups={au['dups'][:8]} "
            f"buracos={au['buracos'][:8]} estado={au['estado']} "
            f"erros={len(erros)} ok={au['ok']}"
        )
        if au["dups"] or au["buracos"] or not au["ok"]:
            print(
                "  ACHADO: flock não serializa threads do mesmo processo "
                "(iachat_core.py:138). Caminho publicado é multiprocessos; "
                "não é gate. Reportar, não consertar."
            )
        else:
            print(
                "  nesta corrida não colidiu (GIL/sorte). O buraco de desenho "
                "continua: LOCK_EX é por PID, não por thread (iachat_core.py:138)."
            )
    finally:
        limpa(base)


def main() -> int:
    medir = "--medir" in sys.argv
    print("teste_carga — IACHAT_HOME temporário, chat pré-existente obrigatório")
    print(f"bin={IACHAT}")

    gate_concorrencia()
    gate_rotacao_sob_escrita()
    gate_oraculo_vermelho()

    if medir:
        medir_q1_extra()
        medir_q2()
        medir_q3()
        medir_q4_repetido()
        medir_q5()
        sonda_threads_mesmo_processo()

    print()
    if falhas:
        print(f"❌ REPROVOU: {falhas}")
        return 1
    print("✅ GATE DE CARGA PASSOU" + (" + medição impressa" if medir else ""))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    finally:
        shutil.rmtree(_PH, ignore_errors=True)
