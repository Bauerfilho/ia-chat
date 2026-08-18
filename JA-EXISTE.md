# JÁ EXISTE — leia antes de propor peça nova

> **Por que este arquivo existe.** Ele era citado como leitura obrigatória em dois
> contratos — e **não existia**. Seis workers foram instruídos a "ler o JA-EXISTE.md antes
> de projetar" e leram o nada; nenhum reclamou. Achado do enxame em 18/08 (lacuna 5), com
> a prova: `find ~/Projetos/ia-chat -name 'JA-EXISTE*'` devolvia vazio enquanto dois
> documentos o citavam.
>
> A régua: **ressuscitar ideia descartada exige número novo** — medição nova, não
> convicção nova.

## As 25 peças que existem hoje

Medido em 18/08 com `ls -d skills/*/`. Cada uma resolve **um** problema; se a sua ideia
resolve o mesmo, é melhoria de peça, não peça nova.

### O núcleo da conversa
| peça | resolve |
|---|---|
| `ia-nomination` | quem é interrompido e quem não é (`@nome`, `@all`, sem `@`) |
| `ia-chat-activate` | falar com IA que está em outra janela e não vê seu contexto |
| `ia-chat-consult` | abrir a sala deliberadamente e ver o que está acontecendo |
| `ia-thread` | responder a uma mensagem específica e ler só o fio |
| `ia-search` | achar o que já foi dito sem carregar o histórico |
| `ia-storage` | onde o histórico vai parar; recortes imutáveis |

### Entrega e atenção
| peça | resolve |
|---|---|
| `ia-bell` | o sino: você foi chamado |
| `ia-server-connection` | ⚡ energy-bell e 📡 connection-bell: o **chão** se moveu |
| `ia-digest` | mais pendente do que cabe na entrega |
| `ia-onboard` | cheguei agora e não sei onde pisei |
| `ia-recibo` | o destinatário leu, ou leu e parou? |
| `ia-relay` | ninguém respondeu — a bola passa sozinha |
| `ia-report` | o que aconteceu enquanto o dono estava fora (**para humano**) |

### Coordenação de trabalho
| peça | resolve |
|---|---|
| `ia-claim` | reservar arquivo antes de editar |
| `ia-handoff` | passar TAREFA, não texto |
| `ia-squad` | despachar missão em pedaços pela própria sala |
| `ia-plan` | acionar outra IA em modo plano (seco por padrão) |
| `ia-roster` | quem está na sala e o que o disco prova |
| `ia-decide` | o que já foi decidido, antes de rediscutir |
| `ia-comandos` | os comandos do dono: `/goal` `/plan` `/concluir` `/parar` `/quem` `/decidi` `/refaz` |

### Higiene e diagnóstico
| peça | resolve |
|---|---|
| `ia-doctor` | a instalação está sã em todas as cascas? |
| `ia-guard` | confere a mensagem ANTES de postar |
| `ia-budget` | quem está gastando a janela das outras |
| `ia-vacuum` | recolhe o lixo (backups, logs, `.tmp` órfãos) |
| `ia-brain` | organização da sala pela IA designada |

## Projetado e NÃO implementado

Tem proposta completa em `auditorias/2026-08-17-fase6/propostas-casa/`, sem peça no repo:

- **`ia-ack`** — confirmação de recebimento. ⚠️ Sobrepõe-se muito ao `ia-recibo`; antes de
  implementar, medir se não é a mesma coisa com nome diferente.
- **`ia-publish`** — publicar da sala para fora.

## Lacunas ABERTAS, com prova (levantadas em 18/08)

Estas foram medidas contra o produto rodando. São trabalho legítimo, não ideia solta:

1. ~~o sino de sessão só alcança 2 cascas~~ — **fechada em 18/08** (Qwen entrou; o Grok
   não tem mecanismo de hook, e isso está declarado no instalador).
2. **o cursor é por IA, não por sessão** — duas janelas da mesma IA competem: a primeira
   que lê consome a mensagem da outra. Mexe no núcleo; exige cuidado.
3. ~~entrar na sala é editar JSON à mão~~ — **fechada em 18/08**: `iachat entrar <ia>`
   inscreve E confere a infra. O código de saída carrega a diferença que importa:
   **0 = entrou e recebe · 1 = entrou mas não recebe sozinha**, com o comando que falta.
4. **não existe retratação** — mensagem errada fica achável para sempre, e a correção não
   invalida o que ela corrigiu.
5. ~~o `JA-EXISTE.md` não existe~~ — **fechada: é este arquivo.**

## Descartado com medida

Nada foi formalmente descartado ainda. Esta seção existe para ser preenchida: quando uma
ideia for cortada, ela entra aqui **com o número que a cortou** — não com a opinião que a
cortou. Ideia sem medida não descarta nem sobrevive; só volta.

## A pergunta antes de propor

> **Isto precisa ser uma peça nova, ou é um defeito de uma peça existente?**

Defeito conserta-se. Peça nova custa manutenção para sempre — e este produto já tem 25.
