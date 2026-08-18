#!/usr/bin/env python3
"""Gates do ia-claim: concorrência real, expiração e contrato cooperativo.

Roda a CLI em subprocessos e usa ``IACHAT_HOME`` temporário; nunca toca a sala
real. O gate central lança duas reservas do mesmo caminho em processos distintos:
exatamente uma deve vencer.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path


CLI = Path(__file__).resolve().parent.parent / "bin" / "iachat-claim"
falhas: list[str] = []


def checa(nome: str, condicao: bool, detalhe: str = "") -> None:
    print(f"{'✔' if condicao else '✗'} {nome}" + (f"  → {detalhe}" if detalhe else ""))
    if not condicao:
        falhas.append(nome)


def roda(env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    """Executa o caminho público real, sem importar funções internas do claim."""
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        env=env,
        capture_output=True,
        text=True,
    )


def disputa(
    env: dict[str, str],
    barreira: threading.Barrier,
    ia: str,
    caminho: str,
) -> tuple[str, int, str]:
    """Sincroniza o disparo; cada chamada abaixo nasce em processo próprio."""
    barreira.wait(timeout=10)
    resposta = roda(
        env,
        "take",
        caminho,
        "--de",
        ia,
        "--para-que",
        f"disputa simultânea de {ia}",
        "--min",
        "30",
    )
    return ia, resposta.returncode, (resposta.stdout + resposta.stderr).strip()


def registro_do(base: Path, caminho: Path) -> tuple[Path, dict] | None:
    alvo = str(caminho.resolve())
    for arquivo in (base / "claims").glob("*.json"):
        registro = json.loads(arquivo.read_text(encoding="utf-8"))
        if registro.get("caminho") == alvo:
            return arquivo, registro
    return None


def expira(arquivo: Path, registro: dict) -> None:
    registro["ate"] = (
        datetime.now().astimezone() - timedelta(seconds=2)
    ).isoformat(timespec="seconds")
    arquivo.write_text(
        json.dumps(registro, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    base = Path(tempfile.mkdtemp(prefix="iachat-claim-teste-"))
    env = {
        **os.environ,
        "IACHAT_HOME": str(base),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    alvo = base / "compartilhado" / "hooks.json"
    alvo.parent.mkdir(parents=True)
    alvo.write_text('{"hooks": []}\n', encoding="utf-8")

    try:
        checa("CLI nova é executável", CLI.is_file() and os.access(CLI, os.X_OK), str(CLI))

        # ---- C1: dois processos, mesmo caminho, disparados juntos -------------
        barreira = threading.Barrier(2)
        with ThreadPoolExecutor(max_workers=2) as executor:
            futuros = [
                executor.submit(disputa, env, barreira, ia, str(alvo))
                for ia in ("claude", "codex")
            ]
            resultados = [f.result(timeout=20) for f in futuros]

        vencedores = [ia for ia, rc, _ in resultados if rc == 0]
        perdedores = [ia for ia, rc, _ in resultados if rc == 1]
        checa(
            "C1 duas reservas simultâneas: exatamente uma vence",
            len(vencedores) == 1 and len(perdedores) == 1,
            f"resultados={[(ia, rc) for ia, rc, _ in resultados]}",
        )

        encontrado = registro_do(base, alvo)
        checa(
            "C1 existe um único registro íntegro para o caminho",
            encontrado is not None
            and len(list((base / "claims").glob("*.json"))) == 1
            and encontrado[1].get("de") == (vencedores[0] if vencedores else None),
            f"claims={len(list((base / 'claims').glob('*.json')))}",
        )

        vencedor = vencedores[0] if vencedores else "claude"
        perdedor = perdedores[0] if perdedores else "codex"
        check_dono = roda(env, "check", str(alvo), "--de", vencedor)
        check_outro = roda(env, "check", str(alvo), "--de", perdedor)
        checa(
            "C1 check distingue dono de terceiro",
            check_dono.returncode == 0 and check_outro.returncode == 1,
            f"dono={check_dono.returncode} terceiro={check_outro.returncode}",
        )

        # A reserva é estado: adquirir não deve postar uma mensagem na conversa.
        chat = (base / "iachat.md").read_text(encoding="utf-8")
        checa(
            "C2 estado mora fora do iachat.md",
            str(alvo.resolve()) not in chat and len(list((base / "claims").glob("*.json"))) == 1,
            f"chat={len(chat.encode())} B",
        )

        free_outro = roda(env, "free", str(alvo), "--de", perdedor)
        free_dono = roda(env, "free", str(alvo), "--de", vencedor)
        checa(
            "C3 só o dono libera explicitamente",
            free_outro.returncode == 1 and free_dono.returncode == 0,
            f"terceiro={free_outro.returncode} dono={free_dono.returncode}",
        )

        # ---- C4: reserva vencida fica livre e outra IA a retoma ---------------
        primeira = roda(
            env,
            "take",
            str(alvo),
            "--de",
            "claude",
            "--para-que",
            "primeira posse",
            "--min",
            "30",
        )
        encontrado = registro_do(base, alvo)
        if encontrado is not None:
            expira(*encontrado)
        check_vencida = roda(env, "check", str(alvo), "--de", "codex")
        retomada = roda(
            env,
            "take",
            str(alvo),
            "--de",
            "codex",
            "--para-que",
            "retomada após vencimento",
            "--min",
            "20",
        )
        depois = registro_do(base, alvo)
        checa(
            "C4 reserva vencida é retomada por outra IA",
            primeira.returncode == 0
            and check_vencida.returncode == 0
            and retomada.returncode == 0
            and depois is not None
            and depois[1].get("de") == "codex",
            f"take1={primeira.returncode} check={check_vencida.returncode} take2={retomada.returncode}",
        )

        # ---- C5: renovação é explícita e parte do presente --------------------
        renovada = roda(env, "renew", str(alvo), "--de", "codex", "--min", "10")
        atual = registro_do(base, alvo)
        segundos = -1.0
        if atual is not None:
            segundos = (
                datetime.fromisoformat(atual[1]["ate"]) - datetime.now().astimezone()
            ).total_seconds()
        checa(
            "C5 renew estende a partir de agora",
            renovada.returncode == 0
            and atual is not None
            and atual[1].get("renovacoes") == 1
            and 590 <= segundos <= 605,
            f"rc={renovada.returncode} restante={segundos:.1f}s",
        )

        # Reserva vencida não pode ser ressuscitada sem nova disputa.
        if atual is not None:
            expira(*atual)
        ressuscitar = roda(env, "renew", str(alvo), "--de", "codex", "--min", "10")
        novo_take = roda(
            env,
            "take",
            str(alvo),
            "--de",
            "kimi",
            "--para-que",
            "nova disputa após expirar",
        )
        checa(
            "C5 reserva vencida exige novo take",
            ressuscitar.returncode == 1 and novo_take.returncode == 0,
            f"renew={ressuscitar.returncode} take={novo_take.returncode}",
        )

        # ---- C6: diretório cobre descendente, não vizinho textual -------------
        roda(env, "free", str(alvo), "--de", "kimi")
        territorio = base / "skills"
        descendente = territorio / "ia-bell" / "SKILL.md"
        vizinho = base / "skills-vizinha" / "SKILL.md"
        descendente.parent.mkdir(parents=True)
        vizinho.parent.mkdir(parents=True)
        pai = roda(
            env,
            "take",
            str(territorio),
            "--de",
            "claude",
            "--para-que",
            "editar skills compartilhadas",
        )
        filho = roda(
            env,
            "take",
            str(descendente),
            "--de",
            "codex",
            "--para-que",
            "editar skill filha",
        )
        ao_lado = roda(
            env,
            "take",
            str(vizinho),
            "--de",
            "codex",
            "--para-que",
            "editar caminho vizinho",
        )
        checa(
            "C6 contenção usa componentes de caminho",
            pai.returncode == 0 and filho.returncode == 1 and ao_lado.returncode == 0,
            f"pai={pai.returncode} filho={filho.returncode} vizinho={ao_lado.returncode}",
        )

        # Todo registro persistido carrega vencimento parseável e finito.
        registros = [
            json.loads(p.read_text(encoding="utf-8"))
            for p in (base / "claims").glob("*.json")
        ]
        checa(
            "C7 toda reserva persistida expira",
            bool(registros)
            and all(
                "ate" in registro
                and datetime.fromisoformat(registro["ate"])
                < datetime.now().astimezone() + timedelta(minutes=241)
                for registro in registros
            ),
            f"registros={len(registros)}",
        )

        print()
        print("✅ IA-CLAIM PASSOU" if not falhas else f"❌ IA-CLAIM REPROVOU: {falhas}")
        return 0 if not falhas else 1
    finally:
        shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
