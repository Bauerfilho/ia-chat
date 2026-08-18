# PROJETO `ia-mail` — a sala alcança o email

> **Estado: síntese de 5 laudos independentes.** Dois workers ainda rodando (OpenClaw;
> omniroute+obsidian). O que depende deles está marcado **[aguarda]** — não inventado.
>
> Substitui o `PLANO-ia-mail.md`, que foi escrito **antes** de mapear o terreno. A ordem
> estava invertida, e o dono corrigiu: *"não se cria plano sem mapear o terreno inteiro"*.
> O plano fica no repositório com os erros marcados, porque quem lê precisa ver o que era
> frouxo e por quê.

## Veredito: **DÁ**, e o caminho está provado

Cinco laudos, quatro braços, ~87 KB. O que sustenta o "dá":

- existe rota que **nunca manuseia senha** e funciona hoje (laudo A);
- existe desenho de porta de volta que **segura** email forjado e reenviado (laudo B);
- **dá para publicar** open-source sem distribuir segredo nosso (laudos C e H);
- o padrão que o dono mandou clonar **existe, está em produção e é copiável** (laudo H).

---

## 1. Conexão — como a peça usa a credencial sem vê-la

Laudo A (codex, 19 KB) mediu as rotas nesta máquina. **Duas famílias cumprem literalmente**
o requisito: delegar ao cliente já autenticado do sistema, ou OAuth.

| provedor | rota | por quê esta |
|---|---|---|
| **Gmail** | Gmail API + OAuth desktop + **PKCE** + callback `127.0.0.1`; refresh no Keychain | ❌ o **device flow do Google NÃO autoriza Gmail** — cobre identidade, Drive e YouTube. O plano original errava aqui |
| **Microsoft** | Graph + **device flow**; token no cofre do sistema | Basic Auth saiu do Outlook.com em **16/09/2024** e está desativada no Exchange Online — senha de app **não é rota Microsoft** |
| **Mail.app** | conector macOS de **zero token** | ⚠️ bloqueado por canário: hoje dá `-1712` (AppleEvent expira). Só entra quando o erro sumir e as 4 operações forem provadas |
| senha de app | fallback **legado** | ❌ **não cumpre literalmente**: algum helper IMAP carrega a senha em memória. Só vale se a promessa for "o *LLM* nunca vê" — não "a *peça* nunca vê" |

**A honestidade que o laudo A impôs:** a diferença entre "o modelo não vê" e "o software não
vê" é real, e vender uma pela outra seria mentir.

---

## 2. A porta de volta — cinco travas em série, fail-closed

Laudo B (grok, 18 KB). Responder o email posta na sala **com o nome do dono** — porta de
escrita vinda de fora, e esta casa já teve uma mensagem assinada `bauer` que ele não
escreveu.

1. **Token por mensagem** — 256 bits, no **corpo** (nunca no assunto: assunto vaza em
   notificação de tela bloqueada), **SHA-256 no disco**, jamais o token.
2. **Allowlist de mailbox** — endereço parseado, minúsculo, match exato.
3. **Queima no uso + validade em duas classes** — 24 h para a notificação (ele responde do
   celular horas depois), 15 min para o segundo tempo. **Estoque em disco, não em RAM.**
4. **Dedupe de `Message-ID`** — cobre o processo cair **entre** aceitar e queimar.
5. **Dois tempos** no que gasta ou mata, **copiando** `EXIGEM_CONFIRMACAO` do servidor.
   Uma fonte de verdade só.

### O que SPF/DKIM/DMARC garantem — e o que não

| evidência | prova | **não** prova |
|---|---|---|
| `From:` | nada | nada |
| SPF | IP autorizado no envelope | o `From:` visual · **morre em encaminhamento** |
| DKIM | os bytes saíram do domínio `d=` | que `d=` seja o do `From:` · **replica** |
| DMARC | o domínio alinha | local-part · conta comprometida |
| token | quem devolveu **viu** a mensagem | que seja o dono |
| allowlist | está na lista | autenticidade do `From:` |

**Nenhum abre a porta sozinho**, e o gate não inventa `dmarc=pass` quando o cabeçalho não vem.

---

## 3. Gerenciar a caixa — dois andares, não um

Laudo D (grok, 17 KB), contra a caixa real: **3.461 na inbox · 2.391 não lidas · 201 em 7
dias · ~70% alerta de vaga de TRÊS remetentes**.

❌ O plano dizia "mesmo remetente + mesmo assunto vira uma linha". Resolve o `×4` do
"Estágio em Criação" e **deixa dezenas de títulos de vaga na tela**. *"Sem o andar da
família, a tela não decide."*

```
andar 1 — FAMÍLIA, só pelo envelope:  alerta-vaga · informa · pessoa
andar 2 — LINHA, dentro da família:   (from_norm, assunto_norm)
```

⛔ **Nunca apagar.** Arquivar e etiquetar são reversíveis; apagar não é.

---

## 4. O padrão a clonar — o dono apontou, o laudo H confirmou

> *"Estude como os outros repositórios criam as pontes com os logins, você mesmo tem isso,
> chat gpt também, é só clonar e clonar perfeito e personalizado."*

Laudo H (kimi, 15 KB) leu o **iron-proxy** do hermes na fonte (2.494 linhas) e na doc:

1. a credencial real **nunca entra** no sandbox — o agente recebe um **token opaco**
   (128 bits de `urandom`, sem estrutura);
2. o mapa token→credencial fica no host (`0o600`) e aponta para o **nome** da variável, não
   o valor;
3. a troca acontece **na borda**, em TLS terminado pelo proxy, com CA **gerada localmente
   por instalação**;
4. **fail-closed em tudo**: request sem token para host allowlisted é rejeitado; allowlist
   default-deny; SSRF deny CIDRs (inclusive o IMDS `169.254.169.254`); bind nunca `0.0.0.0`.

⇒ **É publicável open-source sem distribuir segredo nenhum**, porque o CA nasce em cada
instalação. Era exatamente a pergunta que travava o projeto.

⚠️ **Ressalva do próprio laudo:** sem sandbox Docker, mesmo uid lê `/proc` e o `mappings`.
Para nós seria defesa contra **exfiltração acidental e prompt-injection**, não fronteira
contra atacante local. A diferença entre vender e mentir.

### Os oito clonáveis, por valor

| # | peça | esforço |
|---|---|---|
| 1 | camada `secrets` com cofre externo (resolve chave em texto plano **hoje**) | médio |
| 2 | token-opaco + swap-na-borda | alto |
| 3 | ⭐ **adaptador IMAP+SMTP** — o ia-chat por email, direto | médio |
| 4 | `send` desacoplado do agente (aviso de worker sem abrir LLM) | **baixo** |
| 5 | DM pairing (código em vez de editar allowlist) | baixo |
| 6 | redaction por default (`--show-tokens` para ver) | trivial |
| 7 | aliasing por perfil sobre cofre compartilhado | baixo |
| 8 | higiene: `0o600` desde o 1º byte, `O_NOFOLLOW`, pidfile+nonce | trivial |

O item 3 traz de graça a lição do **GHSA-rxqh-5572-8m77** — alguém já errou nisso, e
herdamos a correção sem pagar o preço.

---

## 5. Viabilidade pública

Laudo C (kimi, 16 KB): **dá, com duas ressalvas**.

- **R1** — o ChatGPT puro **não pluga MCP local**, só remoto. Um servidor MCP local serve
  Claude e as cascas da frota; para ChatGPT exigiria remoto (que traria servidor nosso, e
  aí trai a promessa).
- **R2** — Gmail exige que **cada usuário** crie o próprio OAuth client (~15 min,
  documentável) **ou** o projeto passe pela verificação do Google (não recomendado agora).

---

## 6. Ordem de construção

| # | o quê | por quê agora |
|---|---|---|
| 1 | `send` desacoplado (clonável nº 4) | esforço baixo, valor imediato, **zero risco** |
| 2 | ponte que **só SAI**: nominação vira email na caixinha `iachat` | metade sem porta de escrita |
| 3 | `ia-mail-control` de leitura: os dois andares do laudo D | é o que a caixa dele grita |
| 4 | conexão: Gmail OAuth+PKCE, Microsoft device flow | as rotas provadas |
| 5 | **volta**, com as 5 travas e isca em cada uma | só depois de 1-4 provados |
| 6 | comandos por email, dois tempos no que mata ou gasta | por último |

## 7. O que ainda não sei — **[aguarda]**

- ~~**OpenClaw**~~ → **FECHADO** (laudo W-claw, 9.901 B). Ver §9.
- ~~**omniroute**~~ → **FECHADO**. Ver §10.
- ~~**obsidian**~~ → **FECHADO**. Ver §10.

**As quatro fontes que ele mandou investigar estão fechadas.**

## 8. O que não faço sem palavra dele

apagar email — nunca · mandar email a terceiros · guardar senha em arquivo do projeto,
nem cifrada · ligar a porta de volta antes das cinco travas provadas com isca.

---

## 9. OpenClaw — a fonte nº 1 dele, fechada

Laudo `W-claw` (grok). Veredito: **o `ia-chat` não reimplementa canais — pluga como
cliente MCP no claw.**

### O que ele é

Agregador de **chat**, não de caixa postal. Gateway local **WS :18789**, loopback, auth por
token, LaunchAgent já rodando nesta máquina. **E tem ponte MCP pronta: `openclaw mcp serve`.**

### Autenticação por canal — o que serve de modelo

| canal | mecanismo | senha do usuário? |
|---|---|---|
| ⭐ **iMessage** | sessão do **Messages.app** já logado; o gateway sobe `imsg rpc` (JSON-RPC em **stdio**, sem porta, sem daemon) | **zero** |
| WhatsApp | QR do WhatsApp Web (Baileys); credencial em `~/.openclaw/credentials/` | nenhuma (QR no celular) |
| Telegram | token de bot do @BotFather | token de **bot**, não da conta |
| Signal | `signal-cli` com QR ou SMS em número dedicado | QR no app |
| Slack / Discord | tokens de app / bot | tokens de app |

⭐ **O iMessage é o padrão que eu procurava para o Mail.app**: o app do sistema já
autenticou, e a peça só conversa com ele por um CLI local em stdio. É a rota 1 do §1 desta
proposta, provada funcionando noutro canal.

### Email

**Não é canal do OpenClaw.** O mais perto: hook de Gmail (inbound) ou a skill Himalaya
(IMAP com senha). Ou seja — para email, o caminho continua sendo o do §1, não o claw.

### O que isso muda no projeto

1. **Canais de chat**: não construir. Plugar por MCP no claw, que já resolveu.
2. **Email**: continua nosso, pelas rotas do §1.
3. **A forma do gateway** (servidor local + adapter em stdio, estilo `imsg`) é o desenho a
   copiar quando precisarmos de um canal que o claw não tem.

---

## 10. omniroute e obsidian — as duas últimas fontes, fechadas

Laudo `O-omniroute-obsidian` (grok, 11.175 B).

### omniroute — ⭐ ele JÁ resolve o problema de credencial, e está rodando aqui

Não é Keychain, não é Vault, não é N arquivos de chave espalhados pelas cascas. **Cofre
local de dois andares:**

1. **envelope** — `STORAGE_ENCRYPTION_KEY` no `~/.omniroute/.env`;
2. **segredo cifrado campo a campo** no SQLite:
   - AES-256-GCM · formato `enc:v1:<iv_hex>:<ct_hex>:<authTag_hex>`
   - derivação `scrypt(chave, "omniroute-field-encryption-v1", 32)`
   - campos cifrados: `api_key`, `access_token`, `refresh_token`, `id_token`

**E o mecanismo de uso é exatamente o que precisamos:** as cascas apontam para
`127.0.0.1:20128` com **UMA** chave OmniRoute; o servidor escolhe o provedor, **decifra o
token daquela linha** e fala com o upstream. **A casca nunca vê a credencial** do Google,
Anthropic, xAI ou Qwen.

**Provado em produção nesta máquina:** 15 conexões ativas (10 OAuth + 5 apikey), todas com
envelope `enc:v1` — antigravity, agy, cline, grok-cli, codex, github, claude, kimi-coding…

⇒ Comparado ao iron-proxy do hermes (§4): **mesmo princípio, muito mais simples**. Não
intercepta TLS, não instala CA, não exige sandbox. Troca o segredo **no servidor**, não na
borda da rede. Para o `ia-mail`, é o candidato mais realista.

### ⚠️ O anti-padrão que vem de graça

> *"Sem ele o código entra em **passthrough** (grava texto puro — modo dev)."*

Se a `STORAGE_ENCRYPTION_KEY` falta, o omniroute **grava a credencial em claro**. É
**fail-open**, e é o oposto da doutrina desta casa: chave ausente tem que **parar**, não
degradar em silêncio para texto puro. Ao clonar o mecanismo, clonar o cofre e **inverter
essa escolha** — sem chave, sem gravação.

(Há também fallback de salt legado com auto-migração, de um bug histórico de decrypt
cruzado. Vale copiar a auto-migração, que é honesta.)

### obsidian — não é cofre, mas tem um plug útil

`obs` 1.13.7 é motor de vault, **não** guarda credencial de provedor. O que serve é o
plugin **`obsidian-local-rest-api` 5.1.0** em `127.0.0.1:27124` — REST **e MCP**, com
Bearer. Ou seja: se um dia o mapa de retomada precisar ser lido ou escrito no vault dele
pelo app, a ponte existe e é local.

### O que muda no projeto

| antes | depois |
|---|---|
| construir cofre de credencial | **clonar o do omniroute**, invertendo o fail-open |
| Keychain como única rota sem senha | Keychain **ou** cofre cifrado local, os dois provados |
| vault do Obsidian fora de alcance | alcançável por REST/MCP local, se precisar |
