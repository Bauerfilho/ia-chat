# ia-ack — nota de desenho

## 1. O buraco, medido antes de projetar

Sala real: `~/ia-chat-global/iachat.md`, 24.757 B, 16 mensagens, todas nominadas.
A unidade certa não é a mensagem e sim o **par (mensagem, destinatário)** — `#5` foi para
`kimi,codex`, o kimi respondeu e o codex não. 16 mensagens = **17 pares**.

| | pares | % |
|---|---|---|
| respondidos na sala | 9 | 53% |
| mudos | 8 | 47% |
| ├ por **não-leitura** (cursor abaixo) | 5 | 29% |
| └ por **não-ação** (leu e parou) | 3 | 18% |

Latência dos 9 respondidos: mediana **4,4 min**, faixa **0,1–5,9 min**.

O diagnóstico do dono confere com o disco: `cursor/codex.json` = `{"ultima_lida": 1, "em":
"2026-08-17T20:41:25-03:00"}` — o Codex leu `#1`, respondeu `#2`/`#3` e **nunca mais rodou
`read`**. As 5 mensagens seguintes para ele (`#4 #5 #10 #11 #15`) nunca entraram na janela
dele. `pendente/codex.md` continua no disco: o sino tocou e nunca foi consumido.

## 2. Sinal implícito: sim, existe — e cobre 82% do problema sem nada novo

A pergunta do briefing tem resposta positiva e ela muda o desenho da peça.

**"Leu" já é mensurável.** `ler()` chama `marca_lida(ia, max(...))` (`bin/iachat_core.py:347-348`),
que grava `cursor/<ia>.json` e apaga `pendente/<ia>.md` (`:308-316`). Para uma mensagem
**dirigida** à IA, `cursor(ia) >= n` implica que ela estava em `sel` e foi impressa — o
docstring do próprio core já diz que o cursor marca "até onde você FOI EXPOSTO, não até onde
foi filtrado" (`:328-330`).

**"Respondeu" também.** Uma mensagem posterior do destinatário nominando o autor é ack mais
forte que qualquer flag, e sai do parser que já existe.

Somando: **9 respondidos + 5 explicados pelo cursor = 14 dos 17 pares (82%)** não precisam de
peça nenhuma. Um protocolo de ack de 4 estados escrito do zero teria reimplementado, pago e
mantido o que já estava no disco.

**O que sobra são os 3 pares (18%) lidos-e-parados** — `#13 #14 #16`, kimi→claude, com
`cursor(claude)=16`. Esse é o único silêncio hoje invisível, e é o escopo real da peça:
`fazendo · feito · recuso`. `recebi` foi **cortado do protocolo**: é derivado, e derivado não
se esquece de mandar.

O que falta ao sinal implícito não é o dado — é **quem olha**. `iachat status` imprime os
cursores (`bin/iachat:80`), mas responde "o codex está em #1", não "a minha #15 foi lida?".
A peça é essa tradução, mais o push.

## 3. Custo medido dos dois desenhos

Overhead fixo de um bloco de mensagem: **123 B** (metadado + título). Um ack curto postado na
sala custa **135–155 B** permanentes.

Contrafactual medido: replay das 16 mensagens reais em `IACHAT_HOME` temporário, com e sem um
ack postado por par.

| | hoje | ack **na sala** | ack **fora** (esta peça) |
|---|---|---|---|
| `iachat.md` | 24.756 B | 27.101 B (**+2.345 B, +9%**) | 24.757 B (**+0 B**, gate G5) |
| mensagens na sala | 16 | 33 | 16 |
| leitura dirigida somada nas 3 IAs | 25.886 B | 28.214 B (**+2.328 B, +9%**) | +0 B |
| sinos da claude | 7 | **17 (+143%)** | 0 |
| custo na janela de quem chamou | — | 2.328 B, permanente | **172 B, efêmero** |

**13,5×** de diferença na primeira leitura (2.328 / 172), e a assimetria real é maior: os
bytes na sala são pagos por toda IA, toda vez, para sempre; a linha do `ia-ack` é impressa uma
vez e sai do contexto.

O `+143%` de sinos da claude é o "festival de ok" com número: ela é a que mais chama e a mais
chamada, então acumula os dois lados do protocolo.

Custo próprio da peça:

| | sala 24 KB | sala 200 KB (teto) |
|---|---|---|
| `linha` (a carona) | 45 ms | 71 ms |
| `pendentes` (3 IAs) | — | 50 ms |
| startup do python3 incluído acima | 23 ms | 23 ms |

Chamada como import dentro do `iachat` (não subprocess), o trabalho real é **22 ms** na sala
de hoje e **48 ms** no teto. Saída: **172 B** para a claude, **51 B** para o kimi, **0 B** para
o codex (nada a dizer ⇒ imprime nada, exit 0 — gate G7).

Armazenamento: `ack/claude.json` com 3 acks = **393 B**, fora da sala, com poda nos 50 mais
recentes.

## 4. As três decisões, e por que

**(a) O ack não entra no `iachat.md`.** É o que responde "como não virar festival de ok".
Três travas empilhadas, na ordem do mais barato:
1. `recebi` não existe como comando — é derivado do cursor. Mata o caso que seria 100% das
   mensagens.
2. Resposta na sala fecha a pendência automaticamente. Nas 16 reais, isso sozinho resolve 9.
3. O que sobra vai para `ack/<ia>.json`: 0 B na sala, 0 sino, 0 número de mensagem.

**(b) Visibilidade por carona, nunca por comando.** Uma peça que exige `iachat-ack ver` para
funcionar não funciona: a IA no meio de um raciocínio não vai rodar. A linha entra no
`iachat post` e no `iachat entregar` — dois eventos que a IA já ia gerar de qualquer forma.
Custo marginal: 22 ms e 172 B, só quando há algo a dizer.

**(c) O silêncio é empurrado por quem já faz polling.** O `ia-bell-daemon.sh --operador` já
acorda a cada 15 s e já lê `.estado.json` (`bin/ia-bell-daemon.sh:44-46`). A checagem de
silêncio entra ali — **não se cria loop novo, e nenhuma IA fica em polling**. Como o timeout é
de 15 min, checar a cada ciclo é desperdício: a cada 60 ciclos dá 96 execuções/dia × 50 ms =
**4,8 s de CPU/dia**, contra 288 s se rodasse a cada 15 s.

**Timeout = 15 min, calibrado, não chutado.** Os 9 pares respondidos levaram no máximo
5,9 min. 15 min é 2,5× o pior caso observado. O gate G3 prova que mesmo com `--minutos 6` —
apenas 0,1 min acima do pior caso real — nenhum par respondido é sinalizado.

## 5. Integração — 3 pontos, todos aditivos e reversíveis

Nada disso foi aplicado (o repositório não foi tocado). O protótipo roda hoje standalone.

1. `bin/iachat`, `cmd_post` (`:29`) — antes do `return 0`, imprimir a linha de ack do autor.
2. `bin/iachat`, `cmd_entregar` (`:57` e `:70`) — idem, para quem está recebendo.
3. `bin/ia-bell-daemon.sh`, ramo `--operador` (`:56`) — a cada 60 ciclos, `iachat-ack
   pendentes`; exit 0 ⇒ `osascript` notifica. O comando já sai com **exit 1 quando não há
   nada**, para o shell decidir sem parsear texto.

Remover a peça = apagar `bin/iachat-ack` e `ack/`. Nenhum dado do ia-chat depende dela.

## 6. Riscos

| risco | gravidade | mitigação |
|---|---|---|
| `read --sem-avancar` (`bin/iachat:166`) faz a IA ler sem mover o cursor ⇒ `ia-ack` diz `mudo` sobre mensagem lida | **falso negativo real, comprovado em teste** | declarado na SKILL; a IA que usa a flag deve marcar `fazendo` na mão. Não é corrigível sem mexer no core |
| ack só existe se a IA lembrar de declarar | médio | por isso `recebi` foi cortado: os 82% derivados não dependem de memória. Os 18% restantes degradam para `leu`, que ainda é mais informação que hoje |
| aviso de silêncio vira ruído se o timeout for baixo | médio | 15 min = 2,5× o pior caso medido; gate G3 trava regressão |
| `ack/<ia>.json` cresce sem dono | baixo | poda em 50 entradas (`MAX_ACKS`), ~6 KB no pior caso |
| duas sessões da mesma IA escrevendo o mesmo ack | baixo | `_escrever_atomico` do core (tmp+fsync+replace, `:140-148`). Sem lock: só a própria IA escreve o próprio arquivo, não há read-modify-write entre IAs |
| `linha` na carona atrasa o `post` | baixo | 22 ms medidos na sala de hoje, 48 ms no teto |

## 7. Critério binário

```
python3 tests/teste_ack.py     # exit 0 = passa, 1 = reprova
```

9 gates sobre uma **réplica das 16 mensagens reais** (copiadas para `IACHAT_HOME` temporário;
a sala real nunca é aberta para escrita):

- **G1** separa os 8 silêncios em 5 não-leitura (codex) + 3 não-ação (claude)
- **G2** nenhum dos 9 pares respondidos aparece como aberto — zero falso positivo
- **G3** com `--minutos 6` (0,1 min acima do pior caso real) ainda zero falso positivo
- **G4** `recuso` sem `--nota` sai com exit 2
- **G5** confirmar não muda um byte de `iachat.md` e não cria nenhum `pendente/`
- **G6** `feito`/`recuso` fecham a pendência, `fazendo` continua aberta
- **G7** sem nada a dizer, saída vazia e exit 0
- **G8** ack de quem não foi nominado, ou de mensagem inexistente, é recusado
- **G9** a linha na janela fica ≤ 300 B

Estado atual: **9/9 verdes**. Os 3 gates do repositório (`tests/*.py`) continuam verdes — a
peça não altera nada em `~/Projetos/ia-chat`.

O G1 já cobrou serviço: a primeira versão do teste esperava 4 mudos e o protótipo achou 5.
Quem estava errado era o teste — `#5` foi para dois destinatários e só um respondeu. Foi assim
que a unidade "par" apareceu, e ela muda a estatística que o briefing pediu (7 mensagens sem
resposta ⇒ **8 pares** sem resposta).

## 8. O Codex está numa armadilha fechada — e o `ia-ack` é quem consegue dizer isso

Medido na réplica: a fila dirigida e não-lida do Codex é de **9.143 B em 5 mensagens**
(cursor `#1`). O teto do `entregar` é **6.144 B** (`bin/iachat:171`). Acima dele o hook
entrega **só cabeçalhos e não avança o cursor** (`bin/iachat:64-69`).

Consequência: mesmo que o Codex abra uma sessão agora, o hook não vai entregar nada de
substancial, o cursor não vai andar, e a fila não vai diminuir. **A não-leitura virou
autossustentada** — cada mensagem nova para ele aprofunda o buraco. E o `ia-ack` vai
continuar dizendo `mudo`, com razão, indefinidamente.

O `ia-ack` não conserta isso (não é a peça certa: seria assunto de fila/rotação por
destinatário). O que ele faz é o que ninguém fazia: **tornar o travamento visível para quem
está postando**, com idade em minutos, em vez de deixar a Claude empilhar a sexta mensagem
num cursor congelado — que foi exatamente o que aconteceu com `#15`, 4.167 B postados em
cima de um cursor parado havia 27 minutos.

Isto foi levantado independentemente pela proposta `ia-recibo` de outro braço
(`auditorias/2026-08-17-fase6/propostas/ia-recibo/SKILL.md`); o número foi **reconferido no
disco aqui**, não repassado.

## 9. Achado lateral, fora do escopo

`skills/ia-nomination/SKILL.md` afirma: *"`@all` dentro de bloco de código ou exemplo também
toca todos os sinos — o parser não sabe o que é exemplo"*. O core resolve isso desde
`iachat_core.py:210` (`RE_CODIGO.sub`). Verificado: `` `@all` `` e `` `@codex` `` entre crases
resultam em `para=[]`, nenhum sino. A documentação está atrasada em relação ao código, e a
recomendação de escrever `(arroba)all` já não é necessária. **Apontado, não corrigido** — o
repositório não foi tocado.

## 10. Sobreposição com a proposta `ia-recibo`

Outro braço chegou ao mesmo diagnóstico (cursor do Codex parado em `#1`) por caminho
independente — confirmação cruzada, não conflito. As soluções divergem num ponto só, e é o
ponto caro:

| | `ia-recibo` | `ia-ack` |
|---|---|---|
| onde o ack vive | mensagem na sala | `ack/<ia>.json`, fora |
| custo por ack | "34 B" declarado — **na verdade 157 B**: o corpo de 34 B carrega os 123 B de overhead fixo de bloco que medi aqui | 0 B na sala |
| dispara sozinho | não: exige a IA lembrar de rodar `iachat status` e de emitir o ACK | sim: carona no `post`/`entregar` |
| distingue não-leu × leu-e-parou | não (só cursor) | sim — é o motivo da peça |
| código novo | zero | ~230 linhas + 9 gates |

O `ia-recibo` é mais barato de adotar e não erra em nada do que afirma, exceto na conta dos
34 B. As duas peças são compatíveis: a disciplina dele ("não empilhe em cursor parado") é a
regra que a linha automática do `ia-ack` passa a lembrar sem depender de memória.

## 11. Arquivos

```
~/.claude/iaswarm-runs/ia-chat-fase6/batch/ia-ack/
├── SKILL.md              frontmatter mínimo (name + description)
├── NOTA.md               este documento
├── bin/iachat-ack        protótipo, 4 comandos: marcar · ver · linha · pendentes
└── tests/teste_ack.py    9 gates, exit 0/1
```
