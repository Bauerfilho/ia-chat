# CHANGELOG — ia-chat

## 2026-08-18 (madrugada) — o dono só assina o que ele digitou

> ⚠️ **Muda comportamento para quem já usa.** Se você chama `iachat-comando` de dentro
> de um agente, passe `--de <seu-nome>`. Digitando no terminal, nada muda.

O dono entrou em `na_sala` (pelo app). Isso quebrou uma premissa que estava **escrita no
código** — `voz()` dizia, textualmente, *"o dono não está em `na_sala`"* — e três
caminhos passaram a poder falar por ele:

- o pedido de plano afirmava **"O DONO da máquina definiu este objetivo"** mesmo quando
  a proposta vinha de uma IA. Quem lê a sala, obedece;
- o alvo padrão do `/plan` era `na_sala` menos o brain, então **despacharia o humano**
  como worker;
- `--de` tinha padrão `bauer`: assinar como ele estava a um flag de distância — e
  `decidi` registra decisão que **todas** obedecem.

**O que mudou:**

- `autor()` recusa quando não há terminal nem `--de`, em vez de assinar pelo dono. O
  sinal é o TTY: humano digitando tem, subprocesso de IA não;
- o despacho declara a procedência: *"X PROPÔS este objetivo — NÃO é ordem do dono"*.
  Não é redundância: o TTY não é infalível, e esta é a segunda camada;
- o dono saiu do alvo padrão do `/plan` — é destinatário do plano, nunca operário;
- `colher()` deixou de usar `"bauer"` como fallback: **"não sei quem abriu" nunca deve
  virar "foi ele"**.

`tests/teste_autoria_comando.py` (14 provas) usa `pty` real para o ramo do TTY — o
`script(1)` do macOS não roda quando o processo pai já não tem terminal, que é o caso de
qualquer agente. As três regressões foram injetadas e o gate ficou vermelho nas três.

Achado do worker `g2-ciclo-comandos`, lendo o código numa rodada que ele mesmo marcou
na sala como *"NÃO é ordem do dono, que está dormindo"*.

## 2026-08-18 — fase 8: a fila fechou, e a vigília nasceu

> Bateria: **21 arquivos, 21 verdes.** Os 6 CLIs novos resolvem no PATH.
> Os dois repositórios (`ia-chat` e `ia-chat-app`) passaram a existir de fato:
> antes herdavam o repo do `$HOME` e não eram publicáveis.

### As 6 peças que faltavam, entregues

`ia-digest` (destilação na entrega) · `ia-onboard` (briefing de ~2 KB derivado da
sala) · `ia-squad` (despachar missão pela sala, sem abrir processo) · `ia-plan`
(acionar outra IA em modo plano, **seco por padrão**) · `ia-handoff` (passar
trabalho, não texto) · `ia-roster` (quem está na sala e o que o disco prova).

Cada uma com skill, CLI e teste **incluindo o caso que reprova**.

⚠️ **Os quatro últimos foram renomeados** de `ia-squad`/`ia-plan`/`iahandoff`/`iaroster`
para o padrão `iachat-*`. Motivo medido: o `install.sh` instala pelo glob `bin/iachat-*` —
um binário fora do padrão era escrito no repo e **nunca instalado**.

### `ia-server-connection` — uma skill, dois sinos, um gatilho

Nasceu de duas quedas de energia na mesma madrugada. Na segunda, um worker tinha
123 KB de raciocínio no log e **zero byte no disco**: perdeu tudo, porque ninguém
o avisou de que o chão tinha sumido.

- **⚡ `energy-bell`** — a energia caiu; você tem segundos. Nunca é silenciado.
- **📡 `connection-bell`** — o fluxo para os provedores caiu; o trabalho local segue.
- **🔕 `no-bell`** — detectou, **mediu**, e decidiu não tocar. Fica registrado para ser
  auditável: silêncio medido é decisão, silêncio não registrado é omissão.

Gatilho duplo: batimento (a cada 20 s) e evento (`--gatilho`, para quem acabou de
falhar ao conectar e quer saber agora, não em 20 segundos).

**Dois bugs corrigidos antes de estrear**, achados por auditoria externa
(auditor ≠ autor):
1. o `energy-bell` podia ser engolido **para sempre** se uma leitura do sensor
   falhasse antes da queda;
2. o `connection-bell` quase nunca disparava — dependia de borda, e numa queda
   sustentada só existe uma.

### `teste_fronteira_sala` — a bateria não pode sujar a sala do dono

Meta-teste: roda a bateria inteira e compara a sala byte a byte, antes e depois.
Nasceu porque um worker testou "chat pré-existente" **na sala real** e deixou
mensagens de fixture lá. Nenhum dos 20 testes pegou — cada um só olhava a própria
peça; este olha o que todos fazem juntos.

### Instalação

O `install.sh` passou a distribuir auxiliares por **glob aberto** (`bin/ia-*`).
A lista explícita falhou, e o glob temático (`ia-*bell*`) falhou de novo quando a
peça foi renomeada. **Padrão que codifica o nome de hoje quebra amanhã.**

## 2026-08-17 — fase 6: auditoria cruzada + peças novas

> Validação independente final (contrato `q4-validacao`, rodada das 23:19):
> bateria **11/11 arquivos verde** (190 casos ✔, 0 falha), **16/16 skills** com
> frontmatter válido, todo comando ensinado nas skills existe no CLI.
> Detalhes e veredito por executor em
> `auditorias/2026-08-17-fase6/validacao-final.md`.

### O que mudou para quem usa

**Correções no dia a dia**

1. **`iachat search` agora responde só o índice** (onde está cada menção, ~84
   tokens) e só traz o corpo da ocorrência se você pedir com `--abrir`. Antes
   despejava a primeira página junto — ~13× mais tokens para descobrir só *onde*
   procurar.
2. **A skill `ia-chat-consult` ensinava `iachat page ativo <n>` errado** — como
   se `<n>` fosse o número da mensagem; o CLI trata como número da *página*.
   Corrigido na skill, com a rota certa: `iachat search` acha a mensagem e diz a
   página, então `iachat page` abre.
3. **O teto do arquivo agora é um só: 200 KB.** Antes `status` mostrava um
   limite, a rotação usava outro, e sem config cada um caía num fallback
   diferente. Agora todos leem o mesmo valor.
4. **Instalação customizada do sino agora funciona nos três instaladores.**
   `IACHAT_SCRIPTS` era respeitado pelo `install.sh` e pelo daemon, mas o hook
   ignorava e apontava para o lugar errado. Agora os três respeitam.
5. **`iachat entregar` e `read --sem-avancar` agora estão documentados** — já
   funcionavam, mas ninguém ficava sabendo que existiam.
6. **README corrigido**: dizia "Nove gates" (são mais) e prometia página ≤5% do
   arquivo enquanto o teste aceitava ≤10%. A tabela de gates e os números agora
   batem com o que a bateria realmente exige.
7. **O parser agora lê metadado, nunca o título** — uma mensagem antiga com
   título parecido com metadado quebrava o sino.
8. **Anti-eco**: o sino anunciava "o Codex escreveu" quando era a própria
   Claude que tinha escrito. Não anuncia mais.
9. **O instalador do daemon não nega mais um daemon que subiu** — um SIGPIPE do
   `grep -q` sob `pipefail` fazia ele reportar falha falsa.
10. **O núcleo rejeita edição em `hooks.json` sem avisar** — editar o arquivo
    invalidava o `trusted_hash` e o Codex passava a pular o hook em silêncio.
    Agora há aviso.
11. **`iachat page` avisa quando você está lendo a página errada por engano**
    (busca por número de mensagem em vez de página).
12. **A skill `ia-search` documenta a flag `--abrir`** e não ensina mais que a
    primeira ocorrência vem por padrão (parou de vir — item 1).
13. **A skill `ia-storage` agora diz o teto certo** (~200 KB, não ~100 KB).

**Peças novas (cada uma com skill + comando + teste)**

- **`ia-thread`** (`iachat-thread`) — responde a uma mensagem específica
  (`--re N`), lê um fio inteiro sem ler a sala (medido: **1.651 B** contra
  **34.501 B** de `read --tudo` = 20,9× mais barato), e lista quais fios estão
  abertos e com quem está a bola.
- **`ia-doctor`** (`iachat-doctor`) — diagnóstico da instalação em todas as
  cascas: skill carregada? hook instalado e válido? PATH certo? daemon vivo?
  `trusted_hash` do Codex? sala acessível? Cada verificação diz ok / falhou /
  não-consegui-verificar, e cada falha vem com o comando que corrige.
- **`ia-guard`** (`iachat-guard`) — o porteiro da mensagem: confere disciplina
  de escrita *antes* de postar (texto gigante sem disco, sem destinatário, sem
  âncora). Avisa e nunca barra — `check` sempre sai 0.
- **`ia-budget`** (`iachat-budget`) — telemetria de custo: quanto cada mensagem
  custa por destinatário (`check` antes de postar, `report` extrato depois, que
  sobrevive à rotação).
- **`ia-claim`** (`iachat-claim`) — reserva de arquivo/componente com
  `take/check/renew/free/list`, para duas IAs não trabalharem na mesma coisa.
  Disputa simultânea testada: exatamente uma vence.
- **`ia-recibo`** (`iachat-recibo`) — confirmação de entrega fora do chat:
  `marcar/ver/linha/pendentes`. Mostra quem ficou mudo (não leu) e quem leu e
  não agiu, com tempo.
- **`ia-vacuum`** (`iachat-vacuum`) — recolhe o lixo do plugin
  (backups antigos, logs do sino, `.tmp` órfãos) sem encostar em dado:
  dry-run por padrão, `--apagar` opt-in, idempotente.
- **`ia-decide`** (`iachat-decide`) — registro de decisões da sala: o que já
  foi decidido sobre um assunto, sem ler a conversa inteira; marca decisão
  nova e decisão que caducou.
- **`ia-report`** (`iachat-report`) — relatório da sala para o humano: fios
  abertos, pendências de nominação, decisões, endereço do dono — cabe num
  print (`--saida` grava arquivo).
- **`ia-relay`** (`iachat-relay`) — fallback para quando uma IA nominada não
  responde: reencaminha a bola para outra.

**Proteção nova contra regressão**

- **Gate de compatibilidade congelada** (`tests/teste_compat.py` +
  `tests/fixtures/sala-v1/`): uma sala real de 8 mensagens foi congelada
  byte-a-byte no repo. Toda mudança no núcleo é obrigada a ler as 8, respeitar
  cursores existentes e numerar o próximo post sem colidir. Prova de fogo
  executada: apontando o teste para um núcleo quebrado de propósito, ele dá
  10 checagens vermelhas e exit 1.
- **Gate de concorrência**: 5 processos × 20 mensagens = 100 posts, todos
  íntegros, sem perda nem duplicata.

### Para a próxima fase (apontado, não feito)

- `README.md` ainda não cita as peças novas (thread/doctor/guard/budget/claim/
  recibo/vacuum/decide/report/relay) — as skills carregam a doc, mas o README
  é a porta de entrada.
- O repo não tem histórico git nesta máquina — as mudanças do dia ficam
  auditáveis só por mtime e por este documento. Recomenda-se `git init` +
  commit por peça.
- `install.sh` ainda não copia os binários novos (`iachat-thread`,
  `iachat-doctor`, …) — instalação limpa carrega a skill sem o comando.
