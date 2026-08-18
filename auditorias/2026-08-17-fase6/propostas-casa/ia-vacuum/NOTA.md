# NOTA — ia-vacuum

Medido em 2026-08-17, entre 21:59 e 22:10, na máquina do Bauer. Nada foi apagado fora
de `/private/tmp/.../scratchpad`.

---

## 1. Inventário — o que existe HOJE no disco

### Zona A — backups dos instaladores

```
~/.claude/settings.json.bak-iachat-20260817-204719      25.982 B
~/.kimi-code/config.toml.bak-iachat-20260817-205727     34.039 B
                                                 total: 64 KB (2 arquivos)
```

**A premissa do brief está errada e eu preciso dizer isso.** O brief afirma que
`ia-bell-install-hook.py` "cria um a cada execução". Ele não cria. O caminho do Claude
tem guarda em `ia-bell-install-hook.py:123-125` (`if not mudou: ... return 0` — sai
antes do `copy2` da linha 130) e o do Kimi em `:39-41` (`if "ia-bell-hook.sh" in atual:
... return 0`, antes do `copy2` da linha 61).

Rodei 3× contra um `settings.json` em `/tmp`:

```
--- execucao 1 ---   ✔ +SessionStart +UserPromptSubmit em settings.json
--- execucao 2 ---   = nada a fazer (o hook de claude já estava como você pediu)
--- execucao 3 ---   = nada a fazer (o hook de claude já estava como você pediu)
=== backups criados apos 3 execucoes ===  1
```

**3 execuções → 1 backup.** O instalador é idempotente.

### Zona B — logs e artefatos de daemon em `~/ia-chat-global/`

```
ia-bell-claude.log      464 B   6 linhas
ia-bell-kimi.log        455 B   6 linhas
ia-bell-operador.log    543 B   8 linhas
ia-bell-{claude,kimi,operador}.{out,err}   0 B × 6 arquivos
                          total: 1.462 B em 9 arquivos
```

Todos nasceram hoje 20:45 (claude/kimi) e 21:00 (operador); a leitura foi 21:59.
**74 min de sessão ativa, 16 mensagens, 1.462 B de log** — ~91 B por mensagem na frota.

### Zona C — a sala

```
arquivo/    0 recortes
pendente/   1 arquivo (codex.md, 275 B)
cursor/     3 arquivos (claude, codex, kimi)
.tmp        0 órfãos (busca recursiva)
iachat.md   24,2 KB de um teto de 200 KB
```

---

## 2. O problema real não é o que o brief supôs

O acúmulo de backup **não** vem de rodar o instalador. Vem de **alternar estado**. Cada
`--remover` seguido de instalação é 1 backup de cada lado. Medido — 3 ciclos
remove/instala:

```
=== apos 3 ciclos remove/instala (+1 inicial) ===
7
settings.json.bak-iachat-20260817-220005
settings.json.bak-iachat-20260817-220018
settings.json.bak-iachat-20260817-220019
settings.json.bak-iachat-20260817-220020
settings.json.bak-iachat-20260817-220021
settings.json.bak-iachat-20260817-220022
settings.json.bak-iachat-20260817-220023
```

**6 backups em 6 segundos.** A 25.982 B cada, uma sessão de depuração do instalador
produz megabytes num minuto — e **tudo no mesmo dia**. Isso colide de frente com a
regra "nunca apaga backup do mesmo dia": aplicada à risca, ela protege exatamente o
lixo que ela deveria recolher, e o vacuum vira no-op na única hora em que serve.

**Como resolvi:** a regra fica valendo à risca no padrão — nada do dia sai. A flag
`--incluir-hoje` existe, vem **desligada**, e o dry-run mostra arquivo por arquivo o
que sairia antes de qualquer coisa acontecer. O `#1 mais recente` da família continua
protegido mesmo com a flag ligada; esse não tem override. Escalar a regra é decisão do
dono, não minha — o que eu faço é deixar o custo dela visível na saída:

```
↷ settings.json.bak-iachat-20260817-200003 passou da cota mas é de HOJE — preservado
  (use --incluir-hoje para recolher)
```

---

## 3. O que quase deu errado — três achados que mudaram o desenho

### 3.1 Apagar recorte corrompe a numeração e sobrescreve histórico

`iachat_core.py:422 rotate()`:

```python
nn = len(_recortes()) + 1
nome = f"iachat-{hoje:%Y-%m-%d}-recorte-{nn:02d}.md"
...
(p_arquivo() / nome).write_text(...)   # write_text puro, sem checar existência
```

A numeração nasce da **contagem de arquivos na pasta**. Apague o `recorte-01` com
`recorte-02` presente: `len()` volta a 1, `nn` vira 2, e a próxima rotação do mesmo dia
grava por cima do `recorte-02` **sem erro e sem aviso**. Um vacuum ingênuo com
"apaga recorte com mais de 30 dias" destruiria histórico de duas maneiras ao mesmo
tempo. Por isso `arquivo/` é zona proibida sob qualquer flag — não há `--force` para ela.

### 3.2 Apagar `.out`/`.err` não libera espaço nenhum

`ia-bell-install-daemon.sh:38-39` aponta `StandardOutPath`/`StandardErrorPath` para
esses arquivos e o launchd os mantém abertos. `lsof`, 17/08:

```
COMMAND   PID    FD   TYPE  SIZE/OFF   NODE      NAME
bash    49797    1u    REG         0   97798056  .../ia-bell-claude.out
bash    49797    2u    REG         0   97798057  .../ia-bell-claude.err
```

`unlink` num arquivo com fd aberto não libera o inode — o daemon continua escrevendo no
inode órfão e o espaço só volta no restart. O verbo correto é `truncate(0)`, que
preserva o inode. Está implementado assim.

**Não consegui verificar** se o launchd abre esses fds com `O_APPEND`. Se não abrir, um
`truncate(0)` com o fd em offset alto gera arquivo esparso com NULs até o offset
anterior. Mitigação adotada: o vacuum só age acima de 64 KB, e na prática esses
arquivos estão em **0 B desde 20:45** — o daemon manda tudo para `$LOG` via `>>`
(`ia-bell-daemon.sh:29,59,69`), nada para stdout/stderr. Se algum dia crescerem, o
caminho limpo é `launchctl kickstart -k`, e isso está anotado.

### 3.3 O mtime dos backups mente

`ia-bell-install-hook.py:61` usa `shutil.copy2`, que **preserva o mtime do original**.
No disco:

```
-rw-------  25982  16 ago 18:44  settings.json.bak-iachat-20260817-204719
                   ^^^^^^^^^^^^                      ^^^^^^^^^^^^^^^
                   mtime: 16/08                      nome:  17/08 20:47
```

Um dia de divergência. `backup.sh:43` e `backup-claude.sh:71` ordenam com `ls -t`
(mtime) — sobre esta família, isso ordena errado e apagaria o backup errado. O
`ia-vacuum` ordena pelo **carimbo no nome**.

---

## 4. O que a peça resolve, e o que custa

**Resolve:** dá dono ao lixo das três zonas, com política declarada e registro. Hoje
nada tem dono — o `.log` do sino é append-only sem rotação em lugar nenhum do repo
(`ia-bell-daemon.sh:29,42,54,59,69`, todos `>>`), e o `.bak` cresce por toggle sem teto.

**Custo medido:**

```
=== custo do dry-run na sala real (3 rodadas) ===
real 0,03
real 0,03
real 0,03
=== tamanho do proprio ia-vacuum ===  347 linhas
=== saida do dry-run em bytes ===     982 B  (~250 tokens)
```

**30 ms por rodada, 982 B de saída.** Roda em hook de `SessionStart` sem ser sentido.

**Quanto economiza, honestamente:** hoje, **nada** — 64 KB de backup e 1,4 KB de log
não são problema. O ganho é o teto, não o presente: sem ele, `.log` e `.bak` não têm
limite superior nenhum, e o pior caso medido é 6 backups (156 KB) em 6 segundos de
depuração. **Esta peça é seguro, não faxina.** Vender economia de espaço aqui seria
mentir sobre o número.

---

## 5. Bateria — dry-run e execução real, saídas coladas

Lixo fabricado num `IACHAT_HOME` e num `HOME` temporários sob `/tmp`: 11 backups de
hoje + 10 antigos, 3 backups de **outros donos** como iscas, log de 350 linhas, `.out`
de 90 KB, 3 `.tmp` em situações diferentes, 2 recortes, 1 pendente vivo + 1 órfão.

### 5.1 Dry-run (padrão)

```
🧹 ia-vacuum · sala .../sala-teste · modo dry-run (nada será tocado)

── o que fica, e por quê ──
  · .../home-teste/.claude/settings.json: 11 backup(s)
  ·   ↷ settings.json.bak-iachat-20260817-200003 passou da cota mas é de HOJE — preservado (use --incluir-hoje para recolher)
  ·   ↷ settings.json.bak-iachat-20260817-200002 passou da cota mas é de HOJE — preservado (use --incluir-hoje para recolher)
  ·   ↷ settings.json.bak-iachat-20260817-200001 passou da cota mas é de HOJE — preservado (use --incluir-hoje para recolher)
  · .../home-teste/.kimi-code/config.toml: 10 backup(s)
  · ia-bell-kimi.log: 1 linhas ≤ 200, intacto
  · ia-bell-claude.err: 0 B ≤ 65536, intacto
  · .estado.json.tmp: alvo .estado.json NÃO existe — pode ser o único dado, intacto
  · kimi.json.tmp: 1 min — pode ser escrita em curso, intacto
  · pendente/claude.md: 'claude' está na sala — é RECADO NÃO LIDO, intacto
  · arquivo/: 2 recorte(s) — zona proibida, nunca entra no plano

── plano: 6 ação(ões), 98236 B ──
  [backup] APAGAR    .../config.toml.bak-iachat-20260802-120000
            └─ #9 da família, cota é 8, carimbo 20260802-120000 · 7 B
  [backup] APAGAR    .../config.toml.bak-iachat-20260801-120000
            └─ #10 da família, cota é 8, carimbo 20260801-120000 · 7 B
  [log] RECORTAR  .../ia-bell-claude.log
            └─ 350 linhas → guarda as últimas 200 · 8142 B
  [log] ZERAR     .../ia-bell-claude.out
            └─ 90000 B acima do teto; launchd segura o fd, então trunca (não apaga) · 90000 B
  [tmp] APAGAR    .../cursor/claude.json.tmp
            └─ órfão há 844 min; alvo claude.json existe · 5 B
  [pendente] APAGAR    .../pendente/codex.md
            └─ 'codex' não está em na_sala=['claude', 'kimi']; nenhum post reescreve nem
               read consome — conteúdo copiado para o registro · 75 B

Dry-run. Para executar exatamente este plano: ia-vacuum --apagar
```

### 5.2 Execução real, e a 2ª rodada no mesmo dia

```
@@@@@@@@@@ RODADA 1 (--apagar) @@@@@@@@@@
  [pendente] APAGAR    .../pendente/codex.md
            └─ 'codex' não está em na_sala=['claude', 'kimi']; ... · 48 B

✔ 6 de 6 executada(s) · registro em .../sala-teste/.vacuum.log

@@@@@@@@@@ RODADA 2 (--apagar, mesmo dia) @@@@@@@@@@
  · ia-bell-claude.out: 0 B ≤ 65536, intacto
  · .estado.json.tmp: alvo .estado.json NÃO existe — pode ser o único dado, intacto
  · kimi.json.tmp: 0 min — pode ser escrita em curso, intacto
  · pendente/claude.md: 'claude' está na sala — é RECADO NÃO LIDO, intacto
  · arquivo/: 2 recorte(s) — zona proibida, nunca entra no plano

= nada elegível: o lixo recolhível já foi recolhido.
  última rodada com efeito: 2026-08-17T22:05:34-03:00 (6 ação(ões), 98205 B)
```

### 5.3 Auditoria do disco depois

```
=== backups iachat sobreviventes (era 11 hoje / 10 antigos) ===
settings.json: 11   (cota 8 + 3 de hoje preservados)
config.toml:    8   (cota)

=== VIZINHOS DE OUTROS DONOS (tem que estar os 3) ===
./.kimi-code/config.toml.bak-antes-oauth-20260813
./.claude/settings.json.bak
./.claude/settings.json.bak-graphify-20260810-205542

=== arquivo/ ===   iachat-2026-08-17-recorte-01.md
                   iachat-2026-08-17-recorte-02.md
=== pendente/ ===  claude.md
=== log ===        201 linhas (1 cabeçalho + 200 de conteúdo)
=== .out ===       0 B, inode preservado
```

### 5.4 O registro

```
[22:05:34] apagar .../config.toml.bak-iachat-20260802-120000 · 5 B · #9 da família, cota é 8, carimbo 20260802-120000
[22:05:34] apagar .../config.toml.bak-iachat-20260801-120000 · 5 B · #10 da família, cota é 8, carimbo 20260801-120000
[22:05:34] recortar .../ia-bell-claude.log · 8142 B · 350 linhas → guarda as últimas 200
[22:05:34] zerar .../ia-bell-claude.out · 90000 B · 90000 B acima do teto; launchd segura o fd, então trunca (não apaga)
[22:05:34] apagar .../cursor/claude.json.tmp · 5 B · órfão há 846 min; alvo claude.json existe
[22:05:34] conteúdo de .../pendente/codex.md:
[22:05:34]   | # 🔔 codex
[22:05:34]   |
[22:05:34]   | **claude** te nominou na **#15**.
[22:05:34] apagar .../pendente/codex.md · 48 B · 'codex' não está em na_sala=['claude', 'kimi']; ...
```

O recado do órfão está preservado por inteiro no registro **antes** da linha que o apaga.

### 5.5 Dry-run contra a sala REAL (leitura pura)

```
🧹 ia-vacuum · sala /Users/bauervieiracesarfilhovieira/ia-chat-global · modo dry-run
  · ~/.claude/settings.json: 1 backup(s)
  · ~/.kimi-code/config.toml: 1 backup(s)
  · ia-bell-claude.log: 6 linhas ≤ 200, intacto
  · ia-bell-kimi.log: 6 linhas ≤ 200, intacto
  · ia-bell-operador.log: 8 linhas ≤ 200, intacto
  · ia-bell-{claude,kimi,operador}.{err,out}: 0 B ≤ 65536, intacto
  · pendente/codex.md: 'codex' está na sala — é RECADO NÃO LIDO, intacto
  · arquivo/: 0 recorte(s) — zona proibida, nunca entra no plano

= nada elegível: o lixo recolhível já foi recolhido.
  nunca rodou com --apagar nesta sala.

exit=0
ls: ~/ia-chat-global/.vacuum.json: No such file or directory
ls: ~/ia-chat-global/.vacuum.log: No such file or directory
```

A última linha é a prova de que o dry-run não escreveu nada, nem o próprio registro.
E ele identificou corretamente o `pendente/codex.md` **real** como recado não lido.

---

## 6. Um bug que o teste pegou

A 1ª versão falhou na idempotência. O cabeçalho que o vacuum escreve no `.log`
recortado contava como linha: 200 guardadas + 1 cabeçalho = 201, e a rodada seguinte
via 201 > 200 e recortava de novo — **para sempre, 1 ação por rodada**.

```
@@@@@@@@@@ SEGUNDA RODADA, mesmo dia @@@@@@@@@@   (versão com bug)
── plano: 1 ação(ões), 91 B ──
  [log] RECORTAR  .../ia-bell-claude.log
            └─ 201 linhas → guarda as últimas 200 · 91 B
```

Corrigido filtrando a própria marca antes de contar, nas **duas** pontas (planejamento
e execução) — senão o cabeçalho se acumularia a cada rodada. Registrado aqui porque a
lição vale mais que o patch: **um recolhedor que deixa rastro precisa não contar o
próprio rastro como lixo.**

---

## 7. Riscos

| Risco | Grau | Mitigação |
|---|---|---|
| Glob pegar `.bak` de outro dono | **alto se errado** | glob estrito + regex reconferindo o nome; provado com 3 iscas sobreviventes (§5.3). Medido: 15 dos 17 `.bak*` da casa são de outros donos |
| Apagar recorte e corromper numeração | **alto se errado** | `arquivo/` é zona proibida sem override; aparece no relatório toda rodada |
| Apagar recado não lido | **alto se errado** | só apaga fora de `na_sala`; conteúdo vai para o registro antes; sem `config.json` legível, não julga flag nenhuma |
| Linha de log perdida na corrida read/replace | baixo | aceito e documentado; alvo nunca é o chat |
| `truncate(0)` gerar arquivo esparso | baixo | **não verificado** (§3.2); só age acima de 64 KB, e os arquivos vivem em 0 B |
| `--incluir-hoje` usado sem olhar | médio | desligada por padrão; dry-run lista arquivo por arquivo; `#1` protegido sem override |

---

## 8. Critério binário

A peça está pronta quando, na bateria de `/tmp` do §5, **todas** valem:

1. Dry-run sem `--apagar` não cria `.vacuum.log` nem `.vacuum.json` — ✅ §5.5
2. O plano do dry-run e o da execução são a mesma lista — ✅ mesma função `planejar()`
3. 2ª rodada `--apagar` no mesmo dia: 0 ações + motivo com data da anterior — ✅ §5.2
4. Os 3 `.bak` de outros donos sobrevivem — ✅ §5.3
5. Os 2 recortes de `arquivo/` sobrevivem — ✅ §5.3
6. `pendente/claude.md` (IA na sala) sobrevive; `codex.md` (fora) sai **com o conteúdo
   no registro antes** — ✅ §5.3, §5.4
7. O `#1` de cada família de backup sobrevive — ✅ §5.3
8. `.out` fica 0 B **com o inode preservado**, nunca `unlink` — ✅ §5.3
9. `.tmp` recente ou sem alvo final sobrevive; só o velho-com-alvo sai — ✅ §5.1
10. Toda ação executada tem uma linha no `.vacuum.log` com caminho, bytes e motivo — ✅ §5.4

**10/10 nesta rodada.** Falha em qualquer um = a peça não sobe.

---

## 9. O que eu não fiz

- **Não instalei nada.** Sem LaunchAgent, sem hook, sem entrada em `settings.json`. A
  peça é um executável e um documento; ligar em `SessionStart` (30 ms, §4) ou em cron é
  decisão do dono.
- **Não escrevi em `~/Projetos/ia-chat` nem em `~/ia-chat-global`.** O único contato com
  a sala real foi o dry-run do §5.5, que é leitura.
- **Não apaguei nada real.** Os 2 `.bak-iachat-*` do §1 continuam no disco.
