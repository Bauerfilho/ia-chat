missão: medir consumo real das 16 mensagens de 17/08, achar desperdício restante, julgar se a conversa entre IAs cegas é boa ou só possível, e propor 2–4 peças que não dupliquem as 7 skills existentes.

resultado: o plugin já é barato onde o código manda (post = append, hook = `test -f`, leitura dirigida = 27–47% da sala, busca ≈ 1 página). A conversa é possível e, no fio Claude↔Kimi, às vezes boa. No fio Claude→Codex é um monólogo com cursor preso em #1 e 9.143 B de dívida. O que ainda se paga é gordura de autor (Claude 72,6% do volume; 3 posts acima de AVISO_GRANDE) e a ausência de recibo/tarefa/claim. Quatro skills em `resultados/skills-propostas/` ranqueadas por impacto÷custo: ia-recibo · ia-magro · ia-tarefa · ia-claim.

---

## 1. Consumo real — números do arquivo e do `ler()`, não da cabeça

Fonte: `~/ia-chat-global/iachat.md` (cópia em `IACHAT_HOME=/tmp`, cursors não avançados na sala viva). Token = **bytes/4**, a mesma conta do README e de `ia-chat-consult`. Função: `bin/iachat_core.py:317` (`ler`), `bin/iachat:48` (`entregar`), `bin/iachat_core.py:537` (`buscar`).

### O arquivo hoje

| | |
|---|---|
| tamanho | **24.757 B** / teto vivo **102.400 B** (`config.json`; o `CONFIG_PADRAO` do núcleo fala 204.800 — o vivo é 100 KB) |
| mensagens | 16 · última #16 |
| header “Como funciona” | 875 B — **não** entra no dirigido nem no `--tudo` (o CLI imprime só blocos) |
| `bytes_sala` do `ler()` | **23.867 B ≈ 5.967 tokens** |
| stdout de `read --tudo --sem-avancar` | 23.945 B / 254 linhas |

Cursores reais no momento da medida: claude **#16**, kimi **#14**, codex **#1** (parado desde 20:41).

### Por autor (bloco, incluindo metadado)

| autor | n | bytes | share |
|---|---|---|---|
| claude | 9 | 17.339 | **72,6%** (73,4% antes da #16 — é o número do contrato) |
| kimi | 5 | 5.766 | 24,1% |
| codex | 2 | 777 | 3,3% |

Corpos acima de `AVISO_GRANDE=2048` (`iachat_core.py:49`): **#4 = 2.415 B**, **#9 = 4.727 B**, **#15 = 4.039 B**. Os três são da Claude.

### As quatro operações

**Entregar** (`iachat entregar`, teto default **6.144 B**, `bin/iachat:171`; hook em `bin/ia-bell-hook.sh` faz `test -f pendente/$IA.md` e sai 0 se não há flag).

| situação | o que se paga |
|---|---|
| hook, sem flag | `test -f` · **0 tokens** no contexto · silêncio |
| 1 msg nova (o caso do dia a dia) | o bloco inteiro. As 16 cabem no teto; a mais cara é a #9 = **4.852 B ≈ 1.213 tok** |
| lote cursor 0 (IA que estava fechada) | claude 6.537, codex 11.209, kimi 8.140 — **os três estouram 6.144** → só cabeçalhos ≈ **40–55 tok**, cursor **não** anda (`cmd_entregar` else). O custo adia para um `read` |
| Codex agora (cursor=1) | dirigido não-lido **9.143 B > 6.144** → cabeçalhos. A próxima sessão dele começa com índice, não com a #15 |

**Ler dirigido** (`ler(escopo="meu")`, cursor 0 = primeira leitura / IA nova):

| IA | msgs | bytes | tokens | % da sala | ocultas |
|---|---|---|---|---|---|
| claude | 7 | 6.537 | **1.634** | 27,4% | 0 |
| codex | 6 | 11.209 | **2.802** | 47,0% | 8 |
| kimi | 4 | 8.140 | **2.035** | 34,1% | 7 |

O README (claude 1.574 / 25,8%) é esta sala **sem a #16** (241 B kimi→claude; 6.537−241=6.296; 6.296/4=1.574). Codex e Kimi batem o README no token.

Com cursores reais: claude **0 B**; kimi dirigido **0 B** (`--todas` = 4.167 B da #15, que não é dela); Codex dirigido **9.143 B ≈ 2.286 tok**.

**Ler tudo**: 16 msgs · **23.867 B ≈ 5.967 tok** para qualquer IA. Inclui as próprias (Claude pagaria 17.339 B ≈ 4.335 tok do que ela mesma escreveu). O post **não** avança o cursor do autor de propósito (`iachat_core.py:285-288`) — perder dirigida não-lida é pior. `--tudo` é que é o hábito caro.

**Buscar** (`buscar` + primeira `paginar`): índice (≤12 linhas) + 1 página fechada em 60 linhas **ou** 4.096 B (`iachat_core.py:406-411`).

| termo | achados | página | page B | saída ≈ | tokens ≈ |
|---|---|---|---|---|---|
| trusted_hash | 3 | 1/7 | 3.919 | 4.359 | **1.090** |
| hook | 7 | 1/7 | 3.919 | 4.679 | 1.170 |
| omni | 2 | 4/7 | 3.907 | 4.267 | 1.067 |
| sino | 9 | 1/7 | 3.919 | 4.839 | 1.210 |

Páginas do ativo: 7 · 3.672–4.036 B ≈ **918–1.009 tok** (pág 7 = 1.256 B). Em arquivo de 24 KB uma página é **~16%**, não 5%. O “5% / ~1.000 tok” do `ia-search` vale quando o recorte ≫ 4 KB (o gate G9 foi medido num de 78 KB). O barato é o **teto absoluto de ~1.000 tok**, não a fração.

**Post I/O** (protótipo no `IACHAT_HOME` temp, não na sala viva): append de **189 B** + `estado.json` 50 B = **239 B** de I/O, 1,33 ms. RMW do arquivo inteiro seria 49.703 B. O “17 KB” do briefing é `_cauda=16384` (`iachat_core.py:154`) **se** o estado sumir; hoje o estado existe, então o post é só o bloco novo.

**Status**: 226 B ≈ **56 tokens**.

**IA nova** (grok não está em `na_sala` — `post` recusa, `iachat_core.py:234`): `status` 56 tok + dirigido 1.634–2.802, **ou** `--tudo` 5.967. Carregar as 7 skills = **19.093 B ≈ 4.773 tok**. Entrada ingênua (7 skills + `--tudo`) ≈ **10.740 tok**. Entrada disciplinada (1 skill `ia-chat-activate` 759 + status + dirigido) ≈ **2.500–3.600 tok**.

---

## 2. Desperdício que ainda se paga

O barato estrutural já está no núcleo. O que sobra é **hábito** e ** buraco de protocolo**.

1. **Gordura de autor, não de leitor.** Claude é 72,6% dos bytes com 9/16 posts. Três corpos acima do aviso que o próprio CLI emite. A #15 cola 4.039 B de brief cujo arquivo já existia. A #9 gasta 4.727 B para 3 pedidos e para repetir `PIPE_BUF`/`flock` (já no header, já nas #1 e #5; 6 ocorrências em 3 msgs). As 3 skills são citadas **22 vezes** em 8 mensagens.

2. **Rascunhos magros medidos** (mesmo conteúdo acionável): #9 → 396 B (**−1.083 tok**); #15 → 552 B (**−872 tok**). Kimi dirigido cairia 8.140 → 3.809 B (−53%). Codex dirigido, magro de #4+#15, ~11.209 → 5.807 B (−48%). Quem lê paga isso **toda vez** que o cursor ainda não passou.

3. **Pile-on sem recibo.** Codex em #1 desde 20:41. Claude mandou #4, #10, #11, #15. Dívida agora 9.143 B. `entregar` nessa fila devolve cabeçalhos. `status` já mostra o cursor (`iachat_core.py:390`) — o remetente não olhou. Cada post novo para um cursor atrasado é custo que o destinatário não escolheu e ainda não consumiu.

4. **Sino sem pedido.** #3 = `resposta` (8 B). #10+#11+#12 = 585 B nominando Codex/Kimi por teste do *operador*. Interromper sem tarefa treina a ignorar o sino — o mesmo defeito que o anti-eco nasceu para matar (`iachat_core.py:11-13`).

5. **Releitura da própria.** Só dói no `--tudo` (Claude 4.335 tok de texto dela). No dirigido o filtro é `de != ia` (`iachat_core.py:339`). Não é bug; é o `--tudo` usado como hábito.

6. **Busca que sempre despeja a 1ª página.** `cmd_search` (`bin/iachat:144-148`) imprime o índice **e** a página da primeira ocorrência. Quem queria só “em que # está trusted_hash” paga ~1.090 tok em vez de ~12 linhas de índice (~250 B). Em chat de 24 KB a página é 16% do arquivo.

7. **Entrada de IA nova.** 4.773 tok de skills + 5.967 de `--tudo` se ela “se atualiza”. Nada no plugin a impede. Grok hoje nem entra: não está na sala.

8. **Teto do `entregar` vs lote.** Uma a uma, nenhuma msg estoura 6.144. Em lote (IA fechada, ou Codex com 5 atrasadas), estoura sempre. O teto protege a janela e **esconde** o trabalho — o destinatário vê cabeçalho da #15, não o gate.

Não é desperdício (já resolvido, não refazer): append vs RMW; dirigido vs 100%; hook silencioso; anti-eco; página ≤ ~4 KB; rotação mecânica.

---

## 3. Qualidade da conversa — possível, no fio Kimi às vezes boa, no fio Codex não

Li as 16 como diálogo entre pares cegos.

**O que faz funcionar (e já está aqui):**

- Autocontido com caminho e número. A #7 e a #13 da Kimi são o padrão: `which`, PID do LaunchAgent, mtime do config, o que a *sessão* enxerga vs o que o disco tem.
- Nominação. Kimi de fora nas #1–#3, cursor #0, zero flag — o teste passou (a #5 confirma).
- Correção. Claude #6 afirmou “as 3 skills aparecem” → Kimi #8 mediu o catálogo da TUI → Claude #9 admitiu o instrumento errado (`kimi -p` ≠ TUI). Isso é conversa, não broadcast.
- A #16 é um teste fechado: hipótese + o que contaria como sucesso, uma linha.

**O que falta (os exemplos do contrato, contra as 16):**

| buraco | evidência nesta sala |
|---|---|
| Saber se foi lida | Cursor do Codex em #1; #4/#10/#11/#15 sem ACK. A #14 é o único recibo, e custou 1.330 B. `status` tem o dado; não é protocolo. |
| Encadear em mensagem específica | `RE_META` é `msg/de/para/ts` (`iachat_core.py:30`) — não há `em_resposta_a`. A #8 é “complemento à #6” em prosa. Sem `#N` no topo não há fio consultável. |
| Marcar urgência | #15 (ordem do Bauer, Codex no ultra) e #10 (teste de sino) saem iguais. O hook não distingue. |
| Passar tarefa em vez de informar | Só a #15 é tarefa de verdade, e mesmo assim cola o brief. #1/#5 misturam manual + checklist. #10–#12 informam/testam com `@`. |
| Duas IAs no mesmo arquivo | Hoje não colidiram. `hooks.json` do Codex (trusted_hash) e `config.toml` do Kimi são os alvos óbvios. Consultar via `search` custa ~1.090 tok. |

Veredito: o plugin torna a conversa **possível e barata de receber**. Não a torna **boa por padrão**. Claude↔Kimi fecha laços (mede, corrige, ACK). Claude→Codex é um lado só depois da #3 — e o remetente não tem sinal para parar. Uma conversa entre cegos sem recibo é correio, não diálogo.

---

## 4. Peças novas, ranqueadas por impacto ÷ custo

As 7 existentes cobrem: falar (`activate`), sino (`bell`), quem interromper (`nomination`), arquivo/rotação (`storage`), dono da casa (`brain`), achar sem carregar (`search`), abrir a sala de propósito (`consult`). Nenhuma fecha laço, disciplina o tamanho no `post`, empacota trabalho, ou trava arquivo de trabalho.

Custo da peça = tokens para carregar a skill uma vez + tokens por uso. Impacto = tokens (ou interrupções) que a sala de hoje deixaria de pagar, medidos.

| # | peça | impacto medido | custo medido | impacto÷custo | por quê esta ordem |
|---|---|---|---|---|---|
| 1 | **ia-recibo** | para o pile-on de 9.143 B ≈ 2.286 tok; troca a #14 (1.330 B) por ACK de **34 B ≈ 8 tok**; desbloqueia o fio morto Claude→Codex | `status` já existe (226 B). ACK = 1 post de 34 B. Skill ≈ 3,6 KB uma vez | **o mais alto** — quase zero infra, o buraco mais caro da sala real | sem recibo, magro e tarefa não adiantam: o destinatário não lê e o remetente não sabe |
| 2 | **ia-magro** | #9 −1.083 tok, #15 −872 tok por leitura; Kimi dirigido −53%; Codex dirigido −48% se #4+#15 magros | o CLI já avisa em 2.048 B. Skill ≈ 3,1 KB. Sidecar = 0 tok nas outras IAs | alto e **recorrente** — Claude continua sendo 3/4 do volume | o aviso existe e foi ignorado; a skill é a regra no lado de quem escreve (não é o `ia-brain`) |
| 3 | **ia-tarefa** | transforma #15 em pacote de 552 B com gate; separa P0 de teste de sino; `re: #N` é o fio até existir campo no parser | skill ≈ 3,9 KB; o formato cabe no post magro | médio-alto — a economia de bytes é a do magro; o ganho extra é **aceitação** (a outra sabe o que é pronto) | sem isto, “passar tarefa” continua sendo um ensaio com `@` |
| 4 | **ia-claim** | “posso tocar X?” cai de ~1.090 tok (`search` medido) para **90 B ≈ 22 tok**; evita duas edições em `hooks.json` (trusted_hash) | 90 B por claim; skill ≈ 3,7 KB | menor hoje (zero colisões nas 16) · seguro barato | o consult já manda *ler* a sala; isto é a trava de *escrita* |

Prova de cada uma está no próprio `SKILL.md` (gates binários, números desta sala como baseline).

Não propos CLI novo. Tudo roda com `post` + `status` + um `claims.json` opcional. Campo `em_resposta_a` no `RE_META` e `CLAIM` no `status` seriam o passo seguinte — fora da fronteira desta entrega.

**Não fiz** uma quinta (`ia-entrada`): a economia de IA nova (10.740 → ~3.000 tok) é real, mas grok/agy ainda não estão em `na_sala`, e o protocolo cabe num parágrafo do `activate`.

---

## Artefatos

- `resultados/skills-propostas/ia-recibo/SKILL.md`
- `resultados/skills-propostas/ia-magro/SKILL.md`
- `resultados/skills-propostas/ia-tarefa/SKILL.md`
- `resultados/skills-propostas/ia-claim/SKILL.md`

Nada escrito em `~/Projetos/ia-chat` nem em `~/ia-chat-global`. Protótipos de medida (post de 189 B, rascunhos magros) rodaram em `IACHAT_HOME` sob `/tmp`.
