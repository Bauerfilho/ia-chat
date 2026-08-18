# NOTA — `ia-doctor`

Protótipo executável em `bin/ia-doctor` (765 linhas, Python 3.11+, sem dependências).
**Rodado de verdade nesta máquina** — saída literal no fim deste documento.

## O que resolve

Os três defeitos do primeiro dia são a mesma família: *o instrumento disse uma coisa e a
realidade era outra*. O `ia-doctor` não tenta ser um instrumento melhor — ele é um
instrumento que **separa "não" de "não sei"**.

### 1. Skill no disco, ausente do catálogo da sessão

Kimi e Codex leem catálogo no boot. `install.sh:20-24` copia as skills; `install.sh:33`
confere se o `extra_skill_dirs` do Kimi aponta para o diretório — e é só isso que o
instalador sabe dizer. Nenhuma das duas coisas prova que a **sessão aberta** carregou.

Medida: `mtime` da skill × hora em que o processo da casca abriu (`processos()` em
`bin/ia-doctor:195-220`, via `ps -Ao pid,etime,comm,args`; `etime` é numérico, `lstart`
sai no locale do usuário — aqui, pt-BR). Skill mais nova que a sessão ⇒ **⚠** com o passo
*abra uma sessão nova*.

**O programa nunca alega que a skill está no catálogo.** Mesmo quando o `mtime` é anterior
à sessão, o desfecho é ⚠ com o texto *"provável não é medido"* e o passo para provar
(`/ia-chat-activate` dentro da casca). Foi exatamente aqui que duas medições discordaram
no dia 17 — `kimi -p` listava, a TUI não —, e nenhuma das duas disse "não sei".

### 2. Hook instalado que não dispara

Mesma medida, sobre o arquivo de config de hooks (`bin/ia-doctor:593-607`). O conteúdo
estava certo; o que estava errado era o *tempo*. Nenhuma verificação de conteúdo pegaria.

O `ia-bell-install-hook.py:66` já avisa isso em texto (*"vale a partir da PRÓXIMA sessão
do Kimi"*), mas só no momento da instalação e só para o Kimi — quem abre a sessão três
dias depois não vê esse aviso. O `ia-doctor` mede o estado, não a intenção.

### 3. Instalador que nega um daemon que subiu

`launchctl list | grep -q LABEL` sob `pipefail` = SIGPIPE 141 = pipeline falho.
`ia-bell-install-daemon.sh:48-52` já documenta a lição e usa
`VIVO="$(launchctl list | grep "$LABEL" || true)"` — o `grep` sem `-q` consome a entrada
inteira, então não há SIGPIPE.

Aqui, o cuidado é estrutural: `rodar()` (`bin/ia-doctor:147-161`) usa
`subprocess.run(argv, capture_output=True)` — **sem shell, sem pipe**, saída inteira na
memória antes de qualquer julgamento. E `rc=None` (não consegui executar) vira **⚠**,
nunca ✗: não conseguir perguntar não é receber "não". `bin/ia-doctor:653-672` procura o
label na saída já capturada.

### E mais quatro que a mesma régua entrega de brinde

- **`trusted_hash` do Codex** (`bin/ia-doctor:609-647`): confere se **todo** hook de
  `hooks.json` tem chave em `[hooks.state]` do `config.toml`. Achou 1 sem aprovação nesta
  máquina — hook que o Codex pula em silêncio.
- **Sala íntegra**: `.estado.json` × último `msg=N` da cauda do chat. Se o cache mentir,
  `post` numera em cima de mensagem existente (`iachat_core.py:172-179` recalcula pela
  cauda quando ele some — por isso ausência é ⚠, não ✗).
- **Instalado × repositório**: sha256 de `bin/*` (o `install.sh` copia, e cópia
  envelhece).
- **Flag pendente esquecida**: sino tocou, ninguém leu. Achou uma de 60 minutos.
- **Chave ausente em `config.json`**: sem `teto_bytes` explícito, o core usa **três
  defaults diferentes** para a mesma grandeza — `iachat_core.py:42` grava 204800,
  `:384` (`status`) assume 40960 e `:430` (`rotate`) assume 102400. O status mediria
  contra um teto e a rotação cortaria contra outro. Verificado com config incompleta:
  sai ✗ com os dois números no `passo:`.

## Achados reais desta máquina, agora

| casca | achado | evidência |
|---|---|---|
| **codex** | `ia-bell-hook.sh` **ausente** de `~/.codex/hooks.json` | `grep -c ia-bell hooks.json` = 0 |
| **codex** | daemon `com.bauer.ia-bell-codex` **não carregado** | ausente de `launchctl list` |
| **codex** | `UserPromptSubmit[1][0]` (graphify) sem `[hooks.state]` | conferido à mão em `config.toml:778-805` |
| **codex** | flag pendente há 60 min, cursor em **#1** de 16 | `pendente/codex.md` cita a msg #15 |
| **claude** | sessão de 16/08 13:45; `settings.json` mudou 17/08 20:47 | o hook não vale nessa sessão |
| **kimi** | sessão de 15/08 17:47; `config.toml` mudou 17/08 20:57 | idem |

Além disso, a sala real roda com `teto_bytes = 102400` (`~/ia-chat-global/config.json:8`)
enquanto o código já pede 204800 (`iachat_core.py:42`): a sala nasceu numa versão anterior
e o `garantir_estrutura()` não reescreve config existente. Não é defeito, é drift — mas
significa que a rotação vai disparar na metade do que o desenho atual previu.

**O Codex está surdo pelas duas pernas** — sem hook (perna de dentro) e sem daemon (perna
de fora) — e tem mensagem nominada não lida desde as 21:07. Nada no sistema atual diz
isso; o `iachat status` mostra `cursores codex:#1` e não chama de defeito.

## Custo, medido

| | medida |
|---|---|
| tempo de execução | **0,29 · 0,29 · 0,31 s** (3 rodadas, `/usr/bin/time -p`) |
| saída de texto | **7.536 B / 85 linhas** ≈ 1.900 tokens |
| saída `--json` | 10.870 B ≈ 2.700 tokens |
| leitura do disco | 5 configs + 7 SKILL.md por casca + 16 KB da cauda do chat |
| escrita | **zero** (verificado: `IACHAT_HOME` inexistente ⇒ a sala não foi criada) |

Uma leitura da sala hoje custa 24.757 B. O diagnóstico inteiro custa **menos de um terço
disso** e responde a pergunta que a leitura da sala não responde.

## Riscos

1. **O registro `CASCAS` envelhece.** `bin/ia-doctor:79-115` crava onde cada casca guarda
   skills e hooks — verificado nesta máquina em 17/08 (`~/.kimi-code/config.toml:6` e
   `:1119`, `~/.grok/config.toml:111`, `~/.codex/skills/ia-*` como symlinks). Se uma
   casca mudar de formato, o item vira ⚠ e não ✗ — degrada para "não sei", que é o
   comportamento certo, mas exige manutenção humana.
2. **`ps` por nome de executável é aproximado.** `codex exec --ephemeral` (Skysight) tem
   `comm` = `codex` e não é sessão interativa. Por isso o item imprime a linha de comando
   do processo mais antigo: quem decide se aquilo é uma sessão é o dono. Falso ⚠, nunca
   falso ✓.
3. **`hook-hash-confere` é assumidamente ⚠.** Testei sha256 sobre `command`, sobre o hook
   serializado em JSON (4 formas: compacto, ordenado, indentado, com/sem `type`), sobre o
   script apontado, e sobre `${CLAUDE_PLUGIN_ROOT}` expandido em 3 raízes plausíveis —
   nenhum bate com o `trusted_hash` gravado. A prova de que o hash é do **comando** (e não
   do arquivo) está em `config.toml:790-802`: cinco hooks com `command` idêntico e `if`
   diferentes compartilham o mesmo hash. Sem o algoritmo, verifico presença — e digo isso.
4. **Superfície**: 765 linhas para 8 verificações × 5 cascas. A maior parte é texto de
   mensagem e de conserto. É deliberado: um diagnóstico que não diz o passo é reclamação.
5. **Não cobre**: se o hook, quando dispara, entrega a mensagem certa (isso é o
   `tests/teste_nucleo.py`); nem se a notificação do macOS chega à tela.

## Critério binário

O `ia-doctor` está funcionando se, e somente se, **os quatro** valem:

1. **`ia-doctor` sai 1** quando existe defeito real, e o `passo:` daquele item, executado
   literalmente, faz o item virar ✓ na rodada seguinte. **Medido** em sala isolada
   (`IACHAT_HOME` em `/tmp`, nunca a sala do Bauer): `sala-estrutura` ✗ e exit 1 → colei o
   `passo:` no terminal → `sala-estrutura` ✓, `sala-config` ✓ e exit 0. No mesmo ciclo,
   `.estado.json` ausente saiu **⚠** e não ✗ — que é o desfecho certo para uma sala nova.
2. **`ia-doctor` sai 0** e não escreve **nada** — comprovado por
   `IACHAT_HOME=<inexistente> ia-doctor` deixar o caminho inexistente (medido: sim).
3. **Nenhum comando externo é julgado através de pipe.** `grep -n 'subprocess\.run'
   bin/ia-doctor` devolve 2 chamadas (`:157` e `:308`), ambas com lista de argumentos e
   `capture_output=True`; `grep -c 'os.system\|shell=True\|Popen'` devolve 0. As 4
   ocorrências de `grep -q` no arquivo (`:20`, `:24`, `:151`, `:653`) são **texto** —
   docstring, comentário e a string do campo `como:` —, nenhuma é execução. *(Escrevi este
   critério como "grep -c 'grep -q' devolve 0", rodei, deu 4, e o critério é que estava
   errado. Fica registrado: critério que não foi rodado é palpite.)*
4. **Todo item impossível de medir sai ⚠**, e o placar reporta os três números separados.
   Se algum dia um ⚠ virar ✓ sem uma medição nova, o programa quebrou seu contrato.

O item 1 é o único que precisa de execução para valer: aplicar o passo de
`codex/hook-ativo` (`ia-bell-install-hook.py codex` — que **imprime** em vez de editar, de
propósito, porque editar `hooks.json` invalida o `trusted_hash`) e reconferir.

## Uma escrita no repositório que não foi minha — e não consigo provar que não foi

Durante o trabalho, `~/Projetos/ia-chat/bin/__pycache__/iachat_core.cpython-314.pyc`
ganhou `birth` **17/08 22:12:14**. A regra era não escrever no repositório, então registro
em vez de omitir.

O que sei: meu único acesso ao repositório foi leitura — `Read`, `grep`, `sed`, `shasum`
e `Path.read_bytes()` dentro do `ia-doctor`; nenhuma dessas gera bytecode, e o
`ia-doctor` não importa `iachat_core` (é standalone, de propósito). O candidato compatível
está vivo na máquina: `ps` mostra um worker `a4-qwen` do mesmo enxame rodando há 19 min
sobre este contrato, e `tests/teste_nucleo.py:20` insere `<repo>/bin` no `sys.path` antes
de `:50 import iachat_core` — que produz exatamente esse arquivo, exatamente nesse lugar.

O que **não** sei: atribuir a escrita com certeza. Não há log de autoria de bytecode.
Fica como ⚠, no mesmo padrão do resto deste laudo.

## Onde ele mora

Standalone: `bin/ia-doctor` não importa `iachat_core` — lê a sala pelo disco. Isso é
proposital: se o core estiver quebrado, o diagnóstico ainda roda. Instalação natural:
copiado por `install.sh` para `$DEST_SCRIPTS` e linkado em `$DEST_BIN`, ao lado do
`iachat`, junto com esta `SKILL.md` em `$DEST_SKILLS/ia-doctor/`.

---

## Saída real, `./bin/ia-doctor --repo ~/Projetos/ia-chat` · exit 1

```
ia-doctor · sala /Users/bauervieiracesarfilhovieira/ia-chat-global · 17/08/2026 22:12:00

SALA
  ✓ cli-no-path          /Users/bauervieiracesarfilhovieira/.local/bin/iachat → /Users/bauervieiracesarfilhovieira/.claude/scripts/ia-chat/iachat
    como:  command -v iachat
  ✓ cli-responde         tamanho   24757 B / 102400 B (24% do teto)
    como:  /Users/bauervieiracesarfilhovieira/.local/bin/iachat status
  ✓ sala-estrutura       /Users/bauervieiracesarfilhovieira/ia-chat-global completa
    como:  test -d/-f em /Users/bauervieiracesarfilhovieira/ia-chat-global
  ✓ sala-integra         contador e documento em #16
    como:  json.loads(.estado.json) vs regex na cauda de iachat.md
  ✓ sala-config          brain=claude · teto=102400 · na_sala=claude, codex, kimi · notificar_operador=True
    como:  json.loads(/Users/bauervieiracesarfilhovieira/ia-chat-global/config.json)
  ✓ sala-teto            24757 B = 24% do teto 102400 B
    como:  stat -f %z /Users/bauervieiracesarfilhovieira/ia-chat-global/iachat.md vs config.json:teto_bytes
  ✓ codigo-sincronizado  6/6 idênticos
    como:  sha256 de /Users/bauervieiracesarfilhovieira/Projetos/ia-chat/bin/* vs /Users/bauervieiracesarfilhovieira/.claude/scripts/ia-chat/*

CASCA:CLAUDE
  ✓ sessao-aberta        1 processo(s) `claude`; o mais antigo é pid 416, aberto 16/08 13:45:35 · claude --effort ultracode
    como:  ps -Ao pid,etime,comm,args (etime → segundos; lstart depende de locale)
  ✓ skill-no-disco       7/7 em /Users/bauervieiracesarfilhovieira/.claude/skills
    como:  cabeçalho YAML de <dir>/<skill>/SKILL.md; procurei em: /Users/bauervieiracesarfilhovieira/.claude/skills
  ⚠ skill-na-sessao      skill mudou 17/08 21:27:02, sessão mais antiga abriu 16/08 13:45:35 — o catálogo dela é anterior; NÃO consigo ler o catálogo de dentro
    como:  stat mtime de <skill>/SKILL.md em /Users/bauervieiracesarfilhovieira/.claude/skills vs início do processo (ps)
    passo: abra uma sessão nova de claude (catálogo é lido no boot)
  ✓ hook-ativo           em SessionStart, UserPromptSubmit
    como:  json.loads(/Users/bauervieiracesarfilhovieira/.claude/settings.json) → hooks[*].command
  ✓ hook-executavel      1 comando(s) apontam para binário -x
    como:  os.access(caminho, X_OK) sobre o command declarado
  ⚠ hook-na-sessao       config mudou 17/08 20:47:19, sessão mais antiga abriu 16/08 13:45:35 — essa sessão roda a config ANTERIOR e o hook não dispara nela
    como:  stat mtime de /Users/bauervieiracesarfilhovieira/.claude/settings.json vs início do processo (ps)
    passo: reabra claude: config de hook é lida no boot
  ✓ daemon-vivo          pid 49797 · plist presente · log tocado 17/08 21:03:18
    como:  launchctl list (saída INTEIRA capturada; sem `| grep -q`) + procura de com.bauer.ia-bell-claude
  ✓ caixa                sem pendência · cursor em #16
    como:  test -f /Users/bauervieiracesarfilhovieira/ia-chat-global/pendente/claude.md + json.loads(/Users/bauervieiracesarfilhovieira/ia-chat-global/cursor/claude.json)

CASCA:CODEX
  ⚠ sessao-aberta        nenhum processo `codex` vivo — nada a comparar com a sessão; a próxima abertura já nasce com a config atual
    como:  ps -Ao pid,etime,comm,args
  ✓ skill-no-disco       7/7 em /Users/bauervieiracesarfilhovieira/.codex/skills
    como:  cabeçalho YAML de <dir>/<skill>/SKILL.md; procurei em: /Users/bauervieiracesarfilhovieira/.codex/skills
  ⚠ skill-na-sessao      casca fechada — não há catálogo de sessão a inspecionar
    como:  stat mtime de <skill>/SKILL.md em /Users/bauervieiracesarfilhovieira/.codex/skills vs início do processo (ps)
  ✗ hook-ativo           nenhum `ia-bell-hook.sh` em hooks.json
    como:  json.loads(/Users/bauervieiracesarfilhovieira/.codex/hooks.json) → hooks[*].command
    passo: python3 /Users/bauervieiracesarfilhovieira/.claude/scripts/ia-chat/ia-bell-install-hook.py codex
  ⚠ hook-na-sessao       casca fechada — a próxima abertura lê a config atual
    como:  stat mtime de /Users/bauervieiracesarfilhovieira/.codex/hooks.json vs início do processo (ps)
  ✗ hook-confiado        1 hook(s) sem entrada em [hooks.state]: UserPromptSubmit[1][0]
    como:  tomllib.loads(/Users/bauervieiracesarfilhovieira/.codex/config.toml) → [hooks.state] vs json.loads(/Users/bauervieiracesarfilhovieira/.codex/hooks.json) → hooks[evento][g].hooks[h]
    passo: abra o codex e APROVE o hook quando ele perguntar — enquanto não aprovar, ele pula o hook sem dizer nada
  ⚠ hook-hash-confere    o algoritmo do `trusted_hash` não é reproduzível por fora do Codex — verifico a PRESENÇA da aprovação, não o valor do hash
    como:  sha256 testado sobre command/JSON/script: nenhum bateu
  ✗ daemon-vivo          com.bauer.ia-bell-codex não está carregado
    como:  launchctl list (saída INTEIRA capturada; sem `| grep -q`) + procura de com.bauer.ia-bell-codex
    passo: /Users/bauervieiracesarfilhovieira/.claude/scripts/ia-chat/ia-bell-install-daemon.sh codex
  ⚠ caixa                flag pendente há 64 min (cursor em #1) — o sino tocou e ninguém leu; não sei se a casca está fechada ou surda
    como:  test -f /Users/bauervieiracesarfilhovieira/ia-chat-global/pendente/codex.md + json.loads(/Users/bauervieiracesarfilhovieira/ia-chat-global/cursor/codex.json)
    passo: na sessão de codex: iachat read --de codex --novas

CASCA:KIMI
  ✓ sessao-aberta        3 processo(s) `kimi`; o mais antigo é pid 65750, aberto 15/08 17:47:54 · kimi
    como:  ps -Ao pid,etime,comm,args (etime → segundos; lstart depende de locale)
  ✓ skill-no-disco       7/7 em /Users/bauervieiracesarfilhovieira/.claude/skills
    como:  cabeçalho YAML de <dir>/<skill>/SKILL.md; procurei em: /Users/bauervieiracesarfilhovieira/.claude/skills, /Users/bauervieiracesarfilhovieira/.claude/plugins/cache/thedotmack/claude-mem/current/skills
  ⚠ skill-na-sessao      skill mudou 17/08 21:27:02, sessão mais antiga abriu 15/08 17:47:54 — o catálogo dela é anterior; NÃO consigo ler o catálogo de dentro
    como:  stat mtime de <skill>/SKILL.md em /Users/bauervieiracesarfilhovieira/.claude/skills vs início do processo (ps)
    passo: abra uma sessão nova de kimi (catálogo é lido no boot)
  ✓ hook-ativo           em SessionStart, UserPromptSubmit
    como:  tomllib.loads(/Users/bauervieiracesarfilhovieira/.kimi-code/config.toml) → hooks[*].command
  ✓ hook-executavel      1 comando(s) apontam para binário -x
    como:  os.access(caminho, X_OK) sobre o command declarado
  ⚠ hook-na-sessao       config mudou 17/08 20:57:27, sessão mais antiga abriu 15/08 17:47:54 — essa sessão roda a config ANTERIOR e o hook não dispara nela
    como:  stat mtime de /Users/bauervieiracesarfilhovieira/.kimi-code/config.toml vs início do processo (ps)
    passo: reabra kimi: config de hook é lida no boot
  ✓ daemon-vivo          pid 49817 · plist presente · log tocado 17/08 21:01:34
    como:  launchctl list (saída INTEIRA capturada; sem `| grep -q`) + procura de com.bauer.ia-bell-kimi
  ✓ caixa                sem pendência · cursor em #14
    como:  test -f /Users/bauervieiracesarfilhovieira/ia-chat-global/pendente/kimi.md + json.loads(/Users/bauervieiracesarfilhovieira/ia-chat-global/cursor/kimi.json)

PLACAR  ✓ ok 20 · ✗ falhou 3 · ⚠ não-consegui-verificar 9
        ⚠ não é ✗: é o que este programa admite não saber. Ler os `passo:` dos ⚠
        é o que transforma dúvida em medida.
```
