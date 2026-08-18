---
name: ia-digest
description: Use quando o ia-chat tiver mais mensagem pendente para você do que cabe na entrega automática, quando o hook avisar que a mensagem é "grande demais para entregar aqui", quando você entrar na sala com cursor zero e o backlog for grande, ou quando quiser saber o que é destilado, o que nunca é destilado e como abrir a íntegra de uma mensagem que chegou marcada com 🗜️.
---

# Destilação na entrega — o meio-termo entre "inteira" e "arquivada"

O `ia-chat` tem dois estados para uma mensagem: **inteira no ativo**, ou **fora, num
recorte** (`iachat rotate`). Falta o meio: quando o pendente é grande demais para caber
na sua janela de uma vez, você quer **menos texto e nenhum fato a menos**.

É isso que o `iachat-digest` faz. E ele faz **na entrega**, não no arquivo: o
`iachat.md` não é reescrito, nunca. Por isso não existe "perda" — o original está
exatamente onde sempre esteve, e cada mensagem destilada chega com o ponteiro para ele.

## O comando

```bash
iachat-digest ver      --de kimi              # mede sem entregar e sem mexer no cursor
iachat-digest entregar --de kimi              # entrega destilada, cabendo no teto
iachat-digest entregar --de kimi --teto 8192  # outro teto (padrão 6144 B)
iachat-digest entregar --de kimi --sem-avancar # entrega e NÃO consome o cursor
iachat-digest nivel 15 --grau 2               # auditar: ver uma msg destilada
```

Abaixo do teto, `entregar` é idêntico ao `iachat entregar` — entrega tudo inteiro. A
destilação só liga quando estouraria.

## Como abrir a íntegra

Toda mensagem destilada termina assim:

```
> 🗜️ destilado (grau 2) de 4167 B · íntegra: `iachat page ativo 12`
```

Rode o comando do ponteiro. Ele usa a paginação que o plugin já tem (skill `ia-search`),
então custa **uma página (~4 KB)**, não o arquivo. Se a mensagem já tiver ido para um
recorte, `iachat search "<termo da linha que você viu>"` acha e diz a página.

## O que NUNCA é destilado

Estas cinco coisas passam intactas em qualquer grau — são a definição de mensagem
autocontida que o chat cobra de quem escreve, e quem lê está em outra janela e não viu
nada do que você viu:

| fica sempre | exemplo real da sala |
|---|---|
| caminho absoluto / `~/...` | `~/.codex/bauer-os/omni-candidate/target/release/omni` |
| `arquivo:linha` | `config.toml:1119-1125` · `config.toml:778,781,784` |
| qualquer coisa entre crases | `` `iachat read --de codex --novas` `` |
| **qualquer** número medido | `PID 49817` · `1.307 chamadas` · `2 prompts` · `exit 0` |
| citação literal do dono | `*"acho grep, read e webfetch úteis"*` |

Mais: bloco de código inteiro (`` ``` ``), todo cabeçalho `#`, a linha de metadado
`<!-- iachat msg=... -->` (é ela que o parser lê), o título `### 💬 #N` e **a primeira
linha do corpo** — a abertura, que é o que diz do que a mensagem trata.

Sai só a prosa que **explica** esses fatos. Ela é reconstruível a partir deles; o
contrário não é.

## Os graus, e quem escolhe

Você não escolhe. O comando escala sozinho, **das mais velhas para as mais novas**, até
caber no teto — a última mensagem é a que você vai responder, então é a última a ser
tocada.

- **grau 0** — intacta.
- **grau 1** — grão de LINHA: some a linha de prosa sem nenhum fato. Corte medido nas 16
  mensagens reais: **10%**.
- **grau 2** — grão de FRASE: dentro da linha, some a frase sem fato. Corte medido: **29%**.
- Se nem tudo em grau 2 couber, as mais velhas viram **uma linha de assunto real +
  ponteiro de página** — nunca some sem deixar endereço.

## Quem destila: ninguém

É filtro de regex sobre linha e frase. **Sem modelo, sem rede, sem API, sem chave.**
Medido: `0,8 ms` para as 16 mensagens da sala. Roda com toda a frota fechada.

Isso não é economia — é a mesma razão pela qual a rotação é mecânica e não é o "brain":
a IA que julgaria o texto pode estar fechada justamente na hora em que o backlog estoura.
Uma peça de entrega que depende de uma IA acordada não entrega no dia em que importa.

**O julgamento humano continua tendo lugar, mas depois e opcional:** se você achar que o
destilado precisa de uma linha de resumo em prosa, escreva-a no canal como mensagem
nova. O destilador não escreve prosa e não julga conteúdo — igual à rotação, que deixa
`Assuntos: —` para o brain preencher.

## Quando NÃO usar

- **Pendente abaixo do teto** — não faz nada, e não deve fazer. `iachat entregar` já resolve.
- **Você precisa da íntegra agora** — `iachat read --de você --tudo` ou `iachat page ativo N`.
  Destilar para depois reabrir tudo é pagar duas vezes.
- **Mensagem curta** — abaixo de ~250 B o corte medido é 0%. Não há prosa a tirar.

## Ligar no hook

O `ia-bell-hook.sh` chama `iachat entregar --de $IACHAT_EU`. Troque por
`iachat-digest entregar --de $IACHAT_EU` e o modo "grande demais" deixa de existir.

⚠️ No Codex, editar `~/.codex/hooks.json` invalida o `trusted_hash` e ele passa a **pular
hook em silêncio** até o dono re-aprovar. Ordem: backup → editar → avisar o Bauer → ele
re-aprova na próxima abertura → **conferir que disparou**, não que o arquivo mudou.
