# ia-report — nota de desenho

## A tese, em uma linha

O plugin inteiro é construído para que **nenhuma IA pague a sala inteira**. O dono é a
única entidade que hoje paga 100% dela — ou 0%.

Prova no código: `ler()` (`bin/iachat_core.py:317-357`) devolve à IA só o que a nominou e
conta o resto como `ocultas` (`:345`, `:352`). Medido pelo próprio projeto: 26–46% da sala
por IA. O dono **não tem cursor, não tem nominação e não está em `na_sala`** — para ele
existem exatamente duas leituras: o sino do operador
(`bin/ia-bell-daemon.sh:56`, que diz `"codex → claude · mensagem #15"` e nada mais) ou
`cat iachat.md`. Não há meio-termo.

E o meio-termo dele não é uma fatia menor da sala: **é justamente a parte que a leitura
dirigida esconde.** Nenhuma das 16 mensagens de hoje nominou `bauer`; se ele tivesse
cursor, a leitura dirigida entregaria a ele **zero mensagens**. O que ele precisa é o
tráfego entre terceiros — condensado, não cru. O relatório inverte o filtro do plugin.

## O que medi

Sala real (`~/ia-chat-global/iachat.md`, 17/08 20:36→21:23): **16 mensagens, 24.757 B,
273 linhas**; corpo das mensagens = 23.867 B. Conversão tokens ≈ B/4 é a **calibração do
próprio repo** (`iachat_core.py:48` "~2 KB ≈ 500 tokens"; `:411` "~4 KB ≈ 1.000 tokens").

| artefato | bytes | ~tokens | % do arquivo | fator |
|---|---|---|---|---|
| sala inteira | 24.757 | 6.189 | 100% | — |
| **esqueleto mecânico** (`iachat report`) | **2.696** | **674** | **10,9%** | **9,2× menor** |
| **relatório em prosa** (abaixo) | **3.230** | **807** | **13,0%** | **7,7× menor** |
| os dois juntos | 5.926 | 1.481 | 23,9% | 4,2× menor |

Custo de execução do esqueleto: **40 ms, 3 rodadas idênticas, `$0`** (python local, sem
rede, sem IA).

**Read-only provado — na segunda tentativa.** A primeira foi
`find ~/ia-chat-global -newermt "-10 minutes"`, que voltou **vazio** e eu li como "nada
escrito". Não era: o `find` desta máquina é `bfs`, ele **rejeitou o timestamp relativo** e
saiu com erro — vazio era "não consegui olhar", não "está limpo". Refiz por `st_mtime`
direto nos 21 caminhos da sala: a escrita mais recente é `iachat.md` às 21:25:53, **42 min
antes** das minhas rodadas. O protótipo não escreveu nada. Mesma armadilha que o
`launchctl list | grep -q` do instalador (msg #4 da sala): saída vazia de um comando que
falhou parece saída vazia de um comando que passou.

**A conta honesta das duas camadas é diferente, e isso importa:**

- O **esqueleto economiza**: 674 tokens contra 6.189, sem nenhuma IA envolvida.
- A **prosa gasta**: para escrevê-la, uma IA lê o período uma vez (6.189 tokens) e devolve
  807. Ela não economiza tokens — **gasta tokens para poupar o dono.** É a única peça do
  plugin que faz esse negócio, e é o negócio certo: o leitor mais caro da casa é ele.

## O relatório real da sala de hoje

Isto é o que eu entregaria a ele agora — 3.230 B contra 24.757 B da sala.

---

# 💬 A sala hoje — 17/08, 20:36 → 21:23 · 46 min · 16 mensagens

**A fase 4 (o sino) fechou nas duas pernas. Uma tarefa sua está parada há ~1 h e duas coisas esperam a sua palavra.**

## Precisa de você

1. **Hook do Codex — só você autoriza.** A Claude instalou o hook do Kimi e deixou o do Codex de fora **de propósito**: editar `~/.codex/hooks.json` invalida o `trusted_hash` (`~/.codex/config.toml:778,781,784`) e o Codex passa a pular hook **em silêncio** até você re-aprovar. Sem hook, ele segue cego dentro de sessão já aberta. Decidir: autorizar e re-aprovar na próxima abertura, ou deixar o Codex só com o daemon.
2. **O daemon do sino do Codex nunca subiu.** Uma linha: `~/.claude/scripts/ia-chat/ia-bell-install-daemon.sh codex 15`. A Kimi conferiu no `launchctl list`: `com.bauer.ia-bell-claude` e `-kimi` de pé, o do codex não.
3. **A tarefa do omni na casca do Codex está parada.** Você mandou; a Claude levantou o terreno inteiro e passou às 21:07 (#15, 4,1 KB). O Codex **nem leu** — o sino dele ainda está tocando.

## O que ficou decidido

- **Matcher `Bash|Read|Grep|WebFetch`** nos hooks de tool do Codex — decisão sua, contra o argumento da Claude de que `Read`/`Grep`/`WebFetch` não existem naquela casca (ela mediu 1.307 chamadas `exec` contra 0 das três em 1.473). Fica registrado que os três estão **armados e dormentes**: a cobertura efetiva vem do `Bash`.
- **O gate da tarefa do omni é o banco, não a contagem de hooks.** Há pendência de 17/08 em que os hooks do omni no Codex retornavam `Completed` com o banco em **zero** para `agent_id='codex'`. `Completed` não é prova; abrir o banco é.
- **A Kimi fechou o lado dela:** daemon no ar (PID 49817) + hook em `~/.kimi-code/config.toml:1119-1125`, `kimi doctor config` OK, backup `config.toml.bak-iachat-20260817-205727`. Vale a partir do próximo boot dela.

## O que a sala aprendeu (vale além deste plugin)

- **Skill e hook instalados não entram em sessão já aberta.** Codex e Kimi leem no boot. Instalou? Só vale na próxima abertura. Os dois reportaram isso de forma independente.
- **`kimi -p` e a TUI da Kimi expõem catálogos de skills diferentes.** A Claude mediu na headless, afirmou que as 3 skills apareciam, e a Kimi corrigiu: na TUI dela não constam. A Claude aceitou — a régua é o que a sessão de fato enxerga, não o disco.
- **`launchctl list | grep -q` sob `pipefail` mente:** SIGPIPE mata o `launchctl`, o instalador jura que o daemon não subiu, e ele subiu.

## Do seu lado da tela

O Codex terminou duas respostas com `Stop hook (failed) — error: hook returned invalid stop hook JSON output`. É da casca dele, não do ia-chat: algum script do evento `Stop` devolvendo saída fora do JSON esperado. Ninguém mexeu. Para caçar: `hooks.json` + o script do `Stop` — e o `trusted_hash` antes de editar.

## Conduta

A Claude passou uma correção à Kimi (ela investigou sozinha e deixou prompts seus na fila). A Kimi respondeu reconhecendo, com medida: no `wire.jsonl` da sessão dela chegaram exatamente 2 prompts seus, os dois lidos e agidos; se houve outros, foram para janela paralela. Regra registrada por ela: prompt seu interrompe a linha dela, não o contrário.

---

## Máquina × leitura — a divisão, com o teste aplicado

Rodei o esqueleto na sala real. Ele acertou, sozinho e sem nenhuma IA:

```
## ⚠️ Parado esperando alguém
- claude — kimi chamou na #16 (21:23, 241 B) · 40 min sem responder · leu até #16
- codex  — claude chamou na #15 (21:07, 4.1 KB) · 56 min sem responder · nem leu (sino tocando)
```

Conferido no disco, não no relatório: `~/ia-chat-global/pendente/` contém **só**
`codex.md` (275 B) — o sino dele está de fato tocando; `cursor/` tem os três. O item **3**
do "Precisa de você" se sustenta em artefato, não em inferência.

Os itens **1** e **3** do "Precisa de você" saem daí. **"Quem está travado" é 100%
mecânico** — é aritmética sobre o metadado (`RE_META`, `iachat_core.py:30-32`) cruzada com
o cursor (`:301`) e o flag (`p_pendente`, `:65`). Não precisa de IA e não deve depender de
uma.

O que a máquina **não** extraiu, e declarou:

```
## 📌 Marcado pelas IAs
- nada marcado (nenhuma mensagem usou DECIDIDO:/PENDENTE:/BLOQUEIO:/PERGUNTA:).
```

Isso é o resultado honesto, não uma falha escondida: a sala **não tem convenção de marcar
decisão**, então não há o que extrair. Recusei casar por proximidade ("a frase tem
'Bauer', logo pede a palavra dele") — seria o mesmo defeito do sino que tocou com
`@codex` entre crases (`iachat_core.py:208-222`, comentário do próprio autor: *"sino a
mais é pior que sino a menos"*). **Marcador explícito ou nada.**

Fronteira final:

| item | quem faz | por quê |
|---|---|---|
| quem deve resposta, há quanto tempo | máquina | aritmética sobre metadado + cursor |
| quem nem leu / sino pendurado | máquina | `p_pendente().exists()` |
| quem sumiu no período | máquina | ausência em `de=` |
| onde está o texto denso | máquina | bytes por mensagem |
| **o que foi decidido** | leitura | não existe no metadado |
| **o que exige a palavra dele** | leitura *(hoje)* | vira máquina se a convenção entrar |
| tradução para linguagem de dono | leitura | — |

## Duas correções de rota que o código permite hoje

**1. O dono pode virar nominável trocando UMA linha de config — sem tocar em código.**
`post()` filtra destinos por `na_sala` (`iachat_core.py:249`) e descarta o resto com
aviso (`:257-259`): hoje `--para bauer` **é silenciosamente ignorado**. Mas `ler()`
(`:317`) **não valida `na_sala`** — `iachat read --de bauer --novas` já funciona, só
volta vazio porque nada consegue nominá-lo. Pondo `"bauer"` em `na_sala`
(`~/ia-chat-global/config.json`), ele ganha de graça: nominação, flag `pendente/bauer.md`,
cursor, leitura dirigida e sino próprio (`ia-bell-install-daemon.sh bauer 15`).
Isso resolve **"me chamaram"**. Não resolve o relatório — hoje daria zero mensagens a ele
— mas é o canal certo para o item que exige decisão dele, e é o que torna a seção
"Precisa de você" mecânica no futuro.
*Efeito colateral a decidir com ele:* `@all` passaria a incluí-lo (`:247`).

**2. O gatilho do sino do operador está no eixo errado — medido.**
O daemon notifica por **ciclo de polling com novidade** (`ia-bell-daemon.sh:43-56`).
Simulei os 16 timestamps reais de hoje: **14 notificações** com `INTERVALO=15` (13 com 60).
Um gatilho por **silêncio** — "a sala falou e parou há N min" — dá **2** notificações com
N=10 e 4 com N=5. **7× menos**, e cada uma chega quando a conversa está *completa*, que é
quando o relatório existe e vale a pena abrir.
*Defeito menor no caminho:* `NOVAS` é calculado (`:52`) e só vai para o log (`:54`); a
notificação (`:56`) nomeia apenas a última mensagem. Quando 2+ caem no mesmo ciclo, ele
não fica sabendo que foram 2 — hoje isso aconteceu 2×.

## Periodicidade e gatilho — recomendação

- **Sob demanda é o padrão.** `iachat report` custa 40 ms e `$0`; não há razão para agendar
  o que é grátis pedir.
- **Diário é o eixo errado.** A sala é em rajada: 16 mensagens em 46 min e nada antes nem
  depois. Um resumo às 23:00 de um dia com uma rajada às 20:36 chega tarde e um de um dia
  vazio treina ele a ignorar.
- **O gatilho automático certo é o SILÊNCIO**, pelo número acima: 1 notificação por rajada,
  com o relatório já gravado em disco, em vez de 14 pulsos durante a rajada.
- **Gatilho de exceção:** se `pendente/bauer.md` existir (correção 1), notificar na hora —
  aí é uma pergunta parada nele, não um resumo.

## Formato

Markdown puro em **arquivo**, com stdout junto. Razão: ele lê muito no **celular e
offline**, e nem terminal nem notificação do macOS sobrevivem a ele fechar a máquina e
sair. `--saida` aceita qualquer caminho.

**Não consegui verificar** qual pasta dele chega ao telefone: existe
`~/Documents/claude-organizada-segura/`, mas não há vault Obsidian no caminho padrão do
iCloud (`~/Library/Mobile Documents/iCloud~md~obsidian/Documents/` não existe). Deixei
`--saida` sem default para não cravar um caminho que eu não provei que sincroniza.

Notificação **não** carrega o relatório: `display notification` trunca e não é rolável. Ela
avisa e diz onde está — o pulso continua sendo pulso.

## Protótipo

`bin/iachat-report` (7,1 KB). Roda contra a sala real, read-only, importando
`iachat_core` — sem chamar `config()`/`status()`, que passam por `garantir_estrutura()`
(`:105-115`) e escrevem. Só toca `p_chat()`, `parse()`, `cursor()`, `p_pendente()`.

```
PYTHONPATH=~/Projetos/ia-chat/bin python3 bin/iachat-report --horas 12 --saida ~/sala.md
```

Na integração vira `cmd_report` em `bin/iachat` (padrão dos 8 subcomandos existentes,
`bin/iachat:152-194`) com o corpo em `iachat_core.relatorio()`. Não escrevi no repo, por
regra deste trabalho.

**Auditei meu próprio instrumento e ele estava errado:** `_primeira_frase` limpava
markdown com `re.sub(r"[*_\`#>]+", ...)` e comia o `#` de referências — "a minha #7" virava
"a minha 7", destruindo o dado no meio do relatório. Corrigido para limpar `#` só no
início da linha. Um relatório que corrompe número de mensagem é pior que não ter relatório.

## O que não fiz, de propósito

- Não inferi decisão por palavra-chave (ver acima).
- Não mexi em `ia-bell-daemon.sh` nem em `config.json` — as duas correções acima são
  proposta medida, e a segunda muda o comportamento de uma notificação que é dele.
- Não me sobrepus ao `ia-digest` (condensar a sala **para outra IA** retomar o trabalho é
  outro produto: outro leitor, outra régua de custo). A fronteira está escrita no
  `SKILL.md`.
