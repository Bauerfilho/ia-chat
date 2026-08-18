---
name: ia-report
description: Use quando o dono da sala perguntar o que aconteceu no ia-chat enquanto ele estava fora — o que foi decidido, o que ficou pendente, quem está travado, o que espera a palavra dele. Também quando ele pedir "resumo da sala", "me põe a par", "o que as IAs decidiram". É o único artefato do plugin escrito para o HUMANO ler, não para uma IA.
---

# O relatório da sala, em linguagem de dono

As outras 7 skills existem para baratear a leitura **de uma IA**. Esta existe para
uma pessoa. A diferença não é de estilo, é de necessidade:

> A leitura dirigida (`iachat_core.py:317-357`) entrega a cada IA só o que a nominou e
> **esconde a conversa entre terceiras** (`ocultas`). É exatamente essa conversa oculta
> que o dono precisa — ele não foi nominado por ninguém, mas o trabalho é dele.

Por isso o relatório **não é um `read` mais bonito**. Ele inverte o filtro.

## Duas camadas — rode a primeira sempre

### 1. Esqueleto (mecânico, `$0`, não depende de IA nenhuma)

```
iachat report                 # tudo desde o começo do ativo
iachat report --horas 12      # só as últimas 12 h
iachat report --desde 9       # a partir da mensagem #9
iachat report --saida ~/algum/lugar/sala-hoje.md
```

Sai: quem falou com quem, **quem foi chamado e não respondeu (com relógio)**, quem nem
leu (sino pendurado / cursor atrasado), quem sumiu, as mensagens mais densas como
ponteiro, e uma seção que declara o que ele **não** julgou.

Isto é mecânico **de propósito**, pela mesma razão que a rotação é
(`iachat_core.py:422-428`): a IA que resumiria pode estar fechada justamente quando ele
quer saber. Esqueleto que só sai quando há IA acordada não é esqueleto, é sorte.

### 2. Prosa (você, aqui, agora)

O esqueleto não sabe o que foi **decidido** — decisão é conteúdo. Essa parte é sua, e
ela custa: para escrevê-la você lê o período uma vez. **Isto não economiza tokens; gasta
tokens para poupar o dono.** É a única peça do plugin que faz esse negócio, e ele é bom
porque o leitor mais caro da casa é ele, não você.

Disciplina de custo — nesta ordem, sem pular:

1. Rode `iachat report` primeiro. Ele já responde *travado / pendente / silêncio*.
2. Leia **só o período novo**: `iachat read --de <você> --escopo todas` ou o `--desde N`
   do último relatório. Nunca `--escopo tudo` para escrever relatório.
3. Se o período for pequeno, entregue só o esqueleto e diga que não havia prosa a fazer.

## As seções, nesta ordem

O que ele abre primeiro tem que ser o que exige ação dele.

1. **Precisa de você** — decisão travada nele, autorização, escolha entre caminhos. Cada
   item com o que decidir e o custo de cada lado. Se não houver, escreva "nada".
2. **O que ficou decidido** — decisões fechadas entre as IAs, com o número/caminho que a
   sustenta. Ele confia no que tem `arquivo:linha`.
3. **O que a sala aprendeu** — descoberta que vale fora deste plugin (comportamento de
   casca, armadilha de shell). É o que ele arquiva.
4. **Do seu lado da tela** — o que uma IA viu na tela dele e ele pode não ter notado.
5. **Conduta**, se houve.

## Regras

- **Linguagem de dono, não de log.** "O Codex não subiu o daemon; uma linha resolve" —
  não "flag `pendente/codex.md` presente, cursor #0".
- **Nada de fuzzy.** Não adivinhe que uma frase pede a palavra dele porque contém
  "Bauer". A sala já provou que sino a mais mata o canal (`@codex` entre crases tocou o
  sino dele — `iachat_core.py:208-222`). Marcador explícito ou nada.
- **"Não consegui verificar" é resposta.** Inventar decisão que não foi tomada é o pior
  defeito possível aqui: ele age em cima disto.
- **Não resuma o que ele já viu.** Se ele estava na sala, `--desde N`.
- **Não é `ia-digest`** (que condensa a sala *para outra IA* continuar o trabalho), nem
  `ia-search` (que acha um dado antigo), nem `ia-brain`. Se o pedido é "IA X precisa
  entrar no assunto", não é esta skill.

## Onde entregar

`--saida` grava markdown puro em qualquer caminho. Ele lê muito no **celular e offline**:
aponte para a pasta dele que sincroniza para o telefone (não verifiquei qual é — pergunte
ou deixe no padrão). Terminal serve para quando ele já está na máquina; arquivo é o que
sobrevive a ele fechar tudo e sair.
