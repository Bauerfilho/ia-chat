# LICENSE — três opções, a consequência de cada uma, e a decisão que é sua

Hoje o `ia-chat` **não tem licença nenhuma**. Isso não é "aberto por padrão": sem
arquivo de licença, o padrão legal é *todos os direitos reservados*. O código fica
visível no GitHub, mas ninguém pode usar, adaptar ou redistribuir com segurança
jurídica — e as empresas que ensinam os funcionários a checar licença simplesmente
passam adiante. Um repo público sem LICENSE é um repo que se lê e não se usa.

## As três que cabem numa ferramenta de linha de comando

| licença | a consequência prática, em uma linha |
|---|---|
| **MIT** | qualquer um usa, altera, embute em produto fechado e vende — só precisa manter o seu aviso de copyright junto. |
| **Apache-2.0** | a mesma liberdade da MIT, mais uma **concessão explícita de patente** e a obrigação de sinalizar arquivos modificados — é a que o jurídico de empresa grande costuma preferir. |
| **GPL-3.0** | quem distribuir uma versão derivada é **obrigado a abrir o código** dela — protege contra alguém fechar o seu trabalho, e por isso mesmo afasta boa parte do uso corporativo. |

## O que eu recomendo, e por quê

**MIT.** Dois motivos concretos, nenhum deles ideológico:

1. **Coerência com o que você já publicou.** `~/Projetos/iaswarm/LICENSE:1,3` é
   MIT, com o titular `Bauer Vieira César Filho Vieira` e o ano `2026`. Duas
   contribuições do mesmo autor sob licenças diferentes obriga quem chega a ler as
   duas e perguntar por quê — custo sem retorno.
2. **A natureza da peça.** O `ia-chat` é infraestrutura de conversa entre cascas de
   IA. Se ele der certo, o caminho é alguém embutir isso na própria ferramenta. A
   MIT permite; a GPL-3.0 transformaria essa adoção numa decisão jurídica. Você não
   está tentando proteger um produto — está tentando ser adotado.

A Apache-2.0 só passa à frente da MIT se você tiver **motivo específico** para
querer a cláusula de patente. Num plugin de CLI de 2.197 linhas, não tem.

## Como aplicar (30 segundos)

O arquivo `LICENSE-MIT-pronto.txt`, ao lado deste, já está com o titular e o ano
corretos, **byte a byte igual** ao do `iaswarm`:

```bash
cp ~/.claude/iaswarm-runs/ia-chat-fase6/batch/ia-publish/LICENSE-MIT-pronto.txt \
   ~/Projetos/ia-chat/LICENSE
```

Depois, uma linha no fim do `README.md`, no mesmo formato que o `iaswarm` usa
(`~/Projetos/iaswarm/README.md:154-156`):

```markdown
## Licença

MIT.
```

Com o arquivo `LICENSE` na raiz, o GitHub reconhece a licença sozinho e mostra
"MIT" na barra lateral do repositório — sem configuração nenhuma.

**Custo total: 1 arquivo copiado + 3 linhas no README. Não é uma tarefa; é um
`cp`.** O que não pode é publicar sem ele.
