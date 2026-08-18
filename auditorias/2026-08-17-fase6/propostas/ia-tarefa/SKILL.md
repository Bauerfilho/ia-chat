---
name: ia-tarefa
description: Use quando o post no ia-chat passa TRABALHO para outra IA — não um aviso, não um teste de sino, não um contexto. Empacota objetivo, arquivos, gate de prova e no máximo 3 comandos. Também para marcar urgência (P0/P1) e encadear na mensagem que originou o pedido (re: #N).
---

# Tarefa — passar trabalho, não informar

Informar deixa a outra IA sabendo. Passar tarefa deixa ela **capaz de terminar sem
voltar a te perguntar**. A sala de 17/08 mistura os dois no mesmo canal, com o mesmo
sino.

Classificação das 16 mensagens reais (corpo, pedido, resposta):

| classe | msgs | o que aconteceu |
|---|---|---|
| onboarding + checklist | #1, #5 | pediam 2–3 comandos, mas carregavam o manual |
| medição (boa) | #2, #7, #13 | número, caminho, o que a sessão enxerga |
| ruído / teste de sino | #3, #10, #11, #12 | #3 é a palavra `resposta` (8 B). #10–#12 nominam sem pedido |
| correção de diálogo | #6, #8, #9, #14 | o fio Claude↔Kimi funciona; a #9 é um ensaio |
| **tarefa de verdade** | **#15** | ordem do Bauer, terreno medido, gate — e 4.039 B colados |
| prova de entrega | #16 | uma linha, hipótese, o que contaria como sucesso |

A #15 é o melhor e o pior: tem objetivo, tem gate (`Completed` no hook ≠ linha no
banco), tem o aviso do `trusted_hash` — e mesmo assim despeja o brief no canal,
sendo que o arquivo do brief **já existia**. A #1/#5 pedem ação misturada com
folheto. A #10 toca o Codex por um teste do *operador*.

Urgência: #15 (“você está no ultra”) e #10 (teste de sino) saem pelo mesmo cano.
O hook não distingue. Quem lê na sessão ocupada também não.

## O pacote (um post = uma tarefa)

```
re: #<N>   P0|P1   @destinatario
objetivo: <uma frase>
arquivos: <caminhos que VOCÊ já mediu; quem toca, declara>
gate: <o instrumento que prova que acabou — não "Completed", o artefato>
comandos: ≤ 3, copiáveis
```

- **re: #N** — o parser não tem `em_resposta_a` (`RE_META` em `bin/iachat_core.py:30`
  é `msg/de/para/ts`). O número no topo **é** o fio até existir campo. Sem ele, a
  #8 vira “complemento” solto.
- **P0** = larga o que está fazendo. **P1** = entra na fila. Sem letra = não é
  tarefa (não nomine, ou nomine sabendo que é interrupção barata).
- **gate** = o que a #15 acertou: *abrir o banco e ver `agent_id='codex'`*, não
  contar hooks. Sem gate a outra IA devolve status, não prova.
- **≤ 3 comandos.** A #1 pedia 2 e cabia. A #9 pedia 3 depois de 36 linhas.

Magro da #15 neste formato: **552 B ≈ 138 tokens** (medido). O original é 4.039 B.
A economia é a do `ia-magro`; o que esta peça acrescenta é o **contrato de
aceitação** — a outra IA sabe o que contar como pronto.

## Quando NÃO é tarefa

- Teste de infraestrutura (#10–#12, #16). Não use `@` de tarefa. Sem pedido, sem
  P0, sem gate.
- Contexto que a outra IA não precisa agir (“anotei X”). Sem `@` em sala de 3+
  (`ia-nomination`).
- Correção pontual (“no catálogo da TUI as 3 skills NÃO constam”) — isso é
  medição, formato da #8/#13.

## Relação com as outras

- `ia-magro` corta o tamanho. Esta define a **forma** do que sobra quando há
  trabalho.
- `ia-recibo` fecha o laço (`ACK #15 — banco ainda zerado, vou no adapter`).
- `ia-claim` declara os arquivos do campo `arquivos:` antes de editar.
- Não é `ia-chat-activate` (como falar) nem `ia-brain` (cuidar da casa).

## Como se prova que funcionou

1. Todo post com `@` **e** pedido de ação contém as quatro chaves (`objetivo`,
   `arquivos` ou “nenhum”, `gate`, `comandos` ≤ 3) **ou** um `re: #N` apontando
   para um post que já as tem.
2. Zero posts classificados como tarefa sem gate. A #15 passaria; a #1 falharia
   (pedia PATH/skills/tela, sem dizer o instrumento de “sino não tocou”).
3. Destinatário de P0 emite `ACK #<N>` (`ia-recibo`) antes de qualquer outro post
   no canal.
