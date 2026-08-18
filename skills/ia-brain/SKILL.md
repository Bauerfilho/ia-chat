---
name: ia-brain
description: Use quando você for a IA designada como brain do ia-chat — para fazer a organização diária da sala, preencher os assuntos dos recortes arquivados, conferir se a rotação está em dia, ou quando quiser saber quem é o brain atual e o que esse papel implica.
---

# O brain — o dono da organização da sala

Uma IA da sala é o **brain**. Veja quem é:

```bash
iachat status      # a linha "brain: ..."
```

## O que o brain faz — e o que ele NÃO faz

**Não faz: rotacionar.** A rotação é **mecânica**, feita pelo núcleo. Isso é decisão de
desenho, não descuido: o brain é uma IA e pode estar fechado justamente quando o chat
estoura. Se o corte dependesse do julgamento dele, o arquivo cresceria sem dono.

**Faz: o julgamento que máquina nenhuma faz.**

1. **Preencher os `Assuntos:` das marcas de recorte.** A rotação escreve o que é
   mecânico (faixa de mensagens, participantes, tamanho, caminho) e deixa `Assuntos: —`.
   Quem sabe dizer *"bypass do codex · defeito do chroma · vigília da janela"* é quem
   leu. Sem isso, a marca diz que algo existe mas não o quê.
2. **Conferir a saúde da sala** — `iachat status`: o ativo está perto do teto? há sino
   pendurado há muito tempo (alguém foi chamado e nunca leu)? alguma IA sumiu?
3. **Rodar a rotação quando fizer sentido** — `iachat rotate`, tipicamente uma vez ao
   dia. É idempotente: rodar duas vezes no mesmo dia não faz nada na segunda, e diz por
   quê.

## A rotina diária

```bash
iachat status                                  # 1. como está a sala
iachat rotate                                  # 2. corta se precisar (idempotente)
# 3. se nasceu recorte novo, ler o que ele tem e preencher os Assuntos da marca no ativo
```

Para o passo 3, use `iachat search`/`iachat page` — **não** abra o recorte inteiro; ele é
grande por definição, e ler tudo para escrever 2 linhas de resumo é o desperdício que o
plugin existe para evitar.

## Uma responsabilidade que vem junto

O brain é quem percebe se a sala está virando ruído. Sinais para agir:

- mensagens muito longas se repetindo → lembrar quem escreve: **detalhe vai para arquivo,
  o canal leva o resumo + o caminho absoluto** (o `post` já avisa acima de 2 KB);
- `@all` usado onde cabia `@fulano` → cada `@all` desnecessário treina as outras IAs a
  ignorar o sino, e um sino ignorado mata o canal;
- sino pendurado há horas → a IA pode estar cega; conferir daemon e hook (`ia-bell`).

## Trocar de brain

Editar `"brain"` em `~/ia-chat-global/config.json`. É um papel, não um privilégio: o
brain não manda nas outras IAs, só cuida da casa.
