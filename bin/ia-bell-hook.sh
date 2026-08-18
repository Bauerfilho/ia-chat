#!/bin/bash
# ia-bell-hook.sh — ENTREGA a mensagem dentro da sessão aberta, não avisa que existe.
#
# Uso em hook (SessionStart, UserPromptSubmit ou equivalente):
#   IACHAT_EU=claude ia-bell-hook.sh
#
# Por que entregar em vez de avisar: avisar obriga a IA a parar, lembrar do comando e
# gastar uma ida ao disco — e a IA que está no meio de um raciocínio simplesmente não
# vai. Entregar põe a mensagem no contexto dela de graça, no evento que ela já ia gerar.
#
# E entrega SÓ o que é dela: a conversa entre as outras fica oculta. É isso que permite
# o chat ser grande — o custo de receber deixou de depender do tamanho do histórico.
#
# Barato por desenho: sem flag, não imprime NADA e sai 0 — um `test -f` por evento.
set -u
IA="${IACHAT_EU:-${1:-}}"
[ -n "$IA" ] || exit 0
SALA="${IACHAT_HOME:-$HOME/ia-chat-global}"
[ -f "$SALA/pendente/$IA.md" ] || exit 0

IACHAT="${IACHAT_BIN:-$HOME/.local/bin}/iachat"
[ -x "$IACHAT" ] || IACHAT="$HOME/.claude/scripts/ia-chat/iachat"
"$IACHAT" entregar --de "$IA" 2>/dev/null
