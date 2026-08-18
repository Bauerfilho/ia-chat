#!/usr/bin/env python3
"""Núcleo do `iachat claim` — reserva de território entre IAs na mesma máquina.

POR QUE ISTO EXISTE: as IAs da sala compartilham o disco. Em 17/08 três cascas
tocaram `~/.claude/skills/`, `~/.kimi-code/config.toml` e `~/.codex/hooks.json` no
mesmo dia — e o Codex tem a armadilha do `trusted_hash`, que quebra em SILÊNCIO
quando outro edita o arquivo dele. Colisão aqui não é hipótese; é o dia de ontem.

TRÊS DECISÕES QUE O RESTO SEGUE:

1. RESERVA É ESTADO, NÃO CONVERSA. Mora em `claims/`, ao lado de `cursor/` e
   `pendente/` (iachat_core.py:65-70), não no chat. Se cada reserva postasse, 20
   reservas/dia × ~300 B custariam 6 KB/dia no ativo de 200 KB — e cada IA paga
   o ativo toda vez que entra. O chat é para o que precisa ser LIDO; a reserva
   precisa ser CONSULTADA. Exceção única: `break` sempre posta, porque quebrar a
   reserva de alguém é ato social, não estado.

2. A EXCLUSÃO MÚTUA É DE GRAÇA. `travado()` (iachat_core.py:126-137) já dá lock
   exclusivo por `fcntl.flock`. O "existe reserva viva?" e o "grava a minha" cabem
   na MESMA seção crítica, então não há janela TOCTOU — sem uma linha de lock nova.
   Custo medido do empréstimo: ver NOTA.md §5.

3. EXPIRA POR RELÓGIO DE PAREDE, SEM DAEMON. A reserva carrega `ate`; quem lê
   compara com agora. Não há processo de limpeza, não há cron, não há sino. Uma
   reserva vencida é indistinguível de inexistente no instante em que vence — que é
   exatamente o que se quer de uma IA que fechou a janela e não liberou.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import iachat_core as core  # noqa: E402

# 60 min. Medido em 17/08 nesta máquina: agrupando as escritas de 72 h em
# `~/.claude`, `~/.codex` e `~/.kimi-code` por empreitada (corte em gap > 15 min),
# a MEDIANA de duração foi 65,1 min e o p90 foi 218,6 min.
#
# A régua não é simétrica, e é ela que fixa o número: reserva que expira CEDO
# demais falha em silêncio — a dona ainda está trabalhando e outra IA entra por
# cima, que é o defeito original de volta com uma camada de falsa segurança em
# cima. Reserva que expira TARDE demais só custa um `claim break`, que é um
# comando e fica registrado. Então o padrão cobre a empreitada mediana, e o
# excedente se resolve por renovação explícita.
MIN_PADRAO = 60
# Teto duro: 4 h ≈ o p90 medido (218,6 min). Acima disso não é reserva, é posse —
# e posse se negocia no chat, não num arquivo de estado.
MIN_TETO = 240

# Reserva parada há mais que isto entra no relatório como suspeita de órfã. NÃO
# libera nada: quem libera é a expiração. Isto só qualifica o que o humano/IA vê.
SUSPEITA_MIN = 20


def p_claims() -> Path:
    return core.home() / "claims"


def _agora() -> datetime:
    return datetime.now().astimezone()


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def resolver(caminho: str) -> str:
    """Caminho absoluto e canônico. `~`, `.`, `..` e symlink resolvidos.

    Sem isto, `~/.claude/skills` e `/Users/bauer.../.claude/skills/` seriam duas
    reservas diferentes do MESMO diretório — e o mecanismo inteiro viraria teatro.
    """
    return str(Path(caminho).expanduser().resolve())


def _slug(caminho: str) -> str:
    """Nome do arquivo: hash (unicidade) + cauda legível (para `ls` servir a humano)."""
    h = hashlib.sha1(caminho.encode()).hexdigest()[:12]
    legivel = re.sub(r"[^A-Za-z0-9._-]+", "-", caminho.strip("/"))[-48:].strip("-")
    return f"{h}-{legivel}.json"


def _p_claim(caminho: str) -> Path:
    """Resolve SEMPRE, mesmo já vindo resolvido — resolver é idempotente e barato.

    Sem isto o mesmo alvo gera dois registros e a reserva não vale nada. Pego no
    teste, no macOS: `/var/folders/...` é symlink de `/private/var/folders/...`, e o
    slug do caminho bruto não bate com o slug do resolvido. Mesma armadilha vale
    para `~`, `.` e qualquer symlink no meio do caminho — e a casa é cheia deles.
    """
    return p_claims() / _slug(resolver(caminho))


def colidem(a: str, b: str) -> bool:
    """Conflito = mesmo caminho ou um contém o outro, por COMPONENTE.

    Comparar string crua faria `/a/bc` colidir com `/a/b`. O caso real do projeto é
    justamente de diretório: reservar `~/.claude/skills/` tem que barrar quem quer
    `~/.claude/skills/ia-bell/SKILL.md`, senão a reserva não cobre a colisão que
    motivou a peça.
    """
    if a == b:
        return True
    pa, pb = a.rstrip("/") + "/", b.rstrip("/") + "/"
    return pa.startswith(pb) or pb.startswith(pa)


def _ler(p: Path) -> dict | None:
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not all(k in d for k in ("caminho", "de", "ate")):
        return None
    d["_arquivo"] = str(p)
    return d


def viva(c: dict, quando: datetime | None = None) -> bool:
    try:
        return datetime.fromisoformat(c["ate"]) > (quando or _agora())
    except (ValueError, KeyError):
        return False


def listar(incluir_vencidas: bool = False) -> list[dict]:
    """Todas as reservas em disco. O(n) num diretório de dezenas — irrelevante."""
    p_claims().mkdir(parents=True, exist_ok=True)
    agora = _agora()
    out = []
    for p in sorted(p_claims().glob("*.json")):
        c = _ler(p)
        if c is None:
            continue
        c["viva"] = viva(c, agora)
        if c["viva"] or incluir_vencidas:
            out.append(c)
    return out


def _sinal_de_vida(ia: str) -> dict:
    """Ela ainda está aí? Dois sinais, os dois já existentes e de graça.

    · CURSOR (`cursor/<ia>.json`, iachat_core.py:308-314) — carrega `em`, gravado a
      cada leitura da sala. É o único heartbeat honesto que o projeto tem.
    · MTIME DO ALVO — se a reserva diz "mexendo em X" e X não muda há muito, ou
      acabou e esqueceu de liberar, ou parou.

    O QUE ESTES SINAIS NÃO SÃO: prova de morte. O cursor só avança quando há
    mensagem a ler (`if avancar and msgs`, iachat_core.py:346), então sala parada
    congela o cursor de uma IA perfeitamente viva. Logo o sinal é ASSIMÉTRICO:
    cursor recente PROVA vida; cursor velho não prova nada. Por isso nada aqui
    libera reserva — só a expiração libera. Isto colore o relatório, não decide.

    PID foi considerado e DESCARTADO: o PID disponível é o do processo `iachat`,
    que morre no fim do comando. `os.kill(pid, 0)` sobre ele responderia "morta"
    sempre, e sobre um PID reciclado responderia "viva" mentindo. Sinal pior que
    nenhum é o que a casa chama de instrumento que mente.
    """
    r = {"cursor_em": None, "cursor_min": None, "alvo_min": None}
    try:
        d = json.loads(core.p_cursor(core.normaliza_ia(ia)).read_text())
        r["cursor_em"] = d.get("em")
        r["cursor_min"] = round(
            (_agora() - datetime.fromisoformat(d["em"])).total_seconds() / 60, 1
        )
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        pass
    return r


def _suspeita(c: dict) -> str | None:
    """Frase curta de suspeita, ou None. Advisory — nunca veredito.

    Reserva mais nova que `SUSPEITA_MIN` nunca é suspeita: ela acabou de nascer, e
    nenhum dos dois sinais teve tempo de significar coisa alguma. Sem esta guarda, a
    primeira reserva de uma sala nova sai marcada como possível órfã (medido: sala
    recém-criada, cursor inexistente ⇒ "nunca leu a sala"). Aviso que dispara sozinho
    é o mesmo defeito do sino que anunciava o Codex e era a Claude.
    """
    try:
        if (_agora() - datetime.fromisoformat(c["desde"])).total_seconds() / 60 < SUSPEITA_MIN:
            return None
    except (ValueError, KeyError):
        pass
    s = _sinal_de_vida(c["de"])
    partes = []
    if s["cursor_min"] is not None and s["cursor_min"] > SUSPEITA_MIN:
        partes.append(f"cursor de {c['de']} parado há {s['cursor_min']:.0f} min")
    elif s["cursor_min"] is None:
        partes.append(f"{c['de']} nunca leu a sala")
    if c.get("alvo_min") is not None and c["alvo_min"] > SUSPEITA_MIN:
        partes.append(f"alvo intocado há {c['alvo_min']:.0f} min")
    return "; ".join(partes) + " — pode ser órfã, confira antes de esperar" if partes else None


def _com_alvo(c: dict) -> dict:
    try:
        c["alvo_min"] = round(
            (_agora().timestamp() - os.stat(c["caminho"]).st_mtime) / 60, 1
        )
    except OSError:
        c["alvo_min"] = None
    return c


def restante_min(c: dict) -> float:
    return round(
        (datetime.fromisoformat(c["ate"]) - _agora()).total_seconds() / 60, 1
    )


def reservar(
    de: str, caminho: str, para_que: str, minutos: int = MIN_PADRAO
) -> dict:
    """Reserva `caminho` para `de`. Idempotente para o dono, bloqueante para terceiro.

    Toda a decisão roda DENTRO de `travado()`: ler as reservas existentes, decidir e
    gravar são uma operação só. Duas IAs chamando isto no mesmo instante entram em
    fila no `flock` — a segunda enxerga a reserva da primeira já em disco e perde.
    Não há empate possível, e não escrevi lock nenhum para isso.
    """
    de = core.normaliza_ia(de)
    caminho = resolver(caminho)
    para_que = (para_que or "").strip()
    if not para_que:
        raise ValueError(
            "--para-que é obrigatório: reserva sem motivo não informa quem lê, "
            "e o que não informa ninguém respeita."
        )
    minutos = max(1, min(int(minutos), MIN_TETO))

    with core.travado():
        p_claims().mkdir(parents=True, exist_ok=True)
        for c in listar():
            if colidem(caminho, c["caminho"]) and c["de"] != de:
                return {
                    "ok": False,
                    "motivo": "reservado",
                    "conflito": _com_alvo(c),
                    "restante_min": restante_min(c),
                    "suspeita": _suspeita(_com_alvo(c)),
                }
        agora = _agora()
        p = _p_claim(caminho)
        antigo = _ler(p) if p.exists() else None
        c = {
            "caminho": caminho,
            "de": de,
            "para_que": para_que,
            "desde": (antigo or {}).get("desde", _iso(agora)) if antigo and antigo.get("de") == de else _iso(agora),
            "ate": _iso(agora + timedelta(minutes=minutos)),
            "minutos": minutos,
            "renovacoes": (antigo or {}).get("renovacoes", 0) if antigo and antigo.get("de") == de else 0,
        }
        core._escrever_atomico(p, json.dumps(c, ensure_ascii=False, indent=2) + "\n")
    return {"ok": True, "claim": c, "arquivo": str(p)}


def renovar(de: str, caminho: str, minutos: int = MIN_PADRAO) -> dict:
    """Estende A PARTIR DE AGORA — não soma ao prazo antigo.

    Somar deixaria a reserva de uma IA que renovou 6× viva por 6 h sem que ninguém
    tenha decidido isso. Renovação é uma afirmação de presente ("ainda estou aqui,
    me dá mais 60 min"), não um saldo acumulado.
    """
    de = core.normaliza_ia(de)
    caminho = resolver(caminho)
    minutos = max(1, min(int(minutos), MIN_TETO))
    with core.travado():
        c = _ler(_p_claim(caminho))
        if c is None:
            return {"ok": False, "motivo": "não existe reserva para este caminho"}
        if c["de"] != de:
            return {"ok": False, "motivo": f"a reserva é de {c['de']}, não sua", "conflito": c}
        c["ate"] = _iso(_agora() + timedelta(minutes=minutos))
        c["minutos"] = minutos
        c["renovacoes"] = int(c.get("renovacoes", 0)) + 1
        c.pop("_arquivo", None)
        core._escrever_atomico(
            _p_claim(caminho), json.dumps(c, ensure_ascii=False, indent=2) + "\n"
        )
    return {"ok": True, "claim": c}


def liberar(de: str, caminho: str) -> dict:
    """Só o dono libera. Terceiro usa `break`, que é registrado."""
    de = core.normaliza_ia(de)
    caminho = resolver(caminho)
    with core.travado():
        p = _p_claim(caminho)
        c = _ler(p)
        if c is None:
            return {"ok": True, "motivo": "não havia reserva (já livre)"}
        if c["de"] != de:
            return {
                "ok": False,
                "motivo": f"a reserva é de {c['de']}. Use `claim break` — que avisa {c['de']} no chat.",
                "conflito": c,
            }
        p.unlink(missing_ok=True)
    return {"ok": True, "liberado": caminho, "era_de": de}


def quebrar(de: str, caminho: str, motivo: str) -> dict:
    """Remove reserva alheia E POSTA no chat nominando o dono.

    Este é o escape hatch honesto do desenho. Um plugin de chat não consegue impedir
    o `Write` de outra IA (ver SKILL.md §"o dente"), então fingir que a reserva é
    inviolável seria mentir. O que se pode garantir é que a quebra não seja
    SILENCIOSA — e é isso que o post faz. O dono descobre por sino, não por bug.
    """
    de = core.normaliza_ia(de)
    caminho = resolver(caminho)
    motivo = (motivo or "").strip()
    if not motivo:
        raise ValueError("--motivo é obrigatório: quebra sem motivo é atropelo")
    with core.travado():
        p = _p_claim(caminho)
        c = _ler(p)
        if c is None:
            return {"ok": True, "motivo": "não havia reserva"}
        p.unlink(missing_ok=True)
    dono = c["de"]
    aviso = (
        f"@{dono} quebrei sua reserva de `{caminho}`\n\n"
        f"- reservado para: {c.get('para_que', '—')}\n"
        f"- valia até: {c['ate']} ({restante_min(c):+.0f} min)\n"
        f"- quebrei porque: {motivo}\n\n"
        f"Se você ainda estava mexendo, fale agora — reserve de novo com "
        f"`iachat claim take {caminho} --de {dono} --para-que \"...\"`."
    )
    try:
        r = core.post(de, aviso)
        return {"ok": True, "quebrada": c, "msg": r["n"]}
    except ValueError as e:
        # Fora da sala: a quebra vale, mas o dono não foi avisado — e isso tem que
        # aparecer, não sumir. Quebra sem aviso é o defeito, não um detalhe.
        return {"ok": True, "quebrada": c, "msg": None, "erro_post": str(e)}


def checar(de: str, caminho: str) -> dict:
    """Read-only, sem lock: "posso mexer aqui?". É o que um hook chama.

    Sem lock de propósito. Consulta é o caminho mais quente (todo Write/Edit passaria
    por aqui num hook) e entrar na fila do lock global da sala a cada tecla seria
    cobrar de quem POSTA o preço de quem CONSULTA. O pior que a corrida faz aqui é
    responder "livre" a um caminho reservado meio milissegundo antes — e a resposta
    já era advisory de qualquer jeito.
    """
    de = core.normaliza_ia(de)
    caminho = resolver(caminho)
    for c in listar():
        if colidem(caminho, c["caminho"]):
            if c["de"] == de:
                return {"estado": "minha", "claim": c, "restante_min": restante_min(c)}
            c = _com_alvo(c)
            return {
                "estado": "reservado",
                "claim": c,
                "restante_min": restante_min(c),
                "suspeita": _suspeita(c),
            }
    return {"estado": "livre", "caminho": caminho}
