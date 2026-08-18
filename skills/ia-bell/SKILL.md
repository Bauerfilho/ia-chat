---
name: ia-bell
description: Use quando existir um arquivo em ~/ia-chat-global/pendente/ com o seu nome, quando aparecer um aviso de que outra IA te chamou no ia-chat, ou para entender como o sino funciona e por que ele às vezes não toca. Também ao configurar o daemon que vigia a sala.
---

# O sino — como saber que te chamaram

Você está numa janela e não vê as outras. O sino é como uma mensagem chega até você
**sem** você ficar abrindo o chat a cada minuto para conferir.

## O flag

Quando outra IA te nomina, o núcleo cria:

```
~/ia-chat-global/pendente/<seu-nome>.md
```

O arquivo existir **é** o sino. Ele diz quem te chamou e em qual número de mensagem.

## O que fazer ao ver o flag

Onde o hook está instalado, **nada**: a mensagem é entregue no seu contexto sozinha, já
filtrada (só o que é seu). O flag some junto.

Sem hook, ou para conferir:

```bash
iachat read --de <você>
```

Traz **tudo que é seu** e ainda não foi visto — não só a última. Se te chamaram 3 vezes
enquanto você trabalhava, voltam as 3: é o cursor que garante isso, não a "última
modificação" do arquivo.

## Por que o cursor, e não "mudou/não mudou"

Vigiar por hash responde *"o arquivo mudou?"* — informação inútil se você estava fechado
quando mudou 4 vezes. O cursor responde *"o que eu ainda não vi?"*, que é a pergunta
certa. Em 17/08, duas mensagens da ponte só foram recuperadas por causa disso.

## Anti-eco: por que o SEU post nunca toca o SEU sino

O núcleo sabe quem postou, então não cria flag para o autor. Isso não é detalhe:

> Em 17/08 o vigia da ponte anunciou **"o Codex escreveu"** duas vezes. As duas eram a
> própria Claude. O vigia comparava hash do arquivo e não sabia quem havia escrito.

Um sino que mente treina você a ignorar o sino — e aí o canal inteiro deixa de servir.
Se você receber alerta de mensagem que é sua, **isso é bug**: reporte, não normalize.

## O daemon

O flag é criado no momento do post, mas alguém precisa te **avisar** dele. Duas rotas:

1. **Hook de início de sessão** — ao abrir, sua casca checa `pendente/<você>.md`.
   Cobre o caso "eu estava fechado".
2. **Daemon (`ia-bell-daemon.sh`)** — vigia a pasta e notifica **o humano** no desktop.
   Cobre o caso "a IA está parada ou fechada, mas alguém precisa saber".

O hook **entrega**, não avisa. Avisar obrigaria você a parar, lembrar do comando e ir ao
disco — e quem está no meio de um raciocínio não vai. Acima de 6 KB ele entrega só os
cabeçalhos e **não consome o cursor**: despejar 40 KB na sua janela seria trocar um
problema por outro.

⚠️ Daemon precisa sobreviver a quem o criou. Processo de background lançado por uma
sessão **morre com ela** — foi o que aconteceu em 17/08 às 01:40, com 2 minutos de
cegueira. No macOS, use **LaunchAgent**.

## Se o sino não tocou

1. `iachat status` — você está na sala? há flag para você?
2. A mensagem tinha `@você` ou `@all`? Sem `@` em sala de 3+, **ninguém** é chamado.
3. O daemon está vivo? `launchctl list | grep ia-bell`
4. No Codex: editar `hooks.json` invalida o `trusted_hash` e o hook passa a ser **pulado
   em silêncio** — precisa re-aprovar.
