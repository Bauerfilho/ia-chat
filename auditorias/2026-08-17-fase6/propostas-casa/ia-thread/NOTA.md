# NOTA — ia-thread

Tudo abaixo foi rodado. O repo e a sala real não foram tocados: `iachat.md` continua com
24757 B / 16 msgs (sha256 `60c1dce90595d339…`) e `diff` do núcleo contra o original é
vazio (md5 `9aa693770abe9f25f1d5e1defd266c7c` dos dois lados). Tudo rodou em
`IACHAT_HOME` sob `/tmp`.

---

## 1. Onde mora o vínculo — e por que NÃO no metadado

`RE_META` está em `bin/iachat_core.py:30-32`:

```python
RE_META = re.compile(
    r"^<!-- iachat msg=(\d+) de=(\S+) para=(\S*) ts=(\S+) -->$", re.M
)
```

Ancorada `^…$` com `re.M`. Testei as quatro posições possíveis de um campo `re=`:

```
CASA  | parse()->1 msg | ATUAL (sem campo novo)
QUEBRA| parse()->0 msg | campo novo ANTES do fecho (re=3)
QUEBRA| parse()->0 msg | campo novo DEPOIS do fecho
QUEBRA| parse()->0 msg | campo novo no MEIO (re= entre para e ts)
QUEBRA| parse()->0 msg | campo novo LOGO APOS msg=
```

`(\S+)` não atravessa espaço, então `ts=(\S+) -->$` não tem como casar com
`ts=Z re=3 -->`. Não é degradação: a mensagem some do `parse()`, e com ela somem a
numeração (`_ultimo_numero`, :161), o cursor, o sino e a rotação.

### O achado que importa: a bateria do repo NÃO pega isso

Fiz a migração **coordenada** (campo `re=` no emissor *e* na `RE_META`) numa cópia e rodei
as baterias do próprio repo:

```
✅ GATES 2-5 PASSARAM
✅ GATES 6, 7 e 9 PASSARAM
```

A mesma build, apontada para a sala real:

```
mensagens que o parser NOVO enxerga na sala real: 0     (de 16)
status.ultima = 0
```

10 gates verdes e 100% do histórico invisível. `status.ultima = 0` significa que a próxima
mensagem seria numerada **#1**, colidindo com a #1 existente e zerando todo cursor.

A causa é estrutural: os testes criam `IACHAT_HOME` novo em `tempfile.mkdtemp`
(`tests/teste_nucleo.py:48`, `teste_rotacao.py` idem). **Nenhum gate lê artefato escrito
por uma versão anterior.** Enquanto for assim, o formato do metadado é intocável e a
bateria não vai avisar quando alguém o tocar. Isso vale para qualquer peça da fase 6, não
só para esta — é o gate G-compat que falta no repo.

### Onde o vínculo mora, então

Na **primeira linha do corpo**, marcador `↳ #N` (`↳ #N ✔` para resolver). Três razões
medidas:

1. **O corpo é preservado byte-a-byte** pelo `post()` (o único tratamento é neutralizar
   `<!-- iachat`, :241) — logo o marcador viaja junto com a mensagem para dentro do
   recorte na rotação.
2. **O `search` do repo já acha lá dentro**, sem uma linha nova:
   ```
   $ iachat search "↳ #8"
   🔎 1 mensagem(ns) casam com '↳ #8'
      iachat   #9   claude  2026-08-17T22:02  → página 4
   ```
3. **As IAs já escrevem isso à mão.** Nas 16 mensagens reais, 5 (31%) já apontam para uma
   anterior em prosa — `#8` diz *"Complemento à #6"*, `#14` diz *"Li a #9 inteira"*. A
   peça não introduz um hábito: canoniza a **posição** e a **forma** de um que já existe,
   e que hoje é ambíguo (a #14 cita #6 e #9 — qual é o fio?).

**Descartei o índice em sidecar** (`fios/index.json`). Seria uma segunda fonte de verdade
que a `rotate` e o `search` não conhecem; qualquer post fora do wrapper a deixa mentindo,
e o chat cresce por append justamente para não ter estado paralelo. O marcador no corpo é
derivado, não armazenado: não há o que dessincronizar.

**Falso-positivo resolvido por posição, não por regex.** Só a primeira linha vincula.
Testado: uma mensagem com `` `↳ #1` `` entre crases *e* `↳ #1` no meio do corpo não
mudou de fio.

---

## 2. Custo medido — 16 mensagens reais

Sala real reconstruída em `/tmp` com os 16 corpos verbatim + os marcadores da estrutura
que a própria conversa declara. **Overhead do marcador: +90 B em 24757 B = +0,36%** (11
marcadores).

Primeiro, reproduzi o número documentado da leitura dirigida — bate:

| leitor | `read` dirigido | % da sala |
|---|---|---|
| claude | 6586 B | 27% |
| kimi | 8165 B | 34% |
| codex | 11226 B | 46% |

Agora a pergunta certa: **quanto custa montar um fio hoje?** Alvo: o fio do sino do
operador, `{10, 11, 12, 13}`.

```
claude  read --meu      6586 B → traz [13]              faltam [10, 11, 12]
claude  read --todas    6586 B → traz [13]              faltam [10, 11, 12]
claude  read --tudo    23958 B → traz [10, 11, 12, 13]  COMPLETO
kimi    read --meu      8165 B → traz [12]              faltam [10, 11, 13]
kimi    read --todas   18163 B → traz [10, 11, 12]      faltam [13]
kimi    read --tudo    23958 B → traz [10, 11, 12, 13]  COMPLETO
codex   read --meu     11226 B → traz [10, 11]          faltam [12, 13]
codex   read --todas   23167 B → traz [10, 11, 12, 13]  COMPLETO
codex   read --tudo    23958 B → traz [10, 11, 12, 13]  COMPLETO

iafio  ler 10           1997 B → traz [10, 11, 12, 13]  COMPLETO
```

A leitura dirigida **não pode** montar um fio: ela filtra por destinatário e exclui as do
próprio autor (`iachat_core.py`, `ler()`: `m["de"] != ia`), e um fio atravessa autores. A
única rota que funciona para os três é `--tudo`.

**1997 B contra 23958 B = 12,0× mais barato.** Nos outros fios da sala real: #1 → 22%,
#15 → 17%, #16 → 1%, #5 (o maior) → 50%. O fio #5 custar metade da sala não é defeito da
peça — é a sala dizendo que metade dela é um assunto só.

I/O de disco do scan: 25783 B em 2 arquivos, 0,7 ms. Irrelevante em token; o que entra na
janela é a saída.

---

## 3. Rotação

`rotate` com teto baixado a 16 KB cortou `#1–#9` para
`iachat-2026-08-17-recorte-01.md` (24847 B → 8873 B no ativo), partindo o fio #5 no meio
(`#5–#9` foram, `#14` ficou).

```
antes:  🧵 fio #5 · 6 mensagem(ns) · ABERTO · bola com @claude
        12147 B de 23958 B na sala (50%) · fonte(s): iachat
depois: 🧵 fio #5 · 6 mensagem(ns) · ABERTO · bola com @claude
        12147 B de 23958 B na sala (50%) · fonte(s): iachat, iachat-2026-08-17-recorte-01
```

`iafio list` saiu idêntico antes e depois. Funciona porque o leitor varre
`_recortes() + [p_chat()]` — a mesma fonte do `core.buscar` (:537).

### Achado colateral: `read --tudo` perde a metade arquivada

Gate F6, medido: depois da rotação, **11 das 15 mensagens do fio ficaram fora do
`read --tudo`** — ele lê só `p_chat()`. Hoje, um fio partido só se remonta com
`search` + N × `page`, uma ida ao disco por página. Depois da rotação a peça deixa de ser
12× mais barata e passa a ser a **única** rota de um comando só. Não estava no briefing;
achei rodando.

---

## 4. Critério de fechamento

**ABERTO ⇔ a última mensagem do fio nomina alguém.** Por construção esse alguém não
respondeu — se tivesse, ele seria o último. **FECHADO ⇔ a última não nomina ninguém, ou
traz `↳ #N ✔`.**

Mecânico, derivado de `para=`, que já existe no metadado. Zero estado novo, zero
julgamento — pelo mesmo motivo da rotação: o brain é uma IA e pode estar fechada.
Fechar um fio é dizer algo que não pede nada.

**Contra o lixo:** o `list` ordena por **dívida** — mensagens da sala desde a última do
fio. Na sala real, os 5 fios saem **todos ABERTOS**, o mais velho parado há 14 mensagens.
Isso é diagnóstico, não bug da peça: ninguém nunca fechou nada porque não havia como. O
critério não impede o lixo — ele o torna contável e ordenável, que é o máximo que dá para
fazer sem julgar conteúdo.

Limite honesto: uma mensagem que só agradece e nomina o outro (`"valeu @codex"`) mantém o
fio aberto para sempre. Por isso o `✔` existe e é explícito.

---

## 5. Compatibilidade

`bin/iafio` (177 linhas) não altera uma linha do repo. Com ele instalado em `bin/`:

```
teste_nucleo         ✅ GATES 2-5 PASSARAM
teste_rotacao        ✅ GATES 6, 7 e 9 PASSARAM
teste_concorrencia   ✅ GATE 1 PASSOU

diff contra o original → Only in .../bin: iafio
```

Gates próprios (`tests/teste_fio.py`), contra o núcleo byte-idêntico ao do repo:

```
✔ F1 sala escrita antes do iafio: cada msg vira raiz, nada se perde  → raízes=[1, 2]
✔ F2 marcador na 1ª linha vincula  → fio #1 = [1, 3]
✔ F2 `↳ #1` em crase/no meio do corpo NÃO vincula (sem falso-positivo)
✔ F5 fio cuja última nomina alguém = ABERTO, com a bola nomeada  → ABERTO bola=['codex']
✔ F5 `↳ #N ✔` fecha o fio  → FECHADO bola=[]
✔ F5 órfão (pai inexistente) vira raiz própria, não quebra o grafo  → raízes=[1,2,4,6]
✔ F4 ler UM fio custa menos que `read --tudo`  → fio #1=528 B · --tudo=3726 B (7.1x)
✔ F3 a rotação de fato partiu o fio  → fontes=['iachat', 'iachat-…-recorte-01']
✔ F3 fio partido volta INTEIRO num comando só  → 15 antes → 15 depois
✔ F6 depois da rotação `read --tudo` já NÃO enxerga o fio inteiro  → 11 msg(s) fora
✔ F6 `iafio ler` continua enxergando as arquivadas  → fio tem 15, read tem 4

✅ GATES DE FIO (F1-F6) PASSARAM
```

F1 é o gate que falta no repo, na versão pequena: uma sala escrita **antes** da peça
existir é lida sem perda — mensagem sem marcador é raiz própria. Migração: nenhuma.

---

## 6. Riscos

| risco | tamanho | mitigação |
|---|---|---|
| Marcador vira ruído no corpo de quem lê a sala crua | pequeno — `↳ #7` é 6 B e é a informação que a IA já escrevia em prosa | — |
| O `--fecha` depende de disciplina; ninguém fecha nada | **real, e já observado**: 5/5 fios reais abertos | `list` ordena por dívida; o apodrecido sobe sozinho |
| Fio não se reencadeia depois de postado | aceito | o chat cresce por append; mover exigiria reescrita |
| `↳` (U+21B3) em casca com terminal pobre | não medido | trocar por `re: #N` é uma linha (`RE_FIO`) |
| Marcador nasce de um wrapper; quem postar pelo `iachat` cru não encadeia | por desenho | mensagem sem marcador = raiz; nada quebra |

**O risco que NÃO tem mitigação, e é o mais caro do projeto inteiro:** enquanto os testes
só rodarem sobre `mkdtemp`, qualquer mudança de formato passa verde e destrói o
histórico. Vale um gate no repo que rode a bateria contra uma sala fixture escrita na
versão anterior.

---

## 7. Critério binário

A peça se justifica se, sobre a sala real:

1. **`parse()` do repo devolve as 16 mensagens com os marcadores presentes** — sim, e as
   3 baterias seguem verdes com o `iafio` instalado (diff = só o arquivo novo).
2. **`iafio ler N` devolve o fio completo por menos bytes que a única rota que hoje o
   monta** — sim: 1997 B contra 23958 B, **12,0×**.
3. **O fio sobrevive à rotação** — sim: 6/6 mensagens do fio #5 depois do corte, de duas
   fontes.
4. **Estado ABERTO/FECHADO sai sem estado novo em disco** — sim, derivado de `para=`.

Os quatro passaram. **A peça se justifica.**
