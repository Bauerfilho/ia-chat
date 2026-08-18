# Fechar o omni na casca do Codex

Ordem do Bauer. Levantei o terreno para você não gastar contexto redescobrindo —
está tudo medido abaixo.

## Estado

Contagem direta em `~/.codex/hooks.json`: **11 hooks**, dos quais **4 são omni** —
todos de ciclo, via `omni_lifecycle_adapter.py`: `SessionStart` · `PreCompact` ·
`SessionEnd` · `SubagentStart`.

Faltam **5 eventos** do omni (a casa tem 9): `PreToolUse` · `PostToolUse` ·
`PostToolUseFailure` · `Notification` · `FileChanged`.

O `omni_lifecycle_adapter.py` só mapeia 3 flags (`--session-start`, `--pre-compact`,
`--hook`) e não tem as de tool: faltam `--pre-hook` e `--post-hook` (o que a casa usa
em `PreToolUse`/`PostToolUse`).

Dossiê completo, inclusive o estado do Kimi (7/9, teto real 8 porque `FileChanged`
não existe entre os 11 eventos do binário dele):
`~/.claude/iaswarm-runs/bauer-os-v1/PENDENCIA-OMNI-CASCAS.md`

## Não faça

- **Não substitua** os `PreToolUse`/`PostToolUse` que já existem — eles NÃO são omni:
  `PreToolUse` matcher=`Bash` → `pretool_context_adapter.py` (guard destrutivo + RTK);
  `PostToolUse` → `claude_mem_hook_adapter.py observation`. Substituir custa o guard
  destrutivo ou o claude-mem. **Adicione grupos novos.**
- **Não troque o binário.** O omni da sua casca não é o do homebrew: é
  `~/.codex/bauer-os/omni-candidate/target/release/omni`, cravado no adapter. Trocar
  para `/opt/homebrew/bin/omni` sem medir invalida tudo que você medir depois.
- **Não edite `~/.codex/hooks.json` e siga em frente.** Editar invalida o
  `trusted_hash` (três, em `~/.codex/config.toml:778,781,784`) e você passa a **pular
  hook em silêncio** até re-aprovar. Ordem certa: backup → editar → avisar o Bauer →
  ele re-aprova na próxima abertura → conferir que DISPAROU, não que o arquivo mudou.

## Decisões fechadas

**matcher = `Bash|Read|Grep|WebFetch`** nos hooks de tool. Já argumentei contra e o
Bauer reafirmou — não reabra. Argumentei que `Read`/`Grep`/`WebFetch` não existem na
sua casca (medi `exec` 1.307 chamadas contra 0 dessas três em 1.473) e que instalá-las
faria a contagem virar "9/9" com hooks natimortos. Palavra dele: *"acho grep, read e
webfetch úteis, acho que pode vir a ser útil, apesar dele ter tools semelhantes"*.
Está certa em custo: matcher que não casa não dispara, não custa nada, e fica armado
se a casca ganhar essas tools numa atualização.

Junto vai uma exigência de honestidade: **anote no arquivo que Read/Grep/WebFetch
estão armados-e-dormentes hoje.** Quem contar 9/9 daqui a um mês tem que saber que a
cobertura efetiva vem do `Bash` — é ele que casa com `exec`, e `cat`/`grep`/`curl` são
todos `exec`.

## Caminho sugerido (não é ordem)

Estender o `FLAGS` do `omni_lifecycle_adapter.py` para incluir
`pre-hook`/`post-hook`/`failure`/`notification`/`file-changed`, ou criar um
`omni_tool_adapter.py` no mesmo padrão. Reuse o wrapper existente: ele já resolve as
duas coisas que importam — `OMNI_AGENT_ID=codex` no env do subprocess e o
`suppressOutput` para não poluir a tela.

## Pronto quando

O banco do omni tem registro com `agent_id='codex'` depois de rodar uma tool real.

`Completed` no hook NÃO é prova: existe pendência aberta de 17/08 em que os hooks do
omni na sua casca retornavam `Completed` com o banco em ZERO para `agent_id='codex'`
(hipótese não fechada: `OMNI_AGENT_ID=codex` inline não virar env var de verdade).
Verde no instrumento + zero no artefato é o defeito mais caro que a gente tem aqui.
Se o banco continuar zerado depois dos hooks, o problema é upstream do hook e você
achou algo maior — isso também fecha o handoff, com a medição.

## Retorno esperado

Feche com a prova do banco (a linha/consulta que mostra `agent_id='codex'`), não com a
contagem de hooks.
