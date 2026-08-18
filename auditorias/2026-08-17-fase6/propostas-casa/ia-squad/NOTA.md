# NOTA — ia-squad

## O que resolve

O `ia-chat` hoje tem 7 skills e nenhuma serve para **comandar** outra IA. Todas tratam do
canal (falar, ser chamado, buscar, arquivar, consultar). Falta a peça de orquestrador: um
jeito de partir uma missão em pedaços, entregar cada pedaço com contrato na janela de quem
já está aberto, saber quem pegou, e fazer alguém que **não** é o autor julgar o resultado.

O que o `ia-squad` adiciona é exatamente isso, e só isso: **contrato, rastreio e juiz** em
cima do canal que já existe. Nenhuma infra paralela — sem daemon novo, sem painel, sem
run-loop, sem processo.

O que ele **não** faz e não deve fazer: abrir IA fechada, re-despachar, armar timeout,
trocar de braço. Isso é `iaswarm` (abrir) ou uma peça de fallback (re-despachar).

---

## Custo medido

Tudo abaixo veio de rodar o protótipo em `IACHAT_HOME` temporário sob `/tmp`, com os **5
contratos reais** deste run (`~/.claude/iaswarm-runs/ia-chat-fase6/contratos/*.md`), não
com texto inventado.

### 1. O contrato real tem 1,9 KB — e é isso que decide arquivo-vs-mensagem

```
$ wc -c ~/.claude/iaswarm-runs/ia-chat-fase6/contratos/*.md
1907 a1-codex.md   1789 a2-kimi.md   1759 a3-grok.md
1966 a4-qwen.md    1550 a5-agy.md    ── Σ 8971 · média 1794
```

O gargalo não é o teto da sala (204.800 B, `bin/iachat_core.py:42`) — 9 KB cabem folgados.
**O gargalo é o teto da entrega:** `iachat entregar` só injeta na janela até **6144 B**
(`bin/iachat:171`); acima disso vira lista de cabeçalhos e **não consome o cursor**
(`bin/iachat:64-69`). Ou seja: o contrato simplesmente **não entra** na sessão.

Medido, acumulando despachos ao mesmo destinatário sem ele ler:

| carga por despacho | N=1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | cabem |
|---|---|---|---|---|---|---|---|---|---|
| **ponteiro** (732 B) | 858 | 1716 | 2574 | 3432 | 4290 | 5148 | 6006 | **6864 ✗** | **7** |
| **contrato inteiro** (1907 B) | 2032 | 4064 | 6096 | **8128 ✗** | | | | | **3** |

⇒ **Contrato é arquivo; a sala leva ponteiro.** Não por elegância — porque com contrato
inteiro o 4º despacho não-lido quebra a entrega automática do 1º junto.

### 2. O que a squad põe na sala

Mesma squad de 5, dois modos, salas limpas:

| | sala (`iachat.md`) | entrega ao @codex |
|---|---|---|
| ponteiro | **5.578 B** | **1.044 B** |
| contrato inteiro | **10.464 B** (1,88×) | **2.135 B** (2,05×) |

Ciclo completo medido (5 despachos + 2 julgamentos) = **7.449 B** de sala = **3,6% do
teto** de 204.800 B. Uma squad inteira não move o ponteiro da rotação.

### 3. Quem paga o quê — a leitura dirigida faz o trabalho todo

Sala de 7.449 B, `avancar=False` (nenhuma medição consumiu cursor):

| quem | papel | `meu` | `--todas` | `--tudo` | ocultas |
|---|---|---|---|---|---|
| grok | worker, 1 despacho | **940 B** | 6.569 | 6.569 | 6 |
| kimi | worker + 1 julgamento | **937 B** | 4.687 | 6.569 | 4 |
| dourada | na sala, **fora da squad** | **0 B** | 6.569 | 6.569 | 7 |

⇒ Um worker paga o próprio despacho (940 B), não a squad (7.449 B). **Quem está na sala e
não é da squad paga zero.** Era a pergunta que decidia se dá para despachar pela sala sem
taxar todo mundo: dá.

### 4. A chamada não custa nada a ninguém

```
$ ia-squad chamada <run>
📋 chamada · run · 22:04:33
   w1             @codex    #1    ENTREGUE       51 B
   w2             @kimi     #2    NÃO-VIU        sino ainda pendurado
   w3             @grok     #3    NÃO-VIU        sino ainda pendurado
   w4             @qwen     #4    ENTREGUE       53 B
   w5             @agy      #5    NÃO-VIU        sino ainda pendurado

⚠️  sem sinal: kimi, grok, agy — sino pendurado é sessão fechada ou hook mudo,
   não é worker preguiçoso. Re-despacho/fallback NÃO é desta peça (ver NOTA.md).
─── stdout da chamada: 528 B · escritas na sala: 0 ───
```

**528 B de stdout, 0 bytes escritos na sala.** É a resposta à pergunta "como saber que um
worker está andando sem poluir a sala": a escada sai do que a sala já publica —
`pendente/<ia>.md` (o sino é o próprio flag, `skills/ia-bell/SKILL.md:19`) e
`cursor/<ia>.json` — mais um `progress/<w>.jsonl` no run-dir. Ninguém posta "estou
trabalhando".

Os 5 estados foram vistos rodando, não desenhados:

```
NÃO-VIU      sino pendurado                       → sessão fechada / hook mudo
PEGOU        cursor em #2                         → leu, não marcou etapa
ANDANDO 2/5  corrida reproduzida                  → jsonl appendado
ENTREGUE     53 B                                 → resultados/<w>.md não-vazio
?            sino sumiu e cursor em #0, atrás de #3 → leu outra coisa e levou o sino
```

### 5. Auditor ≠ autor, e o fail-closed

```
$ ia-squad julgar <run> --de claude
⚖️  w1             julgado por w2             @kimi     msg #6
⚖️  w4             julgado por w5             @agy      msg #7
= sem resultado, não julgados: w2, w3, w5
```

Juiz por anel (+1 no `squad.tsv`), fixado **antes** de existir veredito, gravado em
`juizes.json` **e** posto como mensagem na sala — o registro é público e datado por número
de mensagem. Com 3+ workers ninguém julga quem o julga.

Fail-closed provado:

```
$ ia-squad julgar <run-de-1-worker> --de claude
✗ squad de 1: não há juiz possível. auditor≠autor é inegociável.        exit=1

$ ia-squad despachar <run-com-codex-duplicado> --de claude
✗ mesma IA em dois workers: codex. Um worker por IA.                     exit=1
```

E `julgar` aborta se não houver **nenhum** resultado no disco — julgar o que não existe é
teatro.

### 6. O ponteiro é caro em caminho, não em texto

O mesmo ponteiro custou **816 B** com run-dir de 111 chars e **732 B** com run-dir de 62
chars (`/Users/bauervieiracesarfilhovieira/.claude/ia-squad-runs/fase6`, o caminho de
produção). Os 3 caminhos absolutos são ~55% dos bytes. Overhead de mensagem do núcleo
(metadado + linha de título): **126 B**, constante.

---

## Riscos

| # | risco | evidência | como fica |
|---|---|---|---|
| R1 | **Entrega não é garantida.** O hook só roda em evento de sessão (`bin/ia-bell-hook.sh:19-23`). IA aberta e **parada** não recebe nada. | é o desenho do hook | É a diferença de fundo para o `iaswarm`, que garante que o processo subiu. Rota de desempate existente: o daemon `--operador` avisa o humano, que cutuca a janela. Declarado na skill. |
| R2 | Entrega acima de 6144 B degrada para cabeçalhos | `bin/iachat:64-69` | Mitigado (ponteiro: 7 acumulados vs 3). Não some nada — o cursor não avança —, mas o contrato não entra sozinho. |
| R3 | **O sino é flag, não fila.** `p_pendente(d).write_text` (`bin/iachat_core.py:290`) sobrescreve. | leitura do núcleo | Dois despachos seguidos à mesma IA = um sino só, citando a última mensagem. Não perde mensagem (o cursor entrega as duas), perde precisão do aviso. Por isso: **um worker por IA**, imposto pelo CLI. |
| R4 | O protótipo lê o nº da mensagem parseando o stdout de `iachat post` (`bin/iachat:26`) | acoplamento a formato humano | Escolha consciente: postar pela **porta única** vale mais que um parse robusto. Se `cmd_post` mudar o texto, `ia-squad` quebra alto (sai com erro), não em silêncio. Correção futura: `--json` no `iachat post`. |
| R5 | O `progress/*.jsonl` é **cooperativo** — o worker pode não appendar | igual ao iaswarm (`~/.claude/scripts/iaswarm/dispatch.sh:21-28`) | Aí a chamada mostra `PEGOU` até o resultado aparecer. O gate real é o resultado no disco, nunca a barra. |
| R6 | `--prazo` **não arma timer** | `bin/ia-squad`, `cmd_despachar` | É combinado escrito no ponteiro. Timeout armado seria peça de fallback. |
| R7 | `julgar` não **impede** que o autor escreva o próprio veredito | não há lock por autor no run-dir | O que existe é **rastreabilidade**: a atribuição está em `juizes.json` e numa mensagem pública anterior ao veredito. Conferência é um `iachat search`. Chamar isso de impedimento seria mentir. |

---

## Critério binário

A peça entra se os cinco passarem. Um falhou, não entra.

| gate | critério | medido |
|---|---|---|
| G1 | `despachar` de N workers cria N mensagens, cada uma nominando 1 IA, nenhuma > 1 KB | ✅ 5/5 · 732–816 B |
| G2 | worker paga só o próprio despacho; IA na sala fora da squad paga 0 B | ✅ 940 B / **0 B** |
| G3 | `chamada` distingue os 5 estados escrevendo **0 bytes** na sala | ✅ 528 B stdout, 0 escritas |
| G4 | `julgar` nunca atribui worker à própria IA; aborta com squad de 1 | ✅ exit=1 nos dois |
| G5 | ponteiro cabe no teto de 6144 B com ≥5 despachos acumulados | ✅ 7 (contrato inteiro: 3) |

---

## Fronteira com o iaswarm da casa

Não é redundância: os dois resolvem problemas diferentes, e o teste é uma pergunta só —
**a IA está aberta?**

| | **ia-squad** | **iaswarm** |
|---|---|---|
| o worker é | sessão **já aberta**, com contexto vivo | processo **novo**, headless, stateless |
| quem o cria | ninguém | `dispatch.sh` abre o CLI do braço |
| exige | IA aberta **+ um evento de sessão** | adaptador de CLI (`dispatch.sh:128-135`) |
| custo de cota | o turno que a IA já ia gastar | 1 execução por worker por despacho |
| começou? | **não dá para garantir** | o processo subiu ou o log diz que não |
| rastreio | `chamada`: sino + cursor + jsonl | painel vivo + `watch.sh` por transição |
| a conversa fica | **na sala, pública e auditável** | no run-dir, privada |
| contrato | arquivo + ponteiro na sala | arquivo + ponteiro no prompt (`dispatch.sh:21-28`) |

**Use `iaswarm`** quando a missão é longa e pesada, quando você quer worker frio, quando
precisa da garantia de que começou, ou quando quer o painel por etapa.

**Use `ia-squad`** quando as IAs já estão abertas e ociosas nas janelas, o pedaço é curto
a médio, o **contexto vivo** daquela sessão ajuda mais que um worker frio, o braço não tem
adaptador de CLI mas está num terminal aberto, ou você quer a atribuição de juiz no
registro público.

**Não use `ia-squad`** para trabalho que não pode falhar por falta de resposta. O canal
não garante recepção; o `iaswarm` garante execução. Quando isso importa, empurre.

> Regra curta: **iaswarm empurra, ia-squad chama.**

Os dois deliberadamente compartilham a anatomia do run-dir (contrato por worker, etapas
enumeradas, progresso em JSONL, resultado em arquivo, juiz ≠ autor). Isso é de propósito:
quem lê um lê o outro, e um contrato escrito para um serve no outro sem tradução.

---

## Entrega e integração

```
batch/ia-squad/
├── SKILL.md            frontmatter mínimo (name + description), template de contrato pronto
├── NOTA.md             este arquivo
└── bin/ia-squad        protótipo, 3 comandos, rodado de ponta a ponta em /tmp
```

**Uma dívida declarada:** `SKILL.md` ficou com **6.756 B** e as 7 skills do plugin estão
entre **2.052 e 3.316 B** — é 2× a maior. O excesso é quase todo o template de contrato
(~1,6 KB), que foi pedido "pronto" e é o que faz a skill ser acionável em vez de
descritiva. Já cortei uma versão de 9.107 B. Se o dono quiser voltar à família, a saída é
o template virar `contrato-template.md` ao lado da skill, com a skill citando o caminho —
custa uma ida ao disco no momento de escrever contrato, que é raro.

Para instalar junto com o resto do plugin faltam **2 linhas** em `install.sh`: acrescentar
`"$SRC/bin/ia-squad"` à lista de `cp` (`install.sh:15-16`) e o symlink correspondente
(`install.sh:18`). Não fiz — a regra deste trabalho é não escrever em `~/Projetos/ia-chat`.

Nenhuma IA foi disparada. `~/ia-chat-global` está **intocado** (`find -newermt` vazio).
No repo, `find` acusa mtime novo em `bin/__pycache__` — **não é meu**: são os workers
vivos do run fase6 rodando os testes contra o repo real (`progress/a2-kimi.jsonl` gravou
22:06, `a4-qwen.jsonl` 22:06). O `__pycache__` que o meu protótipo gerou está em
`scratchpad/bench/binz/__pycache__` (22:01), porque o `ia-squad` importa o
`iachat_core.py` que estiver **ao lado dele** e eu rodei sobre uma cópia. `IACHAT_HOME`
apontou sempre para `/tmp` ou para o scratchpad.

## O que não consegui verificar

- **Se a entrega chega mesmo numa casca real.** Todo o ciclo foi exercido com o núcleo do
  `ia-chat` num `IACHAT_HOME` de teste; a ponta que injeta na janela (hook por casca) não
  foi testada porque isso exigiria disparar IA, que o contrato deste trabalho proíbe. O
  risco R1 é, portanto, **argumentado a partir do código do hook**, não medido em sessão viva.
- **O comportamento com sala já grande** (perto dos 204.800 B) e rotação disparando no meio
  de uma squad — a mensagem de despacho vira recorte e o ponteiro na sala some do ativo,
  mas o contrato em disco não. Não reproduzi.
