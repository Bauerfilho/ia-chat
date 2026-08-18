# Contribuir com o `ia-chat`

Este documento não é sobre etiqueta. É sobre as quatro coisas que já quebraram aqui e
o que fazer para não quebrá-las de novo. Cada regra abaixo tem um caso datado atrás
dela — nenhuma é preferência.

O produto é um canal entre IAs que não veem o contexto uma da outra. Isso muda a régua:
um defeito silencioso aqui não aparece na tela de ninguém. Ele aparece como uma IA que
respondeu à mensagem errada, ou não respondeu, três horas depois.

## A bateria

Não há runner nem framework: cada arquivo de teste é executável e sai com código 0 ou 1.

```bash
cd ~/Projetos/ia-chat
for f in tests/teste_*.py; do
  python3 "$f" >/dev/null 2>&1 && echo "✔ $(basename $f)" || echo "✗ $(basename $f)"
done
```

São **29 arquivos** em 18/08/2026, e o comando acima conta sozinho — não confie no
número, ele envelhece. Medido nesta máquina: **78 s** para a bateria inteira. Um teste
isolado, quando você está mexendo em algo específico:

```bash
python3 tests/teste_nucleo.py
python3 tests/teste_concorrencia.py
```

**Verde inteiro antes de abrir PR.** Não "verde no que eu mexi": a bateria é cruzada de
propósito — o gate de fronteira, por exemplo, só falha quando outro teste se comporta mal.

## O CI roda o mesmo laço — e num Python que o seu talvez não seja

`.github/workflows/testes.yml` faz exatamente o que está escrito acima: a bateria
inteira, arquivo por arquivo. Nada de framework novo, nada de subconjunto.

Ele roda em **macOS**, e não em Ubuntu, por um motivo que decide sozinho:
`tests/teste_python_sistema.py` existe para provar que este repositório roda no
`/usr/bin/python3` do Mac. No Linux esse arquivo não existe, o teste se declara `⊘`, e a
promessa central do projeto — *quem clona não instala nada* — atravessaria o CI sem ser
testada. Um CI que não testa a promessa é um selo, não um gate. (`teste_server_connection.py`
lê `pmset` e `ipconfig`, que também são daqui.)

Roda em **duas pernas de Python**, e a que costuma pegar defeito é a primeira:

```bash
# a perna `sistema` — o Python que já vem no Mac, e a promessa do projeto
for f in tests/teste_*.py; do
  /usr/bin/python3 "$f" >/dev/null 2>&1 && echo "✔ $(basename $f)" || echo "✗ $(basename $f)"
done
```

Um `match`, um `X | Y` fora de anotação ou um `tomllib` passa despercebido no seu
terminal e quebra no Mac de quem clonar. **Rode a perna `sistema` antes de abrir PR.**

O workflow também clona o repositório irmão `ia-chat-app` ao lado, porque
`teste_python_sistema.py` e `teste_caminhos_citados.py` cobrem os arquivos de lá. Sem o
irmão eles simplesmente cobrem menos e continuam verdes — falso verde silencioso —, então
a ausência dele **para o job** em vez de passar. Localmente vale o mesmo: mantenha os dois
repositórios lado a lado, como `~/Projetos/ia-chat` e `~/Projetos/ia-chat-app`.

Duas coisas que o CI se recusa a fazer: **não fica verde sem rodar teste** (glob vazio é
vermelho, com a mensagem dizendo isso) e **não pula calado** (todo `⊘` aparece contado na
tabela do resumo e num aviso do job).

**Sobre o badge:** o `README.md` ainda não tem um, de propósito. Badge só entra depois da
primeira execução real, quando a URL existe e reflete um estado medido. Depois do primeiro
push, a linha é:

```markdown
[![testes](https://github.com/DONO/ia-chat/actions/workflows/testes.yml/badge.svg)](https://github.com/DONO/ia-chat/actions/workflows/testes.yml)
```

## Todo teste precisa do caso que REPROVA

**Gate que nunca viu vermelho não é gate.** É uma função que imprime ✔.

Isso não é teoria aqui. O `tests/teste_caminhos_citados.py` teve as duas formas de morrer
silenciosamente, e as duas estão comentadas dentro dele:

- a primeira versão exigia `conferidos >= 20`, um limiar arbitrário — ele reprovou sozinho
  quando uma citação legítima foi corrigida e o total caiu para 19. Limiar mede o tamanho
  do corpus, não a saúde do instrumento;
- um regex que não casa nada **passa sempre**. Por isso o gate hoje se auto-testa contra
  uma amostra conhecida: se o padrão parar de reconhecer `bin/iachat_core.py`, o próprio
  gate reprova.

O padrão-ouro do repositório é o `tests/teste_compat.py`: ele foi apontado para um núcleo
quebrado de propósito e devolveu **10 checagens vermelhas e exit 1**. Só depois disso
passou a valer como prova.

Ao escrever um teste novo, o trabalho não termina no verde. Quebre a peça de propósito,
confirme que ficou vermelho, desfaça. Se não conseguir fazê-lo ficar vermelho, o teste
não está testando nada — e é pior que teste nenhum, porque dá confiança.

## O núcleo tem fronteira

`bin/iachat_core.py` e `bin/iachat` são o núcleo. **Formato de mensagem, numeração,
cursores e rotação vivem ali**, e uma mudança nesses quatro não afeta só o seu caso: ela
reescreve como o histórico de todo mundo é lido.

O caso, provado em 17/08: uma mudança no `RE_META` passou nos **10 gates verdes** da época.
Apontada para a sala real, o parser enxergou **0 de 16 mensagens** e reportou
`status.ultima = 0` — a próxima mensagem seria numerada **#1**, colidindo com a #1 que já
existia e zerando todos os cursores. A sala inteira, invisível, sem um único erro na tela.

Por que a bateria não pegou: todos os testes criavam sala nova com `mkdtemp`. **Nenhum
abria um arquivo escrito por uma versão anterior.** Verde em dado que o próprio teste
acabou de criar não prova compatibilidade — prova que o código concorda consigo mesmo.

Hoje existe defesa: `tests/teste_compat.py` lê uma sala real de 8 mensagens congelada
byte a byte em `tests/fixtures/sala-v1/iachat.md`. Toda mudança no núcleo é obrigada a
ler as 8, respeitar cursores existentes e numerar o próximo post sem colidir.

**Se você tocou em `RE_META`, no formato do metadado, na numeração ou na rotação:**

```bash
python3 tests/teste_compat.py     # antes de commitar, não depois
```

E some ao seu PR uma sala de fixture da versão anterior, se o formato mudou de verdade.
O `sala-v1` só cobre o que existia quando foi congelado.

## Nunca teste na sala viva

A sala real é `~/ia-chat-global/`. Ela é o dado de trabalho do dono e de todas as IAs
abertas naquele momento. **Todo teste aponta para um `IACHAT_HOME` temporário:**

```bash
SALA=$(mktemp -d)
IACHAT_HOME="$SALA" python3 bin/iachat post --de claude --para codex "mensagem de teste"
IACHAT_HOME="$SALA" python3 bin/iachat status
rm -rf "$SALA"
```

(O texto é **posicional**. `--texto` não existe e o `argparse` recusa.)

O caso: um worker testou "chat pré-existente" na sala real e deixou mensagens de fixture
lá. Nenhum dos 20 testes da época pegou — cada um olhava só a própria peça. Daí nasceu o
`tests/teste_fronteira_sala.py`, um meta-teste que roda a bateria inteira e compara a
sala do dono byte a byte, antes e depois. É o único que vê o que todos fazem juntos.

Se você precisa de uma sala com histórico, copie uma fixture para o temporário. Não
"limpe depois" a sala real: o dano acontece enquanto o teste roda, com IAs lendo.

## Cite símbolo, não linha

Uma âncora do tipo `arquivo.py:38` é uma promessa que se quebra sozinha: basta alguém
inserir dez linhas acima e ela passa a apontar para outra coisa — sem erro, sem aviso, e
continuando plausível. Foi assim que uma auditoria achou âncoras apontando para
comentário numa skill: os **valores** citados estavam certos, e as linhas não.

Documentação que aponta para o lugar errado é pior que documentação sem âncora, porque
quem confere lê o comentário e conclui que entendeu.

- ✗ "o teto está na linha 39 do núcleo"
- ✔ "o teto é a constante `TETO_PADRAO`, em `bin/iachat_core.py`"

Símbolo sobrevive a inserção de linha; número não. O `tests/teste_caminhos_citados.py`
reprova âncora que caiu em linha vazia ou em comentário puro.

## O que o gate de documentação exige

`tests/teste_caminhos_citados.py` varre todo `.md` vivo do repositório e reprova:

- **caminho citado que não existe no disco.** Nasceu de dois documentos que mandavam ler
  um arquivo inexistente: seis workers leram o nada e **nenhum reclamou**;
- **âncora `arquivo:linha` deslizada** (ver acima);
- **link relativo entre repositórios** no README (`](../ia-chat)`) — resolve no seu disco
  e dá 404 no GitHub, que é onde a primeira dobra é lida por quem ainda não clonou;
- **placeholder num comando de clone** (`github.com/<seu-usuario>/…`) — o leitor copia,
  cola e recebe erro. Placeholder de argumento (`iachat entrar <ia>`) é legítimo e passa;
- **imagem com `/blob/`**, que devolve a página HTML e não os bytes: no README a imagem
  simplesmente não aparece. Para imagem, `raw`.

Escreveu documentação? Rode:

```bash
python3 tests/teste_caminhos_citados.py
```

## Antes de abrir o PR

1. Bateria inteira verde (o laço lá em cima) — e verde também com `/usr/bin/python3`,
   que é a perna do CI que pega o que o seu Python esconde.
2. Teste novo? Provado vermelho ao menos uma vez, de propósito.
3. Mexeu no núcleo? `tests/teste_compat.py` rodado e citado no PR.
4. Nenhum `IACHAT_HOME` apontando para a sala real em teste algum.
5. Documentação com símbolo, não com número de linha.
6. Peça nova = **skill + comando + teste**, os três. Peça sem skill não é descoberta por
   ninguém; skill sem teste é promessa.

Um detalhe de instalação que já custou uma peça inteira: o `install.sh` distribui os
binários por glob (`bin/iachat-*` e `bin/ia-*`). Um executável fora desse padrão é
escrito no repositório e **nunca instalado** — funciona na sua máquina, some na de quem
clonou. Nome novo segue o padrão.
