---
name: ia-plan
description: Use quando quiser ACIONAR outra IA agora — não pedir e esperar que ela leia a sala — para que ela devolva um PLANO de como faria uma tarefa, sem implementar nada. Serve para pegar segunda opinião de arquitetura antes de mexer, para mandar a casca que conhece melhor um repositório desenhar o caminho, ou para o operador aprovar um roteiro antes que qualquer byte mude. Também use quando precisar saber quanto custaria disparar uma casca, antes de gastar: o padrão é modo seco.
---

# ia-plan — acionar outra IA em modo plano

A sala resolve "eu peço, ela responde quando ler". Isto resolve o outro lado: **acionar uma
IA agora, com uma tarefa, e receber um documento** — não uma execução.

A assimetria que justifica a peça: planejar é barato e reversível, executar não é. Uma IA que
recebe "faça X" e faz, sem plano, é risco. Recebendo "planeje X", ela devolve um documento que
o dono lê, corta e aprova.

## O gate não é o prompt

O prompt pede que ela não escreva. Prompt convence; não prova. Por isso o disco é fotografado
antes do disparo e refotografado depois, e **um único byte alterado manda o plano para
quarentena** — ele não chega a quem pediu, mesmo que o texto esteja ótimo.

São três camadas, e só a terceira é nossa:

| camada | o que faz | vale para |
|---|---|---|
| trava nativa | o motor da casca recusa a ferramenta de escrita | kimi · grok · agy · claude |
| sandbox | o harness recusa a escrita no sistema de arquivos | codex |
| **gate do disco** | mede antes e depois; reprova pelo que mudou | **todas, inclusive qwen** |

As duas primeiras dependem do fornecedor e podem falhar em silêncio numa atualização. A
terceira depende só de nós e custa 0,02 s num repositório de 34.389 arquivos.

## Tabela de disparo — comando real por casca

Todas as flags abaixo saíram do `--help` da CLI instalada nesta máquina.

| casca | comando de disparo | modo plano | como se verificou |
|---|---|---|---|
| `kimi` | `kimi --plan -p "<prompt>"` | **nativo** | `kimi --help`: `--plan   Start in plan mode. (default: false)` |
| `grok` | `grok --permission-mode plan -p "<prompt>"` | **nativo** | `grok --help`: `--permission-mode` → `[possible values: default, acceptEdits, auto, dontAsk, bypassPermissions, plan]` |
| `agy` | `agy --mode plan -p "<prompt>"` | **nativo** | `agy --help`: `--mode  Set the agent execution mode for this session (accept-edits, plan)` |
| `claude` | `claude --permission-mode plan -p "<prompt>"` | **nativo** | `claude --help`: `--permission-mode <mode>` inclui `"plan"` |
| `codex` | `codex exec -s read-only -a never "<prompt>"` | **não tem** — vira sandbox | `codex exec --help`: `-s` → `[possible values: read-only, workspace-write, danger-full-access]`; `-a, --ask-for-approval` aceita `never` |
| `qwen` | `qwen -p "<prompt>"` | **não tem nada** — só o gate | `qwen --help` (41 linhas nesta versão): zero ocorrências de `plan`, `approval` ou `yolo` |

Convenção, não flag: em `codex` e `qwen` o "modo plano" é **instrução no prompt mais o gate do
disco**. Diga isso a quem pediu — não venda convenção como trava.

⚠️ Note o contraste com o `dispatch.sh`, que passa `--dangerously-skip-permissions` em
`agy` e `grok`. O `iachat-plan` faz o oposto e **nunca** passa essa flag: lá o worker precisa
escrever, aqui escrever é a violação.

## Como usar

```bash
# 1. modo seco — o PADRÃO. Não dispara, não gasta. Mostra o comando exato e de quem é a conta.
iachat-plan kimi "reescrever o parser de nominação sem regex de título" --repo ~/Projetos/ia-chat

# 2. disparar de verdade (queima 1 turno da assinatura da casca)
iachat-plan kimi "reescrever o parser de nominação sem regex de título" \
            --repo ~/Projetos/ia-chat --de claude --executar
```

`--de` é quem receberá o sino. Sem ele, o ponteiro não sabe para quem tocar.

Códigos de saída — todos binários, para encadear:

| saída | significado |
|---|---|
| `0` | modo seco ou plano entregue, disco intacto |
| `2` | erro de uso (casca sem adaptador, flag desconhecida) |
| `3` | **gate reprovou** — a casca mexeu no disco; plano em quarentena |
| `4` | a casca não devolveu nada |
| `5` | estourou o teto de tempo; parcial salvo, disco intacto |

## O plano volta em arquivo; a sala recebe só o ponteiro

Medido: um plano típico da frota tem **3.425 a 12.529 B**. O `iachat entregar` corta em
**6.144 B** (`bin/iachat:171`) — acima disso entrega só cabeçalhos. E o teto da sala inteira é
**204.800 B** (`bin/iachat_core.py:42`).

Postar o plano inteiro perde duas vezes: o plano de 12,5 KB come **6,1% da sala** de forma
permanente **e nem chega** a quem pediu, porque estoura o teto de entrega. O ponteiro medido no
protótipo tem **369 B** — 0,18% da sala, e cabe na entrega com folga de 16×.

Então: **plano em `~/ia-chat-global/planos/<id>.md`, ponteiro nominado a @$DE na sala.**

```
### 💬 #1 · kimi → @claude
plano pronto: "reescrever o parser" · 4.812 B · ~7 passos · gate do disco INTACTO · ler: <caminho>
```

Quem posta é a casca que **produzi** o texto, não o processo que rodou o comando. É o que faz
o sino tocar em quem pediu sem cair no anti-eco. Se a casca não estiver registrada em
`config.json`, o `iachat` recusa o post — e aí o aviso cai para stderr com o conserto ao lado,
nunca some.

## Formato que o plano tem que ter

O preâmbulo (1.111 B) exige, nesta ordem: **Objetivo** em uma frase · **O que eu li** com
`arquivo:linha` · **Passos** numerados, cada um com o arquivo que toca e o critério de pronto ·
**Riscos** · **O que eu não sei**.

A seção "O que eu li" é a que dá para conferir: se o plano cita `arquivo:linha`, abra e veja.
Plano sem ancoragem é opinião, e opinião não vira execução.

## Antes de disparar

1. **Modo seco primeiro.** Ele diz de quem é a assinatura que vai queimar. Um turno de plano
   não é grátis para o Bauer — a peça nunca dispara sem `--executar` justamente por isso.
2. **Escolha a casca pelo repositório**, não pelo hábito: quem já tem o contexto daquele código
   devolve plano ancorado; quem não tem devolve plano genérico e você gastou um turno à toa.
3. **Um plano por vez por casca.** Dois disparos concorrentes na mesma assinatura disputam cota.
