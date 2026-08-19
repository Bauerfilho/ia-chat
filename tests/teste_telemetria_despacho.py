#!/usr/bin/env python3
"""Gate do ciclo de vida emitido pelo despacho em sidecar descartável.

O teste usa providers forjados e ``IACHAT_HOME`` temporário. Nenhuma sala viva,
nenhum servidor e nenhum braço real participa da prova.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional


RAIZ = Path(__file__).resolve().parent.parent
DESPACHO = RAIZ / "bin" / "iachat-despacho.sh"

OK = 0
FALHOU = 0


def checa(nome: str, condicao: bool, detalhe: str = "") -> None:
    global OK, FALHOU
    if condicao:
        OK += 1
        print(f"  ✔ {nome}")
    else:
        FALHOU += 1
        print(f"  ✗ {nome}" + (f" — {detalhe}" if detalhe else ""))


def registros(caminho: Path) -> List[Dict[str, Any]]:
    if not caminho.is_file():
        return []
    saida: List[Dict[str, Any]] = []
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        if linha.strip():
            saida.append(json.loads(linha))
    return saida


def cria_provider(caminho: Path) -> None:
    caminho.write_text(
        "#!/bin/sh\nprintf 'plano forjado\\n' > \"$MOCK_PLANO\"\n",
        encoding="utf-8",
    )
    caminho.chmod(0o755)


def roda_despacho(
    braco: str,
    tmp: Path,
    sidecar: Path,
    extras: Optional[Dict[str, str]] = None,
) -> subprocess.CompletedProcess[str]:
    prompt = tmp / f"prompt-{braco}.txt"
    plano = tmp / f"plano-{braco}.md"
    log = tmp / f"worker-{braco}.log"
    prompt.write_text("produza o plano pedido", encoding="utf-8")
    ambiente = {
        **os.environ,
        "PATH": f"{tmp / 'mock-bin'}:{os.environ.get('PATH', '')}",
        "IACHAT_HOME": str(tmp / "sala-descartavel"),
        "IACHAT_GROUPCHAT": str(sidecar),
        "MOCK_PLANO": str(plano),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    ambiente.update(extras or {})
    return subprocess.run(
        [str(DESPACHO), braco, f"tdesp-{braco}", str(prompt), str(log), str(plano)],
        env=ambiente,
        capture_output=True,
        text=True,
        timeout=30,
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="iachat-despacho-telemetria-") as bruto:
        tmp = Path(bruto)
        mocks = tmp / "mock-bin"
        mocks.mkdir()
        cria_provider(mocks / "qwen")
        cria_provider(mocks / "codex")

        print("— braço sem medição deixa ciclo de vida completo —")
        sidecar_qwen = tmp / "qwen" / "groupchat.jsonl"
        qwen = roda_despacho("qwen", tmp, sidecar_qwen)
        linhas_qwen = registros(sidecar_qwen)
        checa(
            "despacho forjado conclui",
            qwen.returncode == 0,
            f"rc={qwen.returncode} stderr={qwen.stderr[:200]!r}",
        )
        checa(
            "sidecar recebe exatamente running e exited",
            len(linhas_qwen) == 2
            and [r.get("liveness", {}).get("session_state") for r in linhas_qwen]
            == ["running", "exited"],
            repr(linhas_qwen),
        )
        inicio_qwen = linhas_qwen[0] if linhas_qwen else {}
        fim_qwen = linhas_qwen[-1] if linhas_qwen else {}
        checa(
            "running declara despachada_sem_medicao",
            inicio_qwen.get("ia_id") == "qwen"
            and inicio_qwen.get("context", {}).get("state") == "unknown"
            and inicio_qwen.get("context", {}).get("reason")
            == "despachada_sem_medicao",
            repr(inicio_qwen),
        )
        checa(
            "provider sem fonte termina unknown, nunca zero",
            fim_qwen.get("context", {}).get("state") == "unknown"
            and fim_qwen.get("context", {}).get("last_prompt_tokens") is None
            and fim_qwen.get("context", {}).get("reason") == "nunca_mediu",
            repr(fim_qwen),
        )

        print("— dado separa nunca medido de medição anterior envelhecida —")
        sidecar_antigo = tmp / "antigo" / "groupchat.jsonl"
        sidecar_antigo.parent.mkdir(parents=True)
        sidecar_antigo.write_text(
            json.dumps(
                {
                    "ia_id": "qwen",
                    "session_id": "sessao-anterior",
                    "model_id": "qwen-anterior",
                    "context": {
                        "state": "exact",
                        "last_prompt_tokens": 7000,
                        "estimated_prompt_tokens": None,
                        "context_window_tokens": 32000,
                        "source": "fixture.medicao.exata",
                        "sampled_at": "2026-08-17T10:00:00-03:00",
                        "reason": None,
                    },
                    "liveness": {
                        "last_signal_at": "2026-08-17T10:00:00-03:00",
                        "session_state": "exited",
                    },
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        qwen_antigo = roda_despacho("qwen", tmp, sidecar_antigo)
        linhas_antigas = registros(sidecar_antigo)
        fim_antigo = linhas_antigas[-1] if linhas_antigas else {}
        checa(
            "medição anterior sem medida fresca vira medicao_envelhecida",
            qwen_antigo.returncode == 0
            and len(linhas_antigas) == 3
            and fim_antigo.get("context", {}).get("state") == "unknown"
            and fim_antigo.get("context", {}).get("reason")
            == "medicao_envelhecida",
            repr(fim_antigo),
        )

        print("— Codex reaproveita a leitura auditável do rollout —")
        thread_id = "01a01687-d9d0-7400-93be-bb53163f3303"
        raiz_sessoes = tmp / "sessions"
        rollout = raiz_sessoes / "2026" / "08" / "18" / f"rollout-teste-{thread_id}.jsonl"
        rollout.parent.mkdir(parents=True)
        eventos = [
            {"type": "session_meta", "payload": {"id": thread_id}},
            {"type": "turn_context", "payload": {"model": "gpt-teste"}},
            {
                "timestamp": "2026-08-18T22:00:00Z",
                "type": "event_msg",
                "payload": {
                    "type": "token_count",
                    "info": {
                        "last_token_usage": {"input_tokens": 42000},
                        "model_context_window": 1000000,
                    },
                },
            },
        ]
        rollout.write_text(
            "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in eventos),
            encoding="utf-8",
        )
        sidecar_codex = tmp / "codex" / "groupchat.jsonl"
        codex = roda_despacho(
            "codex",
            tmp,
            sidecar_codex,
            {
                "CODEX_THREAD_ID": thread_id,
                "IACHAT_CODEX_SESSIONS_ROOT": str(raiz_sessoes),
            },
        )
        linhas_codex = registros(sidecar_codex)
        fim_codex = linhas_codex[-1] if linhas_codex else {}
        checa(
            "braço Codex forjado conclui e fecha o ciclo",
            codex.returncode == 0
            and len(linhas_codex) == 2
            and fim_codex.get("liveness", {}).get("session_state") == "exited",
            repr({"rc": codex.returncode, "stderr": codex.stderr, "linhas": linhas_codex}),
        )
        checa(
            "encerramento Codex emite exact do último prompt",
            fim_codex.get("context", {}).get("state") == "exact"
            and fim_codex.get("context", {}).get("last_prompt_tokens") == 42000
            and fim_codex.get("context", {}).get("context_window_tokens") == 1000000
            and fim_codex.get("session_id") == thread_id,
            repr(fim_codex),
        )

        sidecar_codex_arquivo = tmp / "codex-arquivo" / "groupchat.jsonl"
        codex_arquivo = roda_despacho(
            "codex",
            tmp,
            sidecar_codex_arquivo,
            {
                "CODEX_THREAD_ID": "",
                "IACHAT_CODEX_ROLLOUT": str(rollout),
                "IACHAT_CODEX_SESSIONS_ROOT": str(tmp / "raiz-inexistente"),
            },
        )
        linhas_codex_arquivo = registros(sidecar_codex_arquivo)
        fim_codex_arquivo = linhas_codex_arquivo[-1] if linhas_codex_arquivo else {}
        checa(
            "arquivo de rollout explícito também encerra exact",
            codex_arquivo.returncode == 0
            and len(linhas_codex_arquivo) == 2
            and fim_codex_arquivo.get("context", {}).get("state") == "exact"
            and fim_codex_arquivo.get("context", {}).get("last_prompt_tokens") == 42000
            and fim_codex_arquivo.get("liveness", {}).get("session_state") == "exited",
            repr(fim_codex_arquivo),
        )

    print(f"\n{OK} ✔ / {FALHOU} ✗")
    return 1 if FALHOU else 0


if __name__ == "__main__":
    raise SystemExit(main())
