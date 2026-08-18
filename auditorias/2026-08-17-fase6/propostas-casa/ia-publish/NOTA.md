# ia-publish — prontidão do `ia-chat` para o GitHub

**Veredito:** o repositório está tecnicamente pronto e documentalmente acima da
média de repo pequeno. Falta pouco, mas o pouco que falta é do tipo que não dá para
consertar depois: **licença**, **um e-mail pessoal em texto plano** e **um `<este
repo>` que não é clonável**. Nada aqui exige refazer trabalho — o total soma menos
de uma hora, e mais da metade é `cp`.

Tudo abaixo foi medido nesta máquina em 2026-08-17. Nada foi escrito em
`~/Projetos/ia-chat`; o único ensaio de git rodou numa cópia `cp -R` no scratchpad.
O bytecode que a minha própria verificação gerou foi removido — o repositório está
exatamente como estava.

---

## Checklist de prontidão

### 🔴 Bloqueia publicar

| # | item | por que importa | custo |
|---|---|---|---|
| 1 | **`LICENSE` não existe** | sem arquivo de licença o padrão legal é *todos os direitos reservados*: o código fica visível e ninguém pode usar. Um repo público sem LICENSE é um repo que se lê e não se usa. | `cp` de 1 arquivo + 3 linhas no README — ver `LICENSE-sugestoes.md` |
| 2 | **e-mail pessoal em texto plano** — `tests/teste_nucleo.py:126`: `"Manda pro bauervieiracesar@icloud.com e vê o log v1.2@kimi-legado."` | é a única ocorrência não mascarada no repo inteiro (as de `bin/iachat_core.py` e `skills/ia-nomination/SKILL.md` já estão truncadas como `bauer...@icloud.com`). Repo público é varrido por scraper de spam. O gate testa que **e-mail não nomina** — o endereço específico é irrelevante para ele. | trocar 1 string por `fulano@exemplo.com` · 30 s |
| 3 | **`README.md:38` manda `git clone <este repo>`** | é a **primeira instrução executável** do documento, e ela não executa. Quem chega tenta essa linha antes de qualquer outra coisa. | 1 linha, depois que a URL existir (passo 6 do `PUBLICAR.md`) |

### 🟠 Bloqueia a credibilidade — fazer antes de divulgar

| # | item | por que importa | custo |
|---|---|---|---|
| 4 | **sem CI** | o repo afirma coisas fortes ("100 mensagens íntegras", "≤5% do arquivo"). Sem CI, é palavra; com CI, é um verde que qualquer um confere sem instalar nada. E é o que separa "projeto" de "pasta publicada". | `cp` do `workflow-ci.yml` · roda em ~2 s por job |
| 5 | **`README.md:107` diz "Nove gates"; são 10** | a tabela de `README.md:109-119` lista 9 e **omite a leitura dirigida**, que é justamente a decisão de desenho mais interessante do projeto e tem 5 asserções em `tests/teste_nucleo.py` (as marcadas `G10`, incluindo *"leitura dirigida é mais barata que a sala inteira"*, que mediu `meu=151 B · todas=478 B · tudo=2540 B`). O projeto está **subvendendo a si mesmo** e, pior, o número da documentação não bate com o código. | 1 linha na tabela + trocar "Nove" por "Dez" · 5 min |
| 6 | **`bin/ia-bell-install-hook.py` não é executável** (`100644`), mas `README.md:49-50` manda invocá-lo como comando: `ia-bell-install-hook.py claude` | ele **tem** shebang (`#!/usr/bin/env python3`, byte 0), e `install.sh:17` faz `chmod +x` só em `iachat` e `ia-bell-*.sh` — o `.py` fica de fora. Num clone fresco, seguir o README dá `permission denied`. É o tipo de defeito que faz o primeiro usuário desistir na instalação. | `chmod +x bin/ia-bell-install-hook.py` (o git preserva o bit) · 10 s |
| 7 | **`auditorias/` entrou no repo — 19 arquivos, 1.405 linhas** (apareceu durante esta própria auditoria; não existia quando comecei) | são logs de execução da frota (`logs/a1-codex.md`, `a2-kimi.md`, `a3-grok.md`, `a4-qwen.md`, `a5-agy.md`), briefings internos e `propostas/` de 5 skills **ainda não decididas**. Publicado, isso (a) mais que dobra o repo — o primeiro commit vai de 19 para **38 arquivos** — com material que não é o produto; (b) faz quem chega achar que existem 12 skills quando existem 7; (c) leva **7 caminhos absolutos `/Users/bauervieiracesarfilhovieira/...`** para dentro de um repo público. Sem credencial e sem e-mail — varri: zero. | decidir: mover para fora do repo, ou `auditorias/` no `.gitignore` · 2 min |
| 8 | **sem seção de segurança** — `grep -niE "segur\|injeç\|confia\|malicios"` no `README.md` e nas 7 skills retorna **zero** | o `ia-chat` é um canal por onde **uma IA lê texto escrito por outra IA** e age sobre ele. Isso é uma superfície de prompt injection entre agentes, e é honesto declará-la. Você já aprendeu essa lição: o **último commit do `iaswarm`** (`87cc224`, 2026-08-16) foi exatamente *"README: seção de segurança — declarar que os workers rodam com permissões amplas"*. Aqui dá para chegar com a lição já aplicada em vez de aplicá-la depois. | ~15 linhas no README, no modelo de `~/Projetos/iaswarm/README.md:121-142` · 20 min |

### 🟢 Vale fazer, barato

| # | item | por que importa | custo |
|---|---|---|---|
| 9 | **`.gitignore` com rede de segurança** | o atual (3 linhas) **já funciona** — provado abaixo. O que ele não cobre: rodar o CLI apontando a sala para dentro do clone suja o repo com `iachat.md`, `config.json`, `.estado.json`, `.lock/`, `pendente/` — e **`iachat.md` é a conversa**. É o acidente mais fácil de cometer testando um clone. | `cp` do `.gitignore-sugerido` · 30 s |
| 10 | **`CONTRIBUTING.md` curto** | não porque alguém vai contribuir no dia 1, mas porque o GitHub o linka automaticamente na tela de abrir issue/PR, e porque ele é o lugar certo para dizer *"o que entra passa nos 3 testes"* — que é a regra real do projeto. 30 linhas, não 300. | `cp` do `CONTRIBUTING-sugerido.md` · 2 min |
| 11 | **descrição + topics + pin no perfil** | é literalmente o que faz alguém achar o repo. Sem topics, ele só é encontrável por quem já sabe o nome. E `iaswarm` + `ia-chat` fixados juntos contam uma história; separados, parecem dois experimentos. | 1 min (passo 8 do `PUBLICAR.md`) |
| 12 | **badge do CI** — *só depois do primeiro run verde* | badge posto antes do primeiro run nasce vermelho, e ninguém volta para conferir se melhorou. | 1 linha |

### ⚪ Não fazer agora

- **Template de issue** — só compensa depois que chega issue ruim. Antes disso é
  cerimônia que atrapalha quem quer relatar algo. Reavalie na 5ª issue.
- **`CHANGELOG.md`** — o `iaswarm` não tem, e resolve isso melhor: uma seção de
  versão dentro do próprio README (`~/Projetos/iaswarm/README.md:76`, *"v0.2
  (2026-08-16) — o que a segunda execução real quebrou"*). Mantém o histórico onde
  as pessoas realmente leem. Siga o seu próprio padrão. Custo: zero.
- **Code of Conduct** — num repo de um autor, é papel que ninguém lê. O GitHub
  oferece o dele por template se algum dia fizer falta.
- **`SECURITY.md`** — a informação de segurança aqui é *como usar sem se machucar*,
  não *como reportar vulnerabilidade*. O lugar dela é o README (item 7).

---

## 1. Git e história

**O código entra certo sozinho.** Ensaiei numa cópia:

```
cp -R ~/Projetos/ia-chat  <scratchpad>/sim
cd <scratchpad>/sim && git init -q && git add -A
→ 19 files changed, 2197 insertions(+)
```

Os 19: `.gitignore`, `README.md`, `install.sh`, 6 em `bin/`, 7 `SKILL.md`, 3 em
`tests/`. O `bin/__pycache__/iachat_core.cpython-314.pyc` que existe hoje no disco
**ficou de fora** — o `.gitignore` atual (`__pycache__/`, `*.pyc`, `.DS_Store`) faz
o trabalho. Os bits de execução também entram certos: `100755` em `bin/iachat`,
nos 3 `.sh` e no `install.sh`. A única exceção é o item 6 acima.

**Mas isso mudou no meio desta auditoria.** Quando comecei, o repositório tinha 20
arquivos; ao final, apareceu `auditorias/` — 19 arquivos, 124 KB. Refiz a medição:

```
→ 38 files changed, 3602 insertions(+)      (19 deles são auditorias/, 1405 linhas)
```

Varri a pasta: **zero credenciais**, **zero e-mails**, mas **7 ocorrências de
`/Users/bauervieiracesarfilhovieira/...`**. O conteúdo é log de execução da frota,
briefing interno e `propostas/` de 5 skills que ainda não foram decididas.

Duas saídas, e a escolha é sua:

- **Deixar de fora** (recomendo): mover para `~/.claude/…` ou acrescentar
  `auditorias/` ao `.gitignore`. O repo público mostra o **produto**; o processo
  fica onde você o consulta.
- **Publicar como método**: aí não são "auditorias" — vira um `DECISOES.md` na raiz
  com as decisões tomadas e o porquê, escrito para leitor externo. As
  `propostas/` **não** vão junto: proposta não decidida no repo público lê-se como
  feature prometida.

Custo de qualquer uma das duas: 2 minutos. Custo de não decidir: o repo nasce com
mais processo do que produto.

**O risco não está no conteúdo — está em de onde o comando é dado.** Hoje:

```
git -C ~/Projetos/ia-chat rev-parse --git-dir  →  /Users/bauervieiracesarfilhovieira/.git
```

O projeto está **dentro do repositório git do seu home**. Enquanto isso for
verdade, `git add` de dentro do `ia-chat` fala com o repo do home. Esse repo tem
`0` arquivos rastreados e nenhum commit (`git ls-files | wc -l` → 0;
`git rev-list --count HEAD` → *unknown revision*), então o estrago seria um índice
contaminado — não uma perda. Mas é a razão de `git status` ali listar `.ssh/`,
`.aws/` e `.claude.json` como untracked, e é convite a erro.

**Como não arrastar nada do home junto: `git init` antes do primeiro `git add`.**
Só isso. O git para de subir a árvore no primeiro `.git` que encontra — depois do
`init` local, o home some do caminho automaticamente. A sequência conferida está em
`PUBLICAR.md`, com uma verificação antes de cada comando.

**O que o projeto gera de verdade e onde:** nada dentro do repo. Todo estado vai
para `IACHAT_HOME` (default `~/ia-chat-global` — `bin/iachat_core.py:52-54`):
`iachat.md`, `config.json`, `.estado.json`, `pendente/`, `cursor/`,
`arquivo/iachat-*-recorte-*.md` (`bin/iachat_core.py:57-70,150-151,414-419`). Os
testes usam `tempfile.mkdtemp` e limpam no `finally`. O único subproduto que cai no
repo é bytecode `.pyc`, já ignorado.

O que o `.gitignore` atual **não** cobre é o acidente: rodar o CLI com a sala
apontada para dentro do clone. Medido no ensaio —
`IACHAT_HOME=$PWD ./bin/iachat status && ./bin/iachat post ...` produz:

```
?? .estado.json   ?? .lock/   ?? config.json   ?? iachat.md   ?? pendente/
```

Cinco caminhos, um deles a conversa inteira. O `.gitignore-sugerido` fecha isso com
7 linhas.

**Varredura de segredo no commit simulado:** limpa. `sk-`, `ghp_`, `github_pat_`,
`AIza`, `-----BEGIN`, `Bearer` → zero ocorrências reais (os únicos casamentos de
"token" são tokens de LLM na documentação de custo). A única exposição pessoal é o
item 2.

**Mensagem do primeiro commit** — no padrão que você já usou (`iaswarm`, commit
`0cee5fa`: *"iaswarm v0.1 — enxame de frota com painel vivo e juiz rotativo"*):

```
ia-chat v0.1 — sala de conversa entre IAs: escrita atômica, sino nominado e leitura dirigida
```

Autor já configurado: `Bauerfilho <bauervieiracesar@icloud.com>`.

---

## 2. LICENSE

Detalhado em **`LICENSE-sugestoes.md`** (MIT × Apache-2.0 × GPL-3.0, uma linha de
consequência cada). Resumo da minha recomendação — a decisão é sua: **MIT**, porque
`~/Projetos/iaswarm/LICENSE:1,3` já é MIT com o mesmo titular e ano, e duas
contribuições do mesmo autor sob licenças diferentes obriga quem chega a perguntar
por quê sem nenhum retorno. O arquivo pronto, byte a byte igual ao do `iaswarm`,
está em `LICENSE-MIT-pronto.txt`.

---

## 3. CI — o que roda em Linux e o que não roda

Arquivo pronto: **`workflow-ci.yml`** → `.github/workflows/testes.yml`.

### O que RODA no runner Linux, e a prova

| dependência | veredito | prova |
|---|---|---|
| `fcntl` | **roda** | é o único módulo POSIX do núcleo (`bin/iachat_core.py:20`, usado em `:133` e `:136`). `fcntl` é stdlib e **nativo de Linux** — é lá que o `flock` nasceu. Só falta no Windows. |
| `launchctl` | **não roda — e nenhum teste precisa dele** | só aparece em `bin/ia-bell-install-daemon.sh:45,46,52,56` e numa linha de documentação em `skills/ia-bell/SKILL.md:74`. |
| `osascript` | **não roda — e nenhum teste precisa dele** | só em `bin/ia-bell-daemon.sh:56` e `:70`. |
| shell scripts nos testes | **não são invocados** | `grep -rn "\.sh\|launchctl\|osascript" tests/` só casa os shebangs `#!/usr/bin/env python3`. O único `subprocess.run` é `[sys.executable, str(BIN), ...]` — `tests/teste_concorrencia.py:38` e `:51`. Nunca um shell. |

Conclusão: **os 3 arquivos de teste são 100% Python + stdlib POSIX.** O sino é a
única parte macOS-only, e ele fica de fora do CI de propósito — colocá-lo lá seria
fabricar verde falso.

### Medições que sustentam o workflow

Suíte inteira, nesta máquina, com `PYTHONDONTWRITEBYTECODE=1`:

```
teste_concorrencia.py   1,23 s real  (3,33 s user — 100 subprocessos)   ✅ GATE 1 PASSOU
teste_nucleo.py         0,11 s                                          ✅ GATES 2-5 PASSARAM
teste_rotacao.py        0,75 s                                          ✅ GATES 6, 7 e 9 PASSARAM
```

Rodada em três interpretadores: **3.11.15 ✅ · 3.12.13 ✅ · 3.14.6 ✅** — os 3
arquivos, exit 0 em todos. A matriz do workflow inclui **3.13 por interpolação**;
não foi executado aqui, e digo isso em vez de fingir que foi.

**Uma armadilha de encoding, medida e neutralizada:** sob locale C sem a coerção do
PEP 538 (`LC_ALL=C PYTHONCOERCECLOCALE=0 PYTHONUTF8=0`), `teste_nucleo.py` morre com

```
UnicodeEncodeError: 'ascii' codec can't encode character '✔'
  em tests/teste_nucleo.py:26, no primeiro print("✔ ...")
```

Com `PYTHONIOENCODING=utf-8`, passa. O runner `ubuntu-latest` define `LANG=C.UTF-8`
e não cairia nisso — mas a variável está no workflow porque custa uma linha e fecha
a classe inteira, inclusive em runner futuro.

**Segundo job — `bash -n`** nos 4 scripts (`bin/ia-bell-daemon.sh`,
`bin/ia-bell-hook.sh`, `bin/ia-bell-install-daemon.sh`, `install.sh`): confere
sintaxe sem executar nada. Rodei localmente: **os 4 passam**.

**O que deixei de fora, e por quê:** `shellcheck`. Não está instalado aqui, então
nunca foi rodado sobre este código, e não vou prometer verde que não medi. Se você
rodar `brew install shellcheck && shellcheck bin/*.sh install.sh` e sair limpo, aí
sim vale acrescentar um passo.

**Não consegui verificar:** não há Docker/Colima nesta máquina (`command -v docker`
→ *not found*), então **não executei a suíte num Linux real**. O que ofereço é a
análise de dependência acima, arquivo por arquivo e linha por linha — não uma
execução. O primeiro `git push` é que vai fechar essa prova, e por isso o passo 7 do
`PUBLICAR.md` manda esperar o verde antes de pôr o badge.

---

## 4. README em português — o custo real e três caminhos

**O custo, sem eufemismo.** O README é o texto que o GitHub indexa e a primeira
tela que decide se alguém fica. Quem procura esta solução procura em inglês —
*"share context between AI agents"*, *"multi-agent message bus"*, *"claude code
codex bridge"*. Um README em português não casa com nenhuma dessas buscas, e quem
chega por link e não lê português fecha em três segundos, sem descobrir que a
resposta dele estava ali. **Você não perde leitores que discordam; perde leitores
que nunca souberam.**

O custo é assimétrico com o tamanho: `README.md` tem **135 linhas / 1.091 palavras**
(`wc -lw`). É pequeno. O que fica caro não é traduzir uma vez — é manter duas
versões sincronizadas para sempre.

**Contra o inglês, um argumento que não é sentimental:** o seu README é bom
*porque* tem voz. *"Um arquivo markdown comum, um CLI que garante escrita atômica"*,
*"o único jeito é você, humano, virar o mensageiro"* — isso é o que faz alguém
entender o problema em dez segundos. Tradução automática apaga exatamente essa
camada e devolve um texto correto e morto.

| caminho | o que você ganha | o que você paga |
|---|---|---|
| **A. só inglês** | alcance máximo; é o padrão do ecossistema | 1.091 palavras a traduzir **com cuidado** (máquina não serve aqui) e a sua voz fica dependendo de quão bem você escreve em inglês |
| **B. inglês na raiz + `README.pt-BR.md`** | alcance máximo **sem** perder a versão com voz | dois arquivos a sincronizar para sempre; na prática, um dos dois apodrece — com 135 linhas e um projeto estável, é administrável, mas é dívida real |
| **C. português na raiz + resumo em inglês de 10-15 linhas no topo** | pega a busca e a primeira tela (*o que é · para quem · como instalar · onde estão os testes*); **um arquivo só**, zero dessincronização | quem se interessar de verdade lê o resto no tradutor — perde-se a nuance, não a informação |

**Minha recomendação, e a decisão é sua:** **C agora, B se aparecer tração.** O
custo de C é ~200 palavras escritas uma vez; o de B só se justifica quando houver
alguém do outro lado para justificar a manutenção. **A eu não recomendo** — troca
a única coisa que o seu README tem de raro pela coisa que qualquer README tem.

Se escolher C, o bloco em inglês vai **acima** do `# ia-chat`, dentro de um
`<details>` ou como parágrafo curto em itálico, e termina com uma linha do tipo
*"Full documentation below, in Portuguese."*

---

## 5. O que mais um repo desse porte precisa — e o que ele não precisa

Já respondido nos itens 8 a 12 do checklist. Três observações que não cabiam lá:

**A seção "Estado (honesto)".** O `iaswarm` tem uma
(`~/Projetos/iaswarm/README.md:143`). O `ia-chat` tem "Limitações conhecidas"
(`README.md:127-135`), que faz o mesmo trabalho e faz bem — cursor por IA e não por
sessão, paginação estável só nos recortes, um daemon por casca. **Não mexa nisso.**
É a seção que mais constrói confiança no documento inteiro, porque prova que você
sabe onde o seu próprio projeto é fraco.

**A instalação já é testável por terceiro** (`README.md:35-58`): `install.sh` com
destinos por env, tabela por casca, e o aviso do `trusted_hash` do Codex. Falta só
a URL real (item 3). O que **não** existe é uma linha de "como confirmar que
funcionou" logo depois do `install.sh` — algo como `iachat status` e o que ele deve
imprimir. Três linhas, e o primeiro usuário sai da instalação sabendo se deu certo.

**A ordem de divulgação importa.** Publicar → esperar o CI verde → arrumar o badge
e os topics → **só então** mostrar para alguém. Um repo visitado no dia em que o
badge está vermelho não ganha segunda visita.

---

## O que eu não consegui verificar

1. **Execução da suíte em Linux real.** Sem Docker/Colima na máquina. A conclusão
   de que roda vem de análise de dependência (`fcntl` stdlib POSIX; zero `launchctl`
   ou `osascript` em `tests/`; nenhum shell invocado por subprocess) — não de uma
   execução. O primeiro push fecha essa prova.
2. **Python 3.13.** Provei 3.11, 3.12 e 3.14; 3.13 está na matriz por interpolação.
3. **`shellcheck` nos 4 scripts.** Não instalado; por isso ficou fora do workflow.
4. **Comportamento das actions `checkout@v4` / `setup-python@v5` hoje no GitHub.**
   São as majors estáveis que conheço; se o Actions avisar depreciação de runtime
   Node, é só subir a major — os `with:` usados não mudam entre elas.

---

## Arquivos desta entrega

| arquivo | o que é |
|---|---|
| `NOTA.md` | este documento |
| `PUBLICAR.md` | **a sequência exata** do `git init` ao primeiro push, com o que conferir antes de cada comando |
| `LICENSE-sugestoes.md` | MIT × Apache-2.0 × GPL-3.0, consequência de cada uma |
| `LICENSE-MIT-pronto.txt` | pronto para `cp` — titular e ano idênticos aos do `iaswarm` |
| `workflow-ci.yml` | → `.github/workflows/testes.yml`, comentado com a prova de cada decisão |
| `.gitignore-sugerido` | o atual + rede de segurança contra a sala entrar no repo |
| `CONTRIBUTING-sugerido.md` | 30 linhas: os 3 testes como critério de entrada |
