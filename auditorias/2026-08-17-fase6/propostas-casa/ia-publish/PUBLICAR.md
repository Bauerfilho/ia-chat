# Do `git init` ao primeiro push — a sequência exata

Nada aqui foi executado no seu repositório. Tudo foi ensaiado numa **cópia
temporária** (`cp -R` para o scratchpad), e os números abaixo vêm desse ensaio.
Publicar é decisão sua; isto é o roteiro.

---

## Passo 0 — o perigo que existe agora, antes de qualquer comando

```bash
cd ~/Projetos/ia-chat
git rev-parse --git-dir
```

**Hoje isso responde `/Users/bauervieiracesarfilhovieira/.git`.**

O `~/Projetos/ia-chat` está dentro do repositório git do seu **home**. Enquanto
esse for o caso, todo comando git rodado de dentro dele fala com o repo do home,
não com o projeto:

- `git status` lista o home inteiro (é por isso que ele aparece com centenas de
  `??`, incluindo `.ssh/`, `.aws/`, `.claude.json`);
- **`git add .` de dentro do ia-chat indexa no home** — o repo do home tem `0`
  arquivos rastreados e nenhum commit (`git ls-files | wc -l` → 0;
  `git rev-list --count HEAD` → *unknown revision*), então o estrago seria um
  índice contaminado, não uma perda. Mas é estrago.

**Regra do passo 0: não digite nenhum `git add` até o passo 3.** Depois do
`git init` local, o `.git` do projeto vence o do home automaticamente — o git
para de subir a árvore ao encontrar o primeiro `.git`.

> Nota lateral, fora do escopo desta entrega: um repo git vazio no seu home, com
> `.ssh/` e `.aws/` como untracked, é uma armadilha permanente. Vale decidir um dia
> se ele deve existir.

---

## Passo 1 — colocar os arquivos novos no lugar

```bash
cd ~/Projetos/ia-chat
P=~/.claude/iaswarm-runs/ia-chat-fase6/batch/ia-publish

cp  "$P/LICENSE-MIT-pronto.txt"   LICENSE
cp  "$P/.gitignore-sugerido"      .gitignore
mkdir -p .github/workflows
cp  "$P/workflow-ci.yml"          .github/workflows/testes.yml
cp  "$P/CONTRIBUTING-sugerido.md" CONTRIBUTING.md
```

**Confira antes de seguir:**

```bash
ls -1 LICENSE CONTRIBUTING.md .github/workflows/testes.yml
head -3 LICENSE          # "MIT License" / vazio / "Copyright (c) 2026 Bauer..."
```

**Decida sobre `auditorias/` antes de seguir** (item 7 da `NOTA.md`): são 19
arquivos / 1.405 linhas de log de frota, briefing interno e propostas não decididas,
com 7 caminhos `/Users/bauervieiracesarfilhovieira/...`. Sem credencial, mas não é
produto. Ou move para fora do repo, ou:

```bash
echo "auditorias/" >> .gitignore
```

E as duas correções de 1 linha cada (justificativa na `NOTA.md`, itens 2 e 6):

```bash
# 1) e-mail pessoal em texto plano num repo que vai ficar público
#    tests/teste_nucleo.py:126 — troque bauervieiracesar@icloud.com por
#    algo como fulano@exemplo.com. O gate testa que e-mail NÃO nomina; o
#    endereço específico é irrelevante para o teste.
grep -n "bauervieiracesar@icloud.com" tests/teste_nucleo.py

# 2) o único arquivo que o README manda executar e que não é executável
chmod +x bin/ia-bell-install-hook.py
```

---

## Passo 2 — `git init` (é aqui que o projeto deixa de ser do home)

```bash
git init -b main
git rev-parse --git-dir      # AGORA tem que responder apenas: .git
```

Se ainda responder o caminho do home, **pare** — o `init` não pegou e o passo 3
vai escrever no lugar errado.

---

## Passo 3 — ver o que vai entrar, antes de commitar

```bash
git add -A
git status --short
git diff --cached --stat | tail -1
```

**O que esperar** (medido no ensaio):

| cenário | resultado |
|---|---|
| só o código, `.gitignore` atual | `19 files changed, 2197 insertions(+)` |
| como o repo está hoje, com `auditorias/` | `38 files changed, 3602 insertions(+)` |
| código + LICENSE + CONTRIBUTING + workflow, **sem** `auditorias/` | **22 arquivos** ← o alvo |

**O que NÃO pode aparecer:**

| se aparecer | significa | o que fazer |
|---|---|---|
| `*.pyc`, `__pycache__/` | o `.gitignore` não pegou | conferir que o `.gitignore` está na **raiz** do projeto |
| `iachat.md`, `config.json`, `.estado.json`, `pendente/`, `.lock/` | você rodou o CLI com `IACHAT_HOME` apontando para dentro do clone — **`iachat.md` é a conversa** | `git rm -r --cached` nesses caminhos; o `.gitignore` sugerido já os cobre |
| `auditorias/…` | a decisão do passo 1 não foi tomada | `git rm -r --cached auditorias` + a linha no `.gitignore` |
| qualquer caminho fora de `~/Projetos/ia-chat` | o `init` do passo 2 não pegou | volte ao passo 2 |

**Varredura de segredo** (rodei no ensaio: sai limpa, os únicos "token" que casam
são tokens de LLM na documentação de custo):

```bash
git diff --cached | grep -nE "sk-[A-Za-z0-9]|ghp_|github_pat_|AIza|-----BEGIN|Bearer "
git diff --cached | grep -nE "@icloud|@gmail|/Users/[a-z]"
```

A segunda linha é a que importa: no estado atual ela acusa `tests/teste_nucleo.py:126`.
Se você fez a correção do passo 1, sai vazia.

---

## Passo 4 — o primeiro commit

O padrão que você já usou no `iaswarm` (commit `0cee5fa`) é
`nome vX.Y — o que a coisa é`:

```bash
git commit -m "ia-chat v0.1 — sala de conversa entre IAs: escrita atômica, sino nominado e leitura dirigida"
```

Autor: `Bauerfilho <bauervieiracesar@icloud.com>` — já é o seu `git config` global,
nada a ajustar.

**Confira:**

```bash
git log --stat --oneline | head -30
```

---

## Passo 5 — criar o repositório no GitHub e empurrar

```bash
gh auth status          # confirme que está logado como Bauerfilho
```

`gh` já está instalado (`/opt/homebrew/bin/gh`, versão 2.92.0).

```bash
gh repo create Bauerfilho/ia-chat \
  --public \
  --source=. \
  --remote=origin \
  --push \
  --description "Uma sala de conversa para IAs que não veem o contexto uma da outra: escrita atômica, sino que só toca para quem foi nominado, leitura dirigida."
```

Esse comando faz três coisas de uma vez: cria o repo, adiciona o `origin` e dá o
push do `main`. Se preferir separar:

```bash
gh repo create Bauerfilho/ia-chat --public --description "..."
git remote add origin https://github.com/Bauerfilho/ia-chat.git
git push -u origin main
```

**Confira:**

```bash
git remote -v
gh repo view --web
```

---

## Passo 6 — o `<este repo>` do README vira uma URL de verdade

`README.md:38` diz hoje:

```bash
git clone <este repo> && cd ia-chat && ./install.sh
```

Trocar por:

```bash
git clone https://github.com/Bauerfilho/ia-chat.git && cd ia-chat && ./install.sh
```

Enquanto for placeholder, a primeira instrução do README não é executável — e é a
primeira coisa que um terceiro tenta.

---

## Passo 7 — o CI, e o badge só DEPOIS que ele ficar verde

O push do passo 5 dispara o workflow sozinho.

```bash
gh run list --limit 3
gh run watch          # acompanha até terminar
```

Se qualquer job falhar, conserte **antes** de divulgar. Só depois de verde, a linha
do badge no topo do `README.md`, logo abaixo do `# ia-chat`:

```markdown
[![testes](https://github.com/Bauerfilho/ia-chat/actions/workflows/testes.yml/badge.svg)](https://github.com/Bauerfilho/ia-chat/actions/workflows/testes.yml)
```

Badge posto antes do primeiro run nasce vermelho, e ninguém volta para conferir se
melhorou.

---

## Passo 8 — o que faz alguém achar o repositório (1 minuto, retorno alto)

```bash
gh repo edit Bauerfilho/ia-chat \
  --add-topic ai-agents \
  --add-topic claude-code \
  --add-topic multi-agent \
  --add-topic cli \
  --add-topic developer-tools
```

E, na mesma tela do repositório, marcar o `iaswarm` e o `ia-chat` como *pinned* no
seu perfil. As duas contribuições juntas contam uma história; separadas, parecem
dois experimentos.

---

## Resumo em uma tela

```bash
cd ~/Projetos/ia-chat
git rev-parse --git-dir                        # ainda é o home? então cuidado
# ... copiar LICENSE / .gitignore / workflow / CONTRIBUTING (passo 1)
# ... decidir auditorias/ (fora do repo, ou linha no .gitignore)
# ... corrigir tests/teste_nucleo.py:126 e chmod +x bin/ia-bell-install-hook.py
git init -b main
git rev-parse --git-dir                        # tem que ser: .git
git add -A && git status --short               # 22 arquivos, nenhum .pyc, nenhum iachat.md, nenhum auditorias/
git diff --cached | grep -nE "@icloud|ghp_|AIza|-----BEGIN"   # tem que sair vazio
git commit -m "ia-chat v0.1 — sala de conversa entre IAs: escrita atômica, sino nominado e leitura dirigida"
gh auth status
gh repo create Bauerfilho/ia-chat --public --source=. --remote=origin --push --description "..."
gh run watch                                   # verde antes do badge
```
