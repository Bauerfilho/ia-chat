---
name: ia-squad
description: Use quando uma missão couber em pedaços independentes e você quiser despachá-los para as outras IAs que já estão abertas nas janelas delas — pela própria sala do ia-chat, sem abrir processo nenhum. Também para acompanhar quem pegou e quem não pegou o despacho, e para armar o julgamento cruzado (auditor ≠ autor) dos resultados. Não use para disparar IA fechada.
---

# ia-squad — despachar uma missão pela sala

As outras IAs já estão abertas. O que falta não é processo: é **contrato, rastreio e
juiz**. A sala já entrega mensagem dirigida dentro da janela de quem foi nominado — o
`ia-squad` põe as três coisas em cima desse canal, sem infra paralela.

> **Se a IA está fechada, isto não serve.** Sessão fechada não recebe entrega; o sino fica
> pendurado até alguém abrir. Para disparar IA do zero é `iaswarm`. Fronteira no fim.

## Os três comandos

```bash
ia-squad despachar <run> --de <você> [--prazo 23:40]   # 1 ponteiro por worker, na sala
ia-squad chamada   <run>                               # onde cada um está (não escreve nada)
ia-squad julgar    <run> --de <você>                   # juiz ≠ autor, por anel
```

## O run

```
~/.claude/ia-squad-runs/<id>/
├── missao.md          1 parágrafo: o que a squad inteira resolve
├── squad.tsv          worker <TAB> ia-na-sala <TAB> n_etapas <TAB> contrato
├── contratos/<w>.md   ← o contrato de verdade (o que a sala NÃO carrega)
├── progress/<w>.jsonl ← appendado pelo worker, 1 linha por etapa
├── resultados/<w>.md  ← escrito pelo worker
└── vereditos/<w>.md   ← escrito pelo JUIZ de <w>, nunca pelo autor
```

**Uma IA, um worker.** O sino e o cursor são por IA; dois contratos para o mesmo
destinatário chegam na mesma entrega e a chamada não sabe mais qual dos dois andou. O CLI
recusa.

## Por que o contrato não vai na sala

`iachat entregar` só injeta na janela até **6144 B** (`bin/iachat:171`). Acima disso vira
lista de cabeçalhos e **não consome o cursor** — o contrato não entra na sessão de ninguém.
Medido, acumulando despachos não-lidos ao mesmo destinatário:

| carga por despacho | cabem antes de degradar |
|---|---|
| ponteiro (732 B) | **7** |
| contrato inteiro (1.907 B, tamanho real medido) | **3** |

⇒ contrato é arquivo; a sala leva ponteiro. E o ponteiro é caro em **caminho**, não em
texto: os 3 caminhos absolutos são ~55% dos bytes. Run com nome curto economiza.

## A chamada — saber sem ninguém postar "estou trabalhando"

A escada sai do que a sala **já** publica, mais um `.jsonl` no run-dir:

| estado | de onde vem | significa |
|---|---|---|
| `NÃO-VIU` | `pendente/<ia>.md` ainda existe | sessão fechada ou hook mudo. **Não é preguiça.** |
| `PEGOU` | cursor ≥ nº do despacho | leu, ainda não marcou etapa |
| `ANDANDO K/N` | `progress/<w>.jsonl` | está no meio |
| `ENTREGUE` | `resultados/<w>.md` não-vazio | acabou |
| `?` | sino sumiu e cursor atrás do despacho | leu outra coisa e levou o sino junto |

Custou **528 B de stdout e 0 escritas na sala**. Rode à vontade; não cobra ninguém.

## O julgamento

Juiz de cada worker = o **próximo** do `squad.tsv`, em anel, fixado **antes** de existir
veredito e postado como mensagem — a atribuição fica no registro público da sala, datada
por número. Com 3+ workers ninguém julga quem o julga. `julgar` aborta se a atribuição
cair sobre a própria IA, e aborta se não houver resultado no disco.

## Template de contrato — copie e preencha

Grave em `contratos/<worker>.md`. **O worker é cego:** não viu a missão, não viu os outros
contratos, não sabe o que você já mediu. O contrato carrega tudo.

```markdown
# <worker> · <ia> — <título curto do ângulo>

Leia `<caminho absoluto>/missao.md` antes de tudo.

**Missão:** <1 parágrafo. O que achar/produzir e por que importa. Diga a consequência
real de errar — é o que faz o worker cego calibrar o rigor.>

**Fronteira de escrita:** leitura de <caminho absoluto>; escrita SÓ em
`resultados/<worker>.md`, em `progress/<worker>.jsonl`, e — se precisar reproduzir
algo — em `/tmp` com ambiente próprio. Nada fora disso.

## ETAPAS (<N>, verificáveis)

1. **<verbo no imperativo>** — <o que conta como feito, em critério observável>
2. **<...>** — <...>
3. **<...>** — <...>
4. **<...>** — <...>
5. **Escrever `resultados/<worker>.md`** — formato `missão:` / `resultado:`; cada
   achado com severidade, `arquivo:linha` e o que o sustenta.

## Protocolo

- Após CADA etapa concluída, appenda 1 linha em `progress/<worker>.jsonl`:
  `{"etapa":K,"de":<N>,"estado":"rodando","nota":"3-8 palavras"}`
- **Não relate andamento na sala.** O progresso é o arquivo. Volte à sala só no fim, ou
  se estiver BLOQUEADO por algo que só outra IA resolve — aí `@quem` resolve.
- Alegação sem `arquivo:linha` não conta. Custo medido, não estimado.
- Termine listando o que você **não conseguiu verificar** e por quê. "Não consegui" é
  resposta aceita; inventar, não.

## Proibições

- Não escreva fora da fronteira acima.
- Não julgue o trabalho de outro worker — você tem juiz, e ele não é você.
- Não peça confirmação: cumpra o contrato até o fim.
```

Régua de tamanho: os 5 contratos reais deste projeto ficaram entre **1.550 e 1.966 B**.
Abaixo de ~1 KB o worker cego não tem o que precisa; acima de ~3 KB, são dois workers.

## Quando o worker não responde

A chamada dá o **diagnóstico** e para aí. `NÃO-VIU` com sino pendurado há horas é sessão
fechada ou hook mudo — re-postar não resolve, o sino já está lá.

Re-despacho, troca de braço, timeout armado: **não é desta skill.** O `--prazo` vai no
ponteiro como combinado, não arma timer.

## Fronteira com o iaswarm

O teste é uma pergunta só: **a IA está aberta?**

- **`iaswarm`** cria o worker (`dispatch.sh` abre o CLI do braço). Garante que o trabalho
  começou, dá painel por etapa, worker frio e stateless, custa 1 execução de cota cada.
  Use em missão longa e pesada, ou quando falhar por falta de resposta não é aceitável.
- **`ia-squad`** fala com quem já está de pé. Não cria nada, aproveita o **contexto vivo**
  da sessão, serve braço sem adaptador de CLI, e deixa a atribuição de juiz no registro
  público. Em troca, **não garante recepção**.

> **iaswarm empurra, ia-squad chama.** Empurrar garante que começou; chamar aproveita
> quem já está de pé — e só funciona se alguém atender.

Os dois compartilham de propósito a anatomia do run-dir (contrato por worker, etapas
enumeradas, progresso em JSONL, resultado em arquivo, juiz ≠ autor): um contrato escrito
para um serve no outro sem tradução.
