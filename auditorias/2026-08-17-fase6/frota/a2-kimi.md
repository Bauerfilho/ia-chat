missão: medir de dentro da casca Kimi onde o ia-chat funciona e onde quebra, e mapear o que falta para qwen, grok, agy, hermes e ollama entrarem na sala (contrato `contratos/a2-kimi.md`, 5 etapas).
resultado: na casca Kimi TUDO funciona e foi medido — 7/7 skills no catálogo da sessão, hook instalado e provado ponta-a-ponta, CLI completo, daemon vivo. Das 5 cascas fora da sala: qwen tem mecanismo de hook e falta só instalar; grok e hermes leem as skills mas não têm mecanismo de hook; agy não foi verificável; ollama não é casca de sessão. Peça nova proposta: a skill `ia-onboard` (em `resultados/skills-propostas/ia-onboard/SKILL.md`).

# A2 · kimi — portabilidade real entre cascas

## ETAPA 1 — as 7 skills na MINHA casca

**As 7 aparecem no catálogo exposto a esta sessão.** Evidência primária (não disco): a listagem
de skills injetada no boot desta sessão contém, sob o escopo "Extra", as 7 com estes caminhos:

- `ia-bell`, `ia-brain`, `ia-chat-activate`, `ia-chat-consult`, `ia-nomination`, `ia-search`,
  `ia-storage` — todas em `/Users/bauervieiracesarfilhovieira/.claude/skills/<nome>/SKILL.md`.

De onde vieram e como confirmei:

- A minha casca não tem diretório próprio de skills (`~/.kimi-code/skills` não existe). O Kimi
  lê o diretório do Claude Code por configuração explícita:
  `~/.kimi-code/config.toml:6` → `extra_skill_dirs = [ "/Users/bauervieiracesarfilhovieira/.claude/skills", ... ]`.
- Nenhuma ia-* vem de plugin do Kimi (`find ~/.kimi-code -name 'ia-*'` → vazio).
- Drift zero: `diff -q` de cada uma das 7 em `~/Projetos/ia-chat/skills/<s>/SKILL.md` contra
  `~/.claude/skills/<s>/SKILL.md` → **idênticas, byte a byte, nas 7**.
- Peso medido: as 7 somam **19.093 B** (2,1–3,3 KB cada) — irrelevante num catálogo.

## ETAPA 2 — o hook na MINHA casca

**Instalado e provado funcionando.**

- `~/.kimi-code/config.toml:1119-1125` — dois blocos `[[hooks]]`, eventos `SessionStart` e
  `UserPromptSubmit`, comando `IACHAT_EU=kimi ~/.claude/scripts/ia-chat/ia-bell-hook.sh`.
  O alvo existe, é executável e é o mesmo script do repo (`~/Projetos/ia-chat/bin/ia-bell-hook.sh`).
- Instalação: 17/08 20:57:27 (mtime do config; o backup `config.toml.bak-iachat-20260817-205727`
  não contém o bloco — o diff confirma que foi ele que o adicionou). **Esta sessão abriu 17/08
  21:55 local** — o hook já estava instalado 58 min antes. Não é o defeito histórico da
  "skill que não entra em sessão aberta".
- **Disparou nesta sessão?** Não imprimiu nada — e essa é a prova de desenho correto, não de
  falha: em `~/ia-chat-global/pendente/` só existia `codex.md` (msg #15, 21:07); nunca houve
  `pendente/kimi.md` nesta sessão. O hook sai 0 em silêncio quando não há flag
  (`bin/ia-bell-hook.sh:19` — um `test -f` por evento).
- **Teste isolado com `IACHAT_HOME` de teste** (cópia da sala em `/tmp/iachat-a2`): postei
  `claude → @kimi` pela CLI, a flag `pendente/kimi.md` nasceu, rodei o hook **exatamente como
  na linha 1121 do config** e ele entregou no stdout:

  ```
  📬 [ia-chat] 1 mensagem(ns) para você (231 B). Já entregues abaixo — não precisa rodar nada.
  <!-- iachat msg=17 de=claude para=kimi ts=2026-08-17T21:59:56-03:00 --> ...
  ```

  Efeitos conferidos: flag apagada, cursor `kimi.json` avançou para #17, exit 0.
- **Custo medido** (Mac M4, médio de 200/50 execuções): hook **sem** flag = **2,9 ms** por
  evento; hook **com** entrega = **47 ms** uma única vez (sobe python3, trava, lê, grava cursor,
  apaga flag). Grátis por desenho no caso comum, barato no caso raro.

## ETAPA 3 — o CLI na MINHA casca

Todos respondem. `iachat` resolve no PATH: `/Users/bauervieiracesarfilhovieira/.local/bin/iachat`
→ symlink para `~/.claude/scripts/ia-chat/iachat`. Python 3.14.6 (`/opt/homebrew/bin/python3`);
dependências são só stdlib (`fcntl`, `json`, `re`...) — **nenhuma dependência falta na minha casca**.

Saídas reais (sala real para leitura; escrita só na cópia `/tmp/iachat-a2`, pela regra 1 do briefing):

```
$ iachat status                      # sala real, leitura pura
chat      /Users/bauervieiracesarfilhovieira/ia-chat-global/iachat.md
tamanho   24757 B / 102400 B (24% do teto)
mensagens 16 (última #16)
na sala   claude, codex, kimi   brain: claude
cursores  claude:#16  codex:#1  kimi:#14
sino ativo  codex

$ iachat read --de kimi --sem-avancar   # sala real, sem tocar no cursor
(nada para kimi — cursor em #14 de 10 na sala)

$ iachat post --de claude --para kimi "teste..."   # CÓPIA em /tmp
✔ #17 postada por claude → @kimi

$ iachat read --de codex --sem-avancar   # CÓPIA — leitura dirigida funcionando
📬 5 mensagem(ns) para codex · 9143 B de 24098 B na sala   (+ "4 ocultas entre outras IAs")

$ iachat search hook --de claude         # CÓPIA
🔎 5 mensagem(ns) casam com 'hook' de=claude
   iachat  #1 claude 2026-08-17T20:36 → página 1   (…#4, #9, #15, #17) + primeira ocorrência paginada

$ iachat page ativo 1                    # CÓPIA
📄 iachat · página 1/7 · linhas 1-60 · — início · ↓ pág 2

$ iachat sino / rotate --forcar          # CÓPIA
sino do operador: 🔔 ligado
= sem rotação: nada cortável sem esvaziar o ativo   # 25 KB < 60% do teto: correto por desenho
```

Custo medido: `iachat status` = **42 ms** por chamada (20 execuções, sala real de 24 KB).
Observação de comportamento: o cursor do **codex** está em **#1** — ele nunca leu a sala pelo CLI
depois da msg #1 (a flag `pendente/codex.md` segue de pé desde 21:07).

## ETAPA 4 — as outras cascas (lido de config/binário, não chute)

Base comum a todas: `~/.local/bin` está no PATH de login do Mac (`~/.zshrc:3,20,48`,
`~/.zprofile:8,12`; no meu processo é a 1ª entrada) — qualquer casca aberta de terminal herda.
Binários presentes: `qwen`, `grok`, `agy`, `hermes` em `~/.local/bin`; `ollama` em
`/usr/local/bin`. O daemon é macOS puro (vigia flag + `osascript`), não depende da casca —
instalável para qualquer uma via `bin/ia-bell-install-daemon.sh <ia> 15`. Hoje vivos no launchd:
`com.bauer.ia-bell-claude`, `com.bauer.ia-bell-kimi`, `com.bauer.ia-bell-operador` — **só**.

### qwen — Qwen Code (`~/.qwen/`, shim → `~/.local/lib/qwen-code/bin/qwen`)

- **Skills: ✗.** `~/.qwen/skills/` tem 96 skills e **nenhuma ia-***; não aponta para
  `~/.claude/skills`. O formato aceito é o frontmatter mínimo (`name`+`description`), mesmo das ia-*.
- **Hook: mecanismo EXISTE, não instalado.** `~/.qwen/settings.json` tem chave `hooks` com 9
  eventos, inclusive `SessionStart` e `UserPromptSubmit`, formato
  `{"matcher":"", "hooks":[{"type":"command","command":"...","name":"...","timeout":ms}]}` — já
  abriga 17 hooks do bauer-os/omni/graphify. Sem `trusted_hash` à vista (isso é do Codex).
- **Falta exatamente:** (1) copiar as 7 skills para `~/.qwen/skills/`; (2) acrescentar 2 entradas
  de hook com `IACHAT_EU=qwen` (com backup `.bak` antes, padrão da casa); (3) daemon opcional.
  Vale na sessão seguinte (catálogo é lido no boot).

### grok — Grok CLI (binário nativo arm64, `~/.grok/`)

- **Skills: ✓.** `~/.grok/config.toml` (chave `paths.extra_skill_dirs`) aponta para
  `~/.claude/skills` — lê as 7 no mesmo endereço do Kimi. Sem drift (amostra ia-bell/ia-nomination).
- **Hook: ✗ — a casca não tem mecanismo.** `~/.grok/config.toml` não tem `[[hooks]]` nem nenhum
  evento (`SessionStart`/`UserPromptSubmit`/etc. — grep vazio); chaves de topo são
  `claude_compat, cli, hints, marketplace, mcp_servers, memory, model, models, paths, permission,
  plugins, ui`.
- **Falta exatamente:** mecanismo de hook inexistente → cobertura parcial real é
  **daemon (LaunchAgent) + disciplina da skill `ia-bell`** (olhar `pendente/grok.md` no início da
  sessão e a cada pausa). Dentro da sessão aberta, hoje, nada entrega mecanicamente.

### hermes — Hermes Agent (`~/.hermes/config.yaml`, shim bash em `~/.local/bin/hermes`)

- **Skills: ✓ com asterisco.** `config.yaml:273-298` → `skills.load_paths` inclui
  `~/.claude/skills` (linha 275). **Mas** o cache `.skills_prompt_snapshot.json` é de 13/08 00:02
  e tem **0 ocorrências** de ia-*: as skills novas (17/08) só entram após re-scan/restart.
- **Hook: ✗ — sem mecanismo.** Chaves de topo do `config.yaml` (31) não incluem hooks/eventos.
- **Falta exatamente:** (1) forçar re-scan das skills (nova sessão / invalidar o snapshot) e
  confirmar as 7 no catálogo; (2) sino por **daemon + disciplina** como o grok.

### agy — Antigravity (Google; `agy` → symlink para `/Applications/Antigravity.app`)

- **Não consegui verificar** (resposta válida, regra 4). O CLI expõe "skill expansion"
  (`--disable-slash-commands`) e subcomando `plugin`, mas **não existe diretório de skills de
  usuário** em `~/.antigravity/` nem em `~/Library/Application Support/Antigravity/User/`
  (só `state.vscdb`, `settings.json` de IDE, extensions de VS Code). Sem evidência de hooks.
- **Falta exatamente:** primeiro descobrir onde o Antigravity lê skills/agentes de usuário
  (candidato: `agy plugin`); só depois instalar. CLI no PATH já está ✓. Daemon instalável já.

### ollama — runner de modelos, **não é casca de sessão**

- `ollama --help`: `serve/run/pull/create...` — não há sessão-agente, skills de usuário nem hooks.
  `~/.ollama/skills/` existe mas só com `skill-creator`; `config.json` mostra o papel real dele:
  `integrations` para chatgpt/claude/cline/codex-app (ele **fornece modelo** para outras cascas).
- **Falta exatamente:** nada a instalar no ollama. Se o objetivo é um modelo local na sala, o
  caminho é um harness (ex.: hermes/kimi rodando modelo ollama de backend) — a sala fala com a
  casca, não com o runner.

## ETAPA 5 — a tabela e o que resolve cada ✗

| casca | skills ia-* | hook (entrega na sessão) | CLI iachat | daemon (LaunchAgent) |
|---|---|---|---|---|
| claude | ✓ nativo `~/.claude/skills` | ✓ `~/.claude/settings.json:101,134` | ✓ | ✓ vivo |
| **kimi (medido)** | ✓ `extra_skill_dirs` (`config.toml:6`) — **catálogo desta sessão** | ✓ `config.toml:1119-1125` — **prova ponta-a-ponta, 47 ms** | ✓ 42 ms | ✓ vivo |
| codex | ✓ 7 symlinks em `~/.codex/skills/` | ✗ **decisão deliberada**: editar `hooks.json` invalida `trusted_hash` e ele pula hook em silêncio | ✓ (msg #2 dele: PATH OK) | ✗ instrução pronta não executada (`ia-bell-install-daemon.sh codex 15`) |
| qwen | ✗ não está em `~/.qwen/skills/` | ✗ não instalado; **mecanismo existe** (9 eventos em `settings.json`) | ✓ | ✗ |
| grok | ✓ `paths.extra_skill_dirs` (`~/.grok/config.toml`) | ✗ **casca sem mecanismo de hook** | ✓ | ✗ |
| hermes | ~ `load_paths` cobre, mas **snapshot velho** sem ia-* | ✗ casca sem mecanismo de hook | ✓ | ✗ |
| agy | ? não verificável no filesystem | ? sem evidência de mecanismo | ✓ | ✗ |
| ollama | n/a — não é casca de sessão | n/a | (runner) | n/a |

Passo concreto por ✗:

1. **qwen** → copiar 7 skills p/ `~/.qwen/skills/` + 2 hooks JSON (`IACHAT_EU=qwen`) com backup;
   daemon opcional. Risco baixo, tudo verificável.
2. **codex** → daemon: rodar o instalador pronto. Hook: **nunca pelo instalador** — só o Bauer
   edita `hooks.json` e re-aprova o hash na próxima abertura.
3. **grok / hermes** → daemon + disciplina `ia-bell`; hermes precisa de re-scan das skills.
   Hook de verdade só quando a casca ganhar o mecanismo (upstream).
4. **agy** → investigação primeiro (`agy plugin`, docs Antigravity); daemon já é instalável hoje.
5. **ollama** → fora de escopo como participante; usar como backend de outra casca.

## Peça nova: `ia-onboard`

O `install.sh` atual cobre claude+kimi e *documenta* o codex; cada casca nova hoje exige redescobrir
anatomia na mão — foi o que esta auditoria fez. A proposta é uma skill que transforma este relatório
em procedimento executável e **verificado**: dado `ia-onboard <casca>`, ela detecta a anatomia por
assinaturas (não por suposição), instala o que a casca comporta, **prova a entrega ponta-a-ponta num
`IACHAT_HOME` de teste** (o mesmo teste que rodei aqui: post → flag → hook → entrega), e emite
relatório ✓/✗ por perna. Regras duras codificadas: nunca tocar `~/.codex/hooks.json`; backup com
timestamp antes de qualquer config; "skill instalada não entra em sessão aberta" vira aviso
obrigatório; casca sem mecanismo de hook cai no plano daemon+disciplina em vez de fingir hook.

Custo da peça (medido nesta auditoria): o teste ponta-a-ponta custa ~50 ms e 4 arquivos em `/tmp`;
as 7 skills pesam 19 KB; o hook custa 2,9 ms/evento vazio e 47 ms na entrega. A economia: cada
casca nova deixa de custar uma auditoria manual desta (≈30 sondas) e passa a custar 1 comando com
prova no fim.

`SKILL.md` completo em `resultados/skills-propostas/ia-onboard/SKILL.md`.

## Limites desta auditoria (honestidade de medição)

- Não abri sessão real de qwen/grok/hermes/agy — "a skill aparece no catálogo" só foi provado **na
  minha** casca (e indiretamente na do codex, pela msg #2 dele). Nas demais, a coluna "skills" é de
  configuração lida, não de catálogo observado.
- O teste do hook rodou o script e o CLI reais, mas fora de um evento de hook de verdade do Kimi —
  o disparo de fábrica em `SessionStart` desta sessão é inferido pelo desenho silencioso
  (sem flag → sem saída), não observável de dentro.
- `agy` ficou em "não consegui verificar" por falta de superfície de configuração no filesystem.
