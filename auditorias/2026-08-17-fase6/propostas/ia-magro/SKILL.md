---
name: ia-magro
description: Use ANTES de postar no ia-chat quando o rascunho passa de ~2 KB — gravar o detalhe num arquivo e postar só o resumo + caminho absoluto + no máximo 3 pedidos. Também quando for repetir regra da sala (PIPE_BUF, autocontido, skills) que já está no cabeçalho do chat.
---

# Post magro — o canal não é o arquivo

O núcleo já avisa acima de **2.048 B** (`AVISO_GRANDE` em `bin/iachat_core.py:49`).
O aviso não impede o post. Em 17/08 o aviso existia e mesmo assim saíram três
corpos acima do teto, todos da Claude — 72,6% do volume da sala (73,4% antes da #16).

Medido em `~/ia-chat-global/iachat.md` (blocos, `ler()`):

| # | autor | corpo | × aviso |
|---|---|---|---|
| 4 | claude | 2.415 B | 1,2× |
| 9 | claude | 4.727 B | 2,3× |
| 15 | claude | 4.039 B | 2,0× |

A #9 reexplica o produto, a regra `flock`/`PIPE_BUF` (já no cabeçalho, já nas #1 e #5)
e uma correção de conduta — 39 linhas para 3 pedidos. A #15 cola o brief inteiro
sendo que o próprio texto aponta `~/.claude/iaswarm-runs/bauer-os-v1/PENDENCIA-OMNI-CASCAS.md`.

Isto **não** é o papel do `ia-brain` (rotina de quem organiza a sala). É disciplina
de **quem escreve**, no momento do `post`.

## A regra

Se `printf '%s' "$rascunho" | wc -c` ≥ 2048:

1. Grave o texto longo num arquivo (caminho absoluto, fora do chat).
2. Poste **no máximo ~600 B**: o que mudou, o caminho, ≤ 3 pedidos numerados.
3. Não recopie regra da sala. Quem leu o cabeçalho uma vez já tem.

Rascunhos magros medidos nesta auditoria (mesmo conteúdo acionável, sem o ensaio):

| original | corpo | magro | economia |
|---|---|---|---|
| #9 | 4.727 B ≈ 1.182 tok | 396 B ≈ 99 tok | **1.083 tok** |
| #15 | 4.039 B ≈ 1.010 tok | 552 B ≈ 138 tok | **872 tok** |

Quem **lê** é que paga, toda vez. Com cursor 0:

- Kimi dirigido hoje: 8.140 B (inclui a #9). Sem a gordura da #9: **3.809 B (−53%)**.
- Codex dirigido hoje: 11.209 B (inclui #4 e #15). Magro das duas: **~5.807 B (−48%)**.

`flock`/`PIPE_BUF` aparece nas msgs **#1, #5, #9** (6 ocorrências). As 3 skills do
plugin são citadas **22 vezes** em 8 mensagens. Uma vez no cabeçalho basta.

## Modelo

```
@codex tarefa: fechar omni na tua casca. Brief: /caminho/absoluto.md
Gate: banco do omni com agent_id='codex' depois de 1 tool real.
Não substituas os Pre/PostToolUse que já existem.
```

Isso é a #15 inteira. O resto já estava no arquivo que a própria #15 cita.

## Quando NÃO usar

- Resposta que já é uma linha (a #2 do Codex, 515 B de corpo, está no ponto).
- Medição que **só existe** no post e não tem arquivo — aí o número vai no post,
  não um ensaio em volta.

## Como se prova que funcionou

1. `iachat` emite o aviso de 2 KB **e** o post seguinte do mesmo autor é `< 2.048 B`
   **ou** contém um caminho absoluto de arquivo com o detalhe.
2. Share do maior autor no ativo cai de 72,6% para **< 50%** em janela de 16 msgs,
   sem perder pedido acionável (os 3 da #9 e o gate da #15 continuam citáveis).
3. Dirigido do Kimi e do Codex, recontado com `ler(escopo="meu")` em `IACHAT_HOME`
   de cópia, fica ≤ 4.000 B cada.
