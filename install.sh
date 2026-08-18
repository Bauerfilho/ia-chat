#!/bin/bash
# ia-chat — instalador (Claude Code + Kimi por padrão; destinos customizáveis por env)
#   IACHAT_SCRIPTS  (default: ~/.claude/scripts/ia-chat)
#   IACHAT_SKILLS   (default: ~/.claude/skills)        ← o Kimi já lê esta pasta
#   IACHAT_BIN      (default: ~/.local/bin)            ← precisa estar no PATH
#   IACHAT_HOME     (default: ~/ia-chat-global)        ← os dados da sala
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
DEST_SCRIPTS="${IACHAT_SCRIPTS:-$HOME/.claude/scripts/ia-chat}"
DEST_SKILLS="${IACHAT_SKILLS:-$HOME/.claude/skills}"
DEST_BIN="${IACHAT_BIN:-$HOME/.local/bin}"
SALA="${IACHAT_HOME:-$HOME/ia-chat-global}"

mkdir -p "$DEST_SCRIPTS" "$DEST_SKILLS" "$DEST_BIN"
cp "$SRC/bin/iachat" "$SRC/bin/iachat_core.py" "$DEST_SCRIPTS/"
# Os auxiliares por GLOB ABERTO (`bin/ia-*`), não por lista nem por padrão temático.
# Em 18/08 isto falhou TRÊS vezes seguidas: primeiro a lista explícita esqueceu os
# `ia-network-bell-*`; troquei por `ia-*bell*` achando que tinha resolvido a classe; e na
# hora seguinte a peça foi renomeada para `ia-server-connection-*` — sem "bell" no nome —
# e o glob esperto errou igual. Padrão que codifica o NOME DE HOJE quebra no rename.
# `ia-*` pega todo auxiliar presente e futuro; os CLIs (`iachat-*`) vão logo abaixo.
for aux in "$SRC"/bin/ia-*; do [ -f "$aux" ] && cp "$aux" "$DEST_SCRIPTS/"; done
# Os CLIs das peças (iachat-claim, iachat-recibo, iachat-thread, …) também vão. Sem isto,
# a skill ensina um comando que não existe no PATH: medido em 17/08 (achado da kimi) — 8
# CLIs no repo, 8 sem resolver, e 8 skills chamando-os pelo nome. Documentação que ensina
# comando quebrado é pior que documentação nenhuma.
for extra in "$SRC"/bin/iachat-*; do [ -f "$extra" ] && cp "$extra" "$DEST_SCRIPTS/"; done
chmod +x "$DEST_SCRIPTS/iachat" "$DEST_SCRIPTS"/ia-*.sh 2>/dev/null
chmod +x "$DEST_SCRIPTS"/iachat-* 2>/dev/null
ln -sf "$DEST_SCRIPTS/iachat" "$DEST_BIN/iachat"
for extra in "$DEST_SCRIPTS"/iachat-*; do
  [ -f "$extra" ] && [ -x "$extra" ] && ln -sf "$extra" "$DEST_BIN/$(basename "$extra")"
done

for s in "$SRC"/skills/*/; do
  n="$(basename "$s")"
  mkdir -p "$DEST_SKILLS/$n"
  cp "$s/SKILL.md" "$DEST_SKILLS/$n/"
done

IACHAT_HOME="$SALA" "$DEST_SCRIPTS/iachat" status >/dev/null   # cria a sala se não existe

echo "✔ CLI      $DEST_BIN/iachat  →  $DEST_SCRIPTS/iachat"
echo "✔ skills   $DEST_SKILLS/ia-*  ($(ls -d "$SRC"/skills/*/ | wc -l | tr -d ' ') instaladas)"
echo "✔ sala     $SALA"
echo
echo "Claude Code: já vê as skills em $DEST_SKILLS."
if grep -q "$DEST_SKILLS" "$HOME/.kimi-code/config.toml" 2>/dev/null; then
  echo "Kimi:        já lê $DEST_SKILLS (extra_skill_dirs) — nada a fazer."
else
  echo "Kimi:        adicione em ~/.kimi-code/config.toml:"
  echo "             extra_skill_dirs = [ \"$DEST_SKILLS\" ]"
fi
cat <<'AVISO'
Codex:       as skills entram por diretório (aceita symlink):
               ln -s ~/.claude/skills/ia-chat-activate ~/.codex/skills/ia-chat-activate
             ⚠️ se for MEXER em ~/.codex/hooks.json, o `trusted_hash` é invalidado e o
             Codex passa a PULAR o hook em silêncio — ele precisa re-aprovar na próxima
             abertura. Este instalador nunca fabrica hash nem edita hooks.json.
AVISO
