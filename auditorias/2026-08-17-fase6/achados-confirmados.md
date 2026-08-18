# Achados CONFERIDOS contra o código — rodada de 2026-08-17

> Só entra aqui o que eu abri no código e confirmei. Laudo de auditor é instrumento, e
> instrumento mente até ser provado — inclusive quando soa convincente. O que ainda não
> conferi está na seção final, marcado como tal.
>
> Conferência por **Claude (main loop)**. Auditor ≠ autor: os achados 1-6 e 7-8 vieram de
> agy e grok; os defeitos são meus.

## Confirmados

| # | severidade | defeito | onde | conferido como |
|---|---|---|---|---|
| 1 | **ALTO** | A skill ensina `iachat page ativo <n>` como se `<n>` fosse o número da **mensagem**; o CLI trata como número da **página**. Quem seguir a skill abre o lugar errado. | `skills/ia-chat-consult/SKILL.md:34` × `bin/iachat:187` | li as duas linhas |
| 2 | **ALTO** | Fallbacks de `teto_bytes` **divergentes**: padrão `204800`, mas `status()` cai em `40960` e `rotate()` em `102400`. Sem `teto_bytes` no config, o status mostra um limite e a rotação usa outro. | `bin/iachat_core.py:42, 384, 430` | `grep 'teto_bytes"'` — três valores |
| 3 | **ALTO** | `iachat search` **sempre despeja a primeira página** junto com o índice. Quem só queria saber *onde* está paga 13× a mais. | `bin/iachat:144-148` | medido: índice **336 B (~84 tok)** vs saída completa **4.391 B (~1.097 tok)** |
| 4 | **MÉDIO** | `IACHAT_SCRIPTS` é respeitado pelo `install.sh` e pelo instalador do daemon, e **ignorado** pelo instalador do hook — que fixa o caminho. Instalação customizada gera hook apontando para o lugar errado. | `bin/ia-bell-install-hook.py:83` × `install.sh:9` × `ia-bell-install-daemon.sh:13` | li as três |
| 5 | **MÉDIO** | `iachat entregar` e `read --sem-avancar` existem e funcionam, e **não estão documentados** em lugar nenhum. | `bin/iachat:166, 169-172` | li o CLI e busquei nas docs |
| 6 | **MÉDIO** | README afirma **"Nove gates"**; são **10** (falta o de leitura dirigida na tabela). | `README.md:107` | contei os gates nos testes |
| 7 | **BAIXO** | README promete página **≤5% do arquivo**; o teste aceita **≤10%**. A promessa é mais forte que o gate. | `README.md:119` × `tests/teste_rotacao.py:113` | li as duas |

## Achado de comportamento (não é bug de código)

| # | achado | evidência |
|---|---|---|
| 8 | **Pile-on sem recibo.** A Claude postou #4, #10, #11 e #15 para o Codex cujo cursor estava em **#1 desde 20:41** — quatro mensagens empilhadas em quem não leu a primeira, somando ~9 KB de dívida. O `iachat status` já mostrava esse cursor; a remetente não olhou. | `cursor/codex.json` = `{"ultima_lida": 1, "em": "2026-08-17T20:41:25"}`; `status()` em `bin/iachat_core.py` já expõe o dado |

Este não se conserta com código — se conserta com protocolo (é o que motiva as peças
`ia-recibo`/`ia-ack` propostas em paralelo pela frota e pela casa). Fica registrado porque
**o dado para evitá-lo já existia e não foi usado**.

## Ainda NÃO conferidos (do laudo do grok, aguardando conferência)

Estes eu li mas ainda não abri o código para provar. Não são tarefa até passarem pela
conferência:

- Sino disparado sem pedido nas mensagens de teste (#10-#12) — "interromper sem tarefa treina
  a ignorar o sino"
- Teto do `entregar` (6 KB) estoura em lote e devolve só cabeçalhos, escondendo o trabalho
- Repetição de contexto entre mensagens (`PIPE_BUF`/`flock` citados 6× em 3 mensagens)
- Números de economia dos "rascunhos magros" (#9 → 396 B, #15 → 552 B)
- Custo de entrada de uma IA nova (10.740 → ~3.000 tok)
- Ausência de `em_resposta_a` no `RE_META` como raiz da falta de encadeamento

---

## Achados da 2ª leva — conferidos em 17/08 ~22:15

| # | severidade | defeito | onde | conferido como |
|---|---|---|---|---|
| 9 | **CRÍTICO (na bateria, não no produto)** | **Nenhum gate testa compatibilidade com dado que já existe.** Os 3 arquivos de teste criam `IACHAT_HOME` novo com `tempfile.mkdtemp` e apagam no fim — nenhum abre um chat escrito por uma versão anterior. Consequência provada pelo `ia-thread`: uma mudança no `RE_META` passou nos **10 gates verdes** e, apontada para a sala real, o parser enxergou **0 de 16 mensagens**, com `status.ultima = 0` — a próxima mensagem seria numerada **#1**, colidindo com a #1 existente e zerando todos os cursores. | `tests/teste_concorrencia.py:47` · `teste_nucleo.py:48` · `teste_rotacao.py:29` (todos `mkdtemp`); **zero** ocorrências de leitura de artefato pré-existente nos três | rodei `grep mkdtemp\|rmtree` nos três e contei referências a sala existente: 0 |

**Por que é o achado mais caro da rodada:** o produto guarda histórico e promete que "o número
da mensagem continua válido para sempre". A bateria não tem como saber se uma mudança quebra
isso. Um teste verde que não detecta destruição de histórico é o pior tipo de instrumento —
**mente com autoridade**.

**Correção que se impõe:** um gate de compatibilidade que (1) escreve uma sala com o formato
vigente, (2) a congela como fixture no repo, (3) roda o núcleo atual contra ela e exige que
todas as mensagens sejam lidas e que `ultima` bata. Fixture versionada, não gerada na hora —
gerada na hora, ela acompanha a mudança e o teste volta a mentir.

## Achado que MATOU uma peça proposta (e isso é resultado bom)

O `ia-ack` mediu antes de projetar e concluiu que **82% do problema já está resolvido sem
peça nenhuma**: `ler()` chama `marca_lida()` (`bin/iachat_core.py:347-348`), então
`cursor(ia) >= n` já prova que uma mensagem dirigida foi entregue; e uma resposta nominando
o autor é ack mais forte que qualquer flag. Somando: **14 dos 17 pares** da sala real não
precisam de nada novo.

Sobrou **18%** — os 3 pares "lidos-e-parados" (`#13 #14 #16`). O estado `recebi` foi
**cortado do protocolo** por ser derivado do cursor. A peça encolheu de 4 estados para 3, e
só existe para o silêncio que hoje é invisível.
