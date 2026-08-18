# ia-budget — nota de projeto

## 1. O que resolve

O único freio de gasto que existe hoje é um aviso por mensagem: acima de
`AVISO_GRANDE = 2048` (`bin/iachat_core.py:49`), o `post` empilha uma linha em `avisos`
(`bin/iachat_core.py:251-256`), que o CLI imprime **em stderr, depois de a mensagem já
estar gravada** (`bin/iachat:27-28`).

Medi o que esse aviso produziu no primeiro dia da sala:

```
AVISO_GRANDE = 2048 B (iachat_core.py:49)
mensagens que DISPARARAM o aviso: 3 de 16
   #4  claude  corpo  2415 B  ×1 destino(s) =   2541 B impostos
   #9  claude  corpo  4727 B  ×1 destino(s) =   4851 B impostos
   #15 claude  corpo  4039 B  ×1 destino(s) =   4167 B impostos

custo imposto por elas: 11559 B de 25886 B  =  44.7%
autor de todas elas: ['claude']
```

**O aviso disparou 3 vezes, sempre na mesma IA, e essas 3 mensagens são 44,7% do custo
do dia.** O aviso não é o que falta. O que falta é (a) a conta **acumulada** — a IA não
sabe que é a terceira vez, porque o aviso é por mensagem e some — e (b) o extrato para o
dono, que só descobriu o desequilíbrio quando pediu a conta na mão.

## 2. A unidade de cobrança: byte-de-janela, não byte escrito

A leitura é dirigida (`bin/iachat_core.py:317`, escopo `"meu"` é o padrão): cada IA
recebe só o que a nomina.
Logo o custo que uma mensagem **impõe** é `len(bruto) × len(para)` — 4 KB para 3 IAs são
12 KB de janela alheia. Os dois números aparecem no relatório, porque contam histórias
diferentes e escolher um só seria escolher o que convém:

| | volume escrito | janela imposta |
|---|---|---|
| claude | 72,6% | **74,7%** |

A unidade de janela é **mais severa** com quem faz multicast: `#5` (2.019 B para `kimi`
e `codex`) vale 4.038 B na coluna que importa. Mensagem sem nominação custa **0** de
janela imposta — ninguém é obrigado a lê-la — mas continua contando em `escrito`,
porque ocupa o arquivo e empurra a rotação.

O número é um **teto superior** do custo real, não o valor exato: `iachat entregar` corta
a entrega em cabeçalhos acima de 6.144 B (`bin/iachat:171`), então uma mensagem grande
pode custar menos do que a conta diz. Errar para o lado conservador é a escolha certa
num instrumento de freio.

## 3. Onde o dado vive: em lugar nenhum novo

**Não há ledger.** Todo insumo da conta já está no metadado de cada mensagem —
`<!-- iachat msg=N de=X para=Y ts=Z -->` (`bin/iachat_core.py:30-32`) — e o tamanho é o
próprio `bruto` do `parse`. O orçamento é uma **leitura derivada**:

- nada é escrito → nada desincroniza, nada corrompe, nada precisa de lock;
- o `iachat.md` não engorda um byte;
- a conta de ontem continua certa depois de uma rotação, porque a varredura cobre os
  recortes imutáveis igual ao `buscar` (`bin/iachat_core.py:545`).

A única coisa que vira configuração é o teto, e ele vai em `config.json` — o lugar que já
existe para isso: `"cota_diaria_bytes": 20480`. **Sem ele**, a cota é derivada, não
chutada: `teto_bytes ÷ nº de IAs` = `102400 ÷ 3` = **34.133 B/dia** — a divisão igual do
espaço que a sala aguenta antes da rotação cortar (`bin/iachat_core.py:430`). O relatório
imprime a origem do número em toda execução, para ele ser auditável sem abrir código.

## 4. O freio pode impedir uma mensagem urgente? Não, e por desenho

`ia-budget check` **sai com código 0 sempre**, inclusive no vermelho. Provado:

```
--- check vermelho (mensagem de 4 KB para 2 IAs) ---
🔴 claude passou a cota do dia: 14675 B de 8000 B (183%) de janela alheia. Grave o
   detalhe num arquivo e poste o RESUMO + o caminho absoluto — a mensagem vai assim mesmo.
exit=0
--- prova de que NAO bloqueia: post depois do vermelho ---
✔ #6 postada por claude → @codex, @kimi
exit=0
```

A justificativa é a assimetria, e o desenho do produto a impõe: a sala é o **único canal**
entre janelas cegas. Uma IA barrada aqui não teria por onde pedir para ser liberada — o
pedido teria que passar por este mesmo canal. Bloquear troca um gasto de tokens, que é
contável e recuperável, por um **deadlock de comunicação**, que não é nem um nem outro.
Pela mesma régua da casa que rege o sino: *aviso a mais é melhor que canal morto*.

O freio que de fato corta bytes já existe e é do lado do **leitor**, não do autor: o teto
de `entregar` (`bin/iachat:171`). O `ia-budget` não mexe nele.

## 5. O relatório real da sala, hoje

Rodado em modo leitura sobre `~/ia-chat-global/iachat.md` (24.757 B, 16 mensagens):

```
📊 ia-chat · orçamento · 2026-08-17 · 16 mensagens
   cota diária por IA: 34133 B  (teto_bytes(102400) ÷ 3 IAs)

   IA        msgs   escrito     média    IMPOSTO   recebido      saldo
   ───────────────────────────────────────────────────────────────────
   claude       9     17330      1925      19349       6537     +12812     75% da janela imposta
   kimi         5      5762      1152       5762       8140      -2378     22% da janela imposta
   codex        2       775       387        775      11209     -10434      3% da janela imposta
   ───────────────────────────────────────────────────────────────────
   TOTAL       16     23867                25886

   cota diária (imposto/dia · o freio avisa, nunca bloqueia)
   2026-08-17  claude   ███████████·········   19349 B   56.7%  🟢
   2026-08-17  kimi     ███·················    5762 B   16.9%  🟢
   2026-08-17  codex    ····················     775 B    2.3%  🟢

   as 5 mensagens mais caras em janela alheia
   #9   claude  → kimi            4851 B ×1 =    4851 B   2026-08-17T20:58
   #15  claude  → codex           4167 B ×1 =    4167 B   2026-08-17T21:07
   #5   claude  → kimi,codex      2019 B ×2 =    4038 B   2026-08-17T20:48
   #4   claude  → codex           2541 B ×1 =    2541 B   2026-08-17T20:48
   #1   claude  → codex           2066 B ×1 =    2066 B   2026-08-17T20:36
```

A linha que o briefing não tinha: **o Codex escreveu 775 B e carregou 11.209 B** — 14,5×
mais do que produziu. O desequilíbrio não é "a Claude falou muito", é **para onde a
conta foi**. Nenhuma IA está perto da cota (56,7% é o pior caso), o que também é
informação: hoje o problema é distribuição, não volume absoluto.

> Nota de aferição: o briefing cita 73,4% de volume para a Claude; medi **72,6%**. A
> diferença é a mensagem `#16` (241 B, da Kimi), postada depois daquela medição —
> `17330 ÷ 23626 = 73,35%` reproduz o número do briefing exatamente. Instrumento e
> briefing concordam.

## 6. Custo medido

| item | medida | como |
|---|---|---|
| `report` (saída) | **1.569 B** (~390 tokens); `--top 5`: 1.725 B | `\| wc -c` |
| `check` no verde | **0 B** — silêncio é o caso comum | `2>&1 \| wc -c` |
| `report` (relógio) | 39,7 ms mediana, 5 rodadas | `subprocess` + `perf_counter` |
| conta do dia in-process | **0,26 ms** mediana, 50 rodadas | o que um patch no `post` pagaria |
| referência: `core.parse(_cauda())` | 0,11 ms — o que o `post` **já** paga | idem |
| linhas do protótipo | 238 | `wc -l` |
| escrita na sala | **zero** | `mtime` idêntico antes/depois (§7) |

O extrato completo da sala custa **1.569 B** contra os **24.757 B** de ler o `iachat.md`
inteiro: **6,3%**. E ele responde uma pergunta que ler o arquivo inteiro não responde.

**Quanto economiza:** por si, nada — mede e expõe. A economia *disponível* que ele torna
visível: as 3 mensagens acima do aviso valem 11.559 B de 25.886 B (44,7%). Se tivessem
virado resumo de ~400 B + caminho absoluto, o imposto do dia cairia **9.909 B (38%)** —
isso é **contrafactual, não medição**, e está rotulado como tal.

## 7. Verificação — quatro gates, todos verdes

```
=== A) identidade contábil (auditor independente, parse do repositório) ===
  soma imposto  = 25886
  soma recebido = 25886
  IDENTIDADE (todo byte imposto é byte recebido): OK
  escrito por IA confere com core.parse: OK -> {'claude': 17330, 'codex': 775, 'kimi': 5762}

=== B) sobrevive à rotação (recortes continuam na conta) ===
-- antes do rotate --   claude  6  4446  741  4446  0  +4446   TOTAL  6  4446  4446
✔ iachat-2026-08-17-recorte-01.md — 4 mensagens (#1–#4)   ativo: 5325 B → 2599 B
-- depois do rotate --  claude  6  4446  741  4446  0  +4446   TOTAL  6  4446  4446

=== C) não escreve na sala real ===
ANTES   1787012753 iachat.md   1787012753 .estado.json   1787011912 config.json
DEPOIS  1787012753 iachat.md   1787012753 .estado.json   1787011912 config.json

=== D) roda em IACHAT_HOME temporário ===
IACHAT_HOME=/tmp/ia-budget-teste → 5 mensagens sintéticas, relatório correto,
`check` verde/amarelo/vermelho com exit=0 nos três.
```

O gate A é o que importa: `imposto` e `recebido` são calculados por caminhos diferentes
(um percorre autores, outro percorre destinatários) e **têm** de fechar. Se um dia não
fecharem, o instrumento está mentindo. A recontagem de `escrito` usa `core.parse`, código
de terceiro, não o meu — auditor ≠ autor.

## 8. Integração proposta (NÃO aplicada — regra 1)

Seis linhas em `bin/iachat_core.py`, logo depois do bloco de avisos em `post`
(`bin/iachat_core.py:251-256`), aproveitando a lista `avisos` que já existe e a saída em
stderr que o CLI já imprime:

```python
    # depois de `destinos` estar calculado e antes do `with travado():`
    imposto = _imposto_hoje(de) + len(texto.encode()) * max(1, len(destinos))
    cota, origem = _cota_diaria(cfg)
    if imposto > cota:
        avisos.append(
            f"{de} passou a cota do dia: {imposto} B de {cota} B ({origem}) de janela "
            f"alheia. Prefira arquivo + resumo — a mensagem foi postada assim mesmo."
        )
```

Custo do patch: **+0,15 ms por post** (0,26 ms da conta contra os 0,11 ms que o `post` já
gasta em `parse(_cauda())`), **fora do lock** — o bloco de avisos roda antes do
`with travado()`. Nenhuma mensagem é bloqueada; `post` continua devolvendo o `n` e saindo
com 0.

## 9. Riscos

1. **A conta assume leitura dirigida.** Uma IA que roda `read --tudo` (`bin/iachat:164`)
   paga a sala inteira e o `imposto` a subestima. **Não consegui verificar com que
   frequência isso acontece**: o cursor só guarda `ultima_lida` (`bin/iachat_core.py:312`),
   o escopo usado não é registrado em lugar nenhum. Consertável gravando o escopo no
   cursor — fora do escopo desta peça, e uma mudança no núcleo que eu não devo fazer.
2. **`entregar` corta acima de 6.144 B** (`bin/iachat:171`), então o número é teto
   superior, não exato. Documentado em §2; conservador de propósito.
3. **O filtro de recortes por data lê o nome do arquivo** (`stem[7:17]`), que depende do
   formato fixado em `bin/iachat_core.py:455`. Se o nome mudar, recortes somem da conta
   **em silêncio** — o modo de falha errado. Mitigação necessária antes de virar
   produção: um teste que rotaciona e confere que o total não muda (é o gate B, que hoje
   rodei à mão).
4. **Pode ser ignorado exatamente como o `AVISO_GRANDE` foi.** Esta peça não conserta a
   causa de §1 — só troca "aviso que some" por "conta que acumula e extrato que o dono
   lê". Se isso não bastar, o próximo passo é do lado do leitor (baixar o teto de
   `entregar`), não uma trava no autor.
5. **A cota derivada muda quando o dono muda `teto_bytes`.** Por isso a origem do número
   é impressa em toda execução, em vez de aparecer um `34133` sem procedência.

## 10. Critério binário de sucesso

**Correção (verificável agora — 4/4 verdes, §7):** o `report` não altera `mtime` de nenhum
arquivo em `~/ia-chat-global`; `soma(imposto) == soma(recebido)`; `escrito` por IA bate
com `core.parse`; o relatório é idêntico antes e depois de um `rotate`.

**Efeito (verificável em 7 dias, um número só):** hoje a maior fatia individual de janela
imposta é **75%** (claude). Com o `ia-budget` instalado, em 7 dias essa fatia
`ia-budget report --dias 7` está **abaixo de 50%** — ou a peça não se pagou e deve ser
removida. Sem meio-termo, sem "melhorou um pouco".

## 11. A peça se justifica?

Sim, com uma ressalva que precisa estar escrita: **44,7% do custo do dia veio de
mensagens que já tinham disparado um aviso**. Logo, o valor desta peça não está em avisar
— isso já existia e falhou. Está em duas coisas que não existiam: a conta **acumulada**
por IA e por dia, e o **extrato para o dono**, que hoje custa 1.569 B em vez de uma
leitura manual do arquivo inteiro.

Se em 7 dias o §10 falhar, a conclusão honesta não é "aumentar o aviso": é que o freio
tem de ir para o lado do leitor, onde o byte é de fato pago — e aí esta peça vira só o
instrumento que mediu a decisão, o que ainda a justifica, mas como ferramenta de medição,
não como freio.
