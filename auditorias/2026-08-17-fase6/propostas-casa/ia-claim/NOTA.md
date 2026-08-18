# ia-claim — nota de desenho

Reserva de território entre IAs que compartilham o disco. Protótipo rodado e medido em
`IACHAT_HOME` temporário sob `/tmp`; **nada foi escrito em `~/Projetos/ia-chat` nem em
`~/ia-chat-global`**.

**Entrega:** `SKILL.md` · `NOTA.md` · `bin/iachat_claim.py` (núcleo, 370 linhas) ·
`bin/iachat-claim` (CLI protótipo, 153) · `bin/teste_claim.py` (bateria de 9 gates, 216).
Os `bin/iachat_core.py` e `bin/iachat` da pasta são **symlinks de leitura** para o repo.

Rodar: `cd bin && python3 teste_claim.py` — cria e apaga o próprio lab. Verificado: 0
diretórios em `/tmp` e `/var/folders/.../T/` antes e depois da execução.

---

## 1. Onde mora o registro — e por que não no chat

`$IACHAT_HOME/claims/<sha1(caminho)[:12]>-<cauda-legível>.json`, um arquivo por reserva.
Segue o padrão que o projeto já usa para estado: `cursor/<ia>.json` (`iachat_core.py:69-70`) e
`pendente/<ia>.md` (`iachat_core.py:65-66`) — nenhum dos dois vive no `iachat.md`, pelo mesmo
motivo. **Reserva precisa ser consultada, não lida.** O chat é para o que uma IA precisa
receber; a reserva é para o que ela precisa perguntar.

O número que fecha a decisão: se cada reserva postasse, 20 reservas/dia × ~300 B = **6 KB/dia
no ativo de 200 KB** (`teto_bytes`, `iachat_core.py:42`), e o ativo é o que toda IA paga ao
entrar. Em três dias a reserva teria comido 9% do teto com conteúdo que ninguém lê duas vezes.

Um arquivo por reserva, e não um `claims.json` único, por três consequências diretas:
liberar é `unlink` (sem read-modify-write); duas IAs mexendo em caminhos diferentes não
disputam o mesmo arquivo; e um JSON corrompido derruba uma reserva, não o mapa inteiro.

**Custo medido:** registro de **286 B**. `claim list` com 7 reservas: **947 B ≈ 236 tokens**.
240 reservas ocupam 45.640 B em disco — irrelevante, e na prática são unidades por dia.

## 2. Prazo padrão: 60 min, teto 240, renovação explícita

Medi antes de escolher. Agrupando as escritas de 72 h em `~/.claude`, `~/.codex` e
`~/.kimi-code` (só `.md/.json/.toml/.sh/.py`, sem `projects/`, `history/`, `logs/`) por
empreitada, com corte em gap > 15 min: **12 empreitadas, mediana 65,1 min, p90 218,6 min,
máx 615 min**.

O que essa medida É: a janela em que arquivos de config foram mexidos. O que ela **não** é:
o tempo que uma IA identificada segurou um caminho — o disco não guarda autor. É a melhor
proxy disponível nesta máquina, e digo isso em vez de vender precisão que não tenho.

A régua que fixa o número é assimétrica:

| erro | consequência | custo |
|---|---|---|
| prazo **curto** demais | vence com a dona trabalhando; outra IA entra por cima | o defeito original **de volta, com falsa segurança em cima** |
| prazo **longo** demais | caminho travado por IA que fechou | um `claim break`: 1 comando, registrado |

Errar para o lado longo é barato; para o lado curto, é pior que não ter a peça. Daí padrão em
60 min (cobrindo a mediana de 65) e teto duro em 240 (≈ p90). Acima disso não é reserva, é
posse — e posse se negocia no chat.

**Renovação estende a partir de agora, não soma ao prazo antigo** (`renovar()`,
`iachat_claim.py:266-290`). Somar deixaria uma IA que renovou 6× viva por 6 h sem que ninguém
tivesse decidido isso. Gate 5 prova: a 2ª renovação de 10 min moveu o vencimento em **0,0 s**
— somar teria dado +600 s.

Renovação é **explícita**, não heartbeat automático. Heartbeat significaria daemon, e o
briefing já registra por que a rotação não depende de processo vivo (decisão 4): o que depende
de alguém estar de pé falha exatamente quando é preciso.

## 3. O conflito simultâneo — o `fcntl` resolve, e resolve de graça

`travado()` (`iachat_core.py:126-137`) já dá lock exclusivo por `fcntl.flock`. `reservar()`
(`iachat_claim.py:219-264`) põe **o "existe reserva viva?" e o "grava a minha" dentro da mesma
seção crítica**. Não há janela TOCTOU, e não escrevi uma linha de lock nova — reusei a que o
projeto provou.

**Gate 1, medido:** 6 processos de verdade (`ProcessPoolExecutor`, não threads — só processo
separado testa `flock`) disputando o **mesmo** caminho no mesmo instante → **exatamente 1
vence**, os outros 5 recebem "reservado por X". Lock máximo segurado: **3,3 ms**.

**Gate 2:** 6 processos, 6 caminhos distintos → **6/6 vencem**. O lock é global, mas a seção
crítica é curta o bastante para não virar fila.

**A alternativa que descartei:** `os.open(O_CREAT|O_EXCL)` no arquivo da reserva daria exclusão
mútua por caminho, sem lock global. Descartada porque `O_EXCL` também falha contra reserva
**vencida**, e reciclar a vencida exige ler-decidir-escrever — que reintroduz a corrida que o
`O_EXCL` tinha eliminado. O `travado()` cobre os dois casos com o mesmo mecanismo.

**O preço do empréstimo, medido** (o lock é o mesmo do `post`): 60 posts sozinho vs. 60 posts
sob rajada de ~145 reservas/s de outro processo.

```
post SOZINHO           mediana 4,15 ms   p95  9,16 ms
post SOB rajada        mediana 8,74 ms   p95 13,84 ms   → +4,59 ms
```

+4,6 ms de mediana sob uma carga que nunca vai acontecer (na prática são unidades de reserva
por hora, não 145/s). O empréstimo se paga.

**`check` não pega o lock** (`checar()`, `iachat_claim.py:348-370`), de propósito: consulta é o
caminho quente — um hook a chamaria a cada `Write` — e fazer quem só consulta entrar na fila de
quem posta seria cobrar o preço errado. O pior que a corrida faz é responder "livre" a um
caminho reservado meio milissegundo antes, e a resposta já é advisory de qualquer forma.
**Medido: `check` 0,27 ms · `take` 1,53 ms.**

## 4. Cooperativo, com o dente que existe e sem o que não existe

**É cooperativo. Não tem dente hoje, e eu não fingi que tem.** O Codex escreve com a ferramenta
dele, o Kimi com a dele; nenhuma passa pelo `iachat`. Uma IA que ignore a reserva não é barrada
por nada.

Por que ainda vale, em três razões que sustento com o que está no repositório:

1. **O modo de falha real é ignorância, não malícia.** As três cascas não brigaram por
   `~/.claude/skills/` — nenhuma sabia da outra. Contra ignorância, informar resolve;
   e entre IAs do mesmo dono não há a adversarialidade que exigiria coerção.
2. **Resolve o post-mortem, que hoje não tem resposta.** O `trusted_hash` do Codex quebra em
   silêncio. Quando quebrar de novo, "quem mexeu no `hooks.json`, quando e para quê" só tem
   resposta se alguém tiver anotado — e `claim list --todas` é essa anotação, mesmo que
   ninguém tenha respeitado a reserva.
3. **A quebra não pode ser silenciosa, e essa parte é garantida.** `quebrar()`
   (`iachat_claim.py:311-346`) remove a reserva **e** chama `core.post()` nominando a dona, com
   o motivo. Gate 7 prova: a reserva sumiu, o chat ganhou 1 mensagem, `de=kimi`,
   `para=['claude']` — e o `ia-bell-hook.sh` já existente entrega isso na janela da dona sem
   ela pedir. Se `post` falhar (autor fora da sala), o CLI grita em `stderr` em vez de engolir:
   quebra sem aviso é o defeito, não um detalhe.

**O dente possível, e por que não o entreguei:** um hook `PreToolUse` casando `Write|Edit` que
rode `claim check` e saia 2 bloquearia a ferramenta na Claude Code. **Não implementei nem
testei** — e há razão para desconfiar dele justamente onde mais importaria: os hooks do projeto
hoje são `SessionStart` e `UserPromptSubmit` (`ia-bell-install-hook.py:24`), e no Codex mexer no
`hooks.json` invalida o `trusted_hash` e ele pula em silêncio (briefing). Um dente que falha
calado na casca mais frágil é pior que nenhum dente. Fica como proposta explícita, não como
alegação.

## 5. Detecção de reserva morta

**O mecanismo é a expiração; os sinais só coloram o relatório.** Gate 4 prova que reserva
vencida deixa de bloquear sem daemon, sem cron, sem processo de limpeza: quem lê compara `ate`
com o relógio.

Antes de vencer, dois sinais que já existiam de graça (`_sinal_de_vida()`,
`iachat_claim.py:147-176`):

- **Cursor** (`cursor/<ia>.json`, gravado por `marca_lida()`, `iachat_core.py:308-314`) — carrega
  `em`, atualizado a cada leitura da sala. É o único heartbeat honesto que o projeto tem.
- **mtime do caminho reservado** — reserva viva sobre arquivo que não muda há 40 min é suspeita.

**A honestidade que o sinal exige:** ele é **assimétrico**. Cursor recente **prova** vida;
cursor velho **não prova** morte, porque o cursor só avança quando há mensagem
(`if avancar and msgs`, `iachat_core.py:346`) — sala parada congela o cursor de uma IA
perfeitamente ativa. Por isso **nada aqui libera reserva**. Quem libera é o relógio; o sinal só
diz se vale perguntar antes de esperar.

**PID foi considerado e descartado.** O único PID disponível é o do processo `iachat`, que morre
ao fim do comando: `os.kill(pid, 0)` diria "morta" sempre, e sobre um PID reciclado diria "viva"
mentindo. Sinal pior que sinal nenhum — não entrou.

**Guarda contra falso positivo:** reserva mais nova que 20 min nunca é marcada suspeita
(`_suspeita()`, `iachat_claim.py:178-201`). Sem ela, a primeira reserva de uma sala nova sai
rotulada "pode ser órfã" porque o cursor ainda não existe — apareceu no primeiro teste manual.
É a mesma família do sino que anunciava o Codex e era a Claude.

## 6. Contenção de prefixo — sem isto, a peça não cobre o caso que a motivou

O conflito real do briefing é de **diretório**: `~/.claude/skills/`. Reservar o diretório tem
que barrar quem quer `~/.claude/skills/ia-bell/SKILL.md`. `colidem()`
(`iachat_claim.py:100-112`) compara **por componente**, não por string: `/a/bc` não colide com
`/a/b`. Gate 3 prova os dois lados — sub-arquivo barrado, `territorio-vizinho` liberado.

`resolver()` canoniza `~`, `.`, `..` e symlink antes de tudo, e `_p_claim()` resolve **sempre**
(`iachat_claim.py:89-98`). Isso nasceu de um defeito real pego no gate 1: no macOS
`/var/folders/...` é symlink de `/private/var/folders/...`, o mesmo alvo gerava dois registros e
a reserva não valia nada. A casa é cheia de symlink; resolver na função, e não na chamada,
mata a classe inteira.

## 7. Bateria — 9/9 verde

```
✔ 1. mesmo caminho: exatamente 1 vence — vencedor=['claude'] · 6 processos · lock máx 3,3 ms
✔ 2. caminhos distintos: todos vencem — 6/6 · lock máx 10,2 ms
✔ 3. prefixo por componente: sub barrado, vizinho liberado
✔ 4. reserva vencida não bloqueia (sem daemon, sem cron)
✔ 5. renovação = a partir de agora — 2ª renovação moveu o vencimento em 0,0 s (somar daria +600 s)
✔ 6. só o dono libera — terceiro negado, dono ok
✔ 7. break remove E posta nominando o dono — msg #1 de kimi → ['claude']
✔ 8. dono re-reservando o próprio caminho não é conflito — `desde` preservado
✔ 9. custo — registro 286 B · list 947 B (~236 tk) · check 0,27 ms · take 1,53 ms
```

**Dois defeitos que a bateria pegou no meu próprio código, e não no do projeto:**

- `_p_claim()` não resolvia o caminho, então no macOS `/var/folders/...` (symlink de
  `/private/var/folders/...`) gerava **dois registros para o mesmo alvo** — a reserva não valia
  nada e o gate 1 quebrou com `FileNotFoundError`. Corrigido resolvendo dentro da função, não
  na chamada, o que mata a classe inteira (`~`, `.`, `..`, symlink no meio).
- O teste deixava **49 diretórios órfãos** em `/var/folders/.../T/`: no macOS o
  `ProcessPoolExecutor` usa `spawn`, que re-importa o módulo em cada worker, e o `mkdtemp`
  solto no topo dava um lab novo por processo — nenhum apagado. Corrigido com a flag
  `CLAIM_TESTE_LAB`, que distingue pai de filho.

## 8. O que custa, declarado inteiro

| item | custo | contra o quê |
|---|---|---|
| `SKILL.md` na janela | **4.412 B ≈ 1.103 tokens** | maior skill existente 3.316 B; média 2.728 B |
| registro em disco | 286 B/reserva | — |
| `claim list` (7 reservas) | 947 B ≈ 236 tokens | — |
| `check` | 0,27 ms, sem lock | — |
| `take` | 1,53 ms, lock ≤ 3,3 ms | `post` sozinho: 4,15 ms |
| `post` sob rajada de claim | +4,59 ms de mediana | rajada de 145/s, irreal |
| código novo | 370 + 153 linhas | `iachat_core.py` tem 573 |

**A skill está 33% acima da maior existente e eu escolhi não espremer mais.** O que sobra são as
duas seções que impedem a peça de virar garantia falsa: "isto é cooperativo" e "o aviso de
reserva morta não prova morte". Cortá-las devolveria ~900 B e entregaria uma skill que faz a IA
confiar em barreira que não existe — que é o defeito que este projeto mais paga caro.

## 9. Integração — o que falta e não fiz

Não escrevi no repositório, então o que segue é proposta, não estado:

- **`bin/iachat`**: um `sub.add_parser("claim", ...)` por verbo, no estilo de `page`/`search`
  (`iachat:185-194`). O protótipo `bin/iachat-claim` já tem os 6 verbos prontos para colar.
- **`iachat status`**: uma linha `reservas  <n> viva(s)` ao lado de `cursores` (`iachat:80`).
  Custa ~40 B na saída e é onde o operador já olha.
- **`install.sh` / `garantir_estrutura()`**: somar `"claims"` à tupla de `iachat_core.py:107`.
- **Hook `PreToolUse`**: proposta do §4, com a ressalva de confiabilidade lá registrada.

## 10. O que eu não consegui verificar

- **Se as outras cascas vão de fato chamar `take` antes de editar.** Não há como medir isso sem
  as três rodando com a skill instalada por alguns dias. É a premissa da peça, e ela é
  cooperativa por natureza — não sei fingir que testei.
- **Se o hook `PreToolUse` bloqueia mesmo na Claude Code.** Testar exigiria editar o `settings`
  da máquina, fora do escopo desta entrega. Declarei como proposta, não como fato.
- **A medida do §2 mede janela de escrita, não posse por IA.** O disco não guarda autor. É proxy,
  e está rotulada como proxy.
