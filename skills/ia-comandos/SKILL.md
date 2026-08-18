---
name: ia-comandos
description: Use quando o dono da máquina disser /goal, /plan, /concluir, /parar, /quem, /decidi ou /refaz — os comandos dele sobre a sala das IAs e sobre os runs do iaswarm. Também quando precisar abortar uma missão ou um worker de enxame em andamento, saber quem da frota está vivo e há quanto tempo, ressuscitar um worker que caiu de onde ele parou, ou entender por que planejar é coletivo e aplicar é só dele.
---

# Os comandos do dono

> ⚠️ **Se você é uma IA disparando isto, passe `--de <seu-nome>`.** O padrão de `--de` é
> `bauer` porque estes comandos são dele, digitados no terminal dele. Sem terminal e sem
> `--de`, o comando **recusa** em vez de assinar por ele — e faz certo: uma decisão
> assinada por ele que ele não tomou é lida e obedecida por todas as outras IAs da sala.
> `decidi` é o caso mais grave, porque registra decisão que todas obedecem.
>
> ```bash
> iachat-comando goal "..." --de codex        # não `iachat-comando goal "..."`
> ```

Estes não são comandos de IA. São **os comandos dele**, e formam um ciclo fechado:

| ele diz | acontece |
|---|---|
| **`/goal`** | ele explica o objetivo — é o enunciado, ninguém executa nada |
| **`/plan`** | **a frota ativa trabalha junta** e devolve **um plano na sala** |
| **`/concluir`** | autorizado: **pode aplicar** |

O eixo do desenho: **planejar é coletivo e volta para a sala**, onde ele lê, discute e
só então autoriza. Planejar é barato e reversível — N IAs planejando custam N logs num
diretório, e plano ruim se joga fora. Aplicar não volta. Por isso o `plan` dispara a
frota inteira sem pedir licença, e o `concluir` **recusa** enquanto não houver plano no
disco para autorizar: autorizar o vazio é assinar em branco.

## O ciclo, do começo ao fim

```bash
iachat-comando goal "arrumar o sino do codex sem invalidar o trusted_hash"
iachat-comando plan                    # a frota ativa planeja, cada uma no seu ângulo
iachat-comando quem                    # quem está vivo, fazendo o quê, há quanto tempo
iachat-comando plan --colher           # os planos voltam PARA A SALA
iachat-comando concluir --para codex "aplicar só o passo 1"
```

`plan` sem `--ias` despacha **a sala menos o brain** — a orquestradora não se despacha,
ela é quem está rodando o comando. Cada IA recebe um ângulo diferente (implementação,
volume, custo, gate, onde já está escrito) para não pagar N vezes por N planos iguais.
`--seco` mostra quem seria despachado sem gastar nada. `--esperar 600` bloqueia até
entregarem e colhe sozinho.

**O que volta para a sala é resumo + caminho absoluto, nunca o plano inteiro.** A sala
cobra de toda IA que a lê, toda vez.

## `/parar` — o único que ele não conseguia fazer

```bash
iachat-comando parar                   # aborta a missão inteira
iachat-comando parar --ia kimi         # só uma
iachat-comando parar --forte           # SIGKILL, quando o SIGTERM foi ignorado
```

**Mata a árvore, não a casca.** O despacho nasce em sessão própria, então derrubar o
grupo derruba o `codex`/`agy` filho junto. Matar só a casca deixaria o motor rodando —
que foi exatamente a dor de 18/08, quando os processos tiveram que ser caçados a
`pgrep` e `kill` na mão.

**Antes de matar, ele confere de quem é o PID.** Três coisas têm que bater: o número, o
`lstart` (o instante em que aquele processo nasceu, que o sistema não repete) e o
caminho do prompt daquele worker na linha de comando. Divergiu uma, ele **recusa**,
diz qual, e sai com `exit 3` sem tocar em nada:

```
   codex      ⛔ NÃO MATEI — PID 61909 RECICLADO: nasceu em 'Mon Jan  1 00:00:00 2001',
                o worker nasceu em 'Tue Aug 18 01:12:44 2026' — é outro processo
```

Recusar é o desfecho seguro. Um worker que sobrevive custa uma segunda tentativa; um
PID reciclado morto custa o processo de outra pessoa.

**Nunca por `pkill -f`.** `pkill -f codex` casa a linha de comando de quem só
*menciona* o nome — inclusive a própria busca, e qualquer processo com o nome no
`PATH`. Com `exec`, o processo ainda troca de nome no meio do caminho. Aqui o alvo é
sempre o PID gravado no despacho, conferido contra o `ps`.

**SIGTERM é pedido, não ordem.** `bash` esperando em `wait` recebe o sinal e só sai
quando o `wait` retorna — medido: o filho morria e o shell continuava de pé. Então o
comando confere depois de `--espera` (2s) e manda SIGKILL em quem ficou; se ainda
assim restar alguém, ele **diz** em vez de anunciar sucesso.

## Sobre os runs do iaswarm: `--run`

`quem`, `parar` e `refaz` aceitam `--run ~/.claude/iaswarm-runs/<nome>`, que é onde o
enxame de verdade roda. O run é **dado de outro programa**: o `quem` e o `parar` não
escrevem nada lá.

```bash
iachat-comando quem  --run ~/.claude/iaswarm-runs/ia-chat-fase8-pecas
iachat-comando parar --run ~/.claude/iaswarm-runs/ia-chat-fase8-pecas --ia e3-squad
iachat-comando refaz --run ~/.claude/iaswarm-runs/ia-chat-fase8-pecas --ia e3-squad
```

**Três desfechos, nunca dois** — 🟢 vivo · 🔴 morto · 🟡 **não-verificável**. O terceiro
existe porque o `dispatch.sh` grava o PID mas não grava o instante de nascimento, então
a identidade se prova por duas coisas derivadas do disco: o caminho do run tem que
aparecer na linha de comando do processo, e o processo tem que ter nascido **antes** de
o `.pid` ser escrito. Não fechou, é não-verificável — e não-verificável **não se mata**.

O `--run` também denuncia dois enganos que o painel não vê:

- **processo vivo sem `.pid`** — ausência de arquivo não prova morte. Aconteceu:
  `d1-watchdog` rodando sem `.pid` e sem linha no `workers.tsv`;
- **o `state.json` mentindo** — em 18/08 ele dizia `rodando` para seis workers cujos
  PIDs já não existiam no `ps`. O comando põe painel e `ps` lado a lado e nomeia a
  divergência.

**Zumbi não é vivo.** `ps -o pid=` continua listando o defunto até o pai colhê-lo; o
veredito olha `ps -o state=` e trata `Z` como morto.

## `/quem` — a presença

```bash
iachat-comando quem            # tabela legível
iachat-comando quem --json     # para outro programa consumir
```

Cruza três fontes: os workers da missão (vivo? há quanto tempo? qual papel?), o cursor
de cada IA em `cursor/<ia>.json` (quando ela leu a sala pela última vez) e o flag do
sino em `pendente/<ia>.md` (quantos chamados ela ainda não viu).

```
🎯 m2 · planejando · há 4min · arrumar o sino do codex sem quebrar o hash

ia         estado               há   leu a sala  o que está fazendo
🧠claude   ⚪ fora da missão                 há 2min  —
  codex    🟢 pid  61909    há 4min      há 9min  planejando (a implementação) · 1 chamado(s)
  kimi     🔴               há 4min           —  caiu sem entregar — processo já não existe
```

## `/refaz` — ressuscitar de onde parou

```bash
iachat-comando refaz --ia kimi              # redispara o que caiu
iachat-comando refaz --ia kimi --braco grok # troca de braço na retomada
```

Ele lê o que sobrou (o plano parcial, ou a cauda do log) e manda junto no pedido novo:
*"você já tinha escrito isto antes de cair; continue de onde parou, não recomece."* O
parcial vira `<ia>.parcial<N>.md` e não se perde.

**Recusa se a IA ainda está viva** — dois workers escrevendo o mesmo plano é pior do que
um worker travado. `--forcar` para, arquiva o parcial e redispara de propósito.

## `/decidi` — a decisão que todas obedecem

```bash
iachat-comando decidi --de bauer --sobre aplicar \
  --porque "planejar é reversível e aplicar não" \
  "nada é aplicado antes do /concluir"
```

**Delega ao `iachat-decide`**, que já é o registro — duplicar criaria um segundo lugar
onde a mesma decisão pode estar diferente. Valem os gates de lá: `--porque` é
obrigatório, `--revoga D3` mata a antiga com ponteiro para quem a derrubou, e
`iachat-decide decisoes` lista o que está vigente. Ver a skill `ia-decide`.

**E anuncia na sala com a linha `DECIDIDO:`.** Havia dois instrumentos de decisão nesta
casa que não se enxergavam: o `decisoes.md` do `iachat-decide`, e a marca `DECIDIDO:`
dentro de mensagem do chat, que o `iachat-report` lê. Medido em 18/08: a sala real
tinha **cinco** decisões `DECIDIDO:` e o `decisoes.md` **não existia** — o registro
vazio e o que valia de fato só no texto. Um ato do `/decidi` agora alimenta os dois:
registro durável de um lado, relatório do dono do outro.

O dono não está em `na_sala`, então quem posta por ele é a orquestradora, com
`📣 do dono (bauer):` na frente. `--anunciar codex` faz o sino tocar só em quem tem que
obedecer.

## O que sai errado, e o que o comando faz

| situação | resposta |
|---|---|
| `/plan` sem `/goal` | recusa (`exit 2`) — planejaria o quê? |
| `/concluir` sem plano no disco | recusa (`exit 3`) — assinar em branco |
| `/goal` novo com worker vivo | recusa (`exit 3`) — abandonaria quem está rodando |
| `/parar` com PID reciclado ou sem a marca | **recusa e não mata** (`exit 3`) |
| `/parar --run` em worker não-verificável | **recusa e não mata** (`exit 3`) |
| `/refaz` de quem está vivo | recusa (`exit 3`) — dois no mesmo arquivo |
| `/refaz --run` de quem não se prova morto | recusa (`exit 3`) — duplicaria trabalho pago |
| `/refaz` de quem já entregou | recusa (`exit 3`) — apagaria trabalho pronto |
| `/decidi` sem `--porque` | recusa — gate herdado do `iachat-decide` |

`--seco` (no `plan` e no `refaz`) mostra o que aconteceria **sem gastar assinatura e
sem escrever arquivo** — inclusive dentro de um run alheio.

## Onde as coisas ficam

```
~/ia-chat-global/comando/estado.json      a missão corrente: goal, estado, workers, PIDs
~/ia-chat-global/comando/m2/goal.md       o enunciado dele
~/ia-chat-global/comando/m2/planos/*.md   um plano por IA — o artefato
~/ia-chat-global/comando/m2/logs/*.log    o que cada braço cuspiu no caminho
```

`estado` anda por `aberta → planejando → planejada → autorizada`, e `parada` quando ele
aborta. O plano é o arquivo; log não é plano — quem não escreveu o arquivo não entregou.

## Fronteira

Este é o comando **do dono**. Uma IA não roda `/concluir` por conta própria: autorizar é
a única etapa que muda o mundo, e ela é sempre dele. Uma IA pode rodar `quem` e
`decisoes` à vontade, e deve rodar `iachat-decide decisoes` antes de propor qualquer
coisa no plano.
