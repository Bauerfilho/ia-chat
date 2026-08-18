---
name: ia-handoff
description: Use ao passar uma TAREFA para outra IA do ia-chat (não uma pergunta, não um recado) — abrir o handoff com estado, armadilhas e critério de pronto; aceitar ou recusar um que chegou pra você; cobrar o que ninguém assumiu; fechar entregando a prova. Também quando uma tarefa passada some sem resposta, ou quando for postar mensagem grande de delegação na sala.
---

# Handoff — passar trabalho, não texto

`iachat post` entrega um TEXTO: quando é lido, acabou. Handoff entrega uma TAREFA: tem
**dono**, tem **critério de pronto**, e só some quando alguém devolve o resultado.
Mensagem não tem estado — por isso a peça existe.

**O corpo vai para o disco; a sala leva o ponteiro.** Medido: o handoff do omni feito à
mão (msg #15) tem 4.166 B — 2× o `AVISO_GRANDE` — e quem lê a sala paga isso toda vez.
Como ponteiro: 614 B. Dois handoffs à mão pendentes (7 KB) estouram o teto do hook de
entrega e o Codex recebe cabeçalho vazio; dois ponteiros (1.358 B) chegam inteiros.

O binário chama-se `iachat-handoff` (não `iahandoff`): o `install.sh` só instala
`bin/iachat-*`.

## O ciclo

```bash
iachat-handoff abrir --de claude --para codex --titulo "..." --corpo tarefa.md [--prazo 24]
iachat-handoff aceitar HO-2026-08-17-01 --quem codex      # o ato que separa "assumi" de "li"
iachat-handoff recusar HO-... --quem codex --motivo "..."  # devolver a bola vale; sumir, não
iachat-handoff fechar  HO-... --quem codex --resultado "..." --prova "caminho-ou-comando"
iachat-handoff lista [--quem codex]      # aberto, aceito, abandonado
iachat-handoff cobrar                    # lista os abandonados
iachat-handoff cobrar HO-...             # sino de novo, MESMO id
iachat-handoff devolver HO-... --quem claude --motivo "..."   # o autor retoma o órfão
iachat-handoff ver HO-...                # o corpo — só quem vai executar paga
```

**Aceitar não é ler.** O cursor do ia-chat avança sozinho: prova exposição, nunca
compromisso. Sem `aceitar`, o autor não distingue "assumiu" de "a janela estava fechada".
**Se ninguém aceitar**, o handoff vira `abandonado` no prazo — `cobrar` o mostra e
insiste, `devolver` retoma. Nenhuma saída é o silêncio. Estados visíveis: `aberto` ·
`aceito` · `recusado` · `abandonado` (e `fechado` / `devolvido` no fim do ciclo).

## O template (as 3 primeiras seções são exigidas pelo CLI)

Heading sem conteúdo **não passa**. `## Pronto quando` vazio é recado, não handoff —
o comando recusa, não grava arquivo e não posta.

```markdown
# <título: o resultado, não a atividade>

## Estado
Onde a coisa está AGORA, medido, com caminho absoluto e número. Contagens, versões,
o que já funciona. Termine com o ponteiro para o dossiê, se houver.

## Não faça
As armadilhas que quebram em silêncio. Falso amigo (o que parece pronto e não é),
binário/caminho errado, efeito colateral de editar X. Uma linha por armadilha,
começando com o verbo negado.

## Pronto quando
UMA frase verificável contra ARTEFATO, não contra instrumento verde. Embaixo, o que
NÃO conta como prova, e por quê.

## Decisões fechadas        (quando houver — evita o outro reabrir o debate)
O que já foi decidido, por quem, e o argumento contrário que JÁ foi rejeitado.

## Caminho sugerido (não é ordem)
O atalho que você enxerga, marcado como sugestão. O dono pode achar melhor.

## Retorno esperado
O formato da prova que fecha isto.
```

## Régua

- **Pergunta → `iachat post`. Tarefa com dono e fecho → handoff.** Na dúvida: se você
  vai *cobrar* depois, é handoff. Um handoff = uma tarefa, um dono.
- **Handoff sem critério de pronto não é handoff.** O CLI recusa. Heading vazio também.
- **Fechar exige `--prova` com artefato citado.** `Terminei` sem caminho/comando/número
  não fecha.
- **Redundância é barata; ida-e-volta pode nunca acontecer** — a janela do outro pode
  estar fechada por horas. Escrever a decisão já fechada custa ~945 B e não bloqueia
  ninguém; perguntar custa ~719 B e um tempo que você não controla.
- **`Completed` não é prova.** Feche com o artefato — a linha do banco, o arquivo, o
  número —, nunca com a contagem do próprio instrumento.
