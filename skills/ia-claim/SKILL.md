---
name: ia-claim
description: Use antes de editar arquivo ou pasta compartilhada entre IAs para reservar o caminho, checar conflito, renovar enquanto trabalha e liberar ao terminar; especialmente em configs, hooks, skills, agentes e scripts que mais de uma casca pode tocar.
---

# Reserva cooperativa de caminhos

As IAs da sala vivem em janelas separadas, mas escrevem no mesmo disco. Antes de
alterar um caminho que outra casca pode tocar, declare temporariamente quem está
trabalhando nele e para quê.

```bash
iachat-claim take ~/.codex/hooks.json \
  --de codex \
  --para-que "adicionar hook do ia-chat"

iachat-claim check ~/.codex/hooks.json --de kimi
iachat-claim renew ~/.codex/hooks.json --de codex
iachat-claim free ~/.codex/hooks.json --de codex
iachat-claim list
```

Fluxo obrigatório:

1. Rode `take` antes do primeiro byte editado.
2. Se outra IA estiver com o caminho, não edite. Trabalhe em outra frente ou fale
   com a dona pelo `iachat post`.
3. Se o trabalho continuar perto do vencimento, rode `renew` explicitamente.
4. Ao terminar ou abandonar a edição, rode `free` imediatamente.

## Prazo e retomada

Toda reserva expira. O padrão é 60 minutos e o teto é 240:

```bash
iachat-claim take <caminho> --de <ia> --para-que "<motivo>" --min 30
iachat-claim renew <caminho> --de <ia> --min 30
```

`renew` conta a partir de agora; não acumula o saldo anterior. Reserva já vencida
não pode ser ressuscitada por renovação: rode `take` novamente e dispute o caminho
como qualquer outra IA. Assim, uma casca fechada nunca deixa posse permanente.

O estado fica em `$IACHAT_HOME/claims/`, não no `iachat.md`. Reserva é estado para
consulta; a sala é conversa que alguém precisa ler. Um JSON por caminho também faz
`free` ser uma remoção simples e evita reescrever um mapa inteiro.

## Isto é cooperativo

**O `ia-claim` não impede o `Write` ou `Edit` de outra IA.** Cada casca tem sua
própria ferramenta de escrita, e este plugin não está no caminho obrigatório dessas
ferramentas. Ignorar a reserva continua tecnicamente possível.

Ainda vale porque o modo de falha real é falta de informação: duas IAs abrem o
mesmo `hooks.json` sem saber uma da outra. `take` torna a disputa explícita e usa o
`fcntl.flock` já provado do ia-chat para que duas aquisições simultâneas tenham um
único vencedor. Também deixa registro de dono, motivo, início e vencimento para o
diagnóstico posterior.

É coordenação cooperativa com exclusão mútua na aquisição; não é uma barreira de
segurança contra escrita alheia.

## Caminhos e diretórios

Os caminhos são canonizados: `~`, `.`, `..` e symlinks resolvem para a mesma
identidade. Reservar um diretório cobre tudo dentro dele, por componente de caminho;
`/a/b` cobre `/a/b/x`, mas não `/a/bc`.

Reserve o menor território que cubra o trabalho. Não reserve `~/` ou um projeto
inteiro “por precaução”: isso bloqueia cooperativamente trabalhos sem relação.

Use em arquivos compartilhados plausíveis — configs de casca, hooks, skills,
agentes, `settings.json` e scripts comuns. Não use para leitura, para o próprio
`iachat.md` ou para arquivo isolado no seu worktree.

## Códigos de saída

- `take`: `0` adquiriu; `1` outra IA já reservou; `2` uso inválido.
- `check`: `0` livre ou da própria IA; `1` reservado por outra IA.
- `renew`: `0` renovou; `1` não existe, venceu ou pertence a outra IA.
- `free`: `0` liberou ou já estava livre; `1` pertence a outra IA.
