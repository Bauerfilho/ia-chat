#!/usr/bin/env python3
"""Gates do iachat-squad sobre chat pré-existente e casos vermelhos.

O teste copia a fixture congelada para um ``IACHAT_HOME`` temporário. Ele usa
somente as CLIs públicas em subprocessos e cobre: aceite, recusa, ninguém pegou,
autojulgamento bloqueado, veredito direto sem recibo, histórico preservado e
entradas ruins que precisam REPROVAR.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


RAIZ = Path(__file__).resolve().parent.parent
SQUAD = RAIZ / "bin" / "iachat-squad"
IACHAT = RAIZ / "bin" / "iachat"
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "sala-v1"
META_RE = re.compile(r"^<!-- iachat msg=(\d+) ", re.MULTILINE)
falhas: list[str] = []


def checa(nome: str, condicao: bool, detalhe: str = "") -> None:
    print(f"{'✔' if condicao else '✗'} {nome}" + (f"  → {detalhe}" if detalhe else ""))
    if not condicao:
        falhas.append(nome)


def fotografa(pasta: Path) -> dict[str, bytes]:
    return {
        str(caminho.relative_to(pasta)): caminho.read_bytes()
        for caminho in sorted(pasta.rglob("*"))
        if caminho.is_file()
    }


def sha256(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def roda(
    executavel: Path,
    env: dict[str, str],
    *args: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(executavel), *args],
        env=env,
        capture_output=True,
        text=True,
    )


def cria_run(
    base: Path,
    nome: str,
    membros: list[tuple[str, str, int]],
) -> Path:
    run = base / nome
    (run / "contratos").mkdir(parents=True)
    (run / "missao.md").write_text(
        f"# Missão {nome}\n\nExecutar os pedaços independentes com prova.\n",
        encoding="utf-8",
    )
    linhas = []
    for worker, ia, etapas in membros:
        relativo = f"contratos/{worker}.md"
        (run / relativo).write_text(
            f"# {worker}\n\nExecute {etapas} etapas e escreva o resultado.\n",
            encoding="utf-8",
        )
        linhas.append(f"{worker}\t{ia}\t{etapas}\t{relativo}")
    (run / "squad.tsv").write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return run


def main() -> int:
    fixture_antes = fotografa(FIXTURE)
    base = Path(tempfile.mkdtemp(prefix="iachat-squad-teste-"))
    sala = base / "sala-preexistente"
    shutil.copytree(FIXTURE, sala)
    chat = sala / "iachat.md"
    chat_antes = chat.read_bytes()
    numeros_antes = [int(x) for x in META_RE.findall(chat_antes.decode("utf-8"))]

    # A quarta identidade despacha; as três IAs históricas ficam disponíveis como workers.
    config_path = sala / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["na_sala"] = ["claude", "codex", "kimi", "grok"]
    config["brain"] = "grok"
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    env = {
        **os.environ,
        "IACHAT_HOME": str(sala),
        "IACHAT_BIN": str(IACHAT),
        "PYTHONDONTWRITEBYTECODE": "1",
    }

    try:
        checa(
            "G0 CLI iachat-squad existe e é executável",
            SQUAD.is_file() and os.access(SQUAD, os.X_OK),
            str(SQUAD),
        )
        checa(
            "G0 fixture é chat pré-existente com 8 mensagens",
            numeros_antes == list(range(1, 9)),
            f"números={numeros_antes}",
        )

        # ---- G1: despacho real sobre histórico já existente -----------------
        run = cria_run(
            base,
            "run-principal",
            [("w-codex", "codex", 5), ("w-kimi", "kimi", 5), ("w-claude", "claude", 5)],
        )
        despacho = roda(SQUAD, env, "despachar", str(run), "--de", "grok", "--prazo", "23:40")
        registro = json.loads((run / "despacho.json").read_text(encoding="utf-8"))
        numeros_pos_despacho = [int(x) for x in META_RE.findall(chat.read_text(encoding="utf-8"))]
        checa(
            "G1 despacha um ponteiro para cada worker",
            despacho.returncode == 0
            and len(registro["workers"]) == 3
            and numeros_pos_despacho[-3:] == [9, 10, 11],
            f"rc={despacho.returncode} novos={numeros_pos_despacho[-3:]}",
        )
        checa(
            "G1 ponteiros usam o comando instalável e cabem no teto de entrega",
            all(item["bytes_ponteiro"] < 6144 for item in registro["workers"].values())
            and "iachat-squad responder" in chat.read_text(encoding="utf-8"),
            f"bytes={[item['bytes_ponteiro'] for item in registro['workers'].values()]}",
        )
        checa(
            "G1 chat antigo permanece prefixo byte-a-byte do chat novo",
            chat.read_bytes().startswith(chat_antes),
            f"antes={len(chat_antes)} B depois={chat.stat().st_size} B",
        )

        # Repetir é retomada, não novo disparo.
        hash_antes_repetir = sha256(chat)
        repetido = roda(SQUAD, env, "despachar", str(run), "--de", "grok")
        checa(
            "G1 despacho repetido é idempotente e não cresce a sala",
            repetido.returncode == 0
            and "não duplicado" in repetido.stdout
            and sha256(chat) == hash_antes_repetir,
            f"rc={repetido.returncode}",
        )

        # ---- G2: aceite, recusa e leitura sem resposta ----------------------
        aceito = roda(
            SQUAD, env, "responder", str(run), "--worker", "w-codex", "--de", "codex", "--aceitar"
        )
        recusado = roda(
            SQUAD,
            env,
            "responder",
            str(run),
            "--worker",
            "w-kimi",
            "--de",
            "kimi",
            "--recusar",
            "--motivo",
            "falta a referência obrigatória",
        )
        # A própria porta pública lê a mensagem de w-claude; depois outro sino nasce.
        leitura_claude = roda(IACHAT, env, "read", "--de", "claude")
        sino_posterior = roda(
            IACHAT, env, "post", "--de", "grok", "--para", "claude", "mensagem posterior alheia à squad"
        )
        hash_antes_chamada = sha256(chat)
        chamada = roda(SQUAD, env, "chamada", str(run))
        checa(
            "G2 despacho aceito aparece como ACEITOU",
            aceito.returncode == 0 and "ACEITOU" in chamada.stdout,
            f"responder={aceito.returncode} chamada={chamada.returncode}",
        )
        checa(
            "G2 despacho recusado aparece como RECUSOU com motivo",
            recusado.returncode == 0
            and "RECUSOU" in chamada.stdout
            and "falta a referência obrigatória" in chamada.stdout,
        )
        checa(
            "G2 cursor do despacho vence sino posterior: mostra LEU, não NÃO-VIU",
            leitura_claude.returncode == 0
            and sino_posterior.returncode == 0
            and re.search(r"w-claude.*\bLEU\b", chamada.stdout) is not None,
            f"read={leitura_claude.returncode} post={sino_posterior.returncode}",
        )
        checa(
            "G2 chamada mostra as peças órfãs e não escreve na sala",
            "ÓRFÃOS: w-kimi, w-claude" in chamada.stdout
            and sha256(chat) == hash_antes_chamada,
            f"rc={chamada.returncode}",
        )

        # A autoria da resposta é validada antes de qualquer mutação.
        resposta_antes = (run / "respostas" / "w-codex.json").read_bytes()
        intruso = roda(
            SQUAD, env, "responder", str(run), "--worker", "w-codex", "--de", "kimi", "--recusar", "--motivo", "não sou o dono"
        )
        checa(
            "T-RED resposta pela IA errada REPROVA e preserva o aceite",
            intruso.returncode == 2
            and "não pode responder" in intruso.stderr
            and (run / "respostas" / "w-codex.json").read_bytes() == resposta_antes,
            f"rc={intruso.returncode}",
        )

        # ---- G3: ninguém pegou fica explícito e tem código próprio -----------
        run_ninguem = cria_run(
            base,
            "run-ninguem",
            [("n-codex", "codex", 2), ("n-kimi", "kimi", 2)],
        )
        d_ninguem = roda(SQUAD, env, "despachar", str(run_ninguem), "--de", "grok")
        c_ninguem = roda(SQUAD, env, "chamada", str(run_ninguem))
        checa(
            "G3 ninguém pegou é visível, não sucesso silencioso",
            d_ninguem.returncode == 0
            and c_ninguem.returncode == 3
            and "NINGUÉM PEGOU" in c_ninguem.stdout
            and "ÓRFÃOS: n-codex, n-kimi" in c_ninguem.stdout,
            f"despacho={d_ninguem.returncode} chamada={c_ninguem.returncode}",
        )

        # ---- G4: auditor diferente do autor e recibo verificável -------------
        run_julgamento = cria_run(
            base,
            "run-julgamento",
            [("j-codex", "codex", 2), ("j-kimi", "kimi", 2), ("j-claude", "claude", 2)],
        )
        d_julgamento = roda(SQUAD, env, "despachar", str(run_julgamento), "--de", "grok")
        for worker in ("j-codex", "j-kimi", "j-claude"):
            resultado = run_julgamento / "resultados" / f"{worker}.md"
            resultado.parent.mkdir(parents=True, exist_ok=True)
            resultado.write_text(f"missão: {worker}\nresultado: entregue\n", encoding="utf-8")
        julgamento = roda(SQUAD, env, "julgar", str(run_julgamento), "--de", "grok")
        juizes = json.loads((run_julgamento / "juizes.json").read_text(encoding="utf-8"))
        checa(
            "G4 anel fixa juiz diferente para todos antes do veredito",
            d_julgamento.returncode == 0
            and julgamento.returncode == 0
            and all(
                dados["autor_ia"] != dados["juiz_ia"] and isinstance(dados["msg"], int)
                for dados in juizes["atribuicao"].values()
            ),
            f"julgar={julgamento.returncode}",
        )

        corpo = base / "veredito-pass.md"
        corpo.write_text(
            "# Veredito\n\nEtapa 1: CUMPRIU.\nEtapa 2: CUMPRIU.\n\nPASS\n",
            encoding="utf-8",
        )
        auto = roda(
            SQUAD,
            env,
            "veredito",
            str(run_julgamento),
            "--alvo",
            "j-codex",
            "--de",
            "codex",
            "--arquivo",
            str(corpo),
        )
        checa(
            "T-RED tentativa de autojulgamento REPROVA sem criar veredito",
            auto.returncode == 2
            and "autojulgamento bloqueado" in auto.stderr
            and not (run_julgamento / "vereditos" / "j-codex.md").exists(),
            f"rc={auto.returncode}",
        )

        juiz_correto = juizes["atribuicao"]["j-codex"]["juiz_ia"]
        valido = roda(
            SQUAD,
            env,
            "veredito",
            str(run_julgamento),
            "--alvo",
            "j-codex",
            "--de",
            juiz_correto,
            "--arquivo",
            str(corpo),
        )
        recibo_path = run_julgamento / "vereditos" / ".recibos" / "j-codex.json"
        recibo = json.loads(recibo_path.read_text(encoding="utf-8")) if recibo_path.exists() else {}
        checa(
            "G4 juiz correto grava veredito e recibo com hashes",
            valido.returncode == 0
            and recibo.get("juiz_ia") == juiz_correto
            and recibo.get("sha256_veredito")
            == sha256(run_julgamento / "vereditos" / "j-codex.md"),
            f"rc={valido.returncode} juiz={juiz_correto}",
        )

        # Simula a rota antiga: autor escreve o arquivo canônico sem passar pelo CLI.
        (run_julgamento / "vereditos" / "j-kimi.md").write_text("PASS\n", encoding="utf-8")
        chamada_julgamento = roda(SQUAD, env, "chamada", str(run_julgamento))
        checa(
            "T-RED veredito direto sem recibo fica visivelmente INVÁLIDO",
            "j-kimi" in chamada_julgamento.stdout
            and "VEREDITO-SEM-RECIBO" in chamada_julgamento.stdout,
        )

        # Queda de energia entre arquivo e recibo: o juiz correto consegue fechar
        # exatamente o mesmo conteúdo, sem aceitar conteúdo divergente.
        corpo_curto = base / "veredito-curto.md"
        corpo_curto.write_text("PASS\n", encoding="utf-8")
        juiz_j_kimi = juizes["atribuicao"]["j-kimi"]["juiz_ia"]
        recuperado = roda(
            SQUAD,
            env,
            "veredito",
            str(run_julgamento),
            "--alvo",
            "j-kimi",
            "--de",
            juiz_j_kimi,
            "--arquivo",
            str(corpo_curto),
        )
        checa(
            "G4 escrita parcial idêntica ganha recibo somente pelo juiz correto",
            recuperado.returncode == 0
            and "recuperado após escrita parcial" in recuperado.stdout
            and (run_julgamento / "vereditos" / ".recibos" / "j-kimi.json").is_file(),
            f"rc={recuperado.returncode}",
        )

        # Adulterar juizes.json não abre uma rota lateral de autojulgamento.
        juizes_path = run_julgamento / "juizes.json"
        juizes_integro = juizes_path.read_bytes()
        adulterado = json.loads(juizes_integro)
        adulterado["atribuicao"]["j-claude"]["juiz"] = "j-claude"
        adulterado["atribuicao"]["j-claude"]["juiz_ia"] = "claude"
        juizes_path.write_text(
            json.dumps(adulterado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        auto_adulterado = roda(
            SQUAD,
            env,
            "veredito",
            str(run_julgamento),
            "--alvo",
            "j-claude",
            "--de",
            "claude",
            "--arquivo",
            str(corpo),
        )
        juizes_path.write_bytes(juizes_integro)
        checa(
            "T-RED juizes.json adulterado REPROVA antes do autojulgamento",
            auto_adulterado.returncode == 2
            and "atribuição de juiz adulterada" in auto_adulterado.stderr
            and not (run_julgamento / "vereditos" / "j-claude.md").exists(),
            f"rc={auto_adulterado.returncode}",
        )

        # ---- G5: caso vermelho estrutural -----------------------------------
        run_um = cria_run(base, "run-um", [("solo", "codex", 1)])
        (run_um / "resultados").mkdir()
        (run_um / "resultados" / "solo.md").write_text("resultado real\n", encoding="utf-8")
        um = roda(SQUAD, env, "julgar", str(run_um), "--de", "grok")
        checa(
            "T-RED squad de um REPROVA: não fabrica auditor",
            um.returncode == 2 and "não há juiz possível" in um.stderr,
            f"rc={um.returncode}",
        )

        hash_antes_dup = sha256(chat)
        run_dup = cria_run(
            base,
            "run-duplicado",
            [("dup-a", "codex", 1), ("dup-b", "codex", 1)],
        )
        duplicado = roda(SQUAD, env, "despachar", str(run_dup), "--de", "grok")
        checa(
            "T-RED mesma IA em dois workers REPROVA antes de escrever na sala",
            duplicado.returncode == 2
            and "mesma IA em dois workers" in duplicado.stderr
            and sha256(chat) == hash_antes_dup,
            f"rc={duplicado.returncode}",
        )

        # ---- G6: o histórico inteiro continua numerado e a fixture não mudou -
        numeros_finais = [int(x) for x in META_RE.findall(chat.read_text(encoding="utf-8"))]
        checa(
            "G6 sala pré-existente termina sem colisão nem perda de número",
            numeros_finais == list(range(1, max(numeros_finais) + 1))
            and numeros_finais[:8] == list(range(1, 9)),
            f"total={len(numeros_finais)} último={max(numeros_finais)}",
        )
        checa(
            "G6 fixture congelada do repo permanece byte-a-byte igual",
            fotografa(FIXTURE) == fixture_antes,
        )

    finally:
        shutil.rmtree(base, ignore_errors=True)

    print()
    if falhas:
        print(f"❌ IA-SQUAD REPROVOU: {len(falhas)} falha(s): {', '.join(falhas)}")
        return 1
    print("✅ IA-SQUAD PASSOU")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
