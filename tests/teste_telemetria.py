#!/usr/bin/env python3
"""Gate do produtor de telemetria: exato só quando a fonte permite.

Os casos ruins são parte do produto. O teste põe um acumulado enorme ao lado
da medida atual, simula compactação e corrompe o JSONL. Qualquer fallback
"criativo" transforma a bateria em vermelho.
"""
from __future__ import annotations

import json
import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List


RAIZ = Path(__file__).resolve().parent.parent
BIN = RAIZ / "bin"
CLI = BIN / "iachat"
sys.path.insert(0, str(BIN))

SPEC = importlib.util.spec_from_file_location(
    "iachat_telemetria_teste", BIN / "iachat-telemetria.py"
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("não carreguei bin/iachat-telemetria.py")
telemetria = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(telemetria)


OK = 0
FALHOU = 0


def checa(nome: str, condicao: bool, detalhe: str = "") -> None:
    global OK, FALHOU
    if condicao:
        OK += 1
        print("  ✔ %s" % nome)
    else:
        FALHOU += 1
        sufixo = " — %s" % detalhe if detalhe else ""
        print("  ✗ %s%s" % (nome, sufixo))


def meta(session_id: str = "cx_teste") -> Dict[str, Any]:
    return {
        "timestamp": "2026-08-18T18:00:00Z",
        "type": "session_meta",
        "payload": {"id": session_id, "source": "exec"},
    }


def turno(modelo: str) -> Dict[str, Any]:
    return {
        "timestamp": "2026-08-18T18:00:01Z",
        "type": "turn_context",
        "payload": {"model": modelo},
    }


def contagem(
    prompt: Any = 168000,
    acumulado: int = 987654321,
    janela: Any = 250000,
    incluir_ultimo: bool = True,
) -> Dict[str, Any]:
    info: Dict[str, Any] = {
        "total_token_usage": {"input_tokens": acumulado},
        "model_context_window": janela,
    }
    if incluir_ultimo:
        info["last_token_usage"] = {"input_tokens": prompt}
    return {
        "timestamp": "2026-08-18T18:00:02Z",
        "type": "event_msg",
        "payload": {"type": "token_count", "info": info},
    }


def grava(caminho: Path, eventos: List[Dict[str, Any]]) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(
        "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in eventos),
        encoding="utf-8",
    )


def contexto(registro: Dict[str, Any]) -> Dict[str, Any]:
    valor = registro.get("context")
    return valor if isinstance(valor, dict) else {}


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="iachat-telemetria-") as bruto:
        tmp = Path(bruto)

        print("— medida exata separada do throughput —")
        exato_arq = tmp / "exato.jsonl"
        grava(exato_arq, [meta(), turno("gpt-5.6-sol"), contagem()])
        exato = telemetria.le_rollout_codex(exato_arq)
        c_exato = contexto(exato)
        checa(
            "usa a última entrada, não o acumulado gigante",
            c_exato.get("state") == "exact"
            and c_exato.get("last_prompt_tokens") == 168000
            and c_exato.get("last_prompt_tokens") != 987654321,
            repr(c_exato),
        )
        checa(
            "modelo e denominador pertencem à mesma medição",
            exato.get("model_id") == "gpt-5.6-sol"
            and c_exato.get("context_window_tokens") == 250000,
            repr(exato),
        )
        checa(
            "a fonte declara o campo auditável",
            c_exato.get("source") == telemetria.FONTE_CODEX,
            repr(c_exato),
        )

        print("— -1 é medindo, nunca zero —")
        compacto_arq = tmp / "compacto.jsonl"
        grava(compacto_arq, [meta(), turno("gpt-5.6-sol"), contagem(prompt=-1)])
        compacto = contexto(telemetria.le_rollout_codex(compacto_arq))
        checa(
            "-1 força unknown/compacted_waiting_measurement",
            compacto.get("state") == "unknown"
            and compacto.get("reason") == "compacted_waiting_measurement"
            and compacto.get("last_prompt_tokens") == -1,
            repr(compacto),
        )
        checa(
            "-1 não vira estimativa nem zero",
            compacto.get("estimated_prompt_tokens") is None
            and compacto.get("last_prompt_tokens") != 0,
            repr(compacto),
        )

        print("— acumulado e parse ruim falham fechados —")
        acumulado_arq = tmp / "somente-acumulado.jsonl"
        grava(
            acumulado_arq,
            [meta(), turno("gpt-5.6-sol"), contagem(incluir_ultimo=False)],
        )
        acumulado = contexto(telemetria.le_rollout_codex(acumulado_arq))
        checa(
            "token acumulado sozinho não vira ocupação",
            acumulado.get("state") == "unknown"
            and acumulado.get("last_prompt_tokens") is None
            and acumulado.get("reason") == "codex_prompt_tokens_unavailable",
            repr(acumulado),
        )

        parse_arq = tmp / "parse-quebrado.jsonl"
        grava(parse_arq, [meta(), turno("gpt-5.6-sol"), contagem()])
        with parse_arq.open("a", encoding="utf-8") as arquivo:
            arquivo.write("{json-interrompido\n")
        parse = contexto(telemetria.le_rollout_codex(parse_arq))
        checa(
            "falha de parse invalida o número anterior",
            parse.get("state") == "unknown"
            and parse.get("last_prompt_tokens") is None
            and parse.get("reason") == "codex_rollout_parse_error",
            repr(parse),
        )

        zero_arq = tmp / "zero.jsonl"
        grava(zero_arq, [meta(), turno("gpt-5.6-sol"), contagem(prompt=0)])
        zero = contexto(telemetria.le_rollout_codex(zero_arq))
        checa(
            "zero não se passa por exato",
            zero.get("state") == "unknown"
            and zero.get("last_prompt_tokens") is None,
            repr(zero),
        )

        print("— troca de modelo recalcula o denominador —")
        troca_arq = tmp / "troca.jsonl"
        grava(
            troca_arq,
            [
                meta(),
                turno("modelo-antigo"),
                contagem(prompt=200000, janela=250000),
                turno("modelo-novo"),
                contagem(prompt=236000, janela=1000000),
            ],
        )
        troca = telemetria.le_rollout_codex(troca_arq)
        c_troca = contexto(troca)
        checa(
            "a última medida leva modelo e janela novos",
            troca.get("model_id") == "modelo-novo"
            and c_troca.get("last_prompt_tokens") == 236000
            and c_troca.get("context_window_tokens") == 1000000,
            repr(troca),
        )

        sem_janela_arq = tmp / "sem-janela.jsonl"
        grava(
            sem_janela_arq,
            [meta(), turno("gpt-5.6-sol"), contagem(janela=None)],
        )
        sem_janela = contexto(telemetria.le_rollout_codex(sem_janela_arq))
        checa(
            "sem denominador permanece unknown",
            sem_janela.get("state") == "unknown"
            and sem_janela.get("reason") == "context_window_unavailable",
            repr(sem_janela),
        )

        print("— CLI escreve o sidecar consumível —")
        thread_id = "01a01687-d9d0-7400-93be-bb53163f3303"
        sessoes = tmp / "sessions" / "2026" / "08" / "18"
        rollout = sessoes / ("rollout-teste-%s.jsonl" % thread_id)
        grava(rollout, [meta(thread_id), turno("gpt-5.6-sol"), contagem()])
        sidecar = tmp / "sala" / "groupchat.jsonl"
        ambiente = dict(os.environ)
        ambiente.update({
            "CODEX_THREAD_ID": thread_id,
            "IACHAT_CODEX_SESSIONS_ROOT": str(tmp / "sessions"),
            "IACHAT_GROUPCHAT": str(sidecar),
            "PYTHONDONTWRITEBYTECODE": "1",
        })
        chamada = subprocess.run(
            [
                sys.executable,
                str(CLI),
                "telemetria",
                "--raiz-sessoes",
                str(tmp / "sessions"),
            ],
            env=ambiente,
            capture_output=True,
            text=True,
        )
        try:
            saida_cli = json.loads(chamada.stdout)
        except json.JSONDecodeError:
            saida_cli = {"erro": chamada.stdout, "stderr": chamada.stderr}
        linhas = sidecar.read_text(encoding="utf-8").splitlines() if sidecar.is_file() else []
        checa(
            "CLI descobre a sessão pelo ID e emite exact",
            chamada.returncode == 0
            and contexto(saida_cli).get("state") == "exact"
            and contexto(saida_cli).get("last_prompt_tokens") == 168000,
            repr(saida_cli),
        )
        checa(
            "sidecar recebe uma linha JSON inteira",
            len(linhas) == 1 and json.loads(linhas[0]).get("session_id") == thread_id,
            repr(linhas),
        )

        chamada_kimi = subprocess.run(
            [
                sys.executable,
                str(CLI),
                "telemetria",
                "--provider",
                "unknown",
                "--ia",
                "kimi",
                "--session-id",
                "km_teste",
                "--model-id",
                "kimi",
                "--reason",
                "provider_prompt_tokens_unavailable",
                "--source",
                "kimi.footer.layout_unverified",
            ],
            env=ambiente,
            capture_output=True,
            text=True,
        )
        linhas = sidecar.read_text(encoding="utf-8").splitlines()
        kimi = json.loads(linhas[-1])
        checa(
            "segundo braço explicita unknown sem numerador",
            chamada_kimi.returncode == 0
            and kimi.get("ia_id") == "kimi"
            and contexto(kimi).get("state") == "unknown"
            and contexto(kimi).get("last_prompt_tokens") is None
            and contexto(kimi).get("reason") == "provider_prompt_tokens_unavailable",
            repr(kimi),
        )

        print("— cada resposta pode atualizar a barra —")
        auto_sidecar = tmp / "auto" / "groupchat.jsonl"
        ambiente_auto = dict(ambiente)
        ambiente_auto.update({
            "IACHAT_HOME": str(tmp / "auto" / "sala"),
            "IACHAT_GROUPCHAT": str(auto_sidecar),
            "IACHAT_TELEMETRIA": "1",
        })
        post = subprocess.run(
            [
                sys.executable,
                str(CLI),
                "post",
                "--de",
                "codex",
                "--para",
                "all",
                "resposta com ocupação medida",
            ],
            env=ambiente_auto,
            capture_output=True,
            text=True,
        )
        auto_linhas = (
            auto_sidecar.read_text(encoding="utf-8").splitlines()
            if auto_sidecar.is_file()
            else []
        )
        auto_registro = json.loads(auto_linhas[-1]) if auto_linhas else {}
        checa(
            "post com telemetria ligada emite exact no mesmo ciclo",
            post.returncode == 0
            and len(auto_linhas) == 1
            and auto_registro.get("ia_id") == "codex"
            and contexto(auto_registro).get("state") == "exact"
            and contexto(auto_registro).get("last_prompt_tokens") == 168000,
            repr({"post": post.stdout, "stderr": post.stderr,
                  "registro": auto_registro}),
        )

    print("\n%d ✔ / %d ✗" % (OK, FALHOU))
    return 1 if FALHOU else 0


if __name__ == "__main__":
    raise SystemExit(main())
