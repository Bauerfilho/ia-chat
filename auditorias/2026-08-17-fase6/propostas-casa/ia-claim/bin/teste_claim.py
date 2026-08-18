#!/usr/bin/env python3
"""Bateria do ia-claim. Roda em IACHAT_HOME temporário — nunca toca a sala real.

    python3 teste_claim.py

Gates:
  1. concorrência: N processos disputam O MESMO caminho → exatamente 1 ganha
  2. concorrência: N processos, caminhos distintos → todos ganham (não serializa demais)
  3. contenção de prefixo: diretório reservado barra sub-arquivo, por COMPONENTE
  4. expiração: reserva vencida deixa de bloquear sem daemon nenhum
  5. renovação estende a partir de agora, e não soma saldo
  6. dono libera; terceiro não libera (tem que usar break)
  7. break remove E posta no chat nominando o dono (anti-quebra-silenciosa)
  8. idempotência: dono re-reservando o próprio caminho não é conflito
  9. custo: bytes do registro e do `list`, e tempo do lock segurado
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path

BIN = Path(__file__).resolve().parent

# O lab nasce UMA vez, no pai. No macOS o ProcessPoolExecutor usa `spawn`, que
# re-importa este módulo em cada worker — com o `mkdtemp` solto no topo, os 12
# workers criavam 12 labs próprios e nenhum era apagado (medido: 49 diretórios
# órfãos em `/var/folders/.../T/` depois de algumas execuções). A flag no ambiente
# distingue pai de filho, e o filho herda o lab do pai em vez de inventar o seu.
SOU_O_PAI = "CLAIM_TESTE_LAB" not in os.environ
if SOU_O_PAI:
    LAR = Path(tempfile.mkdtemp(prefix="claim-teste-"))
    os.environ["CLAIM_TESTE_LAB"] = str(LAR)
else:
    LAR = Path(os.environ["CLAIM_TESTE_LAB"])
os.environ["IACHAT_HOME"] = str(LAR)
sys.path.insert(0, str(BIN))

import iachat_claim as cl  # noqa: E402
import iachat_core as core  # noqa: E402

OK, FALHOU = [], []


def gate(nome: str, cond: bool, detalhe: str = "") -> None:
    (OK if cond else FALHOU).append(nome)
    print(f"{'✔' if cond else '✗'} {nome}" + (f"  — {detalhe}" if detalhe else ""))


def _disputa(arg):
    """Roda em processo separado: só assim o fcntl.flock é testado de verdade."""
    ia, caminho, lar = arg
    os.environ["IACHAT_HOME"] = lar
    sys.path.insert(0, str(BIN))
    import importlib
    import iachat_claim as c2
    import iachat_core as k2
    importlib.reload(k2)
    importlib.reload(c2)
    t = time.time()
    r = c2.reservar(ia, caminho, f"disputa de {ia}", 30)
    return ia, r["ok"], round((time.time() - t) * 1000, 1)


def main() -> int:
    core.garantir_estrutura()
    cfg = json.loads(core.p_config().read_text())
    cfg["na_sala"] = ["claude", "codex", "kimi", "grok", "qwen", "agy"]
    core.p_config().write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n")

    alvo = LAR / "territorio"
    (alvo / "sub").mkdir(parents=True, exist_ok=True)
    (alvo / "sub" / "arquivo.md").write_text("x")

    # ── 1. mesmo caminho, 6 processos simultâneos ────────────────────────────
    ias = ["claude", "codex", "kimi", "grok", "qwen", "agy"]
    with ProcessPoolExecutor(max_workers=6) as ex:
        res = list(ex.map(_disputa, [(i, str(alvo), str(LAR)) for i in ias]))
    venc = [i for i, ok, _ in res if ok]
    ms = [m for _, _, m in res]
    gate(
        "1. mesmo caminho: exatamente 1 vence",
        len(venc) == 1,
        f"vencedor={venc} · {len(res)} processos · lock máx {max(ms):.1f} ms",
    )
    dono = venc[0] if venc else None

    # ── 2. caminhos distintos: ninguém se atrapalha ──────────────────────────
    alvos = [str(alvo.parent / f"outro-{i}") for i in range(6)]
    with ProcessPoolExecutor(max_workers=6) as ex:
        res2 = list(ex.map(_disputa, [(ia, a, str(LAR)) for ia, a in zip(ias, alvos)]))
    gate(
        "2. caminhos distintos: todos vencem",
        all(ok for _, ok, _ in res2),
        f"{sum(ok for _, ok, _ in res2)}/6 · lock máx {max(m for _, _, m in res2):.1f} ms",
    )
    for a, ia in zip(alvos, ias):
        cl.liberar(ia, a)

    # ── 3. contenção de prefixo, por componente ──────────────────────────────
    outro = next(i for i in ias if i != dono)
    r_sub = cl.reservar(outro, str(alvo / "sub" / "arquivo.md"), "editar sub", 30)
    vizinho = str(alvo) + "-vizinho"  # /x/territorio-vizinho NÃO está sob /x/territorio
    r_viz = cl.reservar(outro, vizinho, "não deve colidir", 30)
    gate(
        "3. prefixo por componente: sub barrado, vizinho liberado",
        (not r_sub["ok"]) and r_viz["ok"],
        f"sub={'barrado' if not r_sub['ok'] else 'PASSOU'} · territorio-vizinho={'ok' if r_viz['ok'] else 'BARRADO'}",
    )
    cl.liberar(outro, vizinho)

    # ── 4. expiração sem daemon ──────────────────────────────────────────────
    p = cl._p_claim(str(alvo))
    c = json.loads(p.read_text())
    c["ate"] = (datetime.now().astimezone() - timedelta(seconds=1)).isoformat(timespec="seconds")
    p.write_text(json.dumps(c, ensure_ascii=False))
    livre = cl.checar(outro, str(alvo))["estado"] == "livre"
    r_dep = cl.reservar(outro, str(alvo), "assumindo depois de vencer", 30)
    gate(
        "4. reserva vencida não bloqueia (sem daemon, sem cron)",
        livre and r_dep["ok"],
        f"check={('livre' if livre else 'AINDA BLOQUEIA')} · re-reserva por {outro}={r_dep['ok']}",
    )

    # ── 5. renovação estende a partir de agora, não soma ─────────────────────
    cl.renovar(outro, str(alvo), 10)
    c1 = json.loads(cl._p_claim(str(alvo)).read_text())
    r5 = cl.renovar(outro, str(alvo), 10)
    c2 = json.loads(cl._p_claim(str(alvo)).read_text())
    d1 = datetime.fromisoformat(c1["ate"])
    d2 = datetime.fromisoformat(c2["ate"])
    delta = (d2 - d1).total_seconds()
    gate(
        "5. renovação = a partir de agora (não acumula saldo)",
        abs(delta) < 5 and c2["renovacoes"] == 2,
        f"2ª renovação moveu o vencimento em {delta:.1f}s (somar daria +600s) · renovações={c2['renovacoes']}",
    )

    # ── 6. dono libera; terceiro não ─────────────────────────────────────────
    terceiro = next(i for i in ias if i not in (outro, dono))
    r_t = cl.liberar(terceiro, str(alvo))
    r_d = cl.liberar(outro, str(alvo))
    gate(
        "6. só o dono libera",
        (not r_t["ok"]) and r_d["ok"],
        f"terceiro={'negado' if not r_t['ok'] else 'LIBEROU!'} · dono={'ok' if r_d['ok'] else 'FALHOU'}",
    )

    # ── 7. break avisa o dono no chat ────────────────────────────────────────
    cl.reservar(dono, str(alvo), "trabalho do dono", 60)
    antes = len(core.parse(core.p_chat().read_text()))
    rb = cl.quebrar(terceiro, str(alvo), "precisei subir um hotfix")
    txt = core.p_chat().read_text()
    depois = core.parse(txt)
    ultima = depois[-1] if depois else {}
    gate(
        "7. break remove E posta nominando o dono",
        (not cl._p_claim(str(alvo)).exists())
        and len(depois) == antes + 1
        and dono in ultima.get("para", [])
        and ultima.get("de") == terceiro,
        f"msg #{rb.get('msg')} de {ultima.get('de')} → {ultima.get('para')}",
    )

    # ── 8. idempotência do dono ──────────────────────────────────────────────
    cl.reservar(dono, str(alvo), "primeira", 30)
    d_ini = json.loads(cl._p_claim(str(alvo)).read_text())["desde"]
    r8 = cl.reservar(dono, str(alvo), "mesma empreitada, prazo novo", 45)
    gate(
        "8. dono re-reservando o próprio caminho não é conflito",
        r8["ok"] and r8["claim"]["desde"] == d_ini and r8["claim"]["minutos"] == 45,
        f"desde preservado={r8['claim']['desde'] == d_ini}",
    )

    # ── 9. custo ─────────────────────────────────────────────────────────────
    for i, ia in enumerate(ias):
        cl.reservar(ia, str(LAR / f"carga-{i}"), f"carga {i}", 60)
    reg = cl._p_claim(str(alvo)).stat().st_size
    saida = subprocess.run(
        [sys.executable, str(BIN / "iachat-claim"), "list"],
        capture_output=True, text=True, env={**os.environ, "IACHAT_HOME": str(LAR)},
    ).stdout
    t0 = time.time()
    for _ in range(50):
        cl.checar("claude", str(LAR / "carga-3"))
    ms_check = (time.time() - t0) / 50 * 1000
    t0 = time.time()
    for _ in range(20):
        cl.reservar("claude", str(LAR / "bench"), "bench", 5)
    ms_take = (time.time() - t0) / 20 * 1000
    gate(
        "9. custo medido",
        reg < 512 and len(saida.encode()) < 4096,
        f"registro {reg} B · `list` com {len(ias)+1} reservas = {len(saida.encode())} B "
        f"(~{len(saida.encode())//4} tokens) · check {ms_check:.2f} ms · take {ms_take:.2f} ms",
    )

    print(f"\n{len(OK)}/{len(OK)+len(FALHOU)} gates" + (f" · FALHOU: {FALHOU}" if FALHOU else " · tudo verde"))
    print(f"lab: {LAR}")
    return 1 if FALHOU else 0


if __name__ == "__main__":
    try:
        rc = main()
    finally:
        if SOU_O_PAI:
            shutil.rmtree(LAR, ignore_errors=True)
    sys.exit(rc)
