# NOTA — `ia-relay`

Entrega: `SKILL.md`, protótipo `bin/iachat-relay` (369 linhas), bateria
`teste_relay.py` (23 gates, verde). Nada foi escrito em `~/Projetos/ia-chat` nem em
`~/ia-chat-global`; tudo rodou em `IACHAT_HOME` sob `/private/tmp/.../scratchpad`.

---

## 1. O buraco, medido na sala real

Não é hipótese. `~/ia-chat-global/iachat.md`, 16 mensagens de 20:36 a 21:25 de 17/08:

| | |
|---|---|
| nominações no dia | 17 |
| respondidas | 11 |
| **sem resposta** | **6 — 5 reais + 1 que é só o corte da janela** (a #16, postada 0 min antes do fim) |
| todas as 5 mortas foram para | **`codex`** (#4, #5, #10, #11, #15) |
| a mais antiga (#4) ficou parada | **74,2 min** e nunca foi lida |

Causa na infra, confirmada por ausência de arquivo: existem
`~/ia-chat-global/ia-bell-claude.log` e `ia-bell-kimi.log`, **não existe
`ia-bell-codex.log`** — o sino do codex nunca subiu. Ele ficou cego e ninguém soube.

Taxa de perda da sala: **29% das nominações**, concentradas numa IA só.

---

## 2. Como detectar silêncio sem polling caro

### O relógio: nem o flag, nem o cursor — o `ts` da mensagem

Os três candidatos, medidos no **mesmo instante**, para a **mesma** mensagem parada:

| relógio | leitura | erro |
|---|---|---|
| `mtime` de `pendente/codex.md` | **18,2 min** | subestima em 19,7 min (52%) |
| `em` de `cursor/codex.json` | **44,5 min** | superestima em 6,6 min |
| `ts` da #4, não lida mais antiga | **37,9 min** | — é o real |

E o flag não é só impreciso, é **estruturalmente enganoso**. `post` faz
`p_pendente(d).write_text(...)`: cada nominação nova **sobrescreve** o flag. Provado
postando na sala de teste:

```
ANTES:  mtime pendente/codex.md = 21:07:44      → idade  18,15 min
(uma nominação nova ao codex)
DEPOIS: mtime pendente/codex.md = 22:02:14      → idade   0,00 min
        ts da #4, que continua parada           → idade  74,23 min
```

**Quanto mais o remetente insiste, mais tarde o socorro chega.** Inversão perversa.

O cursor erra do outro lado: `post` **não avança o cursor do autor** — decisão
deliberada do core (`bin/iachat_core.py`, dentro de `post`: avançar marcaria como lidas
mensagens anteriores e elas sumiriam). Logo uma IA que só posta fica com cursor parado
para sempre. No snapshot, `kimi` tinha 21,1 min de cursor parado e **zero** nominações
pendentes: pelo relógio do cursor, seria repassada à toa.

**Desenho:** o cursor define o CONJUNTO (o que não foi lido), o `ts` define o RELÓGIO
(há quanto tempo). O flag não entra — ele serve ao sino, não ao relay.

### O custo, medido instrumentando `open()`/`read_text()`

| regime | bytes lidos do disco | tempo |
|---|---|---|
| sala em dia (ocioso, não toca o chat) | **1.079 B** | 1,5 ms |
| nada mudou desde a última varredura (cache) | **1.078 B** | 0,3–1,7 ms |
| varredura fria (lê o chat de 24.757 B) | 25.468 B | 4,8 ms |
| processo inteiro, do shell, cache quente | — | **46 ms** |

Duas otimizações nasceram da medição, não do palpite:

1. `config.json` era lido 2× — **82% dos 1.209 B** do ciclo ocioso. Cache por processo.
2. O cache guardava o corpo da mensagem e o ciclo ocioso **subiu** de 1.209 B para
   3.666 B: o cache saía mais caro que o que economizava. Passou a guardar só metadado;
   o corpo é lido uma vez, na hora de repassar. Ledger final: **367 B**.

**Custo diário a 60 s:** 1.440 × 1.078 B = **1,48 MB/dia** + uma varredura fria por
mensagem nova (17 msgs no dia × ~25 KB = 0,42 MB). CPU: 1.440 × 46 ms = **66 s/dia** —
**menos da metade** do sino do operador que já está no ar (25 ms × 5.760 ciclos = 144
s/dia). A peça cabe no orçamento de uma peça que já existe.

**Replay do dia real** (sala copiada, cursores reais, `varrer` a cada minuto das 20:36
às 22:00):

```
21:03  ↷ repassa #4 (claude→codex, parada há 16 min; backlog 5) para @kimi na #17
84 ciclos de 1 min · 2 varreduras frias (o resto veio do cache)
```

**Um** repasse no dia inteiro, carregando as 5 represadas. 98% dos ciclos custaram
1.078 B. A #4, que na realidade ficou 74 min parada e morreu, teria mudado de mão aos
16 min: **58 min de espera a menos**.

---

## 3. Prazo que não atropela trabalho em andamento

Latências reais de nominação → primeira mensagem do nominado, nas 11 que responderam:

```
7s · 66s · 198s · 201s · 266s · 273s · 301s · 316s · 347s · 356s · 373s
mediana 273 s (4min33s)   ·   PIOR CASO 373 s (6min13s)
```

**Prazo padrão: 15 min = 2,4× o pior caso legítimo observado.** Configurável em
`relay.prazo_min`.

O prazo sozinho não basta, e é aqui que quase todo desenho erra: silêncio legítimo
existe (a IA está no meio de outra coisa). A segunda trava é o **teste de vivacidade** —
postou depois da nominação ⇒ está viva ⇒ não repassa. Gate G2 da bateria: 90 min sem
leitura, mas com uma mensagem postada, **não vence**.

---

## 4. Repasse duplica trabalho? — o desenho evita, e aceita o resto

**Transferência declarada, não cópia silenciosa.** O repasse:

- é postado **em nome do remetente original** — não inventa identidade nova na sala (o
  `post` recusaria: `'x' não está na sala`) e não fala como se fosse a IA muda;
- nomina **a irmã e a original**. A original, ao acordar, lê o pedido e o repasse na
  mesma leitura, antes de gastar. Gate G4: `msgs=[1, 2]`, e o repasse diz *não refaça*;
- **assume o backlog inteiro** (as 5 do codex num repasse só, não 5 repasses);
- **dá um salto por mensagem**. Se a irmã também silenciar, chama o operador em vez de
  continuar a cadeia.

Essa última trava veio de um **defeito real que a bateria encontrou** no meu primeiro
desenho: 40 min depois do repasse, a #17 (claude→kimi) vencia e a fila de `construcao`
devolvia a tarefa para **`codex`** — exatamente quem estava mudo. Loop. Corrigido: o
repasse nasce marcado no ledger; irmã muda além de 2× o prazo vira chamado ao operador.

Se as duas trabalharem mesmo assim, o desenho **aceita e reconcilia**: o chat é
append-only, não há estado a corromper, e a segunda responde à primeira. Duplicata custa
token, não integridade.

---

## 5. Onde a tabela de irmãs mora sem virar configuração morta

Em `config.json`, ao lado de `na_sala` — a chave `relay.vocacao` + `relay.irmas`,
espelhando a cascata que a casa já usa (`~/.claude/skills/iaswarm/SKILL.md:16-19`).

Três razões, nesta ordem:

1. **`na_sala` é o único ato de manutenção que já existe** (editada quando uma IA entra
   ou sai). Encostar a tabela nele faz o mesmo gesto passar os olhos nos dois.
2. **A tabela reclama sozinha.** `check` acusa IA na sala sem vocação e fila apontando
   só para braços fora da sala, em toda execução. Gate G6: com `vocacao` incompleta, 2
   avisos; completa, silêncio.
3. **Sem tabela, fail-closed.** Nada de adivinhar destino: notifica o operador e para.
   Mandar trabalho para braço sem vocação custa mais que o silêncio.

---

## 6. Riscos

| risco | gravidade | mitigação no desenho | resíduo |
|---|---|---|---|
| Repassar quem está trabalhando | alto — atropela produção | teste de vivacidade + prazo 2,4× o pior caso | IA que trabalha **sem postar nada** por >15 min é repassada. Custa uma duplicata; não corrompe nada. |
| Loop de repasse entre irmãs | alto — enche a sala | um salto por mensagem; repasse nasce marcado | nenhum (G3) |
| Enxurrada com backlog represado | médio — toda IA paga a sala | backlog inteiro num repasse só | nenhum |
| Repasse inchando a sala | médio | >2 KB vai por referência: 905 B em vez de 2.985 B | o ponteiro depende de o `search` achar o trecho; verificado (cai na #4) |
| Tabela desatualizada | médio | mora ao lado de `na_sala`; `check` reclama | aviso ignorável — reclama, não bloqueia |
| Ledger corrompido/apagado | baixo | `json.JSONDecodeError` → ledger vazio | reabre a possibilidade de um repasse repetido; o pior caso é uma mensagem duplicada |
| `relay run` concorrente com `post` | baixo | usa `core.travado()` e `core.post`, o mesmo lock `fcntl` | nenhum |
| Falso "não lida" por cursor avançado sem exposição | baixo | `ler` avança o cursor mesmo filtrando (documentado no core) | uma nominação **oculta por escopo** conta como lida e nunca é repassada — comportamento herdado, não introduzido |

**Limite do replay, declarado:** as 16 mensagens do histórico têm `ts` real, mas o
repasse gerado nasce com `ts = agora` (o `post` usa `datetime.now()` e eu não toco o
core). Então a fase **pós**-repasse do dia 17/08 não é simulável fielmente. O ramo
"irmã também muda" foi provado na bateria sintética (G3), não no replay.

---

## 7. Critério binário

A peça **passa** se, e só se, os 8 grupos abaixo derem verde. Reproduzir com
`python3 teste_relay.py` (usa `IACHAT_HOME` próprio em `/private/tmp/.../relay-teste`,
não toca a sala real). Estado atual: **23 gates, 23 verdes, exit 0**.

| gate | o que prova | verde |
|---|---|---|
| G1 | 14 min não vence, 16 min vence | ✔ ✔ |
| G2 | postou depois ⇒ não repassa, mesmo com 90 min sem leitura | ✔ ✔ |
| G3 | repassa uma vez; nomina irmã **e** original; posta em nome do remetente; toca o sino da irmã; **não volta em loop**; irmã muda além de 2× o prazo chama o operador | ✔ ×6 |
| G4 | a original acorda e recebe pedido + repasse na mesma leitura, com "não refaça" | ✔ ✔ |
| G5 | sem irmã: não posta na sala, registra no ledger, não inventa destino | ✔ ×3 |
| G6 | a tabela acusa o que falta e cala quando está completa | ✔ ✔ |
| G7 | mensagem grande vai por referência (72% menor) com ponteiro para a íntegra | ✔ ✔ |
| G8 | nominação lida não é silêncio; sala em dia = 0 B de chat lido | ✔ ×3 |

**Falha em qualquer um = a peça não entra.** O G2 e o G3 são os inegociáveis: sem eles a
peça atropela trabalho em andamento ou entra em círculo, e nos dois casos ela piora a
sala em vez de melhorar — que é exatamente o que o plugin existe para não fazer.

---

## 8. O que eu não verifiquei

- **Não rodei o LaunchAgent.** O plist do `SKILL.md` não foi instalado nem testado sob
  `launchd`; o custo por ciclo foi medido chamando o processo direto. O projeto já tem
  cicatriz nessa área (`launchctl list | grep -q` sob `pipefail` negando um daemon que
  havia subido), então o instalador merece a mesma desconfiança que o do sino.
- **Não testei com `qwen`/`grok`/`agy` de verdade na sala** — a sala real tem 3 IAs. A
  fila com braços fora da sala foi exercitada só pelo caminho do aviso (G6).
- **Não medi o custo do repasse em tokens de contexto** de quem recebe, só em bytes de
  chat. Bytes é o que o projeto já usa como régua (`AVISO_GRANDE`, `BYTES_POR_PAGINA`),
  mas não é a mesma coisa.

---

## 9. ⚠️ Achado fora do meu escopo: o core está quebrado NESTE MINUTO

Às 22:15 de 17/08, no meio desta análise, `bin/iachat_core.py` passou a levantar
`NameError` **no import** — ou seja, `iachat post`, `read`, `status`, o hook e o daemon
estão todos fora do ar na máquina:

```
File "/Users/.../Projetos/ia-chat/bin/iachat_core.py", line 42, in <module>
    "teto_bytes": TETO_PADRAO,
NameError: name 'TETO_PADRAO' is not defined
```

Alguém está unificando o teto (o comentário novo diz: *"Antes havia três valores: 204800
no padrão, 40960 em status() e 102400 em rotate()"* — a intenção é boa e o defeito que
ela corrige é real). Mas a constante ficou definida na **linha 52**, depois do uso na
**linha 42**. Correção: mover `TETO_PADRAO = 204800` para antes do `CONFIG_PADRAO`.

**Não corrigi** — a regra 1 deste trabalho é não escrever no repositório, e não é meu
diff. Revalidei contra uma cópia sã em `/private/tmp/.../core-sao/` (`PYTHONPATH`):
**23/23 verdes**.

**Às 22:17 o defeito já não estava lá** — `TETO_PADRAO` agora está na linha 38, antes do
uso, e a bateria roda verde contra o repositório como está. Foi uma janela de ~2 min de
core quebrado durante uma edição concorrente. Registro porque a janela existiu e porque
qualquer IA que tenha rodado `iachat post` nela levou `NameError`: **o `install.sh` do
plugin não tem um smoke test de import**, e um `python3 -c "import iachat_core"` no fim
dele fecharia essa classe inteira de falha.

A sala real segue intocada: 16 mensagens, mesmo número do início, sem `relay.json`.
