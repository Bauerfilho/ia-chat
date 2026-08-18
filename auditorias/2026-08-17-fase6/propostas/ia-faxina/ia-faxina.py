#!/usr/bin/env python3
"""ia-faxina — limpeza automática dos artefatos que o plugin ia-chat gera.

POR QUE EXISTE: o plugin cria arquivo novo e nunca recolhe. Instalador deixa
`.bak-iachat-*` ao lado de cada config de casca; cada daemon do sino appenda no
próprio log para sempre; `.tmp` de escrita atômica fica órfão se o processo morre
no meio; flag de `pendente/` de IA que saiu da sala não tem mais quem leia.
Nenhum deles é grande sozinho — o problema é que nada some, nunca.

A política veio da casa (backup-claude.sh, 11/06), não inventada:
  · retenção DECLARADA por contagem, nunca por julgamento caso a caso
  · idempotência: rodar duas vezes seguidas = a segunda não faz nada
  · TUDO que some deixa linha de log (quem, o quê, quando, quantos bytes)
  · o que está em uso não se toca — a janela de retenção só alcança o antigo

E uma trava a mais, pedida no contrato da faxina: backup do MESMO DIA nunca se
apaga. Backup existe para o dia em que algo dá errado; apagar o de hoje é deixar
o dono sem rede exatamente quando ele mais precisa.

O que esta peça NUNCA toca:
  · iachat.md, config.json, .estado.json       (a sala viva)
  · arquivo/                                    (recortes imutáveis: histórico)
  · cursor/ de IA que ainda está na sala        (posição de leitura)
  · pendente/ de IA que ainda está na sala      (notificação ao vivo)
  · .lock/                                      (o lock do núcleo)

Uso:
  ia-faxina.py                 # DRY-RUN (padrão): mostra o que faria, não toca
  ia-faxina.py --aplicar       # limpa de verdade, logando cada remoção
  ia-faxina.py --json          # relatório em JSON (para outra IA ou gate ler)

A sala é a do IACHAT_HOME (default ~/ia-chat-global) — mesma variável que o
resto do plugin usa, então o teste roda em sala falsa sem sujar a real.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

# ── Retenção declarada ────────────────────────────────────────────────────────
# Cada número aqui é uma decisão, não um detalhe. Mudar é legítimo; esconder, não.
BAK_MANTER = 3        # por config de casca: os N .bak-iachat-* mais recentes
BAK_IDADE_MIN_DIAS = 1  # e só se tiverem 1+ dia — backup do mesmo dia é intocável
LOG_MAX_LINHAS = 500  # acima disso o log do sino é aparado
LOG_CAUDA_LINHAS = 200  # ...para este tamanho (a cauda: o recente é o que importa)
TMP_IDADE_S = 300     # .tmp com 5+ min é órfão certo: a escrita atômica é instante


def home() -> Path:
    return Path(os.environ.get("IACHAT_HOME", "~/ia-chat-global")).expanduser()


def agora_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def idade_dias(p: Path) -> float:
    return (time.time() - p.stat().st_mtime) / 86400


def log_faxina(aplicar: bool, linhas: list[str]) -> None:
    """Toda decisão de REMOÇÃO passa por aqui. Dry-run também loga, marcado."""
    h = home()
    h.mkdir(parents=True, exist_ok=True)
    tag = "APLICADO" if aplicar else "DRY-RUN"
    with (h / "faxina.log").open("a", encoding="utf-8") as f:
        for ln in linhas:
            f.write(f"[{agora_iso()}] [{tag}] {ln}\n")


class Plano:
    """Acumula ações para o relatório — dry-run e aplicar montam o mesmo plano."""

    def __init__(self) -> None:
        self.acoes: list[dict] = []
        self.preservados: list[dict] = []

    def remover(self, categoria: str, caminho: Path, motivo: str, extra: str = "") -> None:
        self.acoes.append({
            "acao": "remover", "categoria": categoria, "caminho": str(caminho),
            "bytes": caminho.stat().st_size if caminho.exists() else 0,
            "motivo": motivo, "extra": extra,
        })

    def truncar(self, caminho: Path, de: int, para: int, motivo: str) -> None:
        self.acoes.append({
            "acao": "truncar", "categoria": "log-sino", "caminho": str(caminho),
            "bytes": caminho.stat().st_size, "motivo": motivo,
            "extra": f"{de}→{para} linhas",
        })

    def preservar(self, categoria: str, caminho: Path, motivo: str) -> None:
        self.preservados.append({
            "categoria": categoria, "caminho": str(caminho), "motivo": motivo,
        })


RE_STAMP_BAK = re.compile(r"\.bak-iachat-(\d{8}-\d{6})$")


def idade_dias_bak(p: Path) -> float:
    """Idade REAL do backup, lida do carimbo no nome — não do mtime.

    Descoberto em sala real: o instalador usa `shutil.copy2`, que PRESERVA o
    mtime do arquivo copiado. Um backup feito HOJE de um settings.json parado
    há 3 dias carrega mtime de 3 dias atrás — e o teste de "backup do mesmo
    dia" aprovaria apagá-lo no dia em que foi criado. O nome do backup é o
    relógio de quem o criou (`datetime.now():%Y%m%d-%H%M%S`); ele não mente.
    Sem carimbo reconhecível, cai no mtime (caso raro, conservador).
    """
    m = RE_STAMP_BAK.search(p.name)
    if m:
        try:
            criado = datetime.strptime(m.group(1), "%Y%m%d-%H%M%S").timestamp()
            return (time.time() - criado) / 86400
        except ValueError:
            pass
    return idade_dias(p)


def varrer_baks(plano: Plano, pastas_shells: list[Path]) -> None:
    """`.bak-iachat-*` que os instaladores deixam ao lado de cada config.

    Regra: por config original (settings.json, config.toml...), mantém os
    BAK_MANTER mais recentes E nunca toca backup do mesmo dia — o resto sai.
    """
    for pasta in pastas_shells:
        if not pasta.is_dir():
            continue
        grupos: dict[str, list[Path]] = {}
        for p in pasta.glob("*.bak-iachat-*"):
            # o nome original é tudo antes de ".bak-iachat-"
            grupos.setdefault(p.name.split(".bak-iachat-")[0], []).append(p)
        for original, baks in grupos.items():
            baks.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            for i, p in enumerate(baks):
                if idade_dias_bak(p) < BAK_IDADE_MIN_DIAS:
                    plano.preservar("bak-iachat", p, "backup do mesmo dia (<1d) — intocável")
                elif i < BAK_MANTER:
                    plano.preservar("bak-iachat", p, f"retido: {BAK_MANTER} mais recentes de {original}")
                else:
                    plano.remover("bak-iachat", p,
                                  f"excedente (mantém {BAK_MANTER} de {original}, idade {idade_dias_bak(p):.1f}d)")


def varrer_logs_sino(plano: Plano) -> None:
    """Logs que o daemon appenda para sempre. Aparar, não apagar: o daemon reabre
    o caminho a cada escrita, e o histórico recente de sino é diagnóstico vivo."""
    for p in sorted(home().glob("ia-bell-*.log")):
        try:
            linhas = p.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        if len(linhas) > LOG_MAX_LINHAS:
            plano.truncar(p, len(linhas), LOG_CAUDA_LINHAS,
                          f"log do sino passou de {LOG_MAX_LINHAS} linhas")
        else:
            plano.preservar("log-sino", p, f"{len(linhas)} linhas ≤ {LOG_MAX_LINHAS}")
    # .out/.err ficam: são 0 bytes e o launchd os recria; mexer neles é risco sem ganho.


def varrer_tmps(plano: Plano) -> None:
    """Órfãos da escrita atômica (tmp+replace). Com 5+ minutos o escritor já morreu;
    mais novo que isso pode ser escrita em curso — não se aproxima."""
    for p in home().rglob("*.tmp"):
        if p.stat().st_mtime < time.time() - TMP_IDADE_S:
            plano.remover("tmp-orfao", p, f"órfão de escrita atômica (idade {int(time.time() - p.stat().st_mtime)}s)")
        else:
            plano.preservar("tmp-orfao", p, "novo demais (<5min): pode ser escrita em curso")


def varrer_pendentes(plano: Plano, sala: list[str]) -> None:
    """Flag de IA que NÃO está mais na sala não tem mais quem leia: é lixo.
    Flag de IA na sala é notificação ao vivo — nem sob tortura."""
    for p in sorted((home() / "pendente").glob("*.md")):
        dono = p.stem
        if dono in sala:
            plano.preservar("pendente", p, f"{dono} está na sala: notificação viva")
        else:
            plano.remover("pendente-sem-dono", p, f"{dono} não está mais em na_sala {sala}")


def varrer_cursoreS(plano: Plano, sala: list[str]) -> None:
    """Cursor órfão: só RELATAR. São ~55 bytes e apagar seria perder a posição de
    leitura caso a IA volte à sala. Faxina que economiza 55 bytes perdendo estado
    é faxina que trabalha contra o dono."""
    for p in sorted((home() / "cursor").glob("*.json")):
        if p.stem not in sala:
            plano.preservar("cursor-orfao", p, f"{p.stem} saiu da sala — retido: é estado, não lixo")


def varrer_arquivo(plano: Plano) -> None:
    n = sum(1 for _ in (home() / "arquivo").glob("*.md")) if (home() / "arquivo").is_dir() else 0
    plano.preservar("arquivo-recortes", home() / "arquivo",
                    f"{n} recorte(s) imutável(is): histórico paginável — fora do escopo da faxina")


def ler_sala() -> list[str]:
    try:
        cfg = json.loads((home() / "config.json").read_text(encoding="utf-8"))
        return [str(x).lower().lstrip("@") for x in cfg.get("na_sala", [])]
    except (OSError, json.JSONDecodeError):
        return []


def aplicar(plano: Plano) -> None:
    linhas = []
    for a in plano.acoes:
        p = Path(a["caminho"])
        if a["acao"] == "remover":
            p.unlink()
            linhas.append(f"removido {a['categoria']} {p} ({a['bytes']} B) — {a['motivo']}")
        elif a["acao"] == "truncar":
            conteudo = p.read_text(encoding="utf-8", errors="replace").splitlines()
            cauda = "\n".join(conteudo[-LOG_CAUDA_LINHAS:]) + "\n"
            # mesma escrita atômica do núcleo: o daemon pode estar lendo
            tmp = p.with_suffix(p.suffix + ".tmp")
            tmp.write_text(cauda, encoding="utf-8")
            os.replace(tmp, p)
            linhas.append(f"aparado {p} ({a['extra']}) — {a['motivo']}")
    if linhas:
        log_faxina(True, linhas)


def relatorio(plano: Plano, aplicar_flag: bool) -> int:
    bytes_liberados = sum(a["bytes"] for a in plano.acoes if a["acao"] == "remover")
    verbo = "seriam removidos" if not aplicar_flag else "removidos"
    print(f"ia-faxina · {'APLICADO' if aplicar_flag else 'DRY-RUN (nada foi tocado)'}")
    print(f"sala: {home()}")
    if not plano.acoes:
        print("✔ nada a limpar — a sala está limpa (idempotente: segunda rodada dá isto)")
        return 0
    for a in plano.acoes:
        print(f"  - [{a['acao']}] {a['categoria']}: {a['caminho']} "
              f"({a['bytes']} B{'; ' + a['extra'] if a['extra'] else ''}) — {a['motivo']}")
    print(f"total: {len(plano.acoes)} ação(ões), {bytes_liberados} B {verbo}")
    if not aplicar_flag:
        print("→ para executar de verdade: ia-faxina.py --aplicar")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(prog="ia-faxina", description=__doc__)
    ap.add_argument("--aplicar", action="store_true",
                    help="limpa de verdade (padrão é dry-run: só mostra)")
    ap.add_argument("--json", action="store_true", help="relatório em JSON")
    ap.add_argument("--pasta-shell", action="append", default=None,
                    help="pasta de casca a varrer por .bak-iachat-* "
                         "(default: ~/.claude e ~/.kimi-code)")
    a = ap.parse_args()

    if not home().is_dir():
        print(f"✗ sala não existe: {home()}", file=sys.stderr)
        return 2

    pastas = [Path(x).expanduser() for x in a.pasta_shell] if a.pasta_shell else [
        Path.home() / ".claude", Path.home() / ".kimi-code",
    ]
    sala = ler_sala()

    plano = Plano()
    varrer_baks(plano, pastas)
    varrer_logs_sino(plano)
    varrer_tmps(plano)
    varrer_pendentes(plano, sala)
    varrer_cursoreS(plano, sala)
    varrer_arquivo(plano)

    if a.aplicar:
        aplicar(plano)

    if a.json:
        print(json.dumps({
            "modo": "aplicar" if a.aplicar else "dry-run",
            "sala": str(home()),
            "na_sala": sala,
            "acoes": plano.acoes,
            "preservados": plano.preservados,
        }, ensure_ascii=False, indent=2))
        return 0
    return relatorio(plano, a.aplicar)


if __name__ == "__main__":
    sys.exit(main())
