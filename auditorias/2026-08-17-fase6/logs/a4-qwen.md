# A4 · qwen — limpeza automática e skills de orquestrador

Leia `~/.claude/iaswarm-runs/ia-chat-fase6/BRIEFING.md` antes de tudo.

**Missão:** dois eixos que o dono pediu — (3) automatizar a limpeza dos backups, (4) as skills do
orquestrador, que hoje **não existem** (nenhuma das 7 serve para comandar outras IAs).

**Fronteira:** leitura do repo e da casa; escrita SÓ em `resultados/a4-qwen.md` e
`resultados/skills-propostas/`.

## ETAPAS (5, verificáveis)

1. **Inventariar o lixo que o plugin gera.** Conte no disco: `.bak-*` criados pelos instaladores
   (`~/.claude/settings.json.bak-iachat-*`, `~/.kimi-code/config.toml.bak-iachat-*`), logs de
   daemon em `~/ia-chat-global/`, `.tmp` órfãos, flags em `pendente/` sem dono, recortes em
   `arquivo/`. Números reais.
2. **Estudar o que a casa já faz** — `~/.claude/scripts/backup.sh`, `backup-claude.sh` e os
   LaunchAgents de manutenção. Não copie: entenda a política (o que guarda, por quanto tempo,
   como evita apagar o que importa) e materialize uma versão **do plugin**, com nome próprio.
3. **Projetar a peça de limpeza:** política de retenção declarada, **dry-run obrigatório**,
   idempotente, nunca apaga sem log, nunca apaga backup do mesmo dia. Escreva o `SKILL.md` e um
   protótipo executável; teste o protótipo em `IACHAT_HOME` de teste com lixo fabricado.
4. **Projetar as skills de orquestrador.** O dono citou: despachar missão para várias IAs pela
   sala; **mandar comando direto em modo `/plan` para outra IA**; e rotação/fallback quando a IA
   chamada não responde. Descubra como cada casca aceita comando não-interativo (`codex exec`,
   `kimi -p`, `qwen -p`, `grok`, `agy`) e o que cada uma faz com "modo plan". Proponha as peças
   com nome próprio e SKILL.md.
5. **Escrever `resultados/a4-qwen.md`** — inventário com números, a peça de limpeza (com saída
   real do dry-run) e as peças de orquestração, cada uma com risco declarado.
