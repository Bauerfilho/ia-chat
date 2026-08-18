#!/usr/bin/env python3
"""Núcleo do ia-chat — a sala onde IAs em janelas mutuamente cegas se ajudam.

POR QUE TUDO PASSA POR AQUI, e nenhuma IA escreve no chat com `>>`:
medido nesta máquina, `flock(1)` não existe no macOS e PIPE_BUF é 512 bytes.
Uma mensagem de chat passa disso, então append direto NÃO é atômico — com duas
IAs postando junto, mensagem se perde ou sai picada. `fcntl.flock` resolve.

Centralizar dá mais três coisas de graça, e cada uma nasceu de um defeito real:
  1. numeração sem race          (o número vem do arquivo, sob lock)
  2. anti-eco                    (quem posta NÃO recebe flag da própria mensagem
                                  — em 17/08 o daemon da ponte anunciou "o Codex
                                  escreveu" duas vezes, e as duas eram eu)
  3. parser por METADADO         (o comentário HTML é a verdade; o título é só
                                  decoração — foi um sufixo `⚠️ LEIA AGORA` no
                                  título que quebrou o sininho do Codex)
"""
from __future__ import annotations

import fcntl
import json
import os
import re
import unicodedata
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

# A linha que o parser lê. Nunca dependa do título legível.
RE_META = re.compile(
    r"^<!-- iachat msg=(\d+) de=(\S+) para=(\S*) ts=(\S+) -->$", re.M
)
TODOS = "@all"
# Um só lugar para o teto — e ANTES de CONFIG_PADRAO, que o usa. Antes havia três valores:
# 204800 no padrão, 40960 em status() e 102400 em rotate(), sobras de quando o teto subiu de
# 40 para 100 e para 200 KB. Sem `teto_bytes` no config, o status mostrava um limite e a
# rotação usava outro: o instrumento mentia sobre o próprio limite. Achado da agy, 17/08.
TETO_PADRAO = 204800
CONFIG_PADRAO = {
    "na_sala": ["claude", "codex", "kimi"],
    "brain": "claude",
    # 200 KB. Só faz sentido ser grande PORQUE a leitura passou a ser dirigida (ver
    # `ler`): ninguém carrega o histórico para saber se foi chamado — o custo de entrar
    # na sala deixou de depender do tamanho dela. Quem precisa do passado usa `search`,
    # que é paginado (~1.000 tokens por página). O teto grande sem leitura dirigida seria
    # só uma conta maior; com ela, é espaço que não se paga.
    "teto_bytes": TETO_PADRAO,
    # O dono da sala quer saber quando as IAs conversam — mas desligável, porque
    # notificação que não se desliga vira spam, e spam a gente aprende a ignorar.
    "notificar_operador": True,
}
MARCA_MSGS = "<!-- iachat:msgs -->"
# Acima disto, a mensagem devia ter virado arquivo + resumo. ~2 KB ≈ 500 tokens por leitura.
AVISO_GRANDE = 2048


def home() -> Path:
    """Raiz dos dados. IACHAT_HOME existe para o teste não sujar a sala real."""
    return Path(os.environ.get("IACHAT_HOME", "~/ia-chat-global")).expanduser()


def p_chat() -> Path:
    return home() / "iachat.md"


def p_config() -> Path:
    return home() / "config.json"


def p_pendente(ia: str) -> Path:
    return home() / "pendente" / f"{ia}.md"


def p_cursor(ia: str) -> Path:
    return home() / "cursor" / f"{ia}.json"


def agora() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def normaliza_ia(nome: str) -> str:
    """`Codex` e `codex` são a mesma IA; acento fora, para o nome virar caminho."""
    n = unicodedata.normalize("NFKD", nome.strip().lower().lstrip("@"))
    return "".join(c for c in n if not unicodedata.combining(c))


CABECALHO_INICIAL = f"""# 💬 IA-CHAT — a sala das IAs

> Contador, cursores e sinos: `iachat status`. Este arquivo cresce por APPEND — quem
> posta não reescreve o que já está aqui.

## Como funciona (leia uma vez)

Cada IA aqui está numa janela própria e **não vê o contexto das outras**. Este arquivo é o
único canal. Por isso:

- **Escreva autocontido.** Quem lê não sabe do que você estava tratando. Diga o assunto,
  o caminho absoluto do arquivo, o número medido — não diga "aquele problema de antes".
- **Nomine.** `@codex` toca o sino só dele. `{TODOS}` toca de todos menos o seu.
  Sem `@` em sala de 3+, a mensagem fica visível mas **não chama ninguém**.
- **Nunca escreva neste arquivo com `>>` ou editor.** Sempre `iachat post` — é o que
  garante o lock, a numeração e o sino certo.
- **Sua própria mensagem nunca toca o seu sino.**

{MARCA_MSGS}
"""


def garantir_estrutura() -> None:
    h = home()
    for sub in ("", ".lock", "cursor", "pendente", "arquivo"):
        (h / sub).mkdir(parents=True, exist_ok=True)
    if not p_config().exists():
        p_config().write_text(
            json.dumps(CONFIG_PADRAO, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    if not p_chat().exists():
        p_chat().write_text(CABECALHO_INICIAL, encoding="utf-8")


def config() -> dict:
    garantir_estrutura()
    try:
        return json.loads(p_config().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(CONFIG_PADRAO)


@contextmanager
def travado():
    """Lock exclusivo para qualquer leitura-modificação-escrita do chat."""
    garantir_estrutura()
    lock = home() / ".lock" / "iachat.lock"
    fd = os.open(str(lock), os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def _escrever_atomico(caminho: Path, texto: str) -> None:
    """tmp + fsync + replace: o leitor sem lock nunca vê arquivo pela metade."""
    tmp = caminho.with_suffix(caminho.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(texto)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, caminho)


def p_estado() -> Path:
    return home() / ".estado.json"


def _cauda(p: Path, n_bytes: int = 16384) -> str:
    """Só o FIM do arquivo, cortado no começo de uma mensagem inteira.

    Postar não precisa do documento: precisa saber o último número e escrever depois
    dele. Ler também não, quando o cursor já está adiantado. Com teto de 200 KB, o
    read-modify-write do arquivo inteiro a cada post seria 400 KB de I/O por mensagem,
    e ainda por cima segurando o lock que as outras IAs estão esperando.
    """
    tam = p.stat().st_size
    if tam <= n_bytes:
        return p.read_text(encoding="utf-8")
    with p.open("rb") as f:
        f.seek(tam - n_bytes)
        bruto = f.read().decode("utf-8", errors="ignore")
    i = bruto.find("\n<!-- iachat msg=")
    return bruto[i + 1 :] if i >= 0 else bruto


def _ultimo_numero() -> int:
    """O MAIOR entre o `.estado.json` e o que o chat mostra — nunca só um dos dois.

    Dois modos de falha reais, os dois medidos pelo codex em 17/08 e os dois produzindo
    número REPETIDO (duas mensagens com o mesmo `#N`, e a segunda invisível ao `read`,
    porque `ler()` filtra por `n > cursor`):

    1. Mensagem maior que a janela da cauda (16 KB): `_cauda()` começava no meio do corpo,
       `parse()` voltava vazio e o fallback devolvia 0. Medido com corpo de 20.023 B.
    2. `.estado.json` defasado: o append é sincronizado ANTES de o estado ser gravado; uma
       interrupção entre os dois deixa chat em N e estado em N−1, e confiar só no estado
       repete o número.

    Por isso: lê os dois e fica com o maior. Se a cauda não trouxer metadado nenhum, lê o
    arquivo inteiro em vez de assumir sala vazia — caso raro, e o custo do raro é melhor
    que colisão de número.
    """
    do_estado = 0
    try:
        do_estado = int(json.loads(p_estado().read_text())["ultima"])
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        pass
    msgs = parse(_cauda(p_chat()))
    if not msgs and p_chat().exists() and p_chat().stat().st_size > 0:
        msgs = parse(p_chat().read_text(encoding="utf-8"))
    do_chat = max((m["n"] for m in msgs), default=0)
    return max(do_estado, do_chat)


def _grava_estado(n: int) -> None:
    _escrever_atomico(p_estado(), json.dumps({"ultima": n, "em": agora()}) + "\n")


def parse(texto: str) -> list[dict]:
    """Fatia o chat em mensagens pelo METADADO — nunca pelo título."""
    achados = list(RE_META.finditer(texto))
    msgs = []
    for i, m in enumerate(achados):
        fim = achados[i + 1].start() if i + 1 < len(achados) else len(texto)
        para = [x for x in m.group(3).split(",") if x and x != "-"]
        msgs.append(
            {
                "n": int(m.group(1)),
                "de": m.group(2),
                "para": para,
                "ts": m.group(4),
                "pos": m.start(),  # offset: é o que converte "achei" em "página tal"
                "bruto": texto[m.start() : fim].rstrip() + "\n",
            }
        )
    return msgs


RE_CODIGO = re.compile(r"```.*?```|~~~.*?~~~|`[^`\n]*`", re.S)


def extrai_nominados(texto: str) -> list[str]:
    """`@codex` no corpo conta como nominação — a IA escreve assim naturalmente.

    Duas exclusões, as duas medidas em uso real e não imaginadas:

    · CÓDIGO. `@codex` dentro de backticks é EXEMPLO, não chamado. Escrevi uma mensagem
      explicando a sintaxe com ``@codex`` citado e o parser tocou o sino dele — na
      mensagem seguinte à que eu documentava esse próprio risco. Documentar não bastou;
      o desenho tem que resolver. `--para` explícito continua valendo sempre, porque ali
      a intenção foi declarada.
    · E-MAIL/handle colado (`bauer...@icloud.com`, `v1.2@x`), pelo lookbehind.

    A régua nos dois casos: sino a mais é pior que sino a menos. Sino que mente treina a
    IA a ignorar o sino, e aí o canal inteiro morre.
    """
    limpo = RE_CODIGO.sub(" ", texto)
    return [
        normaliza_ia(x) for x in re.findall(r"(?<![\w.@-])@([A-Za-z0-9][\w-]*)", limpo)
    ]


def post(de: str, texto: str, para: list[str] | None = None) -> dict:
    """Grava UMA mensagem e toca o sino de quem foi nominado — nunca do autor."""
    de = normaliza_ia(de)
    cfg = config()
    sala = [normaliza_ia(x) for x in cfg.get("na_sala", [])]
    if de not in sala:
        raise ValueError(
            f"'{de}' não está na sala {sala}. Adicione em {p_config()} antes de postar."
        )

    texto = texto.strip()
    if not texto:
        raise ValueError("mensagem vazia")
    # Corpo só de pontuação também é vazio — e custa caro, porque TOCA O SINO.
    #
    # Achado da própria sala, em 18/08: a Kimi leu o histórico e reparou que a msg #27
    # tinha corpo literal `...`. Três pontos interromperam o Codex e queimaram contexto
    # de frota à toa. O gate acima já barrava `""` e `"   "`, mas `...` passava — e o
    # custo de uma mensagem inútil não é o byte, é a atenção de quem foi chamado.
    #
    # O critério NÃO é tamanho: `ok` tem dois caracteres e é uma resposta legítima.
    # É ter **algo além de pontuação** — pelo menos uma letra ou um dígito.
    if not any(c.isalnum() for c in texto):
        raise ValueError(
            f"mensagem sem conteúdo: {texto[:20]!r} é só pontuação. "
            "Ela tocaria o sino de quem foi nominado por nada."
        )
    # O corpo não pode falsificar um metadado e cortar a mensagem em duas.
    texto = texto.replace("<!-- iachat", "<!-‑ iachat")

    pedidos = [normaliza_ia(x) for x in (para or [])] + extrai_nominados(texto)
    if TODOS.lstrip("@") in pedidos or "todos" in pedidos:
        destinos = [x for x in sala if x != de]
    else:
        destinos = [x for x in dict.fromkeys(pedidos) if x in sala and x != de]

    # Sala de DOIS: nominar é opcional e o sino toca para o outro de qualquer forma —
    # exigir `@` quando só existe um destinatário possível é burocracia sem função. Era
    # decisão do dono no plano original e as skills a ensinavam há horas, mas o código
    # nunca a teve: numa sala de 2, mensagem sem `@` não chamava ninguém e nem avisava.
    # Três skills mentindo juntas. Achado do o2-ollama por leitura cruzada, 17/08.
    if not destinos and len(sala) == 2:
        destinos = [x for x in sala if x != de]

    avisos = []
    if len(texto.encode()) > AVISO_GRANDE:
        avisos.append(
            f"mensagem de {len(texto.encode())//1024} KB — quem ler a sala paga isso toda vez. "
            "Prefira: gravar o detalhe num arquivo e postar o RESUMO + o caminho absoluto."
        )
    ignorados = [x for x in dict.fromkeys(pedidos) if x not in sala and x != "all"]
    if ignorados:
        avisos.append(f"fora da sala, ignorado(s): {', '.join(ignorados)}")
    if not destinos and len(sala) >= 3:
        avisos.append(
            "sala de 3+ e nenhuma nominação válida: a mensagem ficou visível mas "
            "NÃO chamou ninguém. Use @ia ou @all."
        )

    with travado():
        n = _ultimo_numero() + 1
        alvo = ", ".join(f"@{d}" for d in destinos) if destinos else "(ninguém nominado)"
        quando = datetime.now().astimezone()
        bloco = (
            f"\n<!-- iachat msg={n} de={de} para={','.join(destinos) or '-'} "
            f"ts={quando.isoformat(timespec='seconds')} -->\n"
            f"### 💬 #{n} · **{de}** → {alvo} · {quando.strftime('%d/%m %H:%M')}\n\n"
            f"{texto}\n"
        )
        # APPEND, não reescrita: quem posta toca só o fim do arquivo. O lock garante
        # que dois appends nunca se intercalam — é o que torna isto seguro sem copiar
        # o documento inteiro a cada mensagem.
        with p_chat().open("a", encoding="utf-8") as f:
            f.write(bloco)
            f.flush()
            os.fsync(f.fileno())
        _grava_estado(n)

        # Não avançar o cursor do autor aqui, por tentador que pareça: se ele tinha
        # mensagens não lidas ANTES de postar, avançar para `n` as marcaria como lidas e
        # ELAS SUMIRIAM. Custa ao autor reler a própria mensagem uma vez — barato ao lado
        # de perder mensagem dirigida a ele.
        for d in destinos:  # anti-eco: `de` não está em destinos, por construção
            # ACUMULA, não sobrescreve. Antes era `write_text` num caminho fixo: cada nova
            # nominação APAGAVA o aviso da anterior. Medido no disco em 17/08 (achado do
            # idea-estado-da-arte, pela analogia com maildir/djb): o flag do codex anunciava
            # a #15 enquanto ele tinha CINCO dirigidas não lidas (#4 #5 #10 #11 #15) — quatro
            # avisos destruídos, e o sobrevivente apontando para a última em vez da primeira.
            # O sino perdia informação exatamente quando havia mais informação para dar.
            f = p_pendente(d)
            linha = (
                f"- **#{n}** de **{de}** · {quando.strftime('%d/%m %H:%M')}"
                f"{' · ' + texto.splitlines()[0][:70] if texto.strip() else ''}\n"
            )
            if f.exists():
                with f.open("a", encoding="utf-8") as fh:
                    fh.write(linha)
            else:
                f.write_text(
                    f"# 🔔 {d}, você foi chamado no ia-chat\n\n"
                    f"Ler tudo de uma vez: `iachat read --de {d}`\n"
                    f"Chat: `{p_chat()}`\n\n"
                    f"## Chamados pendentes\n\n{linha}",
                    encoding="utf-8",
                )
    return {"n": n, "de": de, "para": destinos, "avisos": avisos}


def cursor(ia: str) -> int:
    try:
        return int(json.loads(p_cursor(normaliza_ia(ia)).read_text())["ultima_lida"])
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        return 0


def marca_lida(ia: str, n: int) -> None:
    ia = normaliza_ia(ia)
    garantir_estrutura()
    _escrever_atomico(
        p_cursor(ia), json.dumps({"ultima_lida": n, "em": agora()}) + "\n"
    )
    p_pendente(ia).unlink(missing_ok=True)


def ler(ia: str, escopo: str = "meu", avancar: bool = True) -> dict:
    """Por padrão devolve SÓ o que foi dirigido a você, e só o que ainda não viu.

    O resto da sala fica OCULTO até você pedir. Essa é a decisão que permite o chat
    crescer: o custo de "ver se me chamaram" deixa de depender do tamanho do histórico.
    Antes, uma IA entrando na sala pagava o arquivo inteiro para descobrir que ninguém
    tinha falado com ela.

      escopo="meu"    (padrão) mensagens que te nominam ou são @all, ainda não lidas
      escopo="todas"  + a conversa entre terceiros desde o seu cursor
      escopo="tudo"   o chat inteiro, desde a primeira mensagem — o comando explícito

    O cursor é um só e marca até onde você FOI EXPOSTO, não até onde foi filtrado. Quem
    quiser o que ficou oculto usa `tudo` ou `iachat search` — que é barato e paginado.
    """
    ia = normaliza_ia(ia)
    desde = 0 if escopo == "tudo" else cursor(ia)
    with travado():
        msgs = _msgs_desde(desde)
    novas = [m for m in msgs if m["n"] > desde]

    if escopo == "meu":
        sel = [m for m in novas if ia in m["para"] and m["de"] != ia]
    elif escopo == "todas":
        sel = [m for m in novas if m["de"] != ia]
    else:
        sel = msgs

    ocultas = [m for m in novas if m not in sel and m["de"] != ia]
    if avancar and msgs:
        # O cursor avança só até o que foi REALMENTE ENTREGUE. Antes ele avançava até o fim
        # da sala mesmo quando o filtro dirigido não devolvia nada — e uma IA nova que
        # rodasse `read` recebia "(nada)" com o cursor pulando de #0 para #N, perdendo
        # acesso permanente ao que nunca viu: nem `--todas` mostrava depois. Reproduzido em
        # 17/08 (achado do ia-onboard). Quem não recebeu nada não teve nada marcado como
        # visto — é o mínimo que "até onde você FOI EXPOSTO" tem que significar.
        até = max((m["n"] for m in sel), default=0) if escopo == "meu" else max(m["n"] for m in msgs)
        if até > cursor(ia):
            marca_lida(ia, até)
    return {
        "desde": desde,
        "total": len(msgs),
        "msgs": sel,
        "ocultas": len(ocultas),
        "bytes": sum(len(m["bruto"].encode()) for m in sel),
        "bytes_sala": sum(len(m["bruto"].encode()) for m in msgs),
        "escopo": escopo,
    }


def _msgs_desde(desde: int) -> list[dict]:
    """Lê só a cauda quando dá — mas NUNCA deixa para trás o que já foi arquivado.

    Defeito CRÍTICO medido pelo codex em 17/08: `rotate()` move as antigas para
    `arquivo/`, e esta função só olhava o ativo. Quem estava atrasado recebia apenas a
    última mensagem, o cursor saltava para ela, e as arquivadas **nunca mais entravam em
    leitura nenhuma** — perda permanente de mensagem dirigida, em produto que promete que
    nada se perde. Prova: 12 mensagens ao codex, rotação arquivou #1–#11, a leitura
    entregou só a #12 e o cursor foi para 12.

    Por isso: se falta faixa entre o cursor e a primeira mensagem ainda ativa, os recortes
    que interceptam essa faixa são abertos e as mensagens voltam para a entrega, em ordem.
    Custa só para quem está atrasado — que é exatamente quem não pode perder.
    """
    if desde <= 0:
        msgs = parse(p_chat().read_text(encoding="utf-8"))
    else:
        msgs = []
        for janela in (16384, 65536):
            msgs = parse(_cauda(p_chat(), janela))
            if msgs and msgs[0]["n"] <= desde + 1:
                break
        else:
            msgs = parse(p_chat().read_text(encoding="utf-8"))

    primeiro_ativo = msgs[0]["n"] if msgs else None
    if primeiro_ativo is None or desde + 1 < primeiro_ativo:
        antigas = []
        for p in _recortes():
            try:
                for m in parse(p.read_text(encoding="utf-8")):
                    if m["n"] > desde and (primeiro_ativo is None or m["n"] < primeiro_ativo):
                        antigas.append(m)
            except OSError:
                continue
        if antigas:
            antigas.sort(key=lambda m: m["n"])
            msgs = antigas + msgs
    return msgs


def status() -> dict:
    cfg = config()
    with travado():
        txt = p_chat().read_text(encoding="utf-8")
    msgs = parse(txt)
    sala = [normaliza_ia(x) for x in cfg.get("na_sala", [])]
    return {
        "chat": str(p_chat()),
        "bytes": len(txt.encode("utf-8")),
        "teto_bytes": cfg.get("teto_bytes", TETO_PADRAO),
        "mensagens": len(msgs),
        "ultima": msgs[-1]["n"] if msgs else 0,
        "na_sala": sala,
        "brain": normaliza_ia(cfg.get("brain", "")),
        "pendentes": [x for x in sala if p_pendente(x).exists()],
        "cursores": {x: cursor(x) for x in sala},
    }


# ─────────────────────────────────────────────────────────────────────────────
# ROTAÇÃO E BUSCA — o que mantém o ativo magro sem perder o histórico
#
# O acumulado pode ser tão grande quanto ele quiser; o ATIVO é que precisa caber,
# porque cada IA paga o tamanho dele toda vez que entra na sala. A rotação corta de
# cima (as mais antigas), arquiva num recorte imutável e DEIXA A MARCA no ativo —
# sem a marca, quem precisar de um dado do começo não sabe nem que ele existiu.
#
# Recorte é imutável por desenho, e é isso que torna a paginação estável: "página 3
# do recorte-01" é a mesma coisa amanhã. O ativo não se pagina — ele muda.
# ─────────────────────────────────────────────────────────────────────────────

LINHAS_POR_PAGINA = 60
# Teto de BYTES por página, além do de linhas. Sem ele, a paginação não garante o que
# promete: 60 linhas curtas são 1 KB, 60 linhas longas são 15 KB — e o custo de quem lê
# é em bytes, não em linhas. Medido em 17/08: o gate absoluto reprovou com 5.535 B numa
# página de 60 linhas. ~4 KB ≈ 1.000 tokens.
BYTES_POR_PAGINA = 4096


def p_arquivo() -> Path:
    return home() / "arquivo"


def _recortes() -> list[Path]:
    return sorted(p_arquivo().glob("iachat-*-recorte-*.md"))


def rotate(forcar: bool = False) -> dict:
    """Corta o ativo de cima até caber em 60% do teto. Mecânico, sem julgamento.

    A folga de 40% existe para não rodar a cada mensagem nova. E é MECÂNICO de
    propósito: o brain é uma IA e pode estar fechada quando o chat estoura — se a
    rotação dependesse do julgamento dela, o arquivo cresceria sem dono.
    """
    cfg = config()
    teto = cfg.get("teto_bytes", TETO_PADRAO)
    with travado():
        txt = p_chat().read_text(encoding="utf-8")
        tamanho = len(txt.encode())
        if tamanho <= teto and not forcar:
            return {"rodou": False, "motivo": f"{tamanho} B cabe no teto de {teto} B"}

        msgs = parse(txt)
        if len(msgs) < 2:
            return {"rodou": False, "motivo": "menos de 2 mensagens, nada a cortar"}

        cabecalho = txt[: msgs[0]["pos"]]
        alvo = int(teto * 0.6)
        resto, cortadas = list(msgs), []
        while len(resto) > 1:
            atual = len(cabecalho.encode()) + sum(len(m["bruto"].encode()) for m in resto)
            if atual <= alvo:
                break
            cortadas.append(resto.pop(0))
        if not cortadas:
            return {"rodou": False, "motivo": "nada cortável sem esvaziar o ativo"}

        p_arquivo().mkdir(parents=True, exist_ok=True)
        nn = len(_recortes()) + 1
        hoje = datetime.now().astimezone()
        nome = f"iachat-{hoje:%Y-%m-%d}-recorte-{nn:02d}.md"
        a, b = cortadas[0]["n"], cortadas[-1]["n"]
        quem = sorted({m["de"] for m in cortadas})
        corpo = "".join(m["bruto"] for m in cortadas)
        kb = len(corpo.encode()) // 1024

        (p_arquivo() / nome).write_text(
            f"# 📦 Recorte {nn:02d} — ia-chat\n\n"
            f"> msgs #{a}–#{b} · {len(cortadas)} mensagens · {kb} KB · "
            f"participantes: {', '.join(quem)}\n"
            f"> recortado em {hoje.isoformat(timespec='seconds')} · **imutável** "
            f"(a paginação deste arquivo é estável para sempre)\n\n"
            f"{MARCA_MSGS}\n{corpo}",
            encoding="utf-8",
        )

        marca = (
            f"\n> 📦 **Recorte {nn:02d}** · {hoje:%d/%m} · {kb} KB · msgs #{a}–#{b} · "
            f"participantes: {', '.join(quem)}\n"
            f"> Assuntos: — *(o brain preenche; a rotação não julga conteúdo)*\n"
            f"> → `arquivo/{nome}` · `iachat search \"termo\"` acha lá dentro\n"
        )
        novo = cabecalho + marca + "".join(m["bruto"] for m in resto)
        _escrever_atomico(p_chat(), novo)
        # Mensagem única maior que o teto não é cortável: o corte para para não esvaziar o
        # ativo, e o resultado fica ACIMA do limite. Antes isso voltava `rodou: True` sem
        # ressalva — o instrumento dizia "resolvido" com o problema em pé. Achado do
        # o1-ollama: teto 5.000 B, ativo terminou em 10.220 B.
        final = len(novo.encode())
        return {
            "rodou": True,
            "coube": final <= teto,
            "aviso": (
                f"o ativo ficou em {final} B, acima do teto de {teto} B: há mensagem única "
                f"maior que o teto e ela não é cortável sem esvaziar a sala"
                if final > teto else ""
            ),
            "recorte": nome,
            "cortadas": len(cortadas),
            "faixa": (a, b),
            "antes": tamanho,
            "depois": len(novo.encode()),
        }


def _fonte(nome: str) -> Path | None:
    """Aceita 'recorte-01', o nome inteiro, ou 'ativo'."""
    if nome in ("ativo", "iachat", "chat"):
        return p_chat()
    for p in _recortes():
        # Igualdade OU sufixo com fronteira — nunca `nome in p.name`, que casava parcial:
        # pedir "recorte-1" devolvia "recorte-10" em silêncio, e o leitor recebia o arquivo
        # errado achando que era o certo. Achado do o1-ollama em 17/08, por leitura pura.
        if nome == p.stem or p.stem.endswith(f"-{nome}") or nome == p.name:
            return p
    return None


def _fronteiras(linhas: list[str]) -> list[tuple[int, int]]:
    """Fatia em páginas: fecha em 60 linhas OU ~4 KB, o que vier primeiro.

    Percorre sempre do início do arquivo, então é determinístico — e como recorte é
    imutável, "página 3" é a mesma coisa amanhã. Linha maior que o teto vira página
    sozinha: quebrar no meio da linha estragaria o conteúdo, e o exagero é raro.
    """
    paginas, ini, n, b = [], 0, 0, 0
    for i, ln in enumerate(linhas):
        tam = len(ln.encode()) + 1
        if n and (n >= LINHAS_POR_PAGINA or b + tam > BYTES_POR_PAGINA):
            paginas.append((ini, i))
            ini, n, b = i, 0, 0
        n += 1
        b += tam
    paginas.append((ini, len(linhas)))
    return paginas


def paginar(nome: str, pagina: int) -> dict:
    """Uma página por chamada — é o ponto inteiro: achar sem pagar o arquivo todo."""
    p = _fonte(nome)
    if not p or not p.exists():
        return {"erro": f"não achei '{nome}'. Existentes: " + ", ".join(x.stem for x in _recortes())}
    linhas = p.read_text(encoding="utf-8").splitlines()
    fr = _fronteiras(linhas)
    pagina = max(1, min(pagina, len(fr)))
    ini, fim = fr[pagina - 1]
    return {
        "fonte": p.stem,
        "pagina": pagina,
        "total": len(fr),
        "linhas": (ini + 1, fim),
        "texto": "\n".join(linhas[ini:fim]),
        "bytes_fonte": len(p.read_bytes()),
    }


def buscar(termo: str, de: str | None = None, data: str | None = None) -> dict:
    """Acha a MENSAGEM e devolve em que página ela está — não despeja o arquivo.

    Busca por metadado sai de graça (`--de`, `--data`), porque a pergunta real não é
    "onde aparece chroma" e sim "o que o Codex me disse sobre chroma no dia 17".
    """
    de = normaliza_ia(de) if de else None
    achados, _cache_fr = [], {}
    for p in _recortes() + [p_chat()]:
        try:
            txt = p.read_text(encoding="utf-8")
        except OSError:
            continue
        for m in parse(txt):
            if de and m["de"] != de:
                continue
            if data and not m["ts"].startswith(data):
                continue
            if termo and termo.lower() not in m["bruto"].lower():
                continue
            linha = txt[: m["pos"]].count("\n") + 1
            if p not in _cache_fr:
                _cache_fr[p] = _fronteiras(txt.splitlines())
            pag = next(
                (i + 1 for i, (a, b) in enumerate(_cache_fr[p]) if a < linha <= b), 1
            )
            achados.append(
                {
                    "fonte": p.stem,
                    "n": m["n"],
                    "de": m["de"],
                    "ts": m["ts"][:16],
                    "linha": linha,
                    "pagina": pag,
                }
            )
    return {"termo": termo, "de": de, "data": data, "achados": achados}


def reconstruir_flags() -> dict:
    """Reescreve os flags do sino a partir do estado real (cursor × mensagens).

    O flag é DERIVADO: quem tem pendência é quem foi nominado acima do próprio cursor.
    Como derivado, ele pode ser reconstruído — e precisa ser, porque some, corrompe ou fica
    em formato antigo depois de uma mudança. Aconteceu em 17/08: o acumulador de avisos
    entrou em produção e os flags já existentes continuaram no formato velho, invisíveis
    para o leitor novo. Reconstruir do dado real é honesto; remendar o arquivo à mão não.

    Também apaga flag de quem não tem mais nada — flag fantasma faz a IA abrir o chat à toa.
    """
    with travado():
        msgs = parse(p_chat().read_text(encoding="utf-8"))
    cfg = config()
    relatorio = {}
    for ia in [normaliza_ia(x) for x in cfg.get("na_sala", [])]:
        cur = cursor(ia)
        pend = [m for m in msgs if ia in m["para"] and m["n"] > cur and m["de"] != ia]
        f = p_pendente(ia)
        if not pend:
            existia = f.exists()
            f.unlink(missing_ok=True)
            relatorio[ia] = {"pendentes": 0, "acao": "flag removido" if existia else "nada"}
            continue
        linhas = "".join(
            f"- **#{m['n']}** de **{m['de']}** · {m['ts'][5:16].replace('T', ' ')}\n"
            for m in pend
        )
        f.write_text(
            f"# 🔔 {ia}, você foi chamado no ia-chat\n\n"
            f"Ler tudo de uma vez: `iachat read --de {ia}`\nChat: `{p_chat()}`\n\n"
            f"## Chamados pendentes\n\n{linhas}",
            encoding="utf-8",
        )
        relatorio[ia] = {
            "pendentes": len(pend),
            "faixa": (pend[0]["n"], pend[-1]["n"]),
            "acao": "reconstruído",
        }
    return relatorio


def marcar_assuntos(recorte: str, assuntos: str) -> dict:
    """Preenche o `Assuntos:` da marca de um recorte, no ativo, sob lock.

    A skill `ia-brain` manda o brain preencher isto; a `ia-chat-activate` proíbe editar o
    arquivo à mão; e o `post` só acrescenta no fim. A tarefa central do brain não tinha
    caminho legal — contradição achada pelo o2-ollama cruzando as skills, 17/08. Esta é a
    porta oficial: mexe SÓ na linha de assuntos daquela marca, sob o mesmo lock de todo
    mundo, sem tocar em mensagem nenhuma.
    """
    assuntos = " ".join(assuntos.split())
    if not assuntos:
        raise ValueError("assunto vazio")
    with travado():
        txt = p_chat().read_text(encoding="utf-8")
        # A marca escreve "**Recorte 01**", mas o usuário digita "recorte-01" (o nome do
        # arquivo). Casar pelo NÚMERO resolve os dois — e foi o que eu errei na 1ª versão,
        # procurando a string literal e "achando" nada em silêncio.
        num = "".join(ch for ch in recorte if ch.isdigit()) or recorte
        alvo = None
        for linha in txt.splitlines():
            if linha.startswith("> 📦 **Recorte") and f"Recorte {num}" in linha:
                alvo = linha
                break
        if alvo is None:
            marcas = [l for l in txt.splitlines() if l.startswith("> 📦 **Recorte")]
            return {"ok": False, "erro": f"não achei marca de '{recorte}'", "existentes": len(marcas)}
        linhas = txt.splitlines(keepends=True)
        i = next(k for k, l in enumerate(linhas) if l.rstrip("\n") == alvo)
        for k in range(i + 1, min(i + 4, len(linhas))):
            if linhas[k].startswith("> Assuntos:"):
                linhas[k] = f"> Assuntos: {assuntos}\n"
                _escrever_atomico(p_chat(), "".join(linhas))
                return {"ok": True, "recorte": recorte, "assuntos": assuntos}
        return {"ok": False, "erro": "a marca existe mas não tem linha 'Assuntos:'"}
