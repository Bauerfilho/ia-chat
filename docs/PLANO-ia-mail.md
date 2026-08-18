# PLANO — `ia-mail`: a sala alcança o email, e a IA cuida da caixa

> Proposta dele, 18/08/2026: *"criasse um plugin no app ou no repositório ou uma
> habilidade chamado mail connection, que é simplesmente a skill de logar a sua ia no
> seu email"* · e antes: *"o plug de cada ia deve dar a skill de controlar o meu email…
> para fazer trabalhos de gerenciamento por mim de caixas de entrada"*.

Isto é um **plano**, não código. Nada abaixo foi construído.

---

## Por que isto cabe no projeto (e por que quase não cabe)

O `ia-chat` é local-first: sem conta, sem servidor, sem nuvem. A sala é um arquivo de
texto no disco de quem instala. **Email é o oposto de tudo isso** — é um serviço de
terceiro, com credencial, na rede.

Cabe por um motivo só, e é forte: **o email é a única interface que já está no bolso de
todo mundo.** Ele lê a sala no celular hoje por um túnel efêmero, que cai e troca de
endereço. O email não cai, não precisa de túnel, funciona no avião, e já tem notificação
que ele confia. Para quem prefere não abrir o app — a frase dele — é a porta certa.

Não cabe se trouxer servidor, conta ou credencial nossa para dentro do projeto. **Se a
única forma de fazer for guardar a senha de alguém, não fazemos.**

---

## As três rotas de conexão, em ordem de segurança

O ponto que decide o desenho: **a skill nunca vê a senha de ninguém.** Ela orquestra o
fluxo em que o provedor autentica — e cada rota tem um dono da credencial que não somos
nós.

### Rota 1 · Local (macOS) — zero credencial ⭐ preferida

O Mail.app já está logado na máquina de quem instala. A skill fala com ele por
AppleScript: lê, envia, move para pasta. **Nenhuma senha, nenhum token, nada na rede
além do que o Mail.app já faz.**

O que o usuário faz uma vez: autoriza *Automação* em Ajustes → Privacidade → Automação.
Um clique, e o macOS mostra na cara o que está sendo autorizado.

Serve iCloud, Gmail, Outlook, IMAP — qualquer conta que o Mail.app já tenha.

**Limite honesto:** só macOS, e só com o Mail.app configurado.

### Rota 2 · OAuth (device flow) — token, nunca senha

Para quem não usa o Mail.app, ou está em Linux/Windows. A skill mostra uma URL e um
código; o usuário autoriza no navegador, na página do próprio Google/Microsoft. O token
volta e vai para o **Keychain do sistema**, nunca para um arquivo do projeto.

**Limite honesto:** exige que o usuário registre um app no console do provedor (grátis,
mas é fricção). O `ia-chat` não pode embarcar client secret próprio — seria uma
credencial nossa dentro do repositório de todo mundo.

### Rota 3 · Senha de app (IMAP/SMTP) — último recurso

Para provedor sem OAuth. **A skill não pede, não lê e não guarda a senha.** Ela imprime
o comando para o usuário rodar, e ele digita:

```bash
security add-generic-password -a "$USER" -s ia-mail-<conta> -w
```

O `-w` sem valor faz o macOS pedir a senha em prompt oculto. Ela vive no Keychain; a
skill só a referencia pelo nome. Em Linux, o equivalente via `secret-tool`.

---

## As duas skills, com os nomes que ele deu

### `ia-mail-conexao` — plugar

`conectar` (escolhe a rota e guia) · `estado` (qual rota, qual conta, testado quando) ·
`desconectar` (apaga token do Keychain e para tudo).

O `estado` diz a verdade em três desfechos: **ligado e provado** (mandou um email de
teste para o próprio usuário e ele chegou) · **configurado, não provado** · **não
conectado**. Nunca "ligado" sem prova — é a mesma lição do sino.

### `ia-mail-control` — gerenciar

O que ele pediu: *"trabalhos de gerenciamento por mim de caixas de entrada"*. Com uma
inbox de **3.461 mensagens e 2.391 não lidas** (medido hoje), isto é o que agrega mais:

- **agrupar repetição** — sete emails do mesmo remetente sobre o mesmo assunto viram uma
  linha com sete;
- **separar o que só informa** do que **pede resposta** — a segunda lista é curta e é a
  que importa;
- **achar o que envelheceu** — o que está há N dias esperando resposta dele;
- **propor arquivamento em lote**, sempre com a lista na frente e uma palavra dele.

⛔ **Nada destrutivo sem confirmação, e nada de apagar nunca.** Arquivar e etiquetar são
reversíveis; apagar não. A skill não apaga email, ponto.

---

## A ponte da sala ↔ email

### Sai (fácil e sem risco)

Quando ele é nominado na sala, chega um email na caixinha `iachat` — a que já criei hoje
no Gmail. Assunto com o número da mensagem, corpo com o texto, e o link do app se o
túnel estiver no ar.

### Volta (é aqui que mora o risco)

Responder o email posta na sala **com o nome dele**. Isso é uma porta de escrita vinda
de fora — e a casa já teve uma mensagem assinada `bauer` que ele não escreveu.

Três travas, e as três são necessárias:

1. **Token por mensagem.** Cada email que sai leva um segredo curto, único, que só existe
   naquela mensagem. A resposta precisa devolvê-lo. **O `From:` é forjável; o token não.**
2. **Allowlist de remetente.** Só endereços que ele cadastrou. Sozinha não basta (ver 1),
   mas corta o ruído.
3. **Queima no uso, e expira.** É o mesmo recibo que o `/parar` já usa desde hoje de
   manhã — mesma peça, mesmo motivo.

### Comandos por email

Ele pediu: *"comandos de barra e o nomination devem ser fácil de fazer, afinal é só uma
escrita antes da mensagem"*. É verdade, e o parser é trivial: `@codex …` nomina, `/plan …`
comanda.

**O que muda é a consequência.** `@codex` posta — reversível. `/parar` mata processo e
`/plan` gasta assinatura — não são. Então:

| pelo email | como |
|---|---|
| texto e `@nominação` | direto, com o token |
| `/goal`, `/quem`, `/decidi` | direto, com o token |
| `/plan`, `/parar`, `/refaz` | **dois tempos**: a resposta devolve a previsão por email, e só um segundo email confirma |

Os dois tempos já existem no servidor. Não é peça nova — é a mesma, com outro transporte.

---

## Ordem de construção

| # | o quê | por quê primeiro |
|---|---|---|
| 1 | `ia-mail-conexao` na **rota local** | resolve o Mac dele hoje, sem credencial nenhuma |
| 2 | **sai**: nominação vira email na caixinha | metade sem risco, valor imediato |
| 3 | `ia-mail-control`: agrupar repetição e separar o que pede resposta | é o que a caixa dele grita |
| 4 | **volta**: token por mensagem, texto e `@` só | a porta de escrita, com a trava desde o primeiro dia |
| 5 | comandos por email, com dois tempos no que gasta ou mata | depois que 4 estiver provado |
| 6 | rotas OAuth e Keychain | para quem clona o repo e não usa Mail.app |

---

## O que eu NÃO farei sem a palavra dele

- apagar email — nunca, nem com ordem;
- mandar email para terceiros — a ponte fala com ele, não com o mundo;
- guardar senha em arquivo do projeto — nem cifrada; Keychain ou nada;
- ligar a volta (email → sala) antes das três travas estarem provadas com isca.
