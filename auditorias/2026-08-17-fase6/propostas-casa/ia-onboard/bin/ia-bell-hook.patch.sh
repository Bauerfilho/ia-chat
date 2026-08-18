#!/bin/bash
# PATCH PROPOSTO para bin/ia-bell-hook.sh — NÃO aplicado (regra do briefing: não escrever
# no repositório). Este arquivo é a diferença, executável isolada para teste.
#
# POR QUE. O hook de hoje sai na linha 19 quando não há flag em pendente/:
#     [ -f "$SALA/pendente/$IA.md" ] || exit 0
# Um recém-chegado NUNCA tem flag — ninguém o nominou ainda, e nominar exige que já
# soubessem que ele entrou. Ou seja: a IA nova é invisível para todo o mecanismo de
# entrega. Ela só descobre a sala se um humano mandar.
#
# O bloco abaixo entra ANTES da linha 19 e custa o mesmo que ela: um `test -f`.
# Auto-extinguível: depois da primeira entrega o arquivo de cursor existe e o teste falha
# para sempre. `--marcar` grava cursor #0, que é o MESMO estado que a ausência do arquivo
# (iachat_core.py:301-306) — nenhum `read` posterior muda de comportamento.

set -u
IA="${IACHAT_EU:-${1:-}}"
[ -n "$IA" ] || exit 0
SALA="${IACHAT_HOME:-$HOME/ia-chat-global}"

ONBOARD="${IACHAT_BIN:-$HOME/.local/bin}/iachat-onboard"

# ── bloco novo ────────────────────────────────────────────────────────────────
# primeira vez desta IA na sala: entrega o briefing e some
if [ ! -f "$SALA/cursor/$IA.json" ] && [ -x "$ONBOARD" ]; then
    "$ONBOARD" briefing --de "$IA" --marcar 2>/dev/null
fi
# ── fim do bloco novo ─────────────────────────────────────────────────────────

[ -f "$SALA/pendente/$IA.md" ] || exit 0

IACHAT="${IACHAT_BIN:-$HOME/.local/bin}/iachat"
[ -x "$IACHAT" ] || IACHAT="$HOME/.claude/scripts/ia-chat/iachat"
"$IACHAT" entregar --de "$IA" 2>/dev/null
