# A3 · grok — consumo e qualidade da conversa

Leia `~/.claude/iaswarm-runs/ia-chat-fase6/BRIEFING.md` antes de tudo.

**Missão:** dois eixos que o dono pediu — (1) otimizar consumo, (2) aprimorar a conversa. Olhe de
fora: o plugin já é barato onde importa? A conversa entre IAs é BOA, ou só possível?

**Fronteira:** leitura do repo; escrita SÓ em `resultados/a3-grok.md` e
`resultados/skills-propostas/`.

## ETAPAS (5, verificáveis)

1. **Medir o consumo real.** Leia `~/ia-chat-global/iachat.md` (16 mensagens reais de hoje) e
   calcule: quanto custa hoje cada operação (entregar, ler dirigido, ler tudo, buscar). Use os
   números do arquivo, não estimativa de cabeça.
2. **Achar o desperdício restante.** Onde ainda se paga o que não precisa? Considere: mensagens
   longas demais (a Claude foi 73,4% do volume do primeiro dia), repetição de contexto entre
   mensagens, releitura da própria mensagem pelo autor, o custo de uma IA nova entrando na sala.
3. **Julgar a QUALIDADE da conversa.** Leia as 16 mensagens reais como quem avalia diálogo: o que
   faz uma conversa entre IAs cegas funcionar e o que falta aqui? (ex.: saber se a mensagem foi
   lida, encadear resposta a uma mensagem específica, marcar urgência, passar tarefa em vez de só
   informar, evitar duas IAs mexendo no mesmo arquivo).
4. **Propor 2 a 4 peças novas** — nome próprio, função que não duplica as 7 existentes, e para
   cada uma: o que resolve, quanto custa, quanto economiza, e como se prova que funcionou.
   Escreva o `SKILL.md` de cada uma em `resultados/skills-propostas/<nome>/SKILL.md`.
5. **Escrever `resultados/a3-grok.md`** com as medições, os desperdícios achados e as peças
   propostas ranqueadas por (impacto ÷ custo).
