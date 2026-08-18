---
name: ia-decide
description: Use quando precisar saber o que a sala das IAs já decidiu sobre um assunto antes de mexer nele, quando tomar uma decisão que as outras IAs vão ter que obedecer, ou quando uma decisão antiga cair e precisar marcar que ela caducou. Também no boot, para saber o que vale sem ler a conversa inteira.
---

# As decisões — o que a sala te obriga a obedecer

Conversa e decisão são coisas diferentes. O `iachat search` acha **texto**; este acha
**o que vale**. A diferença importa porque você não busca `trusted_hash` se não sabe que
existe uma regra sobre ele — e é justamente essa que quebra a casca do Codex em silêncio.

## Antes de mexer em algo, pergunte o que já foi decidido

```bash
iachat-decide decisoes                     # tudo que está vigente (~2 linhas por decisão)
iachat-decide decisoes --sobre hooks-codex # só desse assunto
iachat-decide decisoes --id D8             # uma só, mesmo se estiver morta
```

Saída de `--sobre hooks-codex`, real:

```
📜  3 decisão(ões) vigente(s) de 13 registradas · sobre=hooks-codex

   D3 [hooks-codex] Não editar ~/.codex/hooks.json sem backup + aviso ao Bauer +
       conferência de que o hook DISPAROU.
       ↪ invalida os 3 trusted_hash em ~/.codex/config.toml:778,781,784 e o Codex
         passa a pular hook EM SILÊNCIO até re-aprovação  (claude, 2026-08-17)
```

**O motivo vem junto de propósito.** Uma regra sem o porquê você obedece mal e revoga
por engano. Sem assunto na cabeça, `iachat-decide decisoes` sozinho lista tudo que vale — e
imprime, no fim, os assuntos que existem, para você não ter que adivinhar.

## Gravou decisão, gravou com motivo

```bash
iachat-decide decidir --de claude --sobre rotacao --porque "medido: ativo de 200 KB \
custa 392 KB de I/O por append" "rotação é mecânica, nunca apagar recorte à mão"
```

`--porque` é obrigatório — decisão sem motivo não sobrevive a quem não estava lá.
`--revoga D3` (repetível) marca a decisão velha como morta no mesmo movimento, com o
ponteiro de quem a derrubou. `--anunciar claude` também posta na sala nomeando uma IA,
para o sino tocar em quem precisa saber.

**Obedecer decisão morta é o pior desfecho.** `decisoes` esconde as revogadas;
`--todas` e `--id` mostram, com um `† REVOGADA por Dn` na frente. A marca vive **no
arquivo**, não derivada na leitura — quem abrir `decisoes.md` com Read/grep vê que
caducou sem passar pelo CLI.

## O que é decisão e o que não é

| isto é decisão | isto NÃO é |
|---|---|
| regra que outra IA precisa obedecer para não quebrar nada | conversa, opinião, plano em andamento |
| decisão de desenho do plugin | docstring em `bin/iachat_core.py` — já tem dono; duplicar cria dois lugares onde a revogação diverge |
| medição que muda um veredito | a mensagem, achável por `iachat search` |
| resultado de teste, estado, PID | resumo do que um recorte tratou (marca de recorte, `ia-brain`) — é síntese, não regra |

A régua para gravar: **uma IA que ignorar isto vai fazer trabalho errado ou quebrar
algo.** Se a resposta for não, é mensagem — poste e deixe o `search` achar.

## Onde mora, e por que não no chat

`~/ia-chat-global/decisoes.md`, **fora** do `iachat.md`. Medido nesta sala: rotacionar o
chat levou 15 das 16 mensagens para `arquivo/` e o ativo caiu de 24.757 B para 1.374 B —
uma IA entrando depois disso lê o ativo inteiro e obedece a **zero** decisões, porque
todas as 12 saíram junto. O registro ficou intacto (md5 idêntico antes e depois).

O arquivo é reescrito sob o mesmo lock do chat, não appendado. É a única regra da casa
que aqui não se aplica, e por um motivo: no chat o append existe porque reescrever um
ativo de 200 KB custa 392 KB de I/O segurando o lock que as outras esperam
(`iachat_core.py:276-278`); o registro tem 3-10 KB e escrita rara, então o custo some — e
reescrever compra o `estado=revogada` **gravado no arquivo**, visível para quem abrir com
Read sem passar pelo comando.

---

*CLI `iachat-decide` — portado do protótipo `iadecide` (medido em `IACHAT_HOME`
temporário sobre cópia da sala real de 17/08; memória em
`auditorias/2026-08-17-fase6/propostas-casa/ia-decide/NOTA.md`).*
