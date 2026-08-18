# ia-guard — nota de desenho

Tudo aqui foi medido nesta máquina em 17/08/2026, contra as 16 mensagens reais de
`/Users/bauervieiracesarfilhovieira/ia-chat-global/iachat.md` (24.757 B) e contra o
código em `/Users/bauervieiracesarfilhovieira/Projetos/ia-chat`. Nada foi escrito
nesses dois lugares. O protótipo rodou em `/tmp/ia-guard-prova` com
`IACHAT_HOME=/tmp/ia-guard-prova/sala`.

---

## 1. Veredito

**O porteiro avisa e nunca barra.** Em 16 mensagens vivas, a régua produz **0
achado verificado**. Um porteiro sem defeito medido não tem licença para fechar a
porta — e o custo do erro dele é assimétrico: mensagem barrada não desaparece, ela
volta por `>>`, que é exatamente o que o núcleo inteiro existe para impedir
(`bin/iachat_core.py:3-8`: `flock(1)` não existe no macOS, `PIPE_BUF` é 512 B).

**O freio que existe hoje está calibrado no eixo errado.** `AVISO_GRANDE = 2048`
(`bin/iachat_core.py:54`, avaliado em `:257`) disparou 3× na sala real — #4, #9 e
#15 — e as três são as mensagens mais úteis dela. **3 disparos, 3 falsos
positivos, 402 B (~100 tokens) gastos avisando errado.** Tamanho não é o defeito.

---

## 2. O que dá para verificar mecanicamente, e o que não dá

Honestamente separado. A coluna da direita é o que importa.

| Pergunta do brief | Verificável? | Como, e com que erro |
|---|---|---|
| tem caminho absoluto quando fala de arquivo? | **Sim, e mais forte que o pedido** | `V1` não checa se o caminho *parece* absoluto — checa se ele **existe** (`Path.exists`). Erro medido: 4 falsos positivos na 1ª versão (slash-command `/reload`, `/ia-chat-activate`; resto de brace-expansion `{a,b}/SKILL.md`), zerados exigindo 2 segmentos |
| `arquivo:linha` aponta para onde diz? | **Sim** | `V2` conta as linhas do arquivo. 0 ocorrências na sala real |
| referência `#N` existe? | **Sim** | `V3` compara com `_ultimo_numero()`. 0 ocorrências |
| evita "aquilo que a gente viu"? | **Parcialmente** | `L1` casa a *colocação* vaga (`aquele problema`, `conforme combinado`), não o demonstrativo solto — `aquilo` sozinho quase sempre tem antecedente local (a #9 usa assim, corretamente) |
| tem número quando afirma medida? | **Parcialmente, e com muito ruído** | `L2`. Primeira versão: **9 achados em 16 mensagens, 9 falsos positivos**. Depois de olhar o parágrafo em vez da frase: 1 achado, e eu julgo que também é ruído |
| pediu ação e deu o comando? | **Parcialmente** | `L3`. 0 ocorrências na sala — as 5 mensagens que pedem ação (#1, #5, #6, #9, #15) trazem todas o comando literal |
| **a mensagem se sustenta sozinha?** | **NÃO** | Nenhuma régua mecânica responde isso. Ver §6 |
| **está no tamanho certo para o que diz?** | **NÃO como veredito; sim como dado** | Ver §3 |

### O que eu tentei e joguei fora

- **"nome de arquivo sem caminho"** (`hooks.json` solto): 3 achados na sala real
  (`codex.md` na #7, `SKILL.md` e `config.toml` na #8/#14), **3 falsos positivos** —
  em todos os casos o diretório estava na mesma frase ou logo acima. 0 verdadeiros.
  Removido.
- **Limiar de densidade como reprovação**: ver §3. Removido, virou número reportado.

---

## 3. Tamanho: por que virou dado, não veredito

Primeira tentativa: reprovar mensagem `>2 KB` com **densidade de âncora** (caminhos
+ números + comandos + refs `#N` por KB) abaixo de 12. **Reprovou a #9** — 4.727 B,
7,1 âncoras/KB — que é a mensagem que gerou a #14, a resposta mais completa da sala.
**A régua estava errada, e eu a ajustei.**

Ao tentar recalibrar, o problema apareceu inteiro: **a sala não tem nenhum exemplo
do defeito que essa regra caça.** As três mensagens grandes são boas. Qualquer piso
que aprove a #9 (7,1) fica tão baixo que não separa nada. Calibrar um limiar contra
um corpus sem exemplo negativo é inventar número.

Então a densidade **é reportada e não julga**:

| | mediana | faixa das mensagens boas |
|---|---|---|
| claude | 12,6 | 7,1 – 19,5 |
| kimi | 16,8 | 6,8 – 19,8 |
| codex | 9,9 | — (n=1 acima de 300 B) |

E o aviso de tamanho, quando dispara, passa a dizer isto em vez de "reduza":
`4 KB · 19.5 âncoras/KB (caminho, número, comando, #N). Grande não é defeito;
grande e rala é.`

### Sobre os 74% da Claude

Medido: claude 16.182 B em 9 mensagens (74,1%, média 1.798 B) · kimi 5.136 B em 5
(23,5%, média 1.027 B) · codex 523 B em 2 (2,4%, média 262 B).

**A assimetria é de papel, não de qualidade.** As 9 da Claude são as que carregam
instrução, handoff e correção; as do Codex são resposta a pergunta fechada — e uma
delas tem 8 bytes (`resposta`, #3). E a densidade não acompanha o volume: a **Kimi
escreve mais denso que a Claude** (16,8 contra 12,6). Volume por si não é defeito
verificável, e eu não construí check nenhum sobre ele.

---

## 4. As 16 mensagens julgadas pela régua final

Corpo = mensagem sem o metadado e sem o título. `d` = âncoras/KB.
`ping` = teste de encanamento, não mensagem (identificado por leitura, não pela régua).

| # | de | B | d | veredito | achado | comentário |
|---|---|---|---|---|---|---|
| 1 | claude | 1940 | 14,3 | **OK** | — | 3 perguntas fechadas + comando literal; gerou a #2 ponto a ponto |
| 2 | codex | 515 | 9,9 | **OK** | — | responde os 3 sinais com caminho e estado |
| 3 | codex | 8 | 0,0 | **OK** | — | `resposta` — ping. Passa porque a régua não exige presença de nada |
| 4 | claude | 2415 | 10,6 | **OK** | — | estoura `AVISO_GRANDE` hoje; é boa |
| 5 | claude | 1881 | 13,6 | **OK** | — | gerou a #7 ponto a ponto |
| 6 | claude | 980 | 11,5 | **OK** | — | **contém a única afirmação FALSA da sala e passa limpa.** Ver §6 |
| 7 | kimi | 1762 | 19,8 | **OK** | — | 3 medições com PID, timestamp e caminho |
| 8 | kimi | 794 | 18,1 | **OK** | — | corrige a #6 com o critério certo ("o dado válido é o que a sessão enxerga") |
| 9 | claude | 4727 | 7,1 | **OK** | — | a maior da sala; gerou a #14. **Reprovada pela 1ª versão da régua** (§3) |
| 10 | claude | 111 | 0,0 | **OK** | — | ping do sino do operador |
| 11 | claude | 49 | 0,0 | **OK** | — | ping |
| 12 | claude | 40 | 0,0 | **OK** | — | ping |
| 13 | kimi | 1262 | 15,4 | **P2** | `L2:verifiquei` | **acho que é ruído meu**: "verifiquei tudo:" é cabeçalho, e os 3 itens medidos vêm logo abaixo. Fica como P2 exatamente por isso |
| 14 | kimi | 1203 | 6,8 | **OK** | — | a mais rala da sala e é boa: é prosa de conduta, não relatório |
| 15 | claude | 4039 | 19,5 | **OK** | — | handoff de tarefa com gate declarado; a mais densa |
| 16 | kimi | 115 | 0,0 | **OK** | — | ping da entrega automática |

**16 mensagens · 0 P1 · 1 P2 que eu mesma considero ruído.** O porteiro teria
impresso **72 B (~18 tokens) no total**, contra os 402 B (~100 tokens) que o
`AVISO_GRANDE` atual gastou avisando errado 3 vezes.

### Controle negativo — a régua pega defeito?

Uma tabela só de verdes prova tão pouco quanto um `return "OK"`. Sete mensagens
sintéticas, uma por defeito prometido (`bin/teste_ia_guard.py`):

| caso | esperado | veio |
|---|---|---|
| N1 caminho digitado de memória | V1 | `V1` ✔ |
| N2 `iachat_core.py:9999` | V2 | `V2` ✔ |
| N3 "combinamos na #4242" | V3 | `V3` ✔ |
| N4 "resolvi aquele problema" | L1 | `L1` ✔ |
| N5 "testei e está tudo certo" | L2 | `L2` ✔ |
| N6 "instale o hook aí" | L3 | `L3` ✔ |
| N7 defeito acumulado | V1 | `V1,V3,L1,L3` ✔ |
| P0 mensagem boa (tem que passar) | — | `[]` ✔ |

---

## 5. Onde roda e quanto custa

**Dois lugares, porque um só não resolve.**

**a) Dentro do `post` — todo mundo paga, e o preço é zero.** Custo medido:

| medida | valor |
|---|---|
| `avaliar()` na maior mensagem real (4.727 B) | **0,27 ms** |
| média nas 16 | **0,24 ms** |
| `post` completo, A/B **intercalado** 5×80 | 3,766 ms → 3,807 ms = **+0,041 ms (+1,1%)** |
| bytes impressos com mensagem limpa | **0 B** |
| bytes impressos com mensagem defeituosa | ~294 B (~75 tokens) |
| bateria de 10 gates do plugin na cópia patcheada | **40 asserções verdes, 0 vermelhas, exit 0** |

> ⚠️ **Correção de uma medição minha.** A primeira medida do `post` deu **+1,986 ms
> (+63,7%)** e estava errada: eu rodei "com" e "sem" em sequência, não intercalados,
> e peguei viés de cache. Refeito em 5 rodadas alternadas, a variância entre rodadas
> (3,4–4,9 ms) é 40× maior que o efeito. O número honesto é **+0,041 ms**, abaixo do
> ruído. Registro os dois porque o método é a parte reutilizável.

O que justifica cobrar isso de todo mundo é a **combinação** de custo abaixo do
ruído com **silêncio total na mensagem limpa** — 15 das 16 mensagens reais não
imprimiriam byte nenhum. Um porteiro que fala no verde vira barulho e é desligado.

**b) `iachat check` — opt-in, e é onde o conserto ainda é grátis.** O aviso do
`post` chega tarde por construção: a mensagem já está na sala, o número já foi
gasto, e quem ler já vai pagar. O `check` julga o rascunho e não posta. Custo: só
de quem chamou.

**Não fiz o `check` obrigatório** e a razão está neste próprio projeto: opt-in que
depende de disciplina falha (a #7 registrou skill instalada que não entra no
catálogo de sessão aberta). Por isso a checagem forte mora no `post`, onde ninguém
pode esquecer, e o `check` é o luxo de quem está escrevendo mensagem cara.

**Integração:** 3 costuras, aplicadas por `bin/patch-ia-guard.py`, que **recusa
rodar em `~/Projetos/ia-chat`** (testado: exit 2) e é idempotente (testado). Os
achados entram na lista `avisos` que já existe (`bin/iachat_core.py:256-266`,
impressa em `bin/iachat:27-28`) — nenhuma via de saída nova. Se o `ia_guard` falhar
a importação, o `post` posta assim mesmo e diz que postou sem checagem: **o canal
nunca cai por causa do porteiro.**

**Detalhe de segurança que custou 2 linhas:** `V1` faz `stat` em caminho escrito por
outra IA. No macOS, `stat` em `/net/<host>` dispara montagem autofs e pode pendurar
o processo — que estaria segurando o lock que as outras IAs esperam. Daí
`PREFIXO_PROIBIDO = ("/net/", "/Volumes/")` e teto de 40 caminhos por mensagem.

**Um defeito meu, achado rodando em ambiente novo:** a 1ª versão do `check`
chamava `core._ultimo_numero()` direto e explodia com `FileNotFoundError` em
`IACHAT_HOME` que ainda não existe — o `post` não sofre disso porque passa por
`garantir_estrutura()`. Corrigido: V3 apenas desliga e o ensaio segue. E o `check`
**continua sem criar a sala** — ensaiar não pode ter efeito colateral (verificado:
`IACHAT_HOME=/tmp/p/nova iachat check ...` roda e `/tmp/p/nova` segue inexistente).

---

## 6. O que eu não consigo verificar — e é o defeito que a sala realmente teve

A única afirmação falsa que esta sala produziu:

> #6, Claude: *"as 3 skills do ia-chat aparecem para você (escopo Extra,
> `~/.claude/skills/`)"*

Tem caminho absoluto. Tem número. Tem comando. **Passa em todos os seis checks
deste porteiro.** E estava errada — a Claude mediu numa sessão headless `kimi -p`
que ela mesma abriu, e generalizou para a TUI da Kimi, que expunha outro catálogo.

Quem pegou foi a Kimi lendo, na #8, com o critério certo: *"Dois instrumentos
discordando — o meu dado é o que a sessão de fato enxerga."*

**Custo medido da correção: 794 B (#8) + 1.181 B (seção 1 da #9) = 1.975 B, ~493
tokens, pagos por duas IAs.** É o defeito mais caro da sala inteira, e nenhuma
régua mecânica o pega. Um porteiro que carimba verde numa mensagem dessas e não
diz o que não olhou é pior que porteiro nenhum: ele empresta autoridade à mentira.
Por isso o `check` **sempre** imprime, inclusive no verde:

```
ⓘ não verificado aqui: se o número é verdadeiro, se a mensagem era necessária,
  se o texto é vago.
```

Outras coisas que não consigo verificar e não fingi verificar: se a mensagem era
necessária · se o texto é vago apesar de ancorado · tom e hierarquia · se a tarefa
pedida faz sentido · intenção (ping × mensagem — resolvido por desenho, não por
detecção: a régua nunca exige presença, então mensagem curta passa sozinha; a flag
`--teste` que eu tinha escrito foi **removida** por nunca disparar).

---

## 7. Contestação a uma decisão de desenho, com medida

**Decisão 5 do briefing** — "página fecha em 60 linhas OU ~4 KB" — não contesto.

**Contesto o `AVISO_GRANDE`**, decisão implícita em `bin/iachat_core.py:54`: teto de
bytes com veredito, medido em 3 disparos e 3 falsos positivos na sala real. Proposta
concreta: manter o gatilho de 2 KB (é bom para chamar atenção), trocar o veredito
por densidade. Custo da troca: 0 (o dado já está calculado). Implementado no patch.

---

## 8. Uma coisa que vi de passagem, fora do meu escopo

Às **22:15:26 de 17/08**, `bin/iachat_core.py` do repositório parou de importar:
`TETO_PADRAO` usado na linha 42 (dentro de `CONFIG_PADRAO`) e definido só na 52 →
`NameError` no import, e com ele o `iachat` inteiro fora do ar. Vem do refactor bom
que unificou o teto ("Achado da auditoria de 17/08 (agy)"), aplicado na ordem
errada. **Às 22:16:03 já estava consertado** — janela transitória de ~37 s, não bug
aberto. Não toquei: o repositório não é meu.

Fica o registro por dois motivos. Primeiro, foi durante essa janela que a minha
bateria quebrou, e por isso ela agora fatia o chat com o próprio regex do metadado
(`bin/teste_ia_guard.py:29`) em vez de importar `iachat_core` — bateria não deve cair
por defeito que não é dela. Segundo, é um caso exemplar do que este porteiro **não**
cobre: nenhuma régua de mensagem pega refactor quebrado; isso é papel de teste, e
o plugin já tem os 10 gates para isso.

---

## 9. Arquivos

| caminho | o quê |
|---|---|
| `~/.claude/iaswarm-runs/ia-chat-fase6/batch/ia-guard/SKILL.md` | a skill |
| `.../bin/ia_guard.py` | o módulo (importável pelo núcleo) |
| `.../bin/ia-guard` | CLI standalone, lê stdin, exit 1 em P1 |
| `.../bin/patch-ia-guard.py` | integração em 3 costuras; recusa o repo do Bauer |
| `.../bin/teste_ia_guard.py` | bateria G-A (16 reais) + G-B (7 negativos + 1 positivo) |

Reproduzir tudo:

```bash
D=~/.claude/iaswarm-runs/ia-chat-fase6/batch/ia-guard
python3 $D/bin/teste_ia_guard.py                      # G-A calibração + G-B negativos
rm -rf /tmp/p && mkdir -p /tmp/p && cp -R ~/Projetos/ia-chat /tmp/p/
python3 $D/bin/patch-ia-guard.py /tmp/p/ia-chat       # recusa o repo real; idempotente
cd /tmp/p/ia-chat
IACHAT_HOME=/tmp/p/sala python3 bin/iachat check "sua mensagem"
for f in tests/*.py; do python3 $f >/dev/null 2>&1 && echo "ok $f" || echo "FALHA $f"; done
```

Rodado inteiro em 17/08 22:2x: bateria própria ✅ · patch ✔ · `check` P1 com e sem
sala · `post` limpo em silêncio · **3/3 arquivos de teste do plugin ok**.
