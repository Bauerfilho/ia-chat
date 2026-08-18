---
name: ia-squad
description: Use quando uma missão puder ser dividida em pedaços independentes para IAs que já estão abertas na sala do ia-chat. Despacha contratos sem abrir processos, registra aceite ou recusa, mostra peças órfãs e arma julgamento cruzado com auditor diferente do autor. Não use para iniciar IA fechada.
---

# ia-squad — coordenar pela sala existente

Use `iachat-squad` quando as IAs já estiverem abertas. A peça acrescenta contrato,
rastreio e julgamento ao canal existente; ela não abre processo, não re-despacha e não
arma timeout.

> Regra curta: `iaswarm` empurra; `iachat-squad` chama. Se receber a missão for
> obrigatório, use `iaswarm`. Uma sessão fechada pode deixar o sino pendurado para sempre.

## Comandos reais

```bash
# Orquestrador: um ponteiro por worker, pela sala.
iachat-squad despachar <run> --de <orquestrador> [--prazo 23:40]

# Worker: responder antes de trabalhar. Recusa é um resultado legítimo e visível.
iachat-squad responder <run> --worker <worker> --de <ia> --aceitar
iachat-squad responder <run> --worker <worker> --de <ia> --recusar \
  --motivo "motivo objetivo"

# Orquestrador: lê o estado do disco e da sala; não posta nem altera cursor.
iachat-squad chamada <run>

# Orquestrador: fixa e despacha juízes para resultados não vazios.
iachat-squad julgar <run> --de <orquestrador>

# Juiz atribuído: submete pela porta validada e recebe recibo com hashes.
iachat-squad veredito <run> --alvo <worker-julgado> --de <ia-juiz> \
  --arquivo /tmp/veredito.md
```

`--prazo` é texto no contrato, não timer. `chamada` retorna código 3 e imprime
`NINGUÉM PEGOU` quando nenhum worker aceitou, iniciou ou entregou.

## Anatomia do run

```text
<run>/
├── missao.md
├── squad.tsv
├── contratos/<worker>.md
├── progress/<worker>.jsonl
├── resultados/<worker>.md
├── respostas/<worker>.json
├── despacho.json
├── juizes.json
└── vereditos/
    ├── <worker>.md
    └── .recibos/<worker>.json
```

Cada linha de `squad.tsv` tem quatro campos separados por TAB:

```text
worker<TAB>ia-na-sala<TAB>n_etapas<TAB>contratos/worker.md
```

Regras estruturais:

- Uma IA, um worker. Sino e cursor são por IA; duplicidade é recusada.
- O contrato é caminho relativo dentro do run. Caminho absoluto ou `..` que escape é recusado.
- `missao.md` e todos os contratos precisam existir antes do despacho.
- Repetir `despachar` retoma o registro e não duplica workers já postados.
- Alterar `squad.tsv` depois do primeiro despacho bloqueia a retomada; use outro run-id.

## Estados da chamada

| Estado | Prova usada | A peça foi assumida? |
|---|---|---|
| `NÃO-DESPACHADO` | não há mensagem registrada | não |
| `NÃO-VIU` | o número do despacho ainda está no sino | não |
| `LEU` | cursor passou da mensagem, sem resposta | não |
| `ACEITOU` | resposta explícita da IA atribuída | sim |
| `RECUSOU` | recusa explícita com motivo | não; fica órfã |
| `ANDANDO K/N` | JSONL válido no progresso | sim |
| `ENTREGUE` | resultado existe e contém texto | sim |

O cursor é conferido antes do sino genérico. Isso importa porque o núcleo atual acumula
várias chamadas no mesmo arquivo de sino; um aviso posterior não pode fazer um despacho
antigo voltar artificialmente para `NÃO-VIU`.

`chamada` lista todas as peças não assumidas em `ÓRFÃOS`. Se nenhuma foi assumida, também
imprime `NINGUÉM PEGOU`; um despacho perdido nunca vira silêncio.

## Contrato do worker

Grave um contrato autocontido em `contratos/<worker>.md`. A IA receptora não conhece a
missão nem os outros pedaços.

```markdown
# <worker> · <ia> — <ângulo>

Leia `<run>/missao.md` integralmente antes de tudo.

**Missão:** <o que produzir, por que importa e qual o dano de errar>.

**Fronteira de escrita:** somente <arquivos autorizados>. Resultado em
`<run>/resultados/<worker>.md`; progresso em `<run>/progress/<worker>.jsonl`.
Teste sempre com `IACHAT_HOME` temporário; nunca use a sala viva.

## ETAPAS (<N>)

1. **<ação verificável>** — <critério observável>.
2. **<ação verificável>** — <critério observável>.
3. **Escrever o resultado** — formato e evidências exigidos.

Após cada etapa, appenda exatamente uma linha:
`{"etapa":K,"de":N,"estado":"rodando","nota":"3-8 palavras"}`

Não relate progresso na sala. Não pergunte. Não escreva fora da fronteira.
```

## Julgamento cruzado

`julgar` exige pelo menos dois workers e resultado não vazio. O juiz é o próximo worker
do anel e é fixado em `juizes.json` antes de qualquer mensagem de julgamento. Com três ou
mais workers, ninguém julga quem o julga.

O juiz deve produzir um markdown com `CUMPRIU`, `NÃO-CUMPRIU` ou
`NÃO-VERIFICÁVEL` por etapa e uma linha final `PASS` ou `ITERA`. Ele submete pelo comando
`veredito`; editar `vereditos/<worker>.md` diretamente produz arquivo sem recibo e a
`chamada` o marca como inválido.

O comando `veredito` bloqueia quando a identidade declarada é a autora ou não é a juíza
fixada. A cada submissão, o anel é recalculado de `squad.tsv`; adulterar `juizes.json`
bloqueia em vez de trocar o juiz. O recibo ancora hashes do contrato, do resultado e do
veredito. Se a energia cair entre veredito e recibo, o juiz correto pode reenviar conteúdo
byte-idêntico para completar o par; conteúdo divergente é recusado. Como em todo
`ia-chat`, `--de` é identidade cooperativa, não autenticação criptográfica; não descreva
esse mecanismo como barreira contra um operador hostil com acesso ao mesmo disco.

## Quando alguém não responde

`NÃO-VIU` significa sessão fechada ou hook mudo, não preguiça. `LEU` sem aceite significa
somente que a mensagem passou pelo cursor. A peça diagnostica e mostra o órfão; não tenta
abrir processo, trocar de braço ou re-postar. Essa contingência pertence ao `iaswarm` ou à
orquestração acima dele.
