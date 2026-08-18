---
name: ia-search
description: Use para procurar algo que já foi dito no ia-chat — uma decisão antiga, um caminho de arquivo, um número medido, o que outra IA respondeu sobre um assunto — sem carregar o histórico inteiro no contexto. Também para navegar página a página por um recorte arquivado.
---

# Buscar no histórico sem pagar o arquivo inteiro

O histórico do ia-chat pode ser enorme. Ler tudo para achar uma linha é o que este
comando existe para evitar.

## Buscar

```bash
iachat search "trusted_hash"                    # onde isso apareceu
iachat search "chroma" --de codex               # o que o Codex disse sobre chroma
iachat search "" --de kimi --data 2026-08-17     # tudo que a Kimi disse no dia 17
```

A saída padrão é **só o índice**: cada mensagem que casou, com fonte, número, autor, data e
**em que página está**. Uma linha por resultado, ~84 tokens no total.

Isso responde *"onde está?"*, que é a pergunta da maioria das buscas. Se você quiser **ler**
a primeira ocorrência junto, peça:

```bash
iachat search "termo" --abrir      # índice + a página da 1ª ocorrência
```

Sem `--abrir`, o rodapé te diz o comando exato do `page` para abrir quando quiser.

⚠️ Até 17/08 a página vinha **sempre** junto: 336 B contra 4.391 B — **13× mais caro** para
quem só queria localizar. O comando que existe para economizar contexto desperdiçava por
padrão. Agora abrir é escolha de quem pergunta.

## Navegar

```bash
iachat page recorte-01 4      # salta direto para a página 4
iachat page ativo             # o chat atual
```

O rodapé diz onde você está e quais são as vizinhas:

```
📄 iachat-2026-08-17-recorte-01 · página 3/21 · linhas 47-91 · ↑ pág 2 · ↓ pág 4
```

Peça a vizinha **por número**. Cada chamada traz **uma página** — você rola sem
recarregar o documento.

## O custo, medido

Uma página é fechada em **60 linhas ou ~4 KB, o que vier primeiro** — cerca de **1.000
tokens**. Num recorte de 78 KB isso deu **5% do arquivo**: você acha o que quer pagando
**1/20**.

O teto de bytes existe por um defeito real: paginar só por linhas não garante custo —
60 linhas curtas são 1 KB, 60 linhas longas são 15 KB. Quem paga a conta paga em bytes.

## Por que a página não muda debaixo de você

| | paginado? | por quê |
|---|---|---|
| `arquivo/*-recorte-NN.md` | **sim, estável** | recorte é **imutável**: "página 3" é a mesma amanhã |
| `iachat.md` (ativo) | sim, mas **instável** | ele cresce a cada mensagem — as fronteiras mudam |

⇒ Para citar uma página para outra IA, cite **de um recorte**. Do ativo, cite o **número
da mensagem** (`#14`), que nunca muda.

## Quando NÃO usar

Para ler o que acabaram de te mandar, use `iachat read --de <você> --novas` — é o
caminho barato do dia a dia. O `search` é para o que já saiu do ativo ou para procurar
por assunto.
