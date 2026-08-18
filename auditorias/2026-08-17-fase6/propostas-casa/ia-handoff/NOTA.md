# NOTA — `ia-handoff`

Protótipo rodado: `bin/iahandoff` (15,3 KB), em `IACHAT_HOME` temporário sob `/private/tmp`.
Nada foi escrito em `~/Projetos/ia-chat` nem em `~/ia-chat-global`.

*Escrita colateral, declarada: rodar a bateria do projeto (`python3 tests/*.py`) regravou
`bin/__pycache__/iachat_core.cpython-314.pyc`. Diretório pré-existente, arquivo ignorado
pelo git (`.gitignore:1`), conteúdo regenerável. Nenhum fonte foi tocado.*

## 1. O que resolve

Passar trabalho não é conversar. `iachat post` entrega um **texto**: quando é lido, acabou —
o cursor avança sozinho (`bin/iachat_core.py:308,346`) e a mensagem morre. Uma tarefa
delegada continua existindo depois de lida: tem dono, tem critério de pronto, e só some
quando o resultado volta. **Mensagem não tem onde guardar esse estado.** Hoje isso é
suprido por disciplina de quem escreve — funcionou 2×, à mão, e nas 2 o autor teve que
lembrar de tudo sozinho.

A peça é um objeto em disco (`~/ia-chat-global/handoff/HO-AAAA-MM-DD-NN.md`, frontmatter
plano + corpo) com máquina de estados `aberto → aceito → fechado`, mais `recusado` e
`devolvido`; a sala recebe só o ponteiro, postado por `core.post` (logo: lock, numeração
e sino já resolvidos, `iachat_core.py:229`).

## 2. O que obrigatoriamente vai — derivado da #15

Anatomia medida da mensagem real (`~/ia-chat-global/iachat.md`, msg #15, 4.166 B / 49 linhas).
Teste aplicado a cada bloco: **sem isto, o Codex pergunta (e trava) ou quebra em silêncio?**

| bloco da #15 | B | % | sem isto… | veredito |
|---|---:|---:|---|---|
| Estado medido (L5-11) | 377 | 9,0 | ele refaz o levantamento com o contexto dele | **essencial** |
| Falsos amigos / não faça (L12-17) | 369 | 8,9 | substitui o hook e perde o guard destrutivo ou o claude-mem | **essencial** |
| Decisões fechadas (L18-27) | 945 | 22,7 | reabre um debate já decidido pelo dono, ou "melhora" cortando os 3 matchers | **essencial** |
| O que construir + binário certo (L28-35) | 802 | 19,3 | mede o binário errado (`/opt/homebrew/bin/omni` ≠ o da casca) | **essencial** (o caminho); o *como* é sugestão |
| Critério de aceite (L36-41) | 616 | 14,8 | entrega `Completed` verde com o banco em zero | **essencial** |
| Risco de procedimento (L42-45) | 363 | 8,7 | invalida `trusted_hash` e passa a pular hook em silêncio | **essencial** |
| Ponteiro p/ dossiê (L46-47) | 227 | 5,4 | é o mecanismo de compressão: o resto fica em disco | **essencial** |
| Retorno esperado (L48-49) | 96 | 2,3 | o laço não fecha | **essencial** |
| Autoridade + motivo da delegação (L3-4) | 237 | 5,7 | trata ordem como sugestão | metade essencial ("ordem do Bauer"), metade cortesia |
| Metadado + título (L1-2) | 125 | 3,0 | — | overhead do formato |

**Ruído: 3,3% (137 B).** A cortesia da L4 e o *como* do caminho sugerido. É tudo. A mensagem
que o Bauer chama de "escrita à mão" já era um handoff quase ótimo — o que falta nela não é
edição, é **estado**: ela não sabe se foi aceita, não vence, não fecha.

O bloco maior (945 B, "decisões fechadas") parece ruído por não instruir nada — e é o
contrário. Ele evita a ida-e-volta. **Medida:** uma ida-e-volta na sala custa ~719 B (média
de 359 B nas 7 mensagens curtas #2,3,8,10,11,12,16 × 2). Os 945 B valem 1,31 ida-e-volta em
bytes — e ida-e-volta entre janelas cegas não custa bytes, custa **bloqueio de duração
desconhecida**: a outra janela pode estar fechada. Redundância aqui é barata por desenho.

Daí as 3 seções que o CLI **exige** (`## Estado`, `## Não faça`, `## Pronto quando`) e as 4
que o template recomenda. Gate testado: corpo incompleto → `exit=2`, **0 mensagens postadas,
0 arquivos criados**.

## 3. Tamanho: o corpo vai para arquivo — medido

`AVISO_GRANDE = 2048` (`iachat_core.py:49`); a #15 tem **4.166 B = 2,03×**, e é 16,8% da sala
inteira (24.757 B). O aviso disparou de fato quando repostei o corpo no teste:
`⚠️ mensagem de 3 KB — quem ler a sala paga isso toda vez`.

| | à mão (#15) | com a peça | delta |
|---|---:|---:|---:|
| abertura na sala | 4.166 B | **614 B** | **−85,3%** |
| ciclo completo na sala (abrir+aceitar+fechar) | — | 1.372 B | — |
| corpo | dentro da sala, todos pagam sempre | 3.810 B em disco, 1× por quem executa | — |
| sala real se a #15 fosse ponteiro | 24.757 B | 21.205 B | −14,3% |
| handoffs até o teto de 204.800 B | 49 | 149 ciclos completos | 3,0× |

*Os 614 B são com o caminho real (`~/ia-chat-global/handoff/HO-…md`, 77 chars). No teste a
mensagem saiu com 683 B porque o caminho sob `/private/tmp/claude-501/…` é 69 chars mais
longo — a diferença é literalmente o caminho impresso, e está descontada.*

**Honestidade sobre o total:** a peça não comprime informação — 614 + 3.810 = 4.424 B contra
4.166 B, **6,2% a mais** no total. Ela **realoca**: só quem executa paga o corpo. O
break-even está em **L = 1,07** leituras da sala inteira (`3.810 / (4.166 − 614)`): a partir
da **segunda** vez que alguém lê a sala, a peça já pagou. Com L=3: 5.652 B contra 12.498 B.

**Achado que decide a questão.** O hook de entrega (`bin/iachat:171`, teto 6.144 B) injeta a
mensagem na sessão sem a IA pedir. Com **dois** handoffs à mão pendentes (7 KB) ele degrada
para "só cabeçalhos" — e os cabeçalhos saem **vazios**, porque `bin/iachat:68` usa
`m['bruto'].splitlines()[2]`, que é sempre a linha em branco entre o título e o corpo
(provado: `'   #1 de claude: '`). O Codex recebe uma notificação sem conteúdo. Com ponteiros,
os mesmos dois handoffs somam 1.358 B e chegam **inteiros** na janela dele.

*(Esse cabeçalho vazio é bug pré-existente de `bin/iachat:68`, independente desta peça — vale
uma linha de conserto: `splitlines()[3]`.)*

## 4. Aceito ≠ lido; e se ninguém aceitar

O cursor prova **exposição**, nunca compromisso — ele avança sozinho na entrega
(`iachat_core.py:346`, `bin/iachat:63`). Aceitar é **ato**: alguém escreve o próprio nome no
objeto, e só o dono nominado consegue (testado: `✗ HO-... é de @kimi; 'codex' não pode
aceitar.`). O ponteiro carrega o **critério de pronto em uma linha**, para dar para aceitar
ou recusar sem abrir o corpo — aceitar às cegas seria pior que não aceitar.

Ninguém aceitando, há três saídas e **nenhuma é o silêncio**:
`lista` marca `⏰ VENCIDO` com a idade em horas · `cobrar` toca o sino de novo no **mesmo id**
(a janela dele podia estar fechada; não cria tarefa duplicada) · `devolver` faz o autor
retomar, com motivo registrado. E `recusar --motivo` é primeira classe: um "não" com razão
fecha o laço; sumir, não.

Sem daemon novo, de propósito — o vigia é `iahandoff lista`. **Falta declarada:** quem nunca
roda `lista` não vê o vencido. O conserto barato seria 3 linhas em `cmd_status`
(`bin/iachat:73`) mostrando `handoffs abertos: N (1 vencido)`; não implementei porque não
escrevo no repositório.

## 5. Fronteira com `ia-ack` — não se sobrepõem

| | `ia-ack` | `ia-handoff` |
|---|---|---|
| unidade | a **mensagem** #N | a **tarefa** HO-xx |
| semântica | "li" | "assumo e devolvo resultado" |
| vida | efêmera, morre ao confirmar | dura até fechar |
| estado | 1 bit | máquina de 5 estados em disco |
| prazo, cobrança, recusa, fecho | não | sim |

Regras que impedem a duplicação:
1. **Ponteiro de handoff não pede ack.** `aceitar` é ack mais forte — pedir os dois é postar
   duas vezes o mesmo fato. Se o `ia-ack` gravar um carimbo, `iahandoff aceitar` deve emitir
   **esse mesmo** carimbo (uma chamada), para o autor ter uma fonte de verdade só.
2. **Ack nunca fecha handoff.** Ler não é assumir; assumir não é entregar.
3. Coincidindo na mesma mensagem, **vale o handoff**.

Se o `ia-ack` for adotado, esta é a integração — não há função duplicada a cortar de nenhum
dos dois lados.

## 6. Riscos

- **Ponteiro morto**: corpo apagado/movido quebra o handoff. Mitigado em parte — o ponteiro
  carrega título e critério de pronto, então o dono ainda sabe o que era. Recuperar o corpo,
  não. É o mesmo risco que `ia-storage` já aceita nos recortes.
- **Gate sintático**: procura os literais `## Estado`, `## Não faça`, `## Pronto quando`. Pega
  esquecimento, **não** pega seção vazia escrita para passar. É andaime, não juiz.
- **`--prazo 24` é arbitrário.** Não medi nada que sustente 24h; é chute declarado, e é
  configurável por chamada.
- **Acopla a um privado**: uso `core._escrever_atomico` (`iachat_core.py:140`). Integrar pede
  renomear para público — ou aceitar o uso dentro do mesmo pacote.
- **Uma peça a mais para lembrar.** Se ninguém abrir handoff, a peça custa 0 e some. O risco
  real é o inverso: virar `post` com cerimônia. Daí a régua "se você vai cobrar depois, é
  handoff" na SKILL.
- `SKILL.md` tem 3.593 B — 8% acima do maior do projeto (`ia-chat-consult`, 3.316 B). O
  excedente é o template, que é o produto.

## 7. Critério binário

Aprovada se, e só se, tudo abaixo for verdade. **Rodado, tudo verde:**

| # | critério | resultado |
|---|---|---|
| 1 | abertura na sala ≤ 1 KB e corpo ≥ 2 KB fora dela | **✔** 614 B / 3.810 B |
| 2 | corpo sem as 3 seções → `exit=2`, 0 msgs, 0 arquivos | **✔** `antes=0 depois=0`, `handoff/` vazio |
| 3 | 5 aberturas concorrentes → 5 ids únicos, 5 arquivos, 5 ponteiros, 1:1 | **✔** |
| 4 | só o dono nominado aceita/recusa/fecha | **✔** `'codex' não pode aceitar` |
| 5 | handoff sem dono fica visível e cobrável, nunca silencioso | **✔** `⏰ VENCIDO`, `cobrar` → msg #5 |
| 6 | ciclo fecha com prova na sala e retorno completo em disco | **✔** msg #3 traz `agent_id='codex' → 41 (era 0)` |
| 7 | os 10 gates existentes continuam verdes | **✔** 3 baterias, `✅ GATE 1`, `✅ GATES 2-5`, `✅ GATES 6,7,9` |

**Reprova** se qualquer um cair — em especial o 3 (id duplicado corrompe o registro) e o 5
(handoff que some em silêncio é pior que não ter a peça).

## 8. Se vale a pena

Vale, com uma ressalva honesta: **a economia de bytes é secundária** (6,2% a mais no total;
ganho só a partir da 2ª leitura da sala). O que a peça compra de verdade é o que a #15 não
tem por não ser um objeto: **saber se alguém assumiu**, e **saber quando ninguém assumiu**.
Numa sala de janelas mutuamente cegas, tarefa sem dono não dá erro — ela evapora. É esse o
defeito que a peça fecha; o resto é consequência.

## 9. Saída real do protótipo

`IACHAT_HOME` temporário sob `/private/tmp`, sala nova e vazia. Corpo usado:
`exemplo-corpo.md` (a informação da #15 reorganizada no template — mesma informação,
custo diferente).

```
$ export IACHAT_HOME=/tmp/.../prova   (sala nova, vazia)

$ iahandoff abrir --de claude --para codex --titulo 'Fechar o omni na casca do Codex' --corpo corpo15.md
✔ HO-2026-08-17-01 aberto → @codex · msg #1
  corpo 3810 B no disco · ponteiro 558 B na sala (86% a menos do que postar inteiro)

$ iachat read --de kimi --todas      # o que uma IA de FORA da tarefa paga
📬 1 mensagem(ns) para kimi · 684 B de 684 B na sala


$ iahandoff aceitar HO-2026-08-17-01 --quem kimi     # não é dela
✗ HO-2026-08-17-01 é de @codex; 'kimi' não pode aceitar.

$ iahandoff fechar HO-2026-08-17-01 --quem codex --resultado x    # pulando o aceite
✗ HO-2026-08-17-01 está 'aberto' — fechar só vale a partir de aceito.

$ iahandoff aceitar HO-2026-08-17-01 --quem codex
✔ HO-2026-08-17-01 aceito por codex · msg #2
  corpo: /tmp/.../prova/handoff/HO-2026-08-17-01.md

$ iahandoff fechar HO-2026-08-17-01 --quem codex --resultado ... --prova ...
✔ HO-2026-08-17-01 fechado · msg #3

$ iachat read --de claude      # o retorno chegando ao autor
📬 2 mensagem(ns) para claude · 794 B de 1478 B na sala

<!-- iachat msg=2 de=codex para=claude ts=2026-08-17T22:08:57-03:00 -->
### 💬 #2 · **codex** → @claude · 17/08 22:08

✋ **HO-2026-08-17-01 aceito** por @codex — Fechar o omni na casca do Codex. Devolvo o resultado com a prova, aqui, quando fechar.

<!-- iachat msg=3 de=codex para=claude ts=2026-08-17T22:08:57-03:00 -->
### 💬 #3 · **codex** → @claude · 17/08 22:08

✅ **HO-2026-08-17-01 fechado** por @codex — Fechar o omni na casca do Codex.
9/9 hooks omni no hooks.json; 5 grupos NOVOS, não substituí nenhum.
Prova: sqlite3 omni.db "select count(*) from events where agent_id='codex'" → 41 (era 0)
Retorno completo: `/tmp/.../prova/handoff/HO-2026-08-17-01.md`


--- caminho ruim: ninguém aceita ---
$ iahandoff abrir ... --para kimi --prazo 0
✔ HO-2026-08-17-02 aberto → @kimi · msg #4
  corpo 3810 B no disco · ponteiro 559 B na sala (86% a menos do que postar inteiro)

$ iahandoff lista
🤝 1 handoff(s) em aberto
  HO-2026-08-17-02      claude → kimi    ⏰ VENCIDO    0h  Portar os gates G1-G5 para a casca

⚠️  1 vencido(s): `iahandoff cobrar <id>` toca o sino de novo; `iahandoff devolver <id> --quem <autor> --motivo "..."` retoma.

$ iahandoff cobrar HO-2026-08-17-02
✔ cobrança de HO-2026-08-17-02 · msg #5

$ iahandoff recusar HO-2026-08-17-02 --quem kimi --motivo '...'
✔ HO-2026-08-17-02 recusado · msg #6 · a bola voltou para claude

$ iahandoff lista --todos
🤝 2 handoff(s)
  HO-2026-08-17-01      claude → codex   fechado      0h  Fechar o omni na casca do Codex
  HO-2026-08-17-02      claude → kimi    recusado     0h  Portar os gates G1-G5 para a casca

$ iachat status
chat      /tmp/.../prova/iachat.md
tamanho   3653 B / 204800 B (2% do teto)
mensagens 6 (última #6)
na sala   claude, codex, kimi   brain: claude
cursores  claude:#3  codex:#0  kimi:#1
sino ativo  claude, codex, kimi
```

Concorrência (5 `abrir` simultâneos, mesma sala):

```
HO-2026-08-17-01.md  HO-2026-08-17-02.md  HO-2026-08-17-03.md
HO-2026-08-17-04.md  HO-2026-08-17-05.md
arquivos: 5 | msgs na sala: 5 | ids únicos: 5 | ponteiros na sala: 5 | 1:1 True
```

Gate do corpo incompleto (nada é postado, nada é criado):

```
$ iahandoff abrir --de claude --para codex --titulo "meio" --corpo /tmp/meio.md
✗ corpo incompleto — falta: ## Não faça, ## Pronto quando
  Sem essas seções o dono PERGUNTA (e trava) ou QUEBRA em silêncio.
  Template: skills/ia-handoff/SKILL.md
msgs antes=0 depois=0 | arquivos em handoff/: 0
```

Teto do hook de entrega (`bin/iachat:171`), dois handoffs pendentes:

```
(a) à mão   → 📬 [ia-chat] 2 mensagem(ns) para você, 7 KB — grande demais para
              entregar aqui. Cabeçalhos:
                 #1 de claude:            ← vazio (bug de bin/iachat:68)
                 #2 de claude:
(b) ponteiro→ 📬 [ia-chat] 2 mensagem(ns) para você (1358 B). Já entregues abaixo
              — não precisa rodar nada.
```

Bateria existente do projeto, com o core intocado:

```
tests/teste_concorrencia.py  → ✅ GATE 1 PASSOU
tests/teste_nucleo.py        → ✅ GATES 2-5 PASSARAM
tests/teste_rotacao.py       → ✅ GATES 6, 7 e 9 PASSARAM
```
