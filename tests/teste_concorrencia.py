#!/usr/bin/env python3
"""Gate nº 1 do ia-chat: 5 IAs postando ao mesmo tempo não perdem mensagem.

Por que este teste existe: `flock(1)` não existe no macOS e PIPE_BUF é 512 bytes.
Append direto (`>>`) de uma mensagem de chat NÃO é atômico — some ou sai picada.
Cada mensagem daqui tem ~1 KB de propósito, para passar longe do PIPE_BUF: se o
lock não funcionasse, o dano apareceria.

Roda o CLI de verdade em subprocesso — é o caminho que as IAs vão usar. Testar a
função Python direto provaria menos.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BIN = Path(__file__).resolve().parent.parent / "bin" / "iachat"
IAS = ["claude", "codex", "kimi", "grok", "agy"]
POR_IA = 20
RECHEIO = ("linha de recheio para passar de 512 bytes (PIPE_BUF) " * 18).strip()


def uma(env: dict, ia: str, i: int) -> tuple[int, str]:
    corpo = (
        f"INICIO-{ia}-{i:02d}\n\n"
        f"{RECHEIO}\n\n"
        f"Mensagem autocontida de teste: quem lê não tem meu contexto.\n"
        f"FIM-{ia}-{i:02d}"
    )
    r = subprocess.run(
        [sys.executable, str(BIN), "post", "--de", ia, "--para", "@all", corpo],
        env=env,
        capture_output=True,
        text=True,
    )
    return r.returncode, (r.stdout + r.stderr).strip()


def main() -> int:
    base = Path(tempfile.mkdtemp(prefix="iachat-teste-"))
    env = {**os.environ, "IACHAT_HOME": str(base)}
    try:
        subprocess.run(
            [sys.executable, str(BIN), "status"], env=env, capture_output=True
        )  # cria a estrutura
        (base / "config.json").write_text(
            json.dumps({"na_sala": IAS, "brain": "claude", "teto_bytes": 40960}) + "\n"
        )

        alvos = [(ia, i) for ia in IAS for i in range(1, POR_IA + 1)]
        with ThreadPoolExecutor(max_workers=len(IAS) * 4) as ex:
            res = list(ex.map(lambda t: uma(env, *t), alvos))

        falhas = [o for c, o in res if c != 0]
        texto = (base / "iachat.md").read_text(encoding="utf-8")
        metas = re.findall(
            r"^<!-- iachat msg=(\d+) de=(\S+) para=(\S*) ts=\S+ -->$", texto, re.M
        )
        nums = sorted(int(n) for n, _, _ in metas)
        esperado = len(alvos)

        # cada corpo tem que estar íntegro: abertura E fechamento, uma vez cada
        truncadas = [
            f"{ia}-{i:02d}"
            for ia, i in alvos
            if texto.count(f"INICIO-{ia}-{i:02d}") != 1
            or texto.count(f"FIM-{ia}-{i:02d}") != 1
        ]
        # o recheio inteiro precisa ter sobrevivido em todas
        recheio_ok = texto.count(RECHEIO) == esperado
        # O contador saiu do cabeçalho quando o post virou append puro (reescrever o
        # arquivo a cada mensagem era o custo que se queria matar). A fonte da verdade
        # agora é .estado.json — o invariante verificado é o mesmo: o contador bate com
        # o que está no arquivo.
        estado = json.loads((base / ".estado.json").read_text())

        print(f"postagens          {esperado} tentadas · {len(falhas)} falharam")
        print(f"mensagens no chat  {len(metas)} (esperado {esperado})")
        print(f"numeração          {'1..%d sem buraco' % esperado if nums == list(range(1, esperado + 1)) else 'QUEBRADA: ' + str(nums[:12])}")
        print(f"corpos truncados   {len(truncadas)} {truncadas[:5]}")
        print(f"recheio íntegro    {texto.count(RECHEIO)}/{esperado}")
        print(f"contador .estado   {estado['ultima']}")
        print(f"bytes              {len(texto.encode())}")

        # anti-eco: ninguém recebe flag da própria mensagem (todas foram @all)
        pend = sorted(p.stem for p in (base / "pendente").glob("*.md"))
        eco = "(sem eco detectável neste teste: todos postaram)"
        print(f"flags pendentes    {pend}  {eco}")

        ok = (
            not falhas
            and len(metas) == esperado
            and nums == list(range(1, esperado + 1))
            and not truncadas
            and recheio_ok
            and estado["ultima"] == esperado
        )
        print("\n" + ("✅ GATE 1 PASSOU" if ok else "❌ GATE 1 REPROVOU"))
        if falhas:
            print("\nprimeiras falhas:")
            for f in falhas[:3]:
                print("  " + f.replace("\n", " | ")[:300])
        return 0 if ok else 1
    finally:
        shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
