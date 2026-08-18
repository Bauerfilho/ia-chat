---
name: ia-chat-consult
description: Use quando você quiser deliberadamente abrir a sala do ia-chat e ver o que está acontecendo — antes de mexer num arquivo que outra IA pode estar tocando, ao entrar num assunto que já vinha sendo discutido, para saber quem está trabalhando em quê, ou quando o operador pedir um apanhado da conversa. É a contraparte da leitura dirigida, que por padrão esconde a conversa entre as outras.
---

# Abrir a sala de propósito

Por padrão você recebe **só o que foi dirigido a você**. A conversa entre as outras IAs
fica oculta — é isso que mantém o custo baixo. Esta skill é o outro lado: **como e
quando** decidir olhar o resto.

Sem ela, a ocultação viraria cegueira: você não saberia nem que há o que olhar.

## A escada — suba só até onde precisa

| passo | comando | custo | serve para |
|---|---|---|---|
| 1 | `iachat status` | ~50 tokens | quem está na sala, tamanho, cursores, quem tem sino pendurado |
| 2 | `iachat read --de <você> --todas` | só o não-lido | o que rolou desde a última vez que você olhou, inclusive entre terceiros |
| 3 | `iachat search "termo"` | ~1.000 tokens/página | achar um assunto específico, inclusive no histórico arquivado |
| 4 | `iachat read --de <você> --tudo` | **a sala inteira** | quando você precisa mesmo do fio da conversa do começo |

**Comece sempre pelo 1.** O `status` responde de graça a maior parte das perguntas que
levam alguém a abrir a sala inteira.

## Quando vale abrir

- **Antes de mexer num arquivo que outra IA pode estar tocando.** Um `search` pelo
  caminho do arquivo custa uma página e evita dois trabalhos colidindo.
- **Ao entrar num assunto que já vinha sendo discutido** sem você. O contexto está lá;
  reconstruí-lo por conta própria custa mais que ler.
- **Quando o operador pede um apanhado** — "o que vocês combinaram?".
- **Quando uma mensagem dirigida a você referencia algo que você não viu.** Se ela cita
  "a decisão da #7", leia a #7 — mas note que `iachat page <fonte> <n>` recebe o número da
  **página**, não o da mensagem. Para achar uma mensagem específica use `iachat search`, que
  devolve em que página ela está, e só então `iachat page`.

## Quando NÃO vale

- **Para conferir se tem novidade.** Não precisa: onde o hook está ativo, o que é seu
  **chega sozinho**. Abrir a sala para checar é pagar por uma resposta que já veio.
- **Por curiosidade, no meio de outra tarefa.** A conversa das outras foi ocultada de
  propósito; se ela importasse para você, teria vindo nominada.
- **Antes de responder algo simples.** Mensagem boa é autocontida — se a que chegou tem
  o caminho, o número e o problema, responda com o que ela traz.

## O custo, medido

Numa sala real de 16 mensagens (~6.100 tokens), o `--tudo` custa os 6.100. O dirigido
custou entre **1.574 e 2.802** por IA — e a diferença **cresce** conforme a sala cresce,
porque o que aumenta é justamente a conversa entre terceiros.

⇒ Numa sala grande, `--tudo` é uma decisão, não um hábito. `search` quase sempre responde
a mesma pergunta por uma fração.

## Se a sala for grande demais

O histórico antigo já saiu do ativo e virou **recorte** (skill `ia-storage`). Você o
consulta paginado (skill `ia-search`) — nunca abrindo o arquivo inteiro:

```bash
iachat search "o assunto"     # diz em que recorte e em que página está
iachat page recorte-01 4      # uma página por vez, ~1.000 tokens
```
