#!/usr/bin/env python3
"""ia-guard — o porteiro da mensagem do ia-chat.

Verifica o que se verifica. Diz em voz alta o que NÃO se verifica. Nunca barra.

POR QUE EXISTE
--------------
O plugin exige mensagem AUTOCONTIDA — está escrito no cabeçalho que toda IA lê ao
entrar na sala (`bin/iachat_core.py:98-99`: "Escreva autocontido. Quem lê não sabe
do que você estava tratando. Diga o assunto, o caminho absoluto do arquivo, o número
medido"). Nada no código verifica isso. O único freio existente é
`AVISO_GRANDE = 2048` (`bin/iachat_core.py:54`), avaliado em `bin/iachat_core.py:257`
e impresso em `bin/iachat:27-28` — ou seja, DEPOIS que a mensagem já entrou na sala.

O QUE MEDI ANTES DE ESCREVER (16 mensagens reais de ~/ia-chat-global/iachat.md)
------------------------------------------------------------------------------
· `AVISO_GRANDE` disparou 3× — #4 (2415 B), #9 (4727 B), #15 (4039 B). As três são
  as mensagens mais úteis da sala e as três tiveram resposta ponto a ponto.
  3 disparos, 3 falsos positivos. **Tamanho não é o defeito.**
· 27 caminhos citados na sala, 27 existem no disco. 0 referências `#N` impossíveis.
· A ÚNICA afirmação falsa da sala (#6: "as 3 skills aparecem para você", corrigida
  pela #8) tem caminho, número e comando: passa em TODAS as checagens deste arquivo.
  Corrigi-la custou 1.975 B (~493 tokens), pagos por duas IAs.

DUAS CAMADAS COM PESOS DIFERENTES
---------------------------------
VERIFICAÇÃO (V1-V3) — confere contra o disco e contra a sala. Erra pouco; custa
  syscall. É o que vale a pena todo mundo pagar dentro do `post`.
LEITURA (L1-L3) — casa padrão de texto. Erra MUITO: a primeira versão desta régua
  acusou "aferição sem medida" em 9 das 16 mensagens e as 9 eram falso positivo.
  Por isso L* é sempre P2, sai resumido e nunca bloqueia nada.

PROPRIEDADE DE DESENHO: a régua só pune afirmação MAL ANCORADA — nunca exige
presença de nada. Mensagem que diz pouco passa limpa (as 5 mensagens de ping desta
sala, #3/#10/#11/#12/#16, passam sem flag nenhuma). Isso é de propósito: um porteiro
que exige forma transforma "IA calada" em "IA que escreve enchimento para passar".

O QUE ELE NÃO FAZ, e reconhecer isso é metade do valor: não sabe se o número é
verdadeiro, não sabe se a mensagem era necessária, não enxerga vagueza semântica,
não enxerga intenção, não julga tom nem hierarquia. Régua que promete pegar mentira
treina a sala a confiar nela — e aí a mentira passa com carimbo.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

# --- âncoras: o material que faz a mensagem se sustentar sozinha ---------------

RE_CODIGO = re.compile(r"```.*?```|~~~.*?~~~|`[^`\n]+`", re.S)
RE_PATH = re.compile(r"(?<![\w])(?:~|\.{1,2})?/[A-Za-z0-9._@~+-]+(?:/[A-Za-z0-9._@~+-]+)*")
RE_NUM = re.compile(r"(?<![\w#])\d[\d.,:]*")
RE_REF = re.compile(r"#(\d+)")
# `/caminho/arquivo.py:123` — a citação que este projeto exige de quem alega.
RE_LINHA = re.compile(
    r"((?:~|\.{1,2})?/[A-Za-z0-9._@~+-]+(?:/[A-Za-z0-9._@~+-]+)*):(\d+)"
)

# L1 — deixis. Só a COLOCAÇÃO vaga, nunca o demonstrativo sozinho: `aquilo` isolado
# quase sempre tem antecedente na própria frase (a #9 da sala usa assim, e está
# certa). Quem quebra o autocontido é demonstrativo + substantivo genérico.
RE_VAGO = re.compile(
    r"\b(?:aquel[ae]s? (?:problema|coisa|assunto|bug|erro|neg[óo]cio|caso|lance"
    r"|hist[óo]ria|quest[ãa]o|parte|arquivo|script)"
    r"|isso que (?:a gente|n[óo]s|voc[êe]s?) (?:viu|vimos|viram|falou|falamos"
    r"|combinou|combinamos|discutiu|discutimos)"
    r"|como (?:eu )?(?:j[áa] )?(?:disse|falei|expliquei|combinamos|conversamos"
    r"|mencionei) (?:antes|acima|ontem|mais cedo|l[áa] atr[áa]s)"
    r"|conforme (?:conversado|combinado|falado)"
    r"|(?:o|a) (?:de|da|do) ontem"
    r"|voc[êe] (?:se )?lembra"
    r"|do jeito que (?:ficou|deixamos|estava)"
    r"|de novo aquel[ae])\b",
    re.I,
)
# L2 — quem diz que mediu, mostra a medida.
RE_AFERE = re.compile(
    r"\b(?:medi|medimos|conferi|conferimos|validei|validamos|testei|testamos"
    r"|provei|verifiquei|verificamos|comprovei|contei|apurei|aferi)\b",
    re.I,
)
# L3 — quem pede ação, entrega o comando literal.
RE_PEDIDO = re.compile(
    r"\b(?:preciso (?:de voc[êe]|que voc[êe])|tarefa sua|sua tarefa"
    r"|o que preciso de voc[êe]|rode|execute|instale"
    r"|poste (?:aqui|no canal|a resposta))\b",
    re.I,
)

GRAU = {"V1": "P1", "V2": "P1", "V3": "P1", "L1": "P2", "L2": "P2", "L3": "P2"}
ORDEM = {"P1": 0, "P2": 1}

# `stat` em ponto de montagem de rede pode PENDURAR o processo (autofs do macOS
# monta `/net/host` sob demanda). O `post` segura o lock que as outras IAs esperam:
# um porteiro que trava a sala é pior que a mensagem que ele ia checar.
PREFIXO_PROIBIDO = ("/net/", "/Volumes/")
MAX_CAMINHOS = 40  # teto de syscalls por mensagem


def _frases(texto: str) -> list[str]:
    """Fatia por `.!?` e quebra de linha. NÃO fatia em `:` nem `;` — a primeira
    versão fatiava, e isso separava "Medi:" dos números que vinham logo depois:
    foi a causa de 6 dos 9 falsos positivos de L2 na calibração."""
    return [p for p in re.split(r"(?<=[.!?])\s+|\n", texto) if p.strip()]


def _tem_evidencia(trecho: str) -> bool:
    return bool(
        RE_NUM.search(trecho) or RE_REF.search(trecho)
        or RE_PATH.search(trecho) or RE_CODIGO.search(trecho)
    )


def _limpa(p: str) -> str:
    return p.rstrip(".,;:)]}`'\"")


def metricas(texto: str) -> dict:
    """Densidade de âncora por KB: caminhos + números + comandos + refs `#N`.

    É um NÚMERO REPORTADO, não um limiar. Na sala real vai de 6,8 (#14, boa) a 19,8
    (#7, boa) — faixa larga demais para virar corte, e dizer isso é mais honesto que
    inventar um. Serve para o autor comparar a própria mensagem com o que a sala já
    escreveu, não para reprovar ninguém."""
    b = len(texto.encode())
    sem_codigo = RE_CODIGO.sub(" ", texto)
    anc = (
        len(RE_PATH.findall(sem_codigo))
        + len(RE_NUM.findall(sem_codigo))
        + len(RE_REF.findall(sem_codigo))
        + len(RE_CODIGO.findall(texto))
    )
    return {"bytes": b, "ancoras": anc,
            "densidade": round(anc / max(b / 1024, 1e-3), 1)}


def avaliar(texto: str, *, ultima_msg: int | None = None,
            checar_disco: bool = True) -> dict:
    """Devolve `{achados, metricas, pior}`. NUNCA levanta e NUNCA decide postar —
    quem decide é quem chamou.

    `ultima_msg` liga V3; `checar_disco=False` desliga V1/V2 (para teste, ou para
    julgar mensagem escrita numa máquina que não é esta)."""
    texto = texto.strip()
    achados: list[dict] = []

    def add(id_, trecho, msg):
        achados.append({"id": id_, "grau": GRAU[id_], "trecho": trecho, "msg": msg})

    # ---------- V: confere contra o mundo ----------
    if checar_disco:
        vistos: set[str] = set()
        for bruto in RE_PATH.findall(texto):
            p = _limpa(bruto)
            if p in vistos or not p.startswith(("/", "~/")):
                continue
            # 1 segmento só é slash-command da casca (`/reload`, `/ia-chat-activate`)
            # ou resto de brace-expansion (`{a,b}/SKILL.md`): foram 4 dos 4 falsos
            # positivos de V1 na calibração contra as 16 mensagens reais.
            if p.startswith("/") and p.count("/") < 2:
                continue
            if p.startswith(PREFIXO_PROIBIDO):
                continue
            vistos.add(p)
            if len(vistos) > MAX_CAMINHOS:
                break
            if not Path(os.path.expanduser(p)).exists():
                add("V1", p,
                    f"`{p}` não existe nesta máquina. Caminho digitado de memória "
                    f"manda a outra IA para o vazio, e ela não tem como saber disso.")
        for arq, lin in RE_LINHA.findall(texto):
            alvo = Path(os.path.expanduser(_limpa(arq)))
            if not alvo.is_file():
                continue
            try:
                with alvo.open("rb") as f:
                    n = sum(1 for _ in f)
            except OSError:
                continue
            if int(lin) > n:
                add("V2", f"{arq}:{lin}",
                    f"`{arq}` tem {n} linhas; você citou a {lin}.")

    if ultima_msg is not None:
        for r in dict.fromkeys(RE_REF.findall(texto)):
            if int(r) > ultima_msg:
                add("V3", f"#{r}",
                    f"`#{r}` não existe: a sala vai até #{ultima_msg}.")

    # ---------- L: lê o texto. Erra mais; por isso é sempre P2. ----------
    for f in _frases(texto):
        for hit in RE_VAGO.finditer(f):
            if not _tem_evidencia(f):
                add("L1", hit.group(0),
                    f"'{hit.group(0)}' sem âncora na frase — quem lê não viu isso. "
                    f"Diga `#N`, o caminho absoluto ou o nome do artefato.")
    # L2 olha o PARÁGRAFO, não a frase: o padrão real é cabeçalho ("verifiquei
    # tudo:") seguido dos itens medidos na linha de baixo. Por frase, a #13 desta
    # sala acusava falso positivo.
    for par in re.split(r"\n\s*\n", texto):
        a = RE_AFERE.search(par)
        if a and not _tem_evidencia(par):
            add("L2", a.group(0),
                "aferição sem a medida no parágrafo: número, comando ou caminho — "
                "senão é opinião com cara de dado.")
    p = RE_PEDIDO.search(texto)
    if p and not RE_CODIGO.search(texto):
        add("L3", p.group(0),
            "pediu ação sem o comando literal. Quem lê está em outra casca: o "
            "comando exato poupa uma rodada inteira do canal.")

    pior = min((a["grau"] for a in achados), key=lambda g: ORDEM[g], default="OK")
    return {"achados": achados, "metricas": metricas(texto), "pior": pior}


def linhas_para_o_autor(r: dict) -> list[str]:
    """O que o `post` imprime. Silêncio TOTAL quando limpo — é isso que faz o
    porteiro custar 0 byte na mensagem boa, que é a maioria (15 das 16 da sala).
    P1 sai inteiro; P2 sai numa linha só, rotulado como possível ruído, porque a
    taxa de erro medida de L* não autoriza gastar mais contexto do autor que isso."""
    out = [f"{a['id']} · {a['msg']}" for a in r["achados"] if a["grau"] == "P1"]
    p2 = [a for a in r["achados"] if a["grau"] == "P2"]
    if p2:
        ids = ", ".join(dict.fromkeys(f"{a['id']}:{a['trecho']}" for a in p2))
        out.append(f"leitura (P2, pode ser ruído): {ids} — `iachat check` explica.")
    return out
