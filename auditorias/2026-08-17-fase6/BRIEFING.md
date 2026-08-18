# BRIEFING — ia-chat, fase 6 (auditoria + peças novas)

> Você é stateless. **Tudo que precisa saber está aqui e no repositório.** Não pergunte
> a ninguém; leia o código e meça.

## O produto

`ia-chat` é um plugin do **Bauer** (dono da máquina e do projeto). Repositório:
`/Users/bauervieiracesarfilhovieira/Projetos/ia-chat`. Sala viva de dados:
`/Users/bauervieiracesarfilhovieira/ia-chat-global`.

**O problema que ele resolve**, na palavra do dono: *"quando vocês estiverem em chats abertos
sem poderem ver o contexto um do outro e ainda assim poder se ajudarem."*

Várias IAs (Claude Code, Codex, Kimi…) rodam em janelas separadas, cada uma cega ao contexto
das outras. O `ia-chat` é o único canal entre elas: um markdown comum, um CLI que garante
escrita atômica, e um sino que avisa **só quem foi nominado** — sem interromper as demais.

## O que já existe (leia o código, não confie nesta lista)

- `bin/iachat_core.py` — lock `fcntl`, post por **append**, cursor por IA, nominação com
  anti-eco, rotação com recorte imutável, busca paginada
- `bin/iachat` — CLI: `post · read · entregar · status · sino · rotate · page · search`
- `bin/ia-bell-daemon.sh` — sino por casca (LaunchAgent) + modo `--operador`
- `bin/ia-bell-hook.sh` — **entrega** a mensagem dentro da sessão aberta
- `bin/ia-bell-install-{daemon.sh,hook.py}` · `install.sh`
- `skills/` — 7 skills: `ia-chat-activate · ia-bell · ia-nomination · ia-storage · ia-brain ·
  ia-search · ia-chat-consult`
- `tests/` — 3 arquivos, **10 gates**: concorrência (5 processos × 20 msgs = 100 íntegras),
  nominação, anti-eco, cursor, parser, `@` em código, rotação, idempotência, custo da busca,
  leitura dirigida

## Decisões de desenho já tomadas (não refaça, mas pode contestar COM medida)

1. **Nada escreve no chat com `>>`** — `flock(1)` não existe no macOS e `PIPE_BUF` é 512 B; append
   direto de mensagem de chat não é atômico.
2. **Leitura dirigida por padrão** — a IA recebe só o que foi nominado a ela; a conversa entre
   terceiras fica oculta e contada. Medido: cada IA paga 26–46% da sala em vez de 100%.
3. **Post é append puro** — 17 KB de I/O por mensagem em vez de 392 KB (chat de 196 KB).
4. **Rotação é mecânica**, não do "brain" — o brain é uma IA e pode estar fechada quando o chat
   estoura.
5. **Página fecha em 60 linhas OU ~4 KB**, o que vier primeiro — paginar só por linhas não
   garante custo.
6. **Skill com frontmatter mínimo** (`name` + `description`) — é o que funciona em toda casca.

## Defeitos reais já vividos neste projeto (contexto, não lista de tarefas)

- Sino que anunciou "o Codex escreveu" 2× e as 2 eram a própria Claude ⇒ **anti-eco**.
- Regex que exigia o título inteiro quebrou o sino ⇒ **parser lê metadado, nunca título**.
- `launchctl list | grep -q` sob `pipefail`: SIGPIPE fez o instalador **negar um daemon que subiu**.
- `@codex` escrito entre crases, como exemplo, **tocou o sino dele**.
- Skill instalada não entra no catálogo de sessão já aberta (Codex e Kimi leem no boot).
- Editar `~/.codex/hooks.json` invalida o `trusted_hash` e o Codex **pula hook em silêncio**.

## REGRAS INEGOCIÁVEIS DESTE TRABALHO

1. **NÃO ESCREVA** em `~/Projetos/ia-chat` nem em `~/ia-chat-global`. Sua entrega é documento.
   Protótipo, se houver, roda em `IACHAT_HOME` temporário (`/tmp/...`).
2. **Alegação sem `arquivo:linha` não conta.** Leia o código antes de opinar.
3. **Custo medido, não estimado.** Propôs peça? Diga quanto ela custa e quanto economiza, com
   número que você obteve rodando algo.
4. **"Não consegui verificar" é resposta válida e respeitada.** Inventar, não.
5. Escreva **denso, organizado e direto**, em português. Sem preâmbulo, sem elogio, sem resumo
   do que você vai fazer — faça e relate.
