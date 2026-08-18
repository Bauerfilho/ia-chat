---
name: ia-comandos
description: Use quando o dono da máquina disser /goal, /plan, /concluir, /parar, /quem, /decidi ou /refaz — os comandos dele sobre a sala das IAs. Também quando precisar abortar uma missão em andamento, saber quem da frota está vivo e há quanto tempo, redisparar um worker que caiu, ou entender por que planejar é coletivo e aplicar é só dele.
---

# Os comandos do dono

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

## O que sai errado, e o que o comando faz

| situação | resposta |
|---|---|
| `/plan` sem `/goal` | recusa (`exit 2`) — planejaria o quê? |
| `/concluir` sem plano no disco | recusa (`exit 3`) — assinar em branco |
| `/goal` novo com worker vivo | recusa (`exit 3`) — abandonaria quem está rodando |
| `/parar` com PID reciclado ou sem a marca | **recusa e não mata** (`exit 3`) |
| `/refaz` de quem está vivo | recusa (`exit 3`) — dois no mesmo arquivo |
| `/decidi` sem `--porque` | recusa — gate herdado do `iachat-decide` |

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
