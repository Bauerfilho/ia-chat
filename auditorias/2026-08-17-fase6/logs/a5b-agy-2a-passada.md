# A5-B · agy — 2ª passada: o que ficou por fazer

Você já entregou a 1ª passada em `resultados/a5-agy.md`: 6 divergências, todas conferidas
contra o código e **todas confirmadas**. O trabalho estava certo — estava **incompleto**.

Leia primeiro: `~/.claude/iaswarm-runs/ia-chat-fase6/BRIEFING.md` e o seu próprio
`resultados/a5-agy.md` (não repita o que já achou).

**O que faltou** — a etapa 4 do contrato original, que você não cumpriu:

> *"Cruzar caminho por caminho: todo caminho de arquivo citado na documentação existe? Toda
> variável de ambiente documentada é realmente lida pelo código?"*

Você cobriu **uma** env (`IACHAT_SCRIPTS`) e nenhum caminho sistematicamente.

## ETAPAS (5, e nenhuma pode ser pulada)

1. **Extrair TODOS os caminhos** citados em `README.md` e nos 7 `skills/*/SKILL.md` do repo
   `/Users/bauervieiracesarfilhovieira/Projetos/ia-chat` — cada `~/...`, `bin/...`, `arquivo/...`,
   `pendente/...`, `cursor/...`, `.estado.json`, `.lock/`. Lista completa, com origem `arquivo:linha`.
2. **Testar cada um contra a realidade**: existe no disco ou é criado pelo código? Se é criado,
   por qual linha de qual arquivo? Marque os que **não existem nem são criados** — são promessa falsa.
3. **Extrair TODAS as variáveis de ambiente** citadas em qualquer doc (`IACHAT_HOME`,
   `IACHAT_SCRIPTS`, `IACHAT_SKILLS`, `IACHAT_BIN`, `IACHAT_EU`, e o que mais houver) e provar,
   `arquivo:linha`, onde cada uma é **lida** — ou que não é lida por ninguém.
4. **Cruzar os exemplos de saída**: toda saída de comando mostrada na doc (blocos de código com
   resultado) bate com o que o código produz hoje? Rode os comandos que puder num `IACHAT_HOME`
   temporário sob `/tmp` e compare.
5. **Escrever `resultados/a5b-agy.md`** com as divergências NOVAS (não repita as 6 anteriores),
   cada uma com `arquivo:linha` dos dois lados e a correção exata. Termine com a lista do que
   você **não conseguiu** verificar e por quê.

**Proibido:** escrever em `~/Projetos/ia-chat` ou `~/ia-chat-global`; repetir achado da 1ª passada;
entregar com etapa não cumprida — se faltar tempo, entregue as que fez e **declare** as que não fez.
