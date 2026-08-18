#!/usr/bin/env python3
"""O número que o `read` mostra tem que ser o que a legenda promete.

Achado em 18/08 lendo a saída, não o código: com 54 mensagens na sala e o cursor
em #46, o comando dizia "cursor em #46 de 8 na sala". O 8 não era o tamanho da
sala nem o número de novidades — era o tamanho da JANELA lida do disco, que
inclui mensagens anteriores ao cursor.

Número certo com legenda errada mente igual a número errado, e mente pior: quem
lê confia. Este gate trava a correspondência entre o que é dito e o que é medido.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CLI = RAIZ / "bin" / "iachat"

_ok = 0
_falhou = 0


def checa(nome: str, cond: bool, detalhe: str = "") -> None:
    global _ok, _falhou
    if cond:
        _ok += 1
        print(f"  ✔ {nome}")
    else:
        _falhou += 1
        print(f"  ✗ {nome}" + (f" — {detalhe}" if detalhe else ""))


def main() -> int:
    lar = Path(tempfile.mkdtemp(prefix="cursor-legenda-"))
    (lar / "config.json").write_text(json.dumps({
        "na_sala": ["claude", "codex", "kimi"], "brain": "claude",
        "notificar_operador": False, "teto_bytes": 204800,
    }), encoding="utf-8")
    env = {**os.environ, "IACHAT_HOME": str(lar)}

    def roda(*args: str) -> str:
        r = subprocess.run([sys.executable, str(CLI), *args],
                           capture_output=True, text=True, env=env, timeout=30)
        return r.stdout + r.stderr

    # ⚠️ O cenário PRECISA ter mensagens ANTES do cursor, senão `total` (a janela lida
    # do disco) e `novas` (o que passou do cursor) dão o mesmo número — e trocar um pelo
    # outro passa despercebido. Foi o que aconteceu na primeira versão deste gate: a isca
    # trocou `novas` por `total` e o teste ficou verde.
    #
    # Então: 5 mensagens PARA o claude (que ele lê, avançando o cursor), e depois 12 que
    # não são para ele. Aí total > novas, e a legenda tem um número só certo.
    def posta(de: str, para: str, texto: str) -> None:
        subprocess.run([sys.executable, str(CLI), "post", "--de", de, "--para", para, texto],
                       capture_output=True, text=True, env=env, timeout=30)

    for i in range(5):
        posta("codex", "claude", f"antiga {i}")
    roda("read", "--de", "claude")          # o claude lê: o cursor avança
    for i in range(12):
        posta("codex", "kimi", f"mensagem numero {i}")

    print("— o número dito é o número de NOVIDADES —")
    saida = roda("read", "--de", "claude")
    checa("o `read` avisa que não há nada para ele", "nada para claude" in saida, saida[:120])
    # o claude nunca leu: as 12 são novas
    import re
    m = re.search(r"(\d+)\s+mensagem", saida)
    checa("o número aparece na frase", m is not None, saida[:160])
    if m:
        checa("e é 12, o número real de novidades", m.group(1) == "12",
              f"disse {m.group(1)}, e havia 12 · saída: {saida.strip()[:150]}")

    print("— a legenda não promete o que não mede —")
    checa("não diz 'na sala' colado no número da janela",
          "de 12 na sala" not in saida and "de 8 na sala" not in saida,
          "era a frase que fazia parecer tamanho de sala")
    checa("a frase diz que são NOVAS",
          "nova" in saida.lower(), saida[:160])
    checa("e diz que nenhuma é para ele",
          "endereçada a você" in saida or "nenhuma" in saida.lower(), saida[:160])

    print("— o núcleo expõe o número certo —")
    sys.path.insert(0, str(RAIZ / "bin"))
    os.environ["IACHAT_HOME"] = str(lar)
    import importlib
    core = importlib.import_module("iachat_core")
    importlib.reload(core)
    r = core.ler("claude", avancar=False)
    checa("`novas` existe no retorno", "novas" in r, f"chaves: {sorted(r)}")
    checa("`novas` conta só o que passou do cursor", r.get("novas") == 12,
          f"novas={r.get('novas')} · total={r.get('total')}")

    import shutil
    shutil.rmtree(lar, ignore_errors=True)
    print(f"\n{_ok} ✔  {_falhou} ✗")
    return 1 if _falhou else 0


if __name__ == "__main__":
    raise SystemExit(main())
