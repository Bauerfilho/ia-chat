# Plano de implementação — fase 7

> Seis executores, seis partes disjuntas. Cada um **implementa, testa, valida e documenta** a
> sua, propõe melhorias e avisa se vir defeito. Quem vir defeito e souber corrigir **pede o
> okay** à orquestradora antes de mexer — fora da própria fronteira, ninguém corrige sozinho.

## A regra que evita destruição mútua

Cada executor tem **fronteira de escrita exclusiva**. Ninguém toca arquivo de outro. Os dois
arquivos que todos leem e **ninguém edita sem okay** são `bin/iachat` e `bin/iachat_core.py` —
o núcleo. Mudança neles passa pela orquestradora, porque uma alteração de formato ali quebra o
histórico de todo mundo (provado hoje: mudança no `RE_META` passou nos 10 gates e apagou 100%
da sala real).

## As seis partes

| # | executor | parte | fronteira de escrita |
|---|---|---|---|
| 1 | **codex** | `ia-thread` — encadeamento (`re: #N`), ler um fio sem ler a sala | `skills/ia-thread/` · `bin/iachat-thread*` · `tests/teste_thread.py` |
| 2 | **kimi** | `ia-doctor` — diagnóstico da instalação em todas as cascas | `skills/ia-doctor/` · `bin/iachat-doctor*` · `tests/teste_doctor.py` |
| 3 | **grok** | `ia-guard` + `ia-budget` — disciplina de escrita e telemetria de consumo | `skills/ia-guard/` · `skills/ia-budget/` · `bin/iachat-guard*` · `bin/iachat-budget*` · `tests/teste_guard.py` |
| 4 | **qwclaude** | `ia-vacuum` — limpeza com retenção e dry-run | `skills/ia-vacuum/` · `bin/iachat-vacuum*` · `tests/teste_vacuum.py` |
| 5 | **ollama kimi-k3** | **validação e documentação** — rodar toda a bateria, conferir doc × CLI, escrever o `CHANGELOG.md` | `CHANGELOG.md` · `auditorias/2026-08-17-fase6/validacao-final.md` |
| 6 | **claude** (orquestradora) | `ia-report`, integração, gates, revisão de tudo | núcleo, README, integração |

## O que cada um entrega (igual para todos)

1. **Implementação** que roda, dentro da fronteira.
2. **Teste** no estilo dos existentes (função `checa()`, saída ✔/✗, exit 0/1) — incluindo o
   caso que **reprova**, porque gate que nunca viu vermelho não é gate.
3. **Validação**: rodar a bateria inteira do repo e provar que nada regrediu.
4. **Documentação**: `SKILL.md` com frontmatter mínimo (`name` + `description`) e o comando
   real; se mudar comportamento documentado em outro lugar, **avisar** (não editar).
5. **Sugestões de melhoria** — separadas do que foi pedido.
6. **Avisos de defeito** — com `arquivo:linha` e cenário. Se souber corrigir e for **fora da
   sua fronteira**, peça o okay pela sala (`iachat post --de <você> --para claude`).

## Base já escrita — leia antes de projetar do zero

Cada peça já tem proposta completa, com `SKILL.md`, nota de custo e protótipo, em
`auditorias/2026-08-17-fase6/propostas-casa/<peça>/`. Onde a proposta estiver certa, siga; onde
estiver errada, corrija **e diga por quê**. Não recomece do zero sem motivo.

## Anti-redundância

`auditorias/2026-08-17-fase6/JA-EXISTE.md` lista tudo que já existe, já foi proposto e já foi
**descartado com medida**. Ressuscitar ideia descartada exige número novo.
