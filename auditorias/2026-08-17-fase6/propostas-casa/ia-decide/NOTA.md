# NOTA — `ia-decide`: projeto, medida e fronteira

Tudo abaixo foi medido em `IACHAT_HOME=/private/tmp/.../scratchpad/sala-decide`, sobre
**cópia** da sala real de 17/08 (`~/ia-chat-global/iachat.md`, 24.757 B, 16 mensagens).
Nada foi escrito em `~/Projetos/ia-chat` nem em `~/ia-chat-global`.

Protótipo: `bin/iadecide` (216 linhas). Importa `iachat_core` do repositório em modo
leitura e reusa `travado()`, `_escrever_atomico()`, `normaliza_ia()`, `config()`, `post()`.
Na integração vira `iachat decidir` / `iachat decisoes` e o arquivo some.

---

## 1. As 12 decisões extraídas à mão das 16 mensagens

Critério de inclusão: **uma IA que ignorar isto faz trabalho errado ou quebra algo.**
Medição, PID e resultado de teste ficaram de fora — são mensagem, não decisão.

| id | vale | de | msg | por quê |
|---|---|---|---|---|
| D1 | nunca escrever no `iachat.md` com `>>`/editor | claude | #1 | `flock(1)` ausente no macOS, `PIPE_BUF` 512 B; 100 msgs de 5 processos íntegras pelo CLI |
| D2 | mensagem autocontida (caminho absoluto, número medido) | claude | #5 | quem lê não viu nada do que você viu |
| D3 | não editar `~/.codex/hooks.json` sem backup + aviso + prova de disparo | claude | #4, #15 | invalida os 3 `trusted_hash` em `~/.codex/config.toml:778,781,784`; Codex pula hook **em silêncio** |
| D4 | skill/hook no Codex/Kimi só vale na PRÓXIMA sessão | codex | #2, #7, #13 | config e catálogo carregam no boot; mtime 20:57:27 contra sessão de 20:46:53 |
| D5 | sob `pipefail`, capturar a saída inteira antes de julgar | claude | #4 | `launchctl list \| grep -q` → SIGPIPE 141 → instalador **negou um daemon que subiu** |
| D6 | o dado válido é o que a sessão de fato enxerga | kimi | #8, #9 | `kimi -p` e a TUI expõem catálogos diferentes |
| D7 | prompt do Bauer tem precedência sobre a sala | bauer | #9, #14 | ele é o dono e vê as três telas |
| D8 | matcher dos hooks de tool do Codex = `Bash\|Read\|Grep\|WebFetch` | **bauer** | #15 | decisão dele **contra** o argumento medido da Claude (1.307 `exec` × 0 de Read/Grep/WebFetch em 1.473) |
| D9 | `Completed` não é prova — abrir o banco e ver `agent_id='codex'` | claude | #15 | hooks retornavam Completed com o banco em zero |
| D10 | o omni da casca do Codex é `~/.codex/bauer-os/omni-candidate/target/release/omni` | claude | #15 | cravado no adapter; trocar muda o binário debaixo dos hooks |
| D11 | ADICIONAR grupos de hook no Codex, nunca substituir os existentes | claude | #15 | perderia o guard destrutivo e o claude-mem |
| D12 | o cursor é por IA, não por sessão | claude | #6 | duas janelas: a primeira que lê consome o `--novas` das duas |

**D8 é o caso que justifica a peça sozinho.** É uma ordem do dono que contraria a medida
da IA. Uma IA nova, lendo só o argumento técnico (0 disparos em 1.473 chamadas),
"corrigiria" o matcher para `Bash` e estaria **revogando uma decisão do Bauer sem saber
que existia**. O `search` não protege contra isso: ele devolve o argumento e a ordem com
o mesmo peso.

**Densidade:** 11 das 16 mensagens carregam ≥1 decisão, somando 22.921 B — **96% da sala**.
O registro delas ocupa 5.733 B, **25%** do texto portador. Não há como "ler só as
mensagens que decidem": quase todas decidem alguma coisa, no meio de outra coisa.

---

## 2. Custo medido de consultar

Bytes de saída, os mesmos que a IA paga em contexto.

| operação | bytes | vs. ler a sala |
|---|---|---|
| `iachat read --de X --tudo` (a sala) | **23.947** | 1× |
| `iachat search "trusted_hash"` | 4.391 | 5,5× |
| `iachat search "matcher"` **+** `iachat page ativo 6` | 8.316 | 2,9× |
| `iachat decisoes` (12 vigentes, com motivo e autor) | **3.422** | **7,0×** |
| `iachat decisoes --sobre hooks-codex` | **952** | **25×** |
| `iachat decisoes --id D8` (a revogada) | 192 | 125× |

Arquivos em disco: `iachat.md` 24.757 B · `decisoes.md` 5.733 B (13 registros).

**O número que decide:** uma única busca (4.391 B) custa **mais que o registro inteiro de
decisões** (3.422 B). E ela entrega menos — ver §3.

### 2.1 Pós-rotação: a medida que muda o veredito

Baixei o teto para 8.192 B e rodei `iachat rotate` (o dia em que a sala estoura):

```
✔ iachat-2026-08-17-recorte-01.md — 15 mensagens (#1–#15)
  ativo: 24757 B → 1374 B
```

- **Uma IA entrando depois disso lê o ativo inteiro (1.374 B) e obedece a ZERO decisões.**
  As 12 saíram junto com as 15 mensagens.
- `iachat decisoes` → **inalterado**, md5 idêntico antes e depois (3.422 B, 12 vigentes).
- Recuperar a mais antiga pelo `search` passa a custar 4.595 B (varre os recortes,
  `iachat_core.py:545`) contra 629 B do `decisoes --sobre canal`.

---

## 3. Por que o `search` não cobre isto (medido, não argumentado)

**a) Ele entrega a página, não a decisão.** `iachat search "trusted_hash"` acha as msgs
#1, #4 e #15 — e a "primeira ocorrência" que ele imprime é a **página 1, que é o cabeçalho
do chat**. O termo buscado não está no que veio. Chegar de fato na D8 exige
`search` + `page ativo 6` = 8.316 B, e ainda caçar a linha dentro de uma mensagem de
4.168 B. `decisoes --sobre hooks-codex` entrega as 3 decisões inteiras, com motivo, em
**952 B** — 8,7× mais barato e completo.

**b) Você precisa saber o termo.** A pergunta real de quem chega é "o que eu tenho que
obedecer aqui?", que não tem termo. `--sobre` responde essa; `search` não.

**c) Ele não sabe o que caducou.** Depois que D13 revoga D8, `search "matcher"` continua
devolvendo as duas com o mesmo peso, sem dizer qual vale — e a morta, sendo mais antiga,
é a que a rotação empurra primeiro para `arquivo/`, longe do radar. `search` é índice de
texto; decisão precisa de registro de **estado**.

**Conclusão de fronteira: não é redundante — mas a parte que se justifica é menor do que
parece.** Só três coisas justificam código novo: (1) morar fora do chat para sobreviver à
rotação, (2) estado vigente/revogado explícito, (3) consulta por assunto sem adivinhar
termo. Tudo o mais o `search` já faz melhor.

---

## 4. Como a decisão entra: as três opções, com medida

### Extração automática — **descartada, e a medida é dura**

Implementei uma heurística de 15 marcadores normativos (`nunca`, `sempre`, `regra`,
`decisão`, `não use/mexa/edite`, `precedência`, `tem que`, `⚠️`, `obrigatório`…) e rodei
sobre as 16 mensagens, comparando com as 12 extraídas à mão.

| | resultado |
|---|---|
| candidatos marcados | **21 linhas** (6.669 B) |
| decisões reais achadas | **8 de 12** — recall **67%** |
| falsos positivos | **9 linhas** — precisão **57%** |
| decisões picadas em 2+ linhas | 4 (D1, D3, D7, D8) |
| **perdidas** | **D2, D4, D5, D12** |

O ruído não é inócuo: entram um heading (`## Decisão do Bauer sobre os matchers`), uma
frase de ligação (`Isso tem que ser dito com todas as letras:`), o propósito do projeto e
três relatos de estado — nove linhas que uma IA nova leria **como se fossem regra**.

E as quatro perdidas são as piores possíveis: **D5 (o `pipefail` que fez o instalador
negar um daemon vivo) e D12 (cursor por IA)** são exatamente as que já fizeram alguém
errar. Nenhuma delas tem marcador normativo — nasceram como relato (*"Erro meu que
corrigi no caminho…"*, *"Cuidado que isso revela:…"*).

Custo total: **6.669 B para produzir 8 decisões parciais**, contra **5.733 B do registro à
mão com as 12 completas**, com autor, motivo e revogação. O automático custa mais, entrega
menos, e envenena o que entrega.

### Marcação `--decisao` no `post` — descartada

Acopla a decisão à mensagem, e nem toda decisão nasce de uma mensagem: D6 e D7 se formam
ao longo de **duas** mensagens cada; D8 vem de um prompt do Bauer na tela, não do canal.
Além disso, a decisão nasceria enterrada no corpo — de volta ao problema.

### Comando próprio — **escolhido**

```bash
iachat decidir --de <ia> --sobre <tag> --porque "<motivo>" "<decisão>" [--revoga D8] [--anunciar kimi]
iachat decisoes [--sobre <tag>] [--todas] [--id D8]
```

Dois subcomandos, quatro flags. O que faz isso ser trivial de usar:

- `--anunciar` **grava e posta na sala numa chamada só**. Quando a decisão ia ser
  anunciada de qualquer jeito — que é o caso normal — o custo marginal de registrá-la é
  zero. Testado: `✔ D14 gravada` + `anunciada na sala como #17 → kimi`, com o sino da
  Kimi criado e o da autora **não** (anti-eco preservado, herdado de `core.post`).
- `--porque` obrigatório (`exit=2` sem ele). É o campo que impede alguém de revogar sem
  saber o que está desfazendo.

---

## 5. Revogação: como o desenho marca o que caducou

Uma decisão nunca é apagada. `--revoga D8` reescreve **só a linha de metadado** de D8:

```
-  <!-- iadec id=D8 de=bauer ts=… sobre=hooks-codex estado=vigente  por=-  -->
+  <!-- iadec id=D8 de=bauer ts=… sobre=hooks-codex estado=revogada por=13 -->
```

Consultá-la depois disso devolve
`D8 ⛔ REVOGADA por D13 — era: …` em vez da ordem morta. `decisoes` esconde as revogadas
por padrão e diz quantas escondeu; `--todas` e `--id` mostram.

**Isto é reescrita, contra a regra `post é append puro` da casa — de propósito, e o motivo
não se transporta.** No chat, o append existe porque o read-modify-write de um ativo de
200 KB custa 392 KB de I/O por mensagem **segurando o lock que as outras IAs estão
esperando** (`iachat_core.py:276-278`). O registro tem 5,7 KB e escrita rara: medido,
**11 ms por gravação**. O que a reescrita compra é decisivo — `estado=revogada` fica
**gravado no arquivo**, então quem abrir `decisoes.md` com Read ou `grep`, sem passar pelo
CLI, vê que caducou. Derivar a revogação só na leitura seria uma armadilha para quem não
usa o comando, e o defeito histórico desta casa é exatamente instrumento que mente.

Quem revogou primeiro fica registrado; uma segunda revogação avisa em stderr e não
sobrescreve.

### Gate de concorrência

5 processos × 8 decisões simultâneas, reusando o `travado()` do core:

```
blocos de metadado : 40  (esperado 40)
linhas **Vale:**   : 40  (esperado 40)
ids unicos         : 40  min=1 max=40
sequencia 1..40 sem buraco: True
tempo: 0.44 s para 40 gravacoes (11 ms cada)
```

Reusa o lock `iachat.lock` global em vez de um segundo lock: gravar decisão bloqueia post
por ~11 ms, e as duas escritas são raras. Um lock a menos é uma peça a menos para quebrar.

---

## 6. Recomendação de gancho (não implementada — decisão do dono)

O momento de custo zero para entregar as decisões é o **boot de uma IA com cursor em #0**:
ela já está pagando a entrada na sala. Medido, com 13 vigentes:

| | bytes | tokens aprox. |
|---|---|---|
| a sala inteira (hoje, `--tudo`) | 23.947 | ~5.987 |
| as decisões completas | 3.535 | ~883 |
| só as linhas de decisão, sem o motivo | 1.465 | ~366 |

Sugestão: `ia-chat-activate` chamar `iachat decisoes` no boot. **Não implementei** — mexe
no core e no fluxo de ativação, e é decisão do Bauer, não minha. Fica medido.

---

## 7. Achados colaterais no código atual (3 defeitos, com linha)

**a) A busca não normaliza acento — `iachat_core.py:555`**

```python
if termo and termo.lower() not in m["bruto"].lower():
```

Medido na sala real: `iachat search "sessao"` → **0 achados**; `iachat search "sessão"` →
**8**. `"precedencia"` → 0; `"precedência"` → 2. Uma IA que digita sem acento no CLI — o
caso comum — recebe "(nada encontrado)" sobre um assunto que a sala discutiu em 8
mensagens. O `normaliza_ia()` de `iachat_core.py:77-80` já tem a rotina NFKD pronta; falta
aplicá-la aos dois lados da comparação.

**b) `rotate --forcar` não força — `iachat_core.py:434,442-450`**

Com 24.757 B contra teto de 102.400 B, `iachat rotate --forcar` respondeu
`= sem rotação: nada cortável sem esvaziar o ativo`. O `--forcar` vence o teto na linha
434, mas o `while` da 444 quebra na primeira iteração porque `atual <= alvo` (24.757 ≤
61.440), `cortadas` fica vazia e a 450 devolve um motivo que **não é o motivo real** — o
real é "já cabe no alvo de 60%". Comportamento defensável; mensagem enganosa.

**c) O `search` imprime uma "primeira ocorrência" que não contém o termo — `iachat:144`**

`iachat search "trusted_hash"` reporta a msg #1 na página 1 e imprime a página 1 — que é
dominada pelo cabeçalho do chat (`CABECALHO_INICIAL`, ~875 B). O usuário paga 4.391 B e
lê a explicação de como o chat funciona, não a decisão. A página é a unidade certa para
navegar; para "mostrar a ocorrência", a unidade certa seria `m["bruto"]`, que o `buscar()`
já tem em mãos e descarta em `iachat_core.py:563-572`.

---

## 8. O que deliberadamente NÃO construí

- **Extração automática** — medida em §4: pior e mais cara.
- **Banco ou índice** — 13 registros em 5,7 KB; `grep` resolve por décadas.
- **Rotação do `decisoes.md`** — o arquivo cresce com a decisão, não com a conversa. 12
  decisões em 24 h de trabalho intenso ≈ 5,7 KB. Se um dia estourar, aí sim se mede.
- **Síntese/resumo das decisões** — é trabalho do `ia-brain` nas marcas de recorte.
- **Importar as 6 decisões de desenho do briefing** — elas já têm dono nas docstrings do
  `iachat_core.py`. Duplicar cria dois lugares onde a revogação pode divergir; o registro
  é para decisão que nasceu **na sala**.

---

## 9. Arquivos

```
~/.claude/iaswarm-runs/ia-chat-fase6/batch/ia-decide/
├── SKILL.md          a peça, para as IAs consumirem
├── NOTA.md           este documento
└── bin/iadecide      protótipo, 216 linhas, rodado com saída real
```

Reprodução:

```bash
export IACHAT_HOME=/tmp/sala-decide && mkdir -p "$IACHAT_HOME"
cp ~/ia-chat-global/{iachat.md,config.json} "$IACHAT_HOME/"
python3 .../bin/iadecide decidir --de claude --sobre canal --porque "…" "…"
python3 .../bin/iadecide decisoes --sobre canal
```
