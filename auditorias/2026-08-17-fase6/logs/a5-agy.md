# A5 · agy — documentação × código, divergência linha a linha

Leia `~/.claude/iaswarm-runs/ia-chat-fase6/BRIEFING.md` antes de tudo.

**Missão:** seu superpoder é achar onde as coisas estão escritas, lendo tudo de uma vez. Leia o
repositório INTEIRO e ache onde a documentação promete o que o código não faz — e onde o código
faz o que a documentação não conta.

**Fronteira:** leitura; escrita SÓ em `resultados/a5-agy.md`.

## ETAPAS (5, verificáveis)

1. **Ler tudo** de `/Users/bauervieiracesarfilhovieira/Projetos/ia-chat`: `README.md`, os 7
   `skills/*/SKILL.md`, `install.sh`, `bin/*` e `tests/*`.
2. **Cruzar comando por comando:** todo comando citado no README e nas skills existe no CLI
   (`bin/iachat`) com aquela sintaxe e aquelas flags? Todo comando do CLI está documentado?
   Tabela: comando → citado em → existe? → divergência.
3. **Cruzar promessa por promessa:** cada número afirmado na documentação (custos, percentuais,
   limites, "10 gates", "7 skills") bate com o código e com os testes? Aponte `arquivo:linha` dos
   DOIS lados de cada divergência.
4. **Cruzar caminho por caminho:** todo caminho de arquivo citado na documentação existe? Toda
   variável de ambiente documentada é realmente lida pelo código?
5. **Escrever `resultados/a5-agy.md`**: uma tabela de divergências com severidade (uma doc que
   ensina comando inexistente é ALTO — a IA vai tentar e falhar) e a correção exata. **Não
   proponha features**; sua entrega é a divergência entre o dito e o feito.
