# NOTA — `ia-plan`

## O que resolve

Hoje o `ia-chat` é assíncrono por desenho: uma IA posta, o sino toca, a outra responde quando
ler. Isso é certo para conversa e errado para trabalho — quem pede fica dependendo de a outra
ponta estar viva e disposta.

`ia-plan` inverte: **aciona** uma casca agora, com uma tarefa, e devolve um **plano**. A escolha
de devolver plano e não execução não é timidez, é economia de risco: planejar é barato e
reversível, executar não é. O documento volta, o dono corta o que não presta, e só então alguém
executa — com a vantagem de que quem executa pode ser outra IA, ou ele mesmo.

Sem isso, a alternativa real é o que já acontece: alguém manda "faça X" para uma casca com
`--dangerously-skip-permissions` (é o que o `dispatch.sh:90` e `:97` fazem, corretamente, para
workers de swarm) e descobre o que ela entendeu depois que o disco já mudou.

## O gate — a parte que importa

O briefing pergunta como impedir a IA acionada de implementar por conta própria, dado que o
prompt é frágil. A resposta é não depender do prompt.

Três camadas. As duas primeiras são preventivas e do fornecedor; a terceira é probatória e nossa:

1. **Trava nativa** — `kimi --plan`, `grok --permission-mode plan`, `agy --mode plan`,
   `claude --permission-mode plan`. O motor recusa a ferramenta de escrita.
2. **Sandbox** — `codex exec -s read-only -a never`. O harness recusa a escrita.
3. **Gate do disco** — fotografa `git status --porcelain` + `HEAD` antes do disparo e depois.
   Um byte diferente e o plano vai para `<id>.QUARENTENA.md`: não chega a quem pediu, mesmo que
   o texto esteja excelente.

A camada 3 é a única que vale para **todas** as cascas, inclusive `qwen`, que não tem trava
nenhuma. E é a única que sobrevive a uma atualização silenciosa de CLI: se amanhã o `--plan` do
kimi virar no-op, a trava 1 falha em silêncio e a 3 acusa.

**Isto é a Bronca 2 aplicada ao contrário do usual:** o instrumento aqui não é o meu medidor, é
a *palavra da casca acionada*. Ela diz "não implementei". Instrumento mente até ser provado — e
a prova é o disco, não a frase.

Limitação declarada: o gate cobre o diretório passado em `--repo`. Escrita fora dele
(`~/.config`, `/tmp`, caches da própria casca) **não é detectada**. Não vendo cobertura total.

## Custo — medido nesta máquina, não estimado

**Overhead da peça** (foto antes + foto depois + I/O + post), 3 execuções:
`0,16 s · 0,17 s · 0,19 s`.

**O gate em escala**, `git status --porcelain --no-optional-locks` em `~/Projetos/Tangent`
(34.389 arquivos), 3 execuções: `0,08 s · 0,02 s · 0,02 s`. Em `knowledge-graph` (7.751
arquivos): `0,02 s · 0,00 s · 0,00 s`. O gate é ruído comparado a um turno de LLM.

**O que se gasta de verdade** é 1 turno da assinatura da casca acionada. Por isso o padrão é
**modo seco**: sem `--gastar`, a peça imprime o comando exato, a trava e de quem é a conta, e
sai com 0. Fail-closed em custo — nunca queima a assinatura do Bauer por acidente.

**Prompt injetado:** 1.111 B de preâmbulo + a tarefa.

**Volta pela sala ou por arquivo?** Por arquivo, com ponteiro na sala. Os números:

| item | bytes | fonte |
|---|---|---|
| plano típico da frota | 3.425 · 4.812 · 12.529 | `iaswarm-runs/bauer-os-v1/resultados/*-PLANO.md` |
| teto do `iachat entregar` | 6.144 | `bin/iachat:171` |
| teto da sala | 204.800 | `bin/iachat_core.py:42` |
| mensagem-ponteiro medida | 369 | protótipo, caminho longo de scratchpad |

Postar o plano inteiro perde duas vezes: o de 12.529 B come **6,1% da sala** para sempre **e
nem chega**, porque estoura o teto de 6.144 B do `entregar` e vira só cabeçalho. O ponteiro
custa **0,18% da sala** e cabe na entrega com folga de 16×. Fator ~34× a favor do arquivo.

## Riscos

| risco | mitigação | resta |
|---|---|---|
| Casca escreve fora de `--repo` | — | **não coberto**; declarado acima |
| `--plan` vira no-op numa atualização | gate do disco acusa | nada |
| Casca não registrada em `config.json` → post recusado | aviso cai para stderr com o conserto | quem disparou em background não vê |
| Casca trava e queima o turno | watchdog de 600 s; parcial salvo em `<id>.PARCIAL.md` | o turno já foi gasto |
| Netos da casca sobrevivem ao watchdog | `pkill -P` mata os filhos diretos | netos escapam |
| Plano bonito e vazio | preâmbulo exige `arquivo:linha` em "O que eu li" | conferir é trabalho de quem lê |
| Dois disparos na mesma casca disputam cota | documentado na skill | não há trava técnica |

Três defeitos foram encontrados **pelos testes e pela medição**, não pela leitura, e já estão
corrigidos:

- `set -e` matava o script no timeout **antes da foto de depois** — ou seja, casca que escrevia
  e depois travava passava sem gate. Corrigido com `|| SAIU=$?`; o gate G4 cobre exatamente
  esse caso e agora reprova.
- O `sleep` do watchdog herdava o stdout e **pendurava o processo que chamou** a peça mesmo
  depois de ela terminar. Corrigido com `>/dev/null 2>&1` no subshell.
- **Falso positivo do gate, o pior dos três.** `~/Projetos/ia-chat` não é repositório git
  próprio: `git rev-parse --show-toplevel` de lá devolve `/Users/bauervieiracesarfilhovieira`.
  Sem pathspec, a foto pegava **202 linhas do home inteiro** — qualquer cache que outro
  processo escrevesse durante o disparo reprovaria um plano inocente. Um gate que grita à toa
  é desativado pelo dono na terceira vez, e aí não sobra gate nenhum. Corrigido com
  `status --porcelain -- "$REPO"`: 202 linhas → 1, `0,06 s` → `0,00 s`. Gate G7 cobre.

Nota de plataforma medida: `timeout` e `gtimeout` **não existem** neste macOS (nem coreutils do
brew). O watchdog é feito à mão, casado pelo PID do próprio filho — mesma família de armadilha
do `flock(1)` que já está registrada na decisão de desenho nº 1 do briefing.

## Critério binário

A peça está pronta quando os 7 gates passam. Todos rodados com **cascas falsas** em
`IACHAT_HOME` temporário — nenhuma assinatura foi queimada.

| # | gate | resultado |
|---|---|---|
| G1 | sem `--gastar` não dispara nada e sai 0 | ✅ |
| G2 | casca obediente → plano em arquivo + ponteiro na sala + exit 0 | ✅ 839 B em arquivo, `#1 postada por kimi → @claude` |
| G3 | casca que escreve no disco → exit 3, quarentena, plano **não** entregue | ✅ |
| G4 | casca que escreve **e depois trava** → gate reprova mesmo assim | ✅ |
| G5 | casca que trava → morta no teto, exit 5, parcial salvo, chamador não pendura | ✅ 2 s cravados |
| G6 | casca não registrada na sala → aviso de violação não some | ✅ cai para stderr com o conserto |
| G7 | `--repo` em subpasta de repo maior não gera falso positivo | ✅ |

## O que eu NÃO verifiquei

Digo com todas as letras, porque o contrário seria inventar:

- **Nenhuma casca real foi disparada.** As travas nativas da tabela saíram do `--help` da CLI
  instalada, não de execução. Que `kimi --plan` de fato bloqueie escrita, que `codex -s
  read-only` de fato recuse `apply_patch` — não testei, e o desenho não depende disso: é
  exatamente por isso que o gate do disco existe.
- **`--plan` combinado com `-p` não foi testado** em nenhuma casca. Se alguma delas ignorar a
  flag em modo não-interativo, quem acusa é o gate, não a peça.
- **`qwen -y` é aceito** (`qwen -y --version` → `0.21.12`, exit 0), mas **não está documentado**
  no `--help` desta versão (41 linhas, zero ocorrências de `approval`, `plan` ou `yolo`). O
  `dispatch.sh:33` usa `-y`; a peça não usa, porque aqui auto-aprovar é o oposto do objetivo.

## Se vale a pena

Vale, com uma ressalva honesta: **o valor não está no disparo, está no gate**. Disparar uma
casca com um prompt é uma linha de bash que qualquer um escreve — está no `dispatch.sh` desde
sempre. O que não existe hoje em lugar nenhum desta máquina é a prova de que o que voltou foi
plano e não execução disfarçada. Se a peça fosse cortada até o osso, o que precisa sobreviver é
`foto → dispara → foto → compara → quarentena`, e não a tabela de flags.

## Arquivos

- `SKILL.md` — frontmatter mínimo (`name` + `description`, decisão nº 6 do briefing)
- `bin/ia-plan` — protótipo em bash, 6 gates verdes, sem dependência além de git e bash
