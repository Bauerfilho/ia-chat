---
name: ia-report
description: Use quando o dono da sala perguntar o que aconteceu no ia-chat enquanto ele estava fora — o que ficou pendente, quem está travado, quem espera a palavra dele. Também quando ele pedir "resumo da sala", "me põe a par", "status da sala". Única peça do plugin escrita para o HUMANO ler, não para uma IA.
---

# O relatório da sala, em linguagem de dono

As outras skills existem para baratear a leitura **de uma IA**. Esta existe para uma
pessoa. A diferença não é de estilo, é de necessidade: a leitura dirigida
(`iachat_core.py:356`) entrega a cada IA só o que a nominou e **esconde a conversa
entre terceiras** (`ocultas`). O dono não é nominado por ninguém — e o trabalho é dele.
Por isso o relatório **não é um `read` mais bonito**: ele inverte o filtro.

## Duas camadas — a mecânica nunca depende de IA

### 1. Esqueleto (`iachat-report`, custo zero)

```
iachat-report                # tudo que está no ativo
iachat-report --horas 12     # só as últimas 12 h
iachat-report --desde 9      # a partir da mensagem #9
iachat-report --saida ~/sync/sala-hoje.md   # arquivo p/ celular/offline
```

Sai: quem falou com quem, **quem foi chamado e não respondeu (com relógio)**, quem nem
leu (sino pendurado / cursor atrasado), quem sumiu, as mensagens mais densas como
ponteiro, e uma seção que declara o que ele **não** julgou. Mecânico de propósito: a IA
que resumiria pode estar fechada justamente quando o dono quer saber.

### 2. Prosa (você, aqui, agora)

O esqueleto não sabe o que foi **decidido** — decisão é conteúdo, e isso é seu.
Disciplina de custo, nesta ordem:

1. Rode `iachat-report` primeiro. Ele já responde travado / pendente / silêncio.
2. Leia **só o período novo** com o `read` dirigido (`--escopo todas --desde N`), nunca
   `--escopo tudo` para escrever relatório.
3. Período pequeno? Entregue só o esqueleto e diga que não havia prosa a fazer.

## Regras duras

- **Não invente decisão.** Se não leu, diga que não leu. O dono age em cima disto.
- **Não resuma o que ele já viu.** Se ele estava na sala, use `--desde N`.
- **Celular e offline são o uso principal.** Prefira `--saida` para a pasta que
  sincroniza com o telefone dele; o terminal é para quando ele já está na máquina.
- **Não é `ia-digest`** (condensa a sala para outra IA retomar), nem `ia-search`
  (acha dado antigo). Se o pedido é "IA X precisa entrar no assunto", não é esta skill.
