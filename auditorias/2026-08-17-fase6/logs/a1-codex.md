# A1 · codex — auditoria de correção do núcleo

Leia `~/.claude/iaswarm-runs/ia-chat-fase6/BRIEFING.md` antes de tudo.

**Missão:** achar defeitos de CORREÇÃO no núcleo do `ia-chat`, com rigor de quem vai ser
responsabilizado pelo que passar. O produto vai ser publicado no GitHub pelo dono; um bug de
perda de mensagem aqui é perda de trabalho de outra IA.

**Fronteira:** leitura do repo `/Users/bauervieiracesarfilhovieira/Projetos/ia-chat`; escrita
SÓ em `resultados/a1-codex.md` e, para reproduzir, em `/tmp` com `IACHAT_HOME` próprio.

## ETAPAS (5, verificáveis)

1. **Ler `bin/iachat_core.py` inteiro** e mapear todo caminho que ESCREVE estado (chat, cursor,
   pendente, .estado.json). Para cada um: está sob `travado()`? Liste `arquivo:linha`.
2. **Caçar corrida.** Cenários a testar de verdade, não no papel: (a) dois `post` simultâneos com
   `.estado.json` ausente ou corrompido; (b) `rotate` rodando enquanto outra IA dá `post`;
   (c) `rotate` enquanto alguém dá `read`; (d) `marca_lida` concorrente com `post`. Reproduza com
   processos reais em `IACHAT_HOME` de teste.
3. **Atacar `_cauda()` e `_msgs_desde()`** (leitura parcial do arquivo): pode cortar mensagem no
   meio? pode devolver lista incompleta e o cursor avançar por cima do que não veio? Teste com
   mensagem maior que a janela de 16 KB e com UTF-8 partido no corte.
4. **Atacar o cursor e a numeração:** existe cenário em que uma mensagem dirigida a uma IA nunca é
   entregue a ela? E em que dois posts recebem o mesmo número? Prove ou declare que não achou.
5. **Escrever `resultados/a1-codex.md`**: cada achado com severidade (CRÍTICO/ALTO/MÉDIO/NOTA),
   `arquivo:linha`, **cenário reproduzível** (comandos exatos), e a correção sugerida. Separe
   "bug" de "ponto fraco a cristalizar" de "melhoria que não é bug".

Termine listando o que você NÃO conseguiu verificar e por quê.
