# NOTA — `ia-digest`

Entrega: `SKILL.md` + `bin/iachat-digest` (protótipo executável, rodado).
Nada foi escrito em `~/Projetos/ia-chat` nem em `~/ia-chat-global` — provado abaixo.

---

## 1. A peça que me pediram não paga. A medida que mostra isso

O briefing pede destilar **mensagens antigas que ainda estão no ativo, reescrevendo o
corpo**. Construí essa versão primeiro, rodei, e ela não se sustenta. Três medidas:

**(a) O caminho comum de leitura já é limitado por cursor.** `ler()` com
`escopo="meu"` (`iachat_core.py:317-336`) só devolve `m["n"] > cursor`. Cada IA vê cada
mensagem **uma vez**. Destilar o que ela já leu economiza **zero**; destilar o que ela
ainda não leu **apaga conteúdo antes da entrega**. Estado real da sala em 17/08:

```
cursores reais: {'claude': 16, 'codex': 1, 'kimi': 14}
ativo: 24757 B

ia          read --de (meu, cursor atual)     entrando do zero (meu)    --tudo
claude                                  0                       6537     24757
codex                                9143                      11209     24757
kimi                                    0                       8140     24757
```

Um destilador por idade destilaria as mensagens #4 e #5 — **exatamente as que o codex,
com cursor em #1, ainda não viu**. Corrigir isso exige nunca destilar abaixo do menor
cursor da sala; e o menor cursor hoje é **1**, o que zera o conjunto elegível.

**(b) O teto do que se pode cortar sem mentir é baixo.** Medi que fração do corpo das 16
mensagens contém caminho, número, comando, `arquivo:linha` ou citação do dono — a
definição de autocontido que o próprio chat cobra (`iachat_core.py:93`):

```
corpo total (linhas de corpo):        21873 B
protegido no grão LINHA:              16592 B  (75%)
protegido no grão FRASE:              11331 B  (51%)
```

A sala é densa nos fatos **por desenho**. Sobra 25% no grão de linha, 49% no de frase — e
esse é o teto teórico, antes de qualquer prudência.

**(c) O que a reescrita compraria não vale o que custa.** Rodei a versão de arquivo: 17%
de corte nas candidatas, **10% do ativo** (24.757 B → 22.202 B). Em troca disso ela
introduzia: reescrita do ativo a cada rodada, arquivos de íntegra em
`arquivo/integral/`, e uma perda silenciosa — `buscar()` varre só
`iachat-*-recorte-*.md` (`iachat_core.py:419`), então **o texto destilado sairia do
alcance do `iachat search`**. Trocar 10% de bytes por um buraco na busca é mau negócio.

**Veredito:** a versão de arquivo está morta. A necessidade que a originou é real e
tem lugar melhor.

---

## 2. Onde a destilação paga — e um defeito real que achei medindo

`iachat entregar` (o que o hook chama) tem teto de 6.144 B (`bin/iachat:171`). Acima
dele cai num modo degradado (`bin/iachat:64-69`) que imprime, por mensagem:

```python
print(f"   #{m['n']} de {m['de']}: {m['bruto'].splitlines()[2][:90]}")
```

**`splitlines()[2]` é a linha em branco.** O `bruto` é
`[0]` metadado · `[1]` título · `[2]` **vazia** · `[3]` primeira linha de corpo. Provado:

```
  bruto.splitlines()[0] = '<!-- iachat msg=15 de=claude para=codex ts=2026-08-17T21:07:44-03:00 -->'
  bruto.splitlines()[1] = '### 💬 #15 · **claude** → @codex · 17/08 21:07'
  bruto.splitlines()[2] = ''
  bruto.splitlines()[3] = '**Tarefa sua, ordem do Bauer: fechar o omni na SUA casca. ...'
```

Consequência medida no backlog real do codex (9.143 B pendentes):

```
   #4 de claude:
   #5 de claude:
   #10 de claude:
   #11 de claude:
   #15 de claude:
   => 92 B entregues de 9143 B pendentes (1%)
   => cursor NÃO avança; flag NÃO some; ele tem que rodar read na mão
```

O hook entrega **cabeçalhos vazios** e o laço não fecha — exatamente quando há mais o
que dizer. É aqui que a destilação tem trabalho.

---

## 3. O que a peça faz

`iachat-digest entregar --de X` substitui `iachat entregar`. Abaixo do teto, comportamento
idêntico. Acima, destila em vez de degradar:

- **grau 1** (linha) e **grau 2** (frase), escalando **das mais velhas para as mais
  novas** — a última é a que o leitor vai responder.
- Cada destilada leva `> 🗜️ destilado (grau N) de X B · íntegra: iachat page ativo P`,
  com `P` calculado pela mesma conta do `iachat search` (`iachat_core.py:557-561`).
- O que nem em grau 2 couber vira **linha de assunto REAL** (índice 3, não 2) + ponteiro.
- **O `iachat.md` não é tocado.** Reversibilidade sai de graça: o original nunca saiu do
  lugar.

**As quatro perguntas do briefing, respondidas:**

| pergunta | resposta |
|---|---|
| o que nunca se destila | caminho absoluto, `arquivo:linha`, crase, **qualquer** dígito, citação literal do dono, bloco de código, cabeçalho, metadado, título, primeira linha do corpo |
| quem destila | **ninguém** — regex sobre linha e frase. Sem modelo, sem rede, sem chave. `0,8 ms` para as 16 msgs. Roda com a frota inteira fechada, pelo mesmo motivo pelo qual a rotação é mecânica (`iachat_core.py:422`) |
| como se recupera o original | ele nunca foi alterado. `iachat page ativo P` (~4 KB) ou `iachat search`. Prova: `cmp` do ativo antes/depois → **byte a byte intacto** |
| quanto economiza | tabela abaixo |

---

## 4. Custo medido — 16 mensagens reais de `~/ia-chat-global/iachat.md`

Corte por mensagem (bytes reais, `\d` protegido):

```
 msg   orig  grau1  grau2      msg   orig  grau1  grau2
#1     2066   34%    36%       #9     4851   23%    50%
#4     2541   28%    37%       #13    1388    0%    37%
#5     2019   13%    32%       #14    1329    0%    42%
#7     1886   11%    38%       #15    4167    9%    23%
TOTAL 23867 → 21298 (10%) grau 1 · → 16902 (29%) grau 2
```

Mensagens abaixo de ~250 B (#3, #10, #11, #12, #16) cortam **0%** — não há prosa a tirar,
e a peça corretamente não mexe nelas.

Entrega, comparada com o comportamento de hoje (teto 6.144 B):

| cenário | pendente | hoje entrega | digest entrega |
|---|---|---|---|
| codex, cursor real #1 | 9.143 B em 5 msgs | **92 B (1%)**, todos vazios | **5.486 B (60%)** |
| claude entrando do zero | 6.537 B em 7 msgs | 116 B (1%) | **5.736 B (87%)** |
| kimi entrando do zero | 8.140 B em 4 msgs | 72 B (0%) | **5.175 B (63%)** |
| codex entrando do zero | 11.209 B em 6 msgs | 110 B (0%) | **5.486 B (48%)** |

Pela régua do próprio repo (`iachat_core.py:410`: ~4 KB ≈ 1.000 tokens), os 5.486 B do
codex são ~1.340 tokens de conteúdo útil onde hoje chegam ~23 tokens de nada.

Não medi tokens com tokenizador: `tiktoken` e `anthropic` não estão instalados nesta
máquina. Os números acima são **bytes contados**, e a conversão usada é a que o repo já
adota.

---

## 5. O que as 7 skills atuais não resolvem

| skill | cobre | não cobre |
|---|---|---|
| `ia-storage` / `ia-brain` | histórico fora do ativo, rotação, recorte | o pendente que não cabe na entrega **agora** |
| `ia-search` | achar sem pagar o arquivo | não reduz o que já está sendo entregue |
| `ia-bell` | avisar que chegou | o que fazer quando o que chegou é grande demais |
| `ia-nomination` | quem recebe | quanto cada um recebe |
| `ia-chat-activate` / `ia-chat-consult` | entrar e consultar | o teto da entrega |

Nenhuma das sete tem uma linha sobre o modo degradado do `entregar`. Ele é o único ponto
do plugin onde a IA fica **sem o conteúdo e sem saber que ficou**.

---

## 6. Riscos, sem maquiagem

1. **Grau 2 pode cortar a frase que rotula um comando.** Achado real na #1: a linha
   `1. Ler esta mensagem pelo canal oficial (isso apaga o seu sino):` não tem fato
   protegido e cai; a linha seguinte, `` `iachat read --de codex --novas` ``, fica. O
   comando sobrevive sem a frase que diz para que serve. Aceitei em vez de adicionar
   heurística: o comando é autoexplicativo e o ponteiro da íntegra está a uma linha dali.
   **É a limitação conhecida do grau 2**, não um efeito colateral não previsto.
2. **Avançar o cursor sobre uma entrega destilada** significa que a prosa original nunca
   será entregue automaticamente. É a troca: hoje o cursor não avança e o laço fica
   aberto. Quem não quiser, usa `--sem-avancar`.
3. **O ponteiro `iachat page ativo P` envelhece se a mensagem for rotacionada** para um
   recorte depois da entrega. Continua recuperável por `iachat search`, que varre os
   recortes (`iachat_core.py:545`), mas a página muda. Não corrigi: corrigir exigiria
   gravar o número da mensagem no ponteiro E o `page` aceitar `--msg`, que é mudança no
   núcleo, e eu não escrevo no repo.
4. **O destilador é regex, e regex não entende texto.** Ele acerta porque a regra é
   conservadora (na dúvida, mantém) e porque só roda quando a alternativa é entregar
   nada. Não use como resumidor de propósito geral.
5. **Dois erros meus, os dois no INSTRUMENTO, corrigidos no caminho.** O segundo: o
   `ver` comparava o modo de hoje contra a lista de mensagens **já podada** pelo próprio
   digest — 4 msgs em vez de 5 — o que fazia o "hoje" parecer menor (74 B) do que é
   (92 B). Medição a favor de quem mede. `_entrega` passou a devolver a lista original.
   O primeiro: a primeira versão protegia
   `\d{2,}` e o meu próprio gate de perda de fato passava com 0 falhas — mas ele
   procurava a substring `"2"`, que casa com qualquer timestamp. Gate frouxo dando verde.
   A frase real *"chegaram a mim exatamente 2 prompts dele"* (msg #14) estava caindo. Troquei
   a proteção para `\d` (qualquer dígito) e a unidade do gate para **frase**, não substring.
   Custou 5 pontos de corte no grau 2 (34% → 29%). Paguei.

---

## 7. O critério binário de "funcionou"

**Funcionou se, com o backlog real do codex (9.143 B, cursor #1, teto 6.144 B), as quatro
condições valerem ao mesmo tempo:**

1. a entrega cabe no teto e leva **> 50%** do pendente em bytes de conteúdo;
2. **nenhuma frase que contenha caminho, `arquivo:linha`, crase, dígito ou citação do dono
   desaparece** em nenhum grau;
3. `cmp` do `iachat.md` antes e depois é **igual byte a byte**;
4. o cursor avança e o flag do sino some — o laço do hook fecha.

Resultado da rodada (`IACHAT_HOME` temporário, cópia da sala real):

```
=== A) backlog real do codex (cursor #1, teto 6144) ===
pendente para codex: 9143 B em 5 msg(s) · teto 6144 B
   #4     2541 B →      0 B   cortada p/ cabeçalho
   #5     2019 B →   1410 B   grau 2
   #10     239 B →    239 B   grau 2
   #11     177 B →    177 B   grau 2
   #15    4167 B →   3238 B   grau 2
   hoje  (bin/iachat:64-69):     92 B entregues (1% do pendente)
   digest:                     5486 B entregues (60% do pendente) · teto 6144 B OK    → (1) PASS

grau 1: 0 perda(s) em frase-com-fato
grau 2: 0 perda(s) em frase-com-fato
frases-com-fato conferidas: 276  ·  VEREDITO: PASS — nenhuma perdida                  → (2) PASS

=== C) entrega real + laço do hook ===
exit=0 ·     5723 B
cursor={"ultima_lida": 15, "em": "2026-08-17T22:10:56-03:00"} · flag=[]                → (4) PASS
ativo: byte-a-byte intacto                                                             → (3) PASS

bordas: parse do ativo → 16 msgs, última #16 · nada pendente → exit=0 em silêncio ·
        abaixo do teto → entrega idêntica ao `iachat entregar`
```

**Bateria do repo, sem modificar o repo** (o protótipo importa `iachat_core` mas não
escreve nele):

```
teste_concorrencia.py  → recheio íntegro 100/100 · contador .estado 100 · ✅ GATE 1 PASSOU
teste_nucleo.py        → G10 leitura dirigida mais barata (meu=151 B · todas=478 B · tudo=2540 B)
                         ✅ GATES 2-5 PASSARAM
teste_rotacao.py       → G9 recorte 80616 B em 22 páginas · resposta em 5,0% do arquivo
                         ✅ GATES 6, 7 e 9 PASSARAM
```

Os 10 gates seguem verdes.

**Prova de não-escrita** (`find -newermt "2026-08-17 21:30"`): nenhum arquivo alterado em
`~/ia-chat-global`; em `~/Projetos/ia-chat`, só um `bin/__pycache__/` que o import criou —
já removido (e listado no `.gitignore` do repo).

---

## 8. O que eu recomendo ao dono

1. **Consertar `bin/iachat:68`** — `splitlines()[2]` → a primeira linha não-vazia do corpo.
   É uma linha, independe desta proposta, e o modo degradado deixa de entregar vazio.
2. **Adotar a destilação na entrega**, trocando a chamada do `ia-bell-hook.sh`.
3. **Não adotar** a destilação com reescrita do ativo. Medida: 10% do arquivo, em troca de
   reescrita periódica e de um buraco no `iachat search`.
4. Se um dia quiser resumo em **prosa**, ele é mensagem nova no canal, escrita por uma IA
   acordada — não um campo que o destilador preenche. Destilador que depende de IA não
   entrega no dia em que o backlog estoura.
