# NOTA — ia-roster: o que eu medi, o que eu decidi, o que eu não consegui

Tudo abaixo foi rodado na máquina real em 17/08/2026, entre 22:00 e 22:05, contra a sala
viva `/Users/bauervieiracesarfilhovieira/ia-chat-global`. Nada foi escrito lá nem em
`~/Projetos/ia-chat`.

---

## 1. A lista estática é estática mesmo — confirmado por linha

`status()` em `bin/iachat_core.py:375-391`:

- linha 380 · `sala = [normaliza_ia(x) for x in cfg.get("na_sala", [])]` — vem do
  `config.json`, ponto. Nenhum sinal a atualiza.
- linha 387 · `"na_sala": sala` — devolvida crua.
- linha 390 · `"cursores": {x: cursor(x) for x in sala}` — e `cursor()` (linha 301-305)
  devolve **só o inteiro `ultima_lida`**. O campo `em`, que `marca_lida` grava na linha
  312, é **jogado fora**. O sinal de presença já está no disco e o `status` o descarta.

Dois defeitos a mais que achei enquanto lia, ambos com medida:

**(a) `status()` não é read-only.** Linha 376 chama `config()`, que na linha 119 chama
`garantir_estrutura()`, que nas linhas 105-115 faz `mkdir` e escreve `config.json` e
`iachat.md`. Medido numa pasta vazia:

```
antes:  0 arquivo(s)
depois: 3 arquivo(s) — iachat.md config.json .lock/iachat.lock
```

Perguntar quem está na sala **cria a sala**. O `iaroster` na mesma pasta vazia: 0
arquivos, exit 0.

**(b) `status()` pega o lock exclusivo e lê o chat inteiro** (linhas 377-379) só para
contar mensagens. Hoje 24.893 B; no teto configurado, 102.400 B — bloqueando todo mundo
que quer postar. O `iaroster` lê 350 B (config + `.estado.json` + 3 cursores) e **não
pega o lock**. No teto: **292× menos I/O**.

**(c) rótulo invertido.** `bin/iachat:81` imprime `sino ativo  codex` a partir de
`s['pendentes']` (`iachat_core.py:389`), que é *quem tem flag por ler*. A saída real de
hoje era `sino ativo  codex` — a única pista de que a mensagem estava presa, escrita com
palavra de boa notícia.

---

## 2. O caso real, com relógio

Não precisei simular. A sala estava exibindo o defeito:

| hora | fato | evidência |
|---|---|---|
| 20:41:25 | codex lê pela última vez, cursor em `#1` | `cursor/codex.json` |
| 20:45-46 | sobem os sinos de **claude** e **kimi** | `ia-bell-{claude,kimi}.log:1-2` |
| 21:01:23 | sobe o sino do **operador** | `ia-bell-operador.log:4` |
| 21:07:44 | claude nomina codex na `#15`; flag gravado | `pendente/codex.md` |
| 21:07:56 | o operador é notificado da `#15` | `ia-bell-operador.log:7` |
| **22:04** | codex ainda em `#1`, sala em `#16`, flag intacto | `iaroster` |

**56 minutos.** A causa raiz não era lentidão do codex: **o sino dele nunca foi
instalado.** `launchctl list` tem `com.bauer.ia-bell-claude`, `-kimi`, `-operador` e
**não tem `-codex`**; `~/Library/LaunchAgents/` idem. E não há
`ia-bell-codex.log` na sala — o daemon nunca escreveu a primeira linha.

O operador foi avisado 3× sobre mensagens dirigidas ao codex (`ia-bell-operador.log`
linhas 2, 3, 7). O destinatário, nenhuma vez. O sino do dono funcionou; o do morador não
existia.

---

## 3. Cada sinal candidato, medido — qual mente

### `ps` — **mente, e mente na direção errada**

O briefing pergunta se processos vivos denunciam presença. Medido:

```
claude: 20 processos casando /claude
codex:  27 processos casando /codex
kimi:    4 processos casando /kimi
```

Todos são helpers de app desktop: `/Applications/Claude.app/Contents/Frameworks/Claude`,
`/Applications/ChatGPT.app/Contents/Frameworks/Codex`. **O codex — a IA que ficou 56 min
sem ler — é o que tem MAIS processos.** O kimi, o mais responsivo do dia (leu 21:04,
respondeu 21:23), tem o MENOS. A correlação é negativa. Um painel construído sobre `ps`
teria pintado o codex de verde exatamente na hora em que ele estava cego.

Não usei `ps` no protótipo. Não é conservadorismo: é que ele estava errado no único caso
que eu tinha para testar.

### `cursor/<ia>.json` campo `em` — **honesto, mas só numa direção**

Escrito por `marca_lida` (`iachat_core.py:308-314`). Quem o chama:

- `ler(..., avancar=True)` (linha 346-347) — dispara mesmo quando não há nada novo, desde
  que a janela de cauda traga alguma mensagem. Para uma IA que roda `iachat read`, é um
  heartbeat de verdade.
- `cmd_entregar` (`bin/iachat:63`) — **só no ramo em que houve entrega**. Para uma IA no
  hook, o cursor só se move quando ela recebe algo.

Consequência que precisa estar escrita: **"leu há 2 min" prova vida; "leu há 3 h" não
prova morte.** Uma IA aberta, atenta e sem ser chamada nunca toca o próprio cursor. Por
isso a coluna chama `leu`, verbo no passado, e não `visto por último`.

### `pendente/<ia>.md` — **o melhor sinal, porque mede o dano**

Não responde "está viva?" — responde "a mensagem chegou?". A idade do mtime é
exatamente o prejuízo: 56 min de mensagem parada. É o único sinal cuja leitura ruim é
sempre acionável.

### `launchctl list` — **binário, barato, e foi o que pegou a causa raiz**

Custo medido: **0,00 s**. Diz se existe carteiro para aquela IA. Duas armadilhas que
tratei:

1. **Nunca `launchctl list | grep -q`.** O grep sai no primeiro casamento, o pipe fecha,
   o launchctl morre de SIGPIPE — foi o que negou um daemon que tinha subido
   (`ia-bell-install-daemon.sh:48-51`). Capturo a saída inteira e só então julgo.
2. **Sino no ar pode estar vigiando OUTRA sala.** O plist carrega `IACHAT_HOME`
   (`ia-bell-install-daemon.sh:34-35`). Sem conferir isso, `sino: no ar` seria
   precisamente o verde que mente. Leio o plist (0,02 s) e comparo. Provado: na cópia em
   `/tmp`, claude e kimi aparecem como `⚠ outra sala`, com o caminho do conflito.

### `ia-bell-<ia>.log` — **prova que o sino tocou, não que alguém ouviu**

Útil como histórico, não como presença. Não entrou no protótipo.

---

## 4. Presença ≠ disponibilidade — como não mentir

Três decisões de desenho, não de texto:

1. **Não existe coluna "disponível", "online" ou bolinha verde.** Toda coluna é um
   evento observado com idade. Nome de coluna é verbo no passado (`leu`), não adjetivo
   de estado.
2. **O bloco `não sei dizer` é saída obrigatória**, impresso em toda execução, inclusive
   quando está tudo bem. Ele nomeia explicitamente que ninguém sabe se a janela está
   aberta agora e que quem leu há pouco pode estar num raciocínio de 3 minutos. Rodapé
   opcional vira rodapé ignorado.
3. **Ausência de sinal vira `—` e nunca zero.** Testado: numa sala nova com `grok` e
   `qwen` que nunca leram, a coluna `leu` sai `—`, não `há 0s`.

---

## 5. Vocação: declarada, e por quê

**Medida que decidiu:** a sala inteira tem **16 mensagens** — claude 9, kimi 5,
**codex 2**. Inferir "no que o codex é bom" de 2 mensagens é ruído com aparência de
dado. E a inferência erra em silêncio, enquanto uma declaração à mão erra visivelmente e
com dono.

Então: bloco `vocacao` opcional no `config.json`, `bom`/`ruim`/`custo` por IA. Ausente →
o roster escreve `(não declarada)` na tabela e repete no bloco `não sei dizer`. São 3
linhas para uma sala de 3 IAs; não vale motor de inferência.

**Duplica a cascata do iaswarm?** Não, e a distinção é de pergunta, não de estilo. A
cascata (`~/.claude/skills/iaswarm/SKILL.md:15-25`) responde *qual braço contratar* para
um job despachado: 10 braços, tier de bolso (assinatura → free → créditos), ordem de
fallback dele, cota. O roster responde *quem nominar* entre as 3 que estão nesta sala.
Populações diferentes (10 × 3), decisões diferentes (despachar × nominar).

O que se sobrepõe é o **fato** ("codex → código/raciocínio"). Resolvi por hierarquia
declarada em vez de por cópia: quando a `iaswarm` existir na máquina, ela é a fonte de
verdade e a linha do config é legenda local. Está escrito na SKILL.

Assumo o custo: se o Bauer mudar a cascata e esquecer o config, as duas divergem. Achei
melhor que a alternativa — fazer o `ia-chat` (um plugin que instala em outras máquinas)
parsear prosa de uma skill pessoal que pode não existir lá.

---

## 6. O protótipo

`bin/iaroster` — Python, sem dependência, 203 linhas.

**Read-only por construção**, não por promessa: lê os JSON crus com `pathlib` de
propósito, sem importar `iachat_core`, justamente porque `core.status()` escreve (item
1a). Provado com hash dos mtimes da sala:

```
antes:  230299bb7473fdf8284969ed9e4da7594964ce37b28eb50274f06e916ff0ea16
depois: 230299bb7473fdf8284969ed9e4da7594964ce37b28eb50274f06e916ff0ea16
✔ IDÊNTICO
```

### Saída real, sala viva, 22:04:26

```
sala /Users/bauervieiracesarfilhovieira/ia-chat-global · última #16 · 22:04:26

ia       sino             leu         atraso  chamado parado  vocação
claude   no ar 49797      há 40min         —  —               (não declarada)
codex    ✗ SEM SINO       há 83min        15  há 56min ⚠      (não declarada)
kimi     no ar 49817      há 59min         2  —               (não declarada)

⚠ codex: sino NÃO INSTALADO (com.bauer.ia-bell-codex ausente de launchctl). Nomear codex não avisa ninguém.
    subir: ia-bell-install-daemon.sh codex
⚠ codex: chamado há 56min e ainda não leu (cursor #1, sala #16 — 15 atrás).

não sei dizer, e não vou fingir:
  · se a janela de alguma delas está aberta AGORA — nenhum arquivo desta
    sala prova isso; 'leu' é a última vez que ela leu, não que ela existe
  · se quem leu há pouco está LIVRE ou no meio de um raciocínio de 3 min —
    presença não é disponibilidade, e este programa não promete resposta
  · no que claude, codex, kimi são boas: config.json não tem bloco
    `vocacao` para ela(s) — nominar é palpite até alguém declarar
```

### Saída na cópia em /tmp, com vocação declarada

```
ia       sino             leu         atraso  chamado parado  vocação
claude   ⚠ outra sala     há 40min         —  —               orquestrar, gate, julgamento
codex    ✗ SEM SINO       há 83min        15  há 0s ⚠         código, raciocínio longo
kimi     ⚠ outra sala     há 59min         2  —               construção longa, volume

⚠ claude: sino no ar (PID 49797) mas vigiando OUTRA sala (/Users/…/ia-chat-global). Para esta sala ele é inútil.
```

(`há 0s` no codex é artefato do `cp -R`, que reescreveu o mtime do flag. Real, e o
programa não tem como saber — fica registrado aqui em vez de disfarçado.)

### Bordas testadas

- IA na sala que nunca leu (`grok`, `qwen`, sem cursor, sem `.estado.json`): `leu` e
  `atraso` saem `—`, exit 0.
- Sala inexistente: mensagem em stderr, **exit 2** — não uma tabela vazia plausível.

### Custo

| | `iachat status` | `iaroster` |
|---|---|---|
| tempo | 0,04 s | 0,05 s |
| bytes lidos da sala | 24.893 B (chat inteiro) | **350 B** |
| no teto de 100 KB | 102.400 B | 350 B (**292×**) |
| lock exclusivo | **sim** | não |
| escreve? | **sim** (3 arquivos em sala vazia) | não (hash idêntico) |
| saída | 245 B ≈ 61 tk | 1.135 B ≈ 283 tk *(com 2 alertas)* |

A saída é 4,6× maior que a do `status` (régua de 4 B/token é a do próprio repo,
`iachat_core.py:410`). É caro de propósito, e o extra é medido, não estimado:

- bloco `não sei dizer` com os 3 bullets: **488 B** (o 3º bullet, o de vocação não
  declarada, some quando ela é declarada — aí o bloco cai para **347 B**)
- os 2 alertas do codex: **240 B** — somem quando o defeito some
- sala saudável e com vocação declarada, medido na cópia em /tmp: **856 B ≈ 214 tk**

Ou seja, **153 tokens a mais que o `status` no regime normal**, contra 56 minutos de
mensagem parada. Se ele achar caro, o bloco de incerteza cabe em uma linha — mas não
pode sumir, porque é ele que impede a tabela de virar promessa.

---

## 7. O que eu NÃO consegui determinar

Explícito, como o briefing pede:

1. **Se qualquer janela de CLI está aberta agora.** Não achei nenhum sinal em disco que
   prove isso, e `ps` provou-se enganoso (§3). Se existe um caminho — arquivo de sessão
   do harness, socket, lockfile de CLI — eu não o encontrei nesta sala nem em
   `~/.claude/scripts/ia-chat/`. Fica declarado como não-resolvido, não como resolvido
   por aproximação.
2. **Se uma IA está ocupada.** Não há sinal, e desconfio que não deva haver: mesmo que
   houvesse, ele estaria stale no instante seguinte.
3. **Por que o sino do codex nunca foi instalado.** Vi o efeito, não a causa. Existem
   `com.bauer.codex-ponte-bell` (PID 28041, carregado) e os plists
   `com.bauer.vigia-janela-codex` / `com.bauer.vigia-ponte-codex` (presentes em
   `~/Library/LaunchAgents/`, **não carregados**) — uma ponte anterior para o codex, de
   outro projeto. Se o `ia-bell-codex` foi pulado por parecer redundante com ela, isso é
   hipótese minha; não medi.
4. **Se `ler(avancar=True)` de fato atualiza o `em` quando não há mensagem nova.** Li o
   caminho no código (§3) e concluí que sim, mas não executei — executar exigiria
   escrever na sala real, e a regra 1 do briefing proíbe.
5. **Custo em token de verdade.** Usei a régua de 4 B/token do próprio repositório. Não
   tokenizei com o tokenizer do modelo; nenhum estava disponível localmente.

---

## 8. Se ele quiser só uma coisa desta unidade

Instalar o sino do codex. Uma linha, e o defeito de hoje some:

```
~/.claude/scripts/ia-chat/ia-bell-install-daemon.sh codex
```

O roster não conserta isso — ele só é a peça que **não deixa passar batido de novo**, e
que teria mostrado o buraco 56 minutos antes.
