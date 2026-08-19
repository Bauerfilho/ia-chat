#!/usr/bin/env python3
"""Emissor instalável e fail-closed da telemetria consumida pelo groupchat.

O lado visual já sabe ler ``groupchat.jsonl``. Esta peça só produz uma linha
do contrato por medição. A regra central é simples: se o formato de origem não
for exatamente reconhecido, emite ``unknown``; nunca improvisa um percentual.
"""
from __future__ import annotations

import datetime as dt
import argparse
import fcntl
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


FONTE_CODEX = (
    "codex.rollout.event_msg.token_count.info."
    "last_token_usage.input_tokens"
)
RE_THREAD_ID = re.compile(r"^[A-Za-z0-9-]{20,80}$")
RAZAO_NUNCA_MEDIU = "nunca_mediu"
RAZAO_MEDICAO_ENVELHECIDA = "medicao_envelhecida"
RAZAO_HISTORICO_INDISPONIVEL = "historico_medicao_indisponivel"


def agora_iso() -> str:
    """Instante local auditável, com fuso e sem depender do consumidor."""
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def _inteiro(valor: Any) -> bool:
    """Booleano não é token, embora ``bool`` herde de ``int`` em Python."""
    return isinstance(valor, int) and not isinstance(valor, bool)


def _positivo(valor: Any) -> bool:
    return _inteiro(valor) and valor > 0


def destino_padrao() -> Path:
    """Replica o caminho fixo que o adaptador do app consome."""
    declarado = os.environ.get("IACHAT_GROUPCHAT")
    if declarado:
        return Path(declarado).expanduser()
    sala = Path(os.environ.get("IACHAT_HOME", "~/ia-chat-global")).expanduser()
    return sala / "groupchat.jsonl"


def raiz_sessoes_padrao() -> Path:
    """Raiz real do Codex, desviável apenas para prova isolada."""
    declarada = os.environ.get("IACHAT_CODEX_SESSIONS_ROOT")
    if declarada:
        return Path(declarada).expanduser()
    return Path.home() / ".codex" / "sessions"


def registro_unknown(
    ia_id: str,
    reason: str,
    session_id: str = "",
    model_id: str = "",
    source: Optional[str] = None,
    sampled_at: Optional[str] = None,
    last_prompt_tokens: Optional[int] = None,
    context_window_tokens: Optional[int] = None,
) -> Dict[str, Any]:
    """Constrói o terceiro estado sem transformar ausência em zero."""
    instante = agora_iso()
    return {
        "ia_id": ia_id,
        "session_id": session_id,
        "model_id": model_id,
        "context": {
            "state": "unknown",
            "last_prompt_tokens": last_prompt_tokens,
            "estimated_prompt_tokens": None,
            "context_window_tokens": context_window_tokens,
            "source": source,
            "sampled_at": sampled_at or instante,
            "reason": reason,
        },
        "liveness": {
            "last_signal_at": instante,
            "session_state": "running",
        },
    }


def _registro_codex(
    session_id: str,
    model_id: str,
    prompt_tokens: Any,
    context_window: Any,
    sampled_at: Optional[str],
) -> Dict[str, Any]:
    """Normaliza um evento Codex já separado do acumulado da sessão."""
    if prompt_tokens == -1:
        return registro_unknown(
            "codex",
            "compacted_waiting_measurement",
            session_id=session_id,
            model_id=model_id,
            source=FONTE_CODEX,
            sampled_at=sampled_at,
            last_prompt_tokens=-1,
            context_window_tokens=context_window if _positivo(context_window) else None,
        )
    if not _positivo(prompt_tokens):
        return registro_unknown(
            "codex",
            "codex_prompt_tokens_unavailable",
            session_id=session_id,
            model_id=model_id,
            source=FONTE_CODEX,
            sampled_at=sampled_at,
            context_window_tokens=context_window if _positivo(context_window) else None,
        )
    if not _positivo(context_window):
        return registro_unknown(
            "codex",
            "context_window_unavailable",
            session_id=session_id,
            model_id=model_id,
            source=FONTE_CODEX,
            sampled_at=sampled_at,
        )
    if not model_id:
        return registro_unknown(
            "codex",
            "model_id_unavailable",
            session_id=session_id,
            source=FONTE_CODEX,
            sampled_at=sampled_at,
            context_window_tokens=context_window,
        )

    instante = agora_iso()
    return {
        "ia_id": "codex",
        "session_id": session_id,
        "model_id": model_id,
        "context": {
            "state": "exact",
            "last_prompt_tokens": prompt_tokens,
            "estimated_prompt_tokens": None,
            "context_window_tokens": context_window,
            "source": FONTE_CODEX,
            "sampled_at": sampled_at or instante,
            "reason": None,
        },
        "liveness": {
            "last_signal_at": instante,
            "session_state": "running",
        },
    }


def le_rollout_codex(
    caminho: Path,
    session_id_esperada: str = "",
) -> Dict[str, Any]:
    """Lê o rollout em ordem e devolve somente a última medida confiável.

    ``total_token_usage`` não aparece neste caminho de dados de propósito: ele
    é throughput acumulado. Uma linha ilegível invalida a leitura inteira, pois
    manter um número anterior depois de falhar o parse seria erro silencioso.
    """
    session_id = session_id_esperada
    model_id = ""
    ultima: Optional[Dict[str, Any]] = None
    try:
        linhas: Iterable[str] = caminho.read_text(encoding="utf-8").splitlines()
    except OSError:
        return registro_unknown(
            "codex",
            "codex_rollout_unreadable",
            session_id=session_id,
            source=FONTE_CODEX,
        )

    for linha in linhas:
        if not linha.strip():
            continue
        try:
            item = json.loads(linha)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return registro_unknown(
                "codex",
                "codex_rollout_parse_error",
                session_id=session_id,
                model_id=model_id,
                source=FONTE_CODEX,
            )
        if not isinstance(item, dict):
            return registro_unknown(
                "codex",
                "codex_rollout_parse_error",
                session_id=session_id,
                model_id=model_id,
                source=FONTE_CODEX,
            )

        payload = item.get("payload")
        if not isinstance(payload, dict):
            continue
        if item.get("type") == "session_meta":
            ident = payload.get("id")
            if isinstance(ident, str) and ident:
                session_id = ident
            continue
        if item.get("type") == "turn_context":
            modelo = payload.get("model")
            if isinstance(modelo, str) and modelo:
                model_id = modelo
            continue
        if item.get("type") != "event_msg" or payload.get("type") != "token_count":
            continue

        info = payload.get("info")
        if not isinstance(info, dict):
            ultima = registro_unknown(
                "codex",
                "codex_prompt_tokens_unavailable",
                session_id=session_id,
                model_id=model_id,
                source=FONTE_CODEX,
                sampled_at=item.get("timestamp") if isinstance(item.get("timestamp"), str) else None,
            )
            continue
        uso_ultimo = info.get("last_token_usage")
        prompt_tokens = (
            uso_ultimo.get("input_tokens")
            if isinstance(uso_ultimo, dict)
            else None
        )
        ultima = _registro_codex(
            session_id=session_id,
            model_id=model_id,
            prompt_tokens=prompt_tokens,
            context_window=info.get("model_context_window"),
            sampled_at=item.get("timestamp") if isinstance(item.get("timestamp"), str) else None,
        )

    if ultima is None:
        return registro_unknown(
            "codex",
            "codex_prompt_tokens_unavailable",
            session_id=session_id,
            model_id=model_id,
            source=FONTE_CODEX,
        )
    return ultima


def localiza_rollout_codex(
    thread_id: str,
    raiz_sessoes: Optional[Path] = None,
) -> Optional[Path]:
    """Localiza a sessão pelo ID injetado pelo próprio Codex, não por horário."""
    if not thread_id or not RE_THREAD_ID.fullmatch(thread_id):
        return None
    raiz = raiz_sessoes or raiz_sessoes_padrao()
    try:
        candidatos = [
            p for p in raiz.rglob("*-%s.jsonl" % thread_id) if p.is_file()
        ]
    except OSError:
        return None
    if not candidatos:
        return None
    try:
        return max(candidatos, key=lambda p: p.stat().st_mtime_ns)
    except OSError:
        return None


def mede_codex(
    arquivo: Optional[Path] = None,
    thread_id: str = "",
    raiz_sessoes: Optional[Path] = None,
) -> Dict[str, Any]:
    """Mede a sessão Codex explícita ou a sessão atual descoberta pelo ID."""
    ident = thread_id or os.environ.get("CODEX_THREAD_ID", "")
    caminho = arquivo or localiza_rollout_codex(ident, raiz_sessoes)
    if caminho is None:
        return registro_unknown(
            "codex",
            "codex_rollout_not_found" if ident else "codex_thread_id_unavailable",
            session_id=ident,
            source=FONTE_CODEX,
        )
    return le_rollout_codex(caminho, session_id_esperada=ident)


def grava_snapshot(caminho: Path, registro: Dict[str, Any]) -> None:
    """Faz append de uma linha inteira sob lock; concorrência não mistura JSON."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    linha = json.dumps(registro, ensure_ascii=False, separators=(",", ":")) + "\n"
    with caminho.open("a", encoding="utf-8") as arquivo:
        fcntl.flock(arquivo.fileno(), fcntl.LOCK_EX)
        try:
            arquivo.write(linha)
            arquivo.flush()
            os.fsync(arquivo.fileno())
        finally:
            fcntl.flock(arquivo.fileno(), fcntl.LOCK_UN)


def registro_despacho(
    ia_id: str,
    session_state: str,
    reason: str,
) -> Dict[str, Any]:
    """Cria um sinal de vida sem fingir que o despacho mediu contexto."""
    registro = registro_unknown(ia_id.strip().lower(), reason)
    registro["liveness"]["session_state"] = session_state
    return registro


def emite_despacho(
    ia_id: str,
    session_state: str,
    reason: str,
    caminho: Optional[Path] = None,
) -> Dict[str, Any]:
    """Persiste um evento de ciclo de vida usando o append travado canônico."""
    registro = registro_despacho(ia_id, session_state, reason)
    grava_snapshot(caminho or destino_padrao(), registro)
    return registro


def historico_tem_medicao_exata(caminho: Path, ia_id: str) -> Optional[bool]:
    """Distingue ausência real de histórico ilegível, sob lock compartilhado."""
    try:
        with caminho.open("r", encoding="utf-8") as arquivo:
            fcntl.flock(arquivo.fileno(), fcntl.LOCK_SH)
            try:
                linhas = arquivo.readlines()
            finally:
                fcntl.flock(arquivo.fileno(), fcntl.LOCK_UN)
    except FileNotFoundError:
        return False
    except OSError:
        return None

    ia = ia_id.strip().lower()
    encontrou = False
    for linha in linhas:
        if not linha.strip():
            continue
        try:
            registro = json.loads(linha)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None
        if not isinstance(registro, dict):
            return None
        if str(registro.get("ia_id", "")).strip().lower() != ia:
            continue
        contexto = registro.get("context")
        if isinstance(contexto, dict) and contexto.get("state") == "exact":
            encontrou = True
    return encontrou


def razao_sem_medicao(caminho: Path, ia_id: str) -> str:
    """Rotula dado nunca medido sem confundi-lo com medida anterior vencida."""
    historico = historico_tem_medicao_exata(caminho, ia_id)
    if historico is True:
        return RAZAO_MEDICAO_ENVELHECIDA
    if historico is False:
        return RAZAO_NUNCA_MEDIU
    return RAZAO_HISTORICO_INDISPONIVEL


def finaliza_despacho(
    ia_id: str,
    caminho: Optional[Path] = None,
    arquivo_codex: Optional[Path] = None,
    thread_id: str = "",
    raiz_sessoes: Optional[Path] = None,
) -> Dict[str, Any]:
    """Fecha o braço e mede Codex somente quando existe rollout auditável."""
    ia = ia_id.strip().lower()
    destino = caminho or destino_padrao()
    if ia == "codex":
        arquivo_env = os.environ.get("IACHAT_CODEX_ROLLOUT", "").strip()
        arquivo = arquivo_codex or (Path(arquivo_env).expanduser() if arquivo_env else None)
        registro = mede_codex(
            arquivo=arquivo,
            thread_id=thread_id,
            raiz_sessoes=raiz_sessoes,
        )
    else:
        registro = registro_unknown(
            ia,
            "provider_prompt_tokens_unavailable",
            source="%s.provider_usage.layout_unverified" % ia,
        )
    contexto = registro.get("context")
    if isinstance(contexto, dict) and contexto.get("state") != "exact":
        contexto["measurement_reason"] = contexto.get("reason")
        contexto["reason"] = razao_sem_medicao(destino, ia)
    registro["liveness"]["session_state"] = "exited"
    grava_snapshot(destino, registro)
    return registro


def emite_para_ia(ia_id: str, caminho: Optional[Path] = None) -> Dict[str, Any]:
    """Mede o braço conhecido; os demais entram como unknown justificado."""
    ia = ia_id.strip().lower()
    if ia == "codex":
        registro = mede_codex()
    else:
        registro = registro_unknown(
            ia,
            "provider_prompt_tokens_unavailable",
            source="%s.provider_usage.layout_unverified" % ia,
        )
    grava_snapshot(caminho or destino_padrao(), registro)
    return registro


def executar(argumentos: Any) -> int:
    """Ponte usada pelo subcomando de ``bin/iachat``."""
    if argumentos.provider == "codex":
        registro = mede_codex(
            arquivo=argumentos.arquivo,
            thread_id=argumentos.thread_id or "",
            raiz_sessoes=argumentos.raiz_sessoes,
        )
    else:
        registro = registro_unknown(
            argumentos.ia,
            argumentos.reason,
            session_id=argumentos.session_id or "",
            model_id=argumentos.model_id or "",
            source=argumentos.source,
        )

    destino = argumentos.saida or destino_padrao()
    grava_snapshot(destino, registro)
    print(json.dumps(registro, ensure_ascii=False, separators=(",", ":")))
    return 0


def executar_direto(argv: Optional[Iterable[str]] = None) -> int:
    """CLI estreita para o shell de despacho, sem duplicar escrita/lock em Bash."""
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="comando", required=True)
    despacho = sub.add_parser("despacho", help="emitir ciclo de vida de um braço")
    despacho.add_argument("--ia", required=True)
    despacho.add_argument(
        "--session-state", required=True, choices=("running", "exited")
    )
    despacho.add_argument("--reason", required=True)
    despacho.add_argument("--saida", type=Path)
    encerramento = sub.add_parser(
        "encerramento", help="fechar o braço e medir Codex quando possível"
    )
    encerramento.add_argument("--ia", required=True)
    encerramento.add_argument("--saida", type=Path)
    encerramento.add_argument("--arquivo-codex", type=Path)
    encerramento.add_argument("--thread-id", default="")
    encerramento.add_argument("--raiz-sessoes", type=Path)
    argumentos = parser.parse_args(list(argv) if argv is not None else None)

    if argumentos.comando == "despacho":
        registro = emite_despacho(
            argumentos.ia,
            argumentos.session_state,
            argumentos.reason,
            caminho=argumentos.saida,
        )
        print(json.dumps(registro, ensure_ascii=False, separators=(",", ":")))
        return 0
    if argumentos.comando == "encerramento":
        registro = finaliza_despacho(
            argumentos.ia,
            caminho=argumentos.saida,
            arquivo_codex=argumentos.arquivo_codex,
            thread_id=argumentos.thread_id,
            raiz_sessoes=argumentos.raiz_sessoes,
        )
        print(json.dumps(registro, ensure_ascii=False, separators=(",", ":")))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(executar_direto(sys.argv[1:]))
