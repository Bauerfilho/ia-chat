# A2 · kimi — portabilidade real entre cascas

Leia `~/.claude/iaswarm-runs/ia-chat-fase6/BRIEFING.md` antes de tudo.

**Missão:** você é a única que pode medir isto de dentro. O `ia-chat` promete funcionar em
qualquer casca; prove onde funciona e onde quebra, **medindo na sua**, e mapeie o que falta para
as outras entrarem na sala.

**Fronteira:** leitura do repo; escrita SÓ em `resultados/a2-kimi.md` e
`resultados/skills-propostas/`.

## ETAPAS (5, verificáveis)

1. **Na sua própria casca:** as 7 skills `ia-*` aparecem no seu catálogo? Liste as que aparecem e
   as que não. Diga o caminho de onde vieram e como você confirmou (não confie no disco — confira
   o catálogo exposto à sessão).
2. **O hook seu:** `~/.kimi-code/config.toml` tem `[[hooks]]` de `ia-bell-hook.sh` em
   `SessionStart` e `UserPromptSubmit`. Ele disparou nesta sessão? Se não, por quê (compare mtime
   do config com o início da sua sessão). Teste o comando isolado com `IACHAT_HOME` de teste.
3. **O CLI:** `iachat status`, `read`, `post`, `search`, `page` — todos respondem na sua casca?
   Colar saída real. Alguma dependência que a sua casca não tem?
4. **As outras cascas** (`qwen`, `grok`, `agy`, `ollama`, `hermes`): para cada uma, descubra e
   registre — onde ficam as skills, se há mecanismo de hook, se `~/.local/bin` está no PATH dela,
   e **o que exatamente seria preciso** para ela entrar na sala. Não chute: leia config/binário.
5. **Escrever `resultados/a2-kimi.md`** com uma tabela casca × (skill · hook · CLI · daemon) e,
   para cada ✗, o passo concreto que resolveria. Proponha, se fizer sentido, **uma peça nova** com
   nome próprio que torne a instalação multi-casca confiável (escreva o SKILL.md em
   `resultados/skills-propostas/`).
