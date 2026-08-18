---
name: ia-compactacao
description: Use quando aparecer no seu flag do ia-chat um aviso 🧭 compact-bell, quando o SessionStart/PostCompact apontar para caminho.md, ou quando você acabou de ser compactada e precisa se situar sem reler a conversa. Também para instalar ou conferir o mapa curto de retomada.
---

# O caminho de volta — uma skill, um sino, um documento

Compactação é a queda de energia da IA: o trabalho continua, o contexto some.
O sino comum avisa que **alguém te chamou**. Este avisa que **você perdeu a sala
de estar e o chão está no disco**.

Irmão do `ia-server-connection`. Mesmo desenho: um gatilho, o sino do dono
(`ia-bell`), um documento. Sem segundo sistema de notificação.

## A regra que vale antes de qualquer outra

> **Não é um resumo do que aconteceu. É o mapa de para onde ir.**

Ao ver `compact-bell` ou o bloco injetado no SessionStart, o primeiro gesto
**nunca** é reconstruir a conversa. É **abrir `caminho.md`**.

```
$IACHAT_HOME/caminho.md
```

Quatro seções, sempre as mesmas, sempre curtas:

| seção | o que tem |
|---|---|
| **Onde parou** | o último arquivo com prova no disco (path + mtime + tamanho) |
| **Rodando agora** | workers do iaswarm / progress no disco |
| **Espera decisão** | o que está marcado PENDENTE/BLOQUEIO para o dono |
| **3 links** | sala · painel · relatórios |

Se o arquivo passar de ~12 KB ou vier com `<analysis>`, **não é este mapa** —
é a captura-resumo do vault (`Obsidian/inbox-capturas/AAAA-MM-DD capturas.md`).
Aquilo é buffer. Não comece por lá.

## O que fazer, nesta ordem

1. Leia `caminho.md` inteiro. Cabe numa tela.
2. Abra o primeiro path de **Onde parou**. Retome dali.
3. Só então olhe a sala (`iachat read --de <você>`) se o mapa apontar uma mensagem.

## O gatilho é passivo — depois de armado UMA vez

| caminho | quando | o que acontece |
|---|---|---|
| **PreCompact** | a casca vai compactar | o script grava o mapa **antes** do contexto morrer |
| **PostCompact** | a compactação acabou | atualiza o mapa; injeta o ponteiro no contexto |
| **SessionStart** | você abriu / voltou / entrou na sala | se `caminho.md` existe, o hook imprime o ponteiro |

Não depende de a IA lembrar da skill. O hook escreve e entrega. A skill existe
para você **saber o que fazer** quando o aviso chegar.

> ⚠️ **O `install.sh` NÃO arma esses hooks, e isso é de propósito.** Um instalador
> que edita sozinho o `settings.json` de quem instala é invasivo — e em algumas
> cascas (Codex) mexer no arquivo de hooks invalida o `trusted_hash` e quebra o
> que já funcionava. O instalador **mostra** o bloco pronto para colar; armar é
> um gesto seu.
>
> Enquanto não for armado, a skill funciona **na mão**: `ia-compactacao --mapa`
> escreve o mapa, `--inicio` imprime o ponteiro. O que não acontece sozinho é o
> gatilho. Rode `iachat-doctor` para ver se ele está armado nesta máquina.

## O sino

Reusa `ia-bell`. O arquivo `pendente/<você>.md` **é** o sino — uma linha
`🧭 compact-bell`. O daemon que já vigia essa pasta avisa o humano. O
`ia-bell-hook.sh` entrega o flag na sessão.

Se o dono desligou o sino (`notificar_operador: false` / `iachat sino off`),
**não se escreve flag nenhum**. O mapa continua no disco. Silêncio é inteiro.

Este script **não** chama `osascript`. Quem notifica é o daemon que já existe.

## Instalar e conferir

```bash
# o binário (depois que a orquestradora integrar)
ia-compactacao --mapa          # grava caminho.md agora, sem esperar compactar
ia-compactacao --validar "$IACHAT_HOME/caminho.md"
ia-compactacao --inicio        # o que o SessionStart injeta
```

Proposta de hook — **não editar `~/.codex/hooks.json` à mão** (invalida
`trusted_hash` e o Codex passa a pular hook em silêncio). Ver
`proposto/hooks-*.json` neste pacote.

## Dois limites honestos

**Não existe push para dentro de uma sessão já aberta.** Igual ao
`ia-server-connection`: o aviso chega no próximo evento da casca
(SessionStart, UserPromptSubmit, ou o stdout do PostCompact).

**Grok/Kimi/Qwen não têm o hook armado nesta casa hoje.** Grok *aceita*
`PreCompact`/`PostCompact` (`~/.grok/docs/user-guide/10-hooks.md:102-103`),
mas `~/.grok/hooks/` está vazio. Sem o JSON proposto, nesta casca o mapa
só nasce se alguém rodar `ia-compactacao --mapa` ou se a sessão herdar o
`~/.claude/settings.json` (compat do Grok, configurável).

## O que esta skill NÃO é

- Não substitui `ia-onboard` (entrada na sala pela primeira vez).
- Não substitui `ia-server-connection` (energia/rede).
- Não é o `captura-compact-vault.sh` (esse guarda o resumo longo no vault).
- Não posta sozinha na sala viva.
