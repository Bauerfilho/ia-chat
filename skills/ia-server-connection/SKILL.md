---
name: ia-server-connection
description: Use quando aparecer no seu flag do ia-chat um aviso ⚡ energy-bell ou 📡 connection-bell — a energia caiu, a energia voltou, o IP mudou, a conexão com os provedores caiu ou voltou. Ele carrega o contrato do que fazer ANTES de continuar o que você estava fazendo, e a conduta é diferente para cada sino. Também para instalar ou conferir a vigília, ou para entender por que uma oscilação de rede não te acordou.
---

# A vigília da conexão — uma skill, dois sinos, um gatilho

O sino comum avisa que **alguém te chamou**. Este avisa que **o chão saiu do lugar**.

Ele nasceu de duas quedas de energia na madrugada de 18/08. Na segunda, um worker tinha
**123 KB de raciocínio no log e zero byte no disco**. Perdeu tudo. Ninguém o avisou.

## A regra que vale antes de qualquer outra

> **O que não está no disco não existe.**

Ao ver um aviso, o primeiro gesto **nunca** é diagnosticar. É **salvar o parcial**.
Diagnosticar leva minutos; a queda leva segundos.

## Os dois sinos têm nomes diferentes porque a conduta é oposta

### ⚡ `energy-bell` — você tem SEGUNDOS

| aviso | o que fazer, nesta ordem |
|---|---|
| **ENERGIA CAIU** (saiu da tomada) | **1.** Grave agora o que tem, mesmo pela metade, com um cabeçalho dizendo que é parcial. **2.** Só então avalie. O Mac aguenta na bateria — **o roteador não**. |
| **ENERGIA VOLTOU** | Não retome de onde parou: **remapeie primeiro**. Worker pode ter morrido, IP pode ter mudado, servidor pode estar no endereço errado. |

Energia **nunca** é silenciada. Não há tolerância nem contador: mudou, avisa. É o sinal
mais precoce que existe, e os segundos que ele ganha são os que separam "salvei" de
"perdi tudo".

### 📡 `connection-bell` — você tem MINUTOS, e o trabalho local segue

| aviso | o que fazer |
|---|---|
| **CONEXÃO FORA** | **Não redispare nada para fora.** O que roda local segue normal; o que fala com API remota vai morrer. Grave e espere. |
| **CONEXÃO PARCIAL** (LAN sim, provedores não) | A casa está de pé e a nuvem não. **Não conclua que um worker falhou** — ele está sem linha. |
| **CONEXÃO VOLTOU** | Remapeie **contra o disco** e redispare só o que comprovadamente morreu. Log grande sem artefato = morreu sem salvar. |
| **O IP MUDOU** | Toda URL de servidor **virou pó, em silêncio**. Reinicie os servidores e refaça o link do celular. Nada quebra na hora — é por isso que é traiçoeiro. |

### 🔕 `no-bell` — o terceiro grupo, e o mais importante

Detectei, **medi**, e decidi **não** tocar. Uma piscada de Wi-Fi de um ciclo não acorda
ninguém: a conexão precisa falhar **dois ciclos** para virar sino.

Um vigia que toca a cada oscilação vira ruído, e ruído todo mundo aprende a ignorar — aí,
no dia real, ninguém olha. Mas o `no-bell` **fica registrado** em `rede/EVENTOS.md`
justamente para ser auditável: dá para conferir depois se ele calou algo que devia ter
falado.

> **Silêncio medido é decisão. Silêncio não registrado é omissão.**

## O contrato, por papel

**Se você é WORKER de enxame:**
1. Escreva o parcial no seu arquivo de resultado. Sempre. **Antes de pensar.**
2. Depois da volta, **releia o seu próprio parcial** e retome dali — não do zero.
3. Nunca conclua que terminou sem o arquivo no disco.

**Se você é ORQUESTRADORA:**
1. Mapeie contra o **disco**, nunca contra memória ou laudo.
2. O par que decide vivo × morto é **stderr + artefato**: stderr vazio e sem artefato =
   ainda trabalhando, espere. stderr com erro = morreu, redispare. Artefato com tamanho e
   hora = terminou, não importa o que qualquer contador diga.
3. Quem morreu **duas vezes** troca de braço.
4. Se o IP mudou, reinicie os servidores e publique a URL nova.

**Se você está em conversa com o dono:**
Diga o estado em uma linha, com o que foi medido, e siga trabalhando.

## O gatilho é um só, e dispara por dois caminhos

| caminho | quando | por quê |
|---|---|---|
| **batimento** | a cada 20 s | se a energia cai e ninguém tenta conectar, só o batimento percebe |
| **evento** | `ia-server-connection-daemon.sh --gatilho` | quem acabou de falhar ao conectar chama isto e sabe **agora**, não em 20 s |

Os dois caem no mesmo classificador — a decisão é uma só, e é por isso que é **uma skill**.

## Os três sensores

| sensor | comando | por que está aqui |
|---|---|---|
| energia | `pmset -g batt` | **o mais precoce**: sair da tomada avisa antes de tudo quebrar |
| IP | `ipconfig getifaddr en0` | mudança **silenciosa**: nada falha, e toda URL antiga morre |
| conexão | `curl` na API + `ping` | distingue **sem rede** de **provedor fora** — decisões diferentes |

Cada um devolve sempre um valor, inclusive `?` para "não consegui olhar". Esse terceiro
desfecho **nunca** é fundido em "está tudo bem".

## Instalar e conferir

```bash
ia-server-connection-install.sh          # sobe como LaunchAgent
ia-server-connection-install.sh --parar

cat ~/ia-chat-global/rede/EVENTOS.md     # tudo que se moveu, inclusive o que foi calado
cat ~/ia-chat-global/.rede-estado.json   # o estado do último ciclo
```

## Dois limites honestos

**LaunchAgent, não background.** Processo de background do harness morre junto com a
sessão — já custou 2 minutos de cegueira às 01:40 de 17/08. Um vigia que depende de quem
ele vigia não é vigia.

**Não existe push para dentro de uma sessão de CLI já aberta.** O aviso fica no flag
`pendente/<ia>.md` e quem entrega é o hook da casca, no próximo evento da IA. Ou seja:
**uma IA ocupada só vê o aviso na próxima ferramenta que rodar.** É o melhor que a
arquitetura permite — e é melhor que nada, que era o que existia até 18/08.
