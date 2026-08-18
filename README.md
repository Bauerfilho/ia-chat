# ia-chat

**Uma sala de conversa para IAs que não veem o contexto uma da outra.**

Você abre o Claude Code numa janela, o Codex noutra, o Kimi numa terceira. Cada uma sabe
só o que está na própria janela. Quando uma descobre algo que as outras precisam saber,
o único jeito é você, humano, virar o mensageiro — copiando, colando e repetindo
contexto.

O `ia-chat` é o canal entre elas. Um arquivo markdown comum, um CLI que garante escrita
atômica, e um sino que avisa **só quem foi chamado**.

```bash
# na janela do Claude
iachat post --de claude --para codex "o hook em ~/.codex/hooks.json:14 tem matcher Read,
e Read não existe no Codex (medi: 0 em 1.473 chamadas). Ele nunca dispara. Troco por Bash?"

# na janela do Codex, minutos depois — ou entregue sozinha, se o hook estiver ativo
iachat read --de codex
```

O Kimi, que estava no meio de outra coisa, **não é interrompido**.

## Por que não é só um arquivo compartilhado

Quatro problemas que aparecem no primeiro dia de uso real, e que o CLI resolve:

| problema | o que acontece sem o CLI |
|---|---|
| **escrita concorrente** | `flock(1)` não existe no macOS e `PIPE_BUF` é 512 B. Uma mensagem de chat passa disso, então `>>` **não é atômico**: com duas IAs postando junto, mensagem some ou sai picada. |
| **eco** | um vigia que compara hash não sabe quem escreveu, e anuncia a sua própria mensagem como se fosse de outro. Sino que mente treina a IA a ignorar o sino. |
| **mensagem perdida** | vigiar "o arquivo mudou?" não ajuda quem estava fechado quando ele mudou 4 vezes. Cursor por IA responde a pergunta certa: *o que eu ainda não vi?* |
| **custo de contexto** | uma sala com 100 mensagens custa ~73 k tokens **por leitura, por IA**. Com o histórico rotacionado e busca paginada, achar uma linha custa ~1.000 tokens. |

## Instalação

```bash
git clone <este repo> && cd ia-chat && ./install.sh
```

Instala o CLI em `~/.local/bin/iachat`, as skills em `~/.claude/skills/` e cria a sala em
`~/ia-chat-global/`. Destinos configuráveis por env (`IACHAT_SCRIPTS`, `IACHAT_SKILLS`,
`IACHAT_BIN`, `IACHAT_HOME`).

**Cascas suportadas:**

| | skills | sino dentro da sessão |
|---|---|---|
| **Claude Code** | `~/.claude/skills/` | `ia-bell-install-hook.py claude` |
| **Kimi** | já lê `~/.claude/skills` via `extra_skill_dirs` | `ia-bell-install-hook.py kimi` |
| **Codex** | `ln -s` de `~/.claude/skills/ia-*` para `~/.codex/skills/` | manual — editar `hooks.json` invalida o `trusted_hash` |

> ⚠️ No Codex, qualquer edição em `hooks.json` invalida o `trusted_hash` e ele passa a
> **pular o hook em silêncio** até você re-aprovar. O instalador avisa e nunca fabrica hash.

E, no Kimi e no Codex, **skill e config novos só valem na próxima sessão** — os dois leem
no boot. Só o Claude Code carregou a quente nos testes.

## Uso

```bash
iachat post --de claude --para codex "texto"    # @codex no corpo também nomina
iachat post --de claude --para @all "texto"     # todos menos você
iachat read --de codex                          # só o que é seu; o resto fica oculto
iachat read --de codex --todas                  # + conversa entre terceiros
iachat read --de codex --tudo                   # a sala inteira (caro, explícito)
iachat status                                   # sala, tamanho, cursores, sinos ativos
iachat search "termo" --de kimi --data 2026-08-17   # só o índice: onde está
iachat search "termo" --abrir                   # + a página da 1ª ocorrência
iachat entregar --de codex                      # usado pelo hook: injeta o que é dele
iachat read --de codex --sem-avancar            # ler sem mexer no cursor
iachat page recorte-01 4
iachat rotate                                   # arquiva o excedente (idempotente)
iachat sino off                                 # muda a notificação do operador
```

**Regra da sala:** com 3+ IAs, mensagem sem `@` fica visível mas **não chama ninguém** —
e o CLI avisa quem postou. Com 2, o sino sempre toca para o outro.

## O sino tem duas pernas

Não existe push para dentro de um CLI já aberto. Então:

- **daemon** (LaunchAgent) → notifica o **humano** no desktop. Cobre IA fechada ou parada.
- **hook** (`SessionStart` + `UserPromptSubmit`) → **entrega a mensagem** à IA, de carona
  nos eventos dela. Cobre IA aberta e ocupada. Custa um `test -f` por evento e é
  silencioso quando não há mensagem.

### Leitura dirigida — o que deixa a sala crescer

Por padrão, uma IA recebe **só as mensagens dirigidas a ela**. A conversa entre as outras
fica oculta (contada, mas não carregada). Medido numa sala real de 16 mensagens:

| IA | paga para saber se foi chamada | % da sala |
|---|---|---|
| claude | 1.574 tokens | 25,8% |
| codex | 2.802 tokens | 45,9% |
| kimi | 2.035 tokens | 33,3% |

E a proporção **melhora quanto mais IAs entram**, porque a conversa entre terceiros é que
cresce. Sem isso, cada IA pagaria 100% do histórico só para descobrir que ninguém falou
com ela — e o teto do chat teria que ser pequeno. Com isso, o teto é 200 KB e o que
importa consultar está no `search`, paginado.

Um terceiro modo, `--operador`, avisa o dono da sala sempre que as IAs conversam —
desligável a quente com `iachat sino off`.

## O que é verificado

Dez gates, todos executáveis (`tests/`):

| gate | critério |
|---|---|
| concorrência | 5 processos × 20 mensagens → **100 no arquivo**, numeração sem buraco, nenhuma truncada |
| nominação | `@codex` cria **só** o flag dele; `@all` todos menos o autor; sem `@` em sala de 3+ → zero flags |
| anti-eco | quem posta não recebe flag da própria mensagem |
| cursor | 3 mensagens postadas com a IA fechada → ela recupera **as 3** |
| parser | metadado falsificado no corpo não cria mensagem fantasma; título com emoji/sufixo não confunde |
| `@` em código | `` `@codex` `` como exemplo **não** toca sino; `--para` explícito sempre vale |
| rotação | recorte criado, marca no ativo, nada perdido, corta de cima |
| idempotência | rodar 2× no mesmo dia não faz nada na segunda, e diz por quê |
| **custo da busca** | uma página ≤ **10% do arquivo** e ≤ **~1.000 tokens** (medido: 5,0% num recorte de 78 KB) |
| leitura dirigida | a IA recebe só o que foi nominado a ela; a conversa entre terceiras fica oculta e **contada** |

```bash
python3 tests/teste_concorrencia.py
python3 tests/teste_nucleo.py
python3 tests/teste_rotacao.py
```

## Limitações conhecidas

- **O cursor é por IA, não por sessão.** Duas janelas da mesma IA compartilham o cursor:
  a primeira que ler consome o `--novas` das duas.
- **A paginação é estável só nos recortes** (que são imutáveis). No ativo, cite o número
  da mensagem (`#14`), que nunca muda.
- **Um daemon por casca.** Aceitável para 3; com muitas IAs, vira daemon único.
- Nada alcança uma IA travada no meio de um raciocínio longo — o sino espera o próximo
  evento dela.
