#!/usr/bin/env python3
"""Aplica o ia-guard num CLONE do plugin ia-chat. Idempotente.

    python3 patch-ia-guard.py /caminho/para/uma/COPIA/do/ia-chat

RECUSA rodar em ~/Projetos/ia-chat: a integração é proposta, e quem decide mexer no
repositório do Bauer é o Bauer. Copie primeiro (`cp -R`), patcheie a cópia, meça.

O patch são 3 costuras:
  1. `bin/iachat_core.py:post()` — chama o porteiro e junta os achados aos `avisos`
     que já existem (`bin/iachat_core.py:256-266`), impressos por `bin/iachat:27-28`.
  2. o veredito de tamanho de `AVISO_GRANDE` vira um DADO (densidade de âncora).
  3. `bin/iachat` ganha `check` — o ensaio ANTES de postar.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

PROIBIDO = (Path.home() / "Projetos" / "ia-chat").resolve()

ALVO_POST = '''    avisos = []
    if len(texto.encode()) > AVISO_GRANDE:
        avisos.append(
            f"mensagem de {len(texto.encode())//1024} KB — quem ler a sala paga isso toda vez. "
            "Prefira: gravar o detalhe num arquivo e postar o RESUMO + o caminho absoluto."
        )'''

NOVO_POST = '''    avisos = []
    # ia-guard: o porteiro roda ANTES do lock — 0,27 ms na maior mensagem real da
    # sala, +0,04 ms no `post` inteiro (A/B intercalado, abaixo do ruído), e imprime
    # ZERO byte quando a mensagem está limpa (15 das 16 mensagens reais estão).
    # Ele AVISA e NUNCA barra: em 16 mensagens vivas produziu 0 achado verificado,
    # e um porteiro sem defeito medido não tem licença para fechar a porta.
    _g = None
    try:
        import ia_guard
        _g = ia_guard.avaliar(texto, ultima_msg=_ultimo_numero())
        avisos += ia_guard.linhas_para_o_autor(_g)
    except Exception as e:  # o canal nunca cai por causa do porteiro
        avisos.append(
            f"ia-guard indisponível ({e.__class__.__name__}) — postada SEM checagem"
        )
    if len(texto.encode()) > AVISO_GRANDE and _g:
        # O veredito de tamanho vira DADO. Medido: o teto de 2 KB disparou nas #4,
        # #9 e #15 desta sala, que são as três mensagens mais úteis dela — 3 de 3
        # falsos positivos. O que informa não é o tamanho, é a densidade de âncora.
        avisos.append(
            f"{len(texto.encode())//1024} KB · {_g['metricas']['densidade']} âncoras/KB "
            f"(caminho, número, comando, #N). Grande não é defeito; grande e rala é."
        )'''

ALVO_CLI = "def cmd_read(a) -> int:"

NOVO_CLI = '''def cmd_check(a) -> int:
    """Ensaio: julga o rascunho e NÃO posta.

    Existe porque o aviso do `post` chega tarde — a mensagem já está na sala e todo
    mundo já vai pagar por ela. Aqui o custo é só de quem chamou."""
    import ia_guard
    texto = " ".join(a.texto).strip() if a.texto else sys.stdin.read()
    try:
        # Sala ainda não criada (IACHAT_HOME novo): V3 desliga e o ensaio segue.
        # Um ensaio NÃO pode criar a sala como efeito colateral — `garantir_estrutura`
        # fica de fora de propósito.
        ultima = core._ultimo_numero()
    except OSError:
        ultima = None
    r = ia_guard.avaliar(texto, ultima_msg=ultima)
    m = r["metricas"]
    print(f"{m['bytes']} B · {m['ancoras']} âncoras · {m['densidade']}/KB · "
          f"veredito {r['pior']}")
    for x in r["achados"]:
        print(f"  {x['grau']} {x['id']} · {x['trecho']}")
        print(f"       {x['msg']}")
    if not r["achados"]:
        print("  nada a apontar mecanicamente.")
    print("  \\u24d8 não verificado aqui: se o número é verdadeiro, se a mensagem "
          "era necessária, se o texto é vago.", file=sys.stderr)
    if ultima is None:
        print("  \\u24d8 sala ainda não existe: as referências `#N` não foram "
              "checadas.", file=sys.stderr)
    return 1 if r["pior"] == "P1" else 0


def cmd_read(a) -> int:'''

ALVO_SUB = '    p = sub.add_parser("read", help="ler a sala")'

NOVO_SUB = '''    p = sub.add_parser("check", help="ensaiar a mensagem ANTES de postar (não posta)")
    p.add_argument("--de", required=False, help="ignorado; aceito por simetria")
    p.add_argument("texto", nargs="*")
    p.set_defaults(f=cmd_check)

    p = sub.add_parser("read", help="ler a sala")'''


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    raiz = Path(sys.argv[1]).resolve()
    if raiz == PROIBIDO:
        print(f"✗ recusado: {raiz} é o repositório do Bauer. Patcheie uma CÓPIA.",
              file=sys.stderr)
        return 2
    core_py, cli = raiz / "bin" / "iachat_core.py", raiz / "bin" / "iachat"
    if not core_py.is_file() or not cli.is_file():
        print(f"✗ não parece um clone do ia-chat: {raiz}", file=sys.stderr)
        return 2

    origem = Path(__file__).resolve().parent / "ia_guard.py"
    shutil.copy2(origem, raiz / "bin" / "ia_guard.py")

    s = core_py.read_text(encoding="utf-8")
    if "import ia_guard" in s:
        print("· núcleo já patcheado")
    else:
        if ALVO_POST not in s:
            print("✗ âncora do post não encontrada — o núcleo mudou; releia antes de forçar.",
                  file=sys.stderr)
            return 1
        core_py.write_text(s.replace(ALVO_POST, NOVO_POST), encoding="utf-8")
        print("✔ bin/iachat_core.py: post() chama o porteiro")

    s = cli.read_text(encoding="utf-8")
    if "cmd_check" in s:
        print("· CLI já patcheado")
    else:
        cli.write_text(s.replace(ALVO_CLI, NOVO_CLI, 1).replace(ALVO_SUB, NOVO_SUB, 1),
                       encoding="utf-8")
        print("✔ bin/iachat: subcomando `check`")
    print(f"\npronto. Prove com:\n  IACHAT_HOME=/tmp/sala-teste python3 {raiz}/bin/iachat "
          f"check 'sua mensagem'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
