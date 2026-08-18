#!/usr/bin/env bash
# iachat-despacho.sh — o braço que EXECUTA um pedido de plano numa IA da frota.
#
# Uso: iachat-despacho.sh <braco> <missao> <prompt.txt> <log> <plano-saida.md>
#
# O `<missao>` vai na linha de comando DE PROPÓSITO: é a marca que o `iachat-comando
# parar` procura em `ps -o command=` antes de matar. Sem ela, matar por PID é apostar
# que o número não foi reciclado — e PID reciclado é o pior desfecho de um /parar.
#
# Adaptadores portados de ~/.claude/scripts/iaswarm/dispatch.sh:37-127 (os mesmos que
# rodaram a frota nas fases 6-7). Duas lições vêm junto do código de lá:
#   1. Casca Claude Code (qwclaude/dsclaude) SEM --append-system-prompt autônomo entra em
#      modo conversa e devolve "me diga o objetivo" — medido 17/08 (dispatch.sh:16-20).
#   2. `kimi -p` não escreve arquivo; a Kimi só produz por sessão tmux (dispatch.sh:67).
#
# Este script roda em sessão própria (o chamador usa setsid): matar o grupo mata a
# árvore inteira. Matar só a casca deixaria o `codex`/`agy` filho vivo — que foi
# exatamente a dor da madrugada de 18/08.
set -uo pipefail

BRACO="${1:?braco}"; MISSAO="${2:?missao}"; PROMPT="${3:?prompt}"; LOG="${4:?log}"; PLANO="${5:?plano}"

[ -f "$PROMPT" ] || { echo "prompt inexistente: $PROMPT" >&2; exit 2; }
P="$(cat "$PROMPT")"

# Sobrepõe a doutrina de conversa da casa só para este worker (dispatch.sh:20).
AUTONOMO='Você é um WORKER DE PLANEJAMENTO em modo não-interativo. NÃO existe humano nesta sessão: ninguém vai responder pergunta sua. NÃO peça esclarecimento, NÃO peça aprovação, NÃO proponha plano para aprovação — o plano PEDIDO é a entrega. Execute o pedido do começo ao fim e escreva o arquivo pedido. Se algo estiver ambíguo, escolha a interpretação mais conservadora, ANOTE a escolha no plano e siga. Sua sessão só termina depois de o arquivo de plano existir no disco.'

case "$BRACO" in
  codex)     codex exec "$P" > "$LOG" 2>&1 ;;
  qwen)      QWEN_CODE_SUPPRESS_YOLO_WARNING=1 qwen -y -p "$P" > "$LOG" 2>&1 ;;
  qwclaude)  qwclaude -p "$P" --permission-mode bypassPermissions \
               --append-system-prompt "$AUTONOMO" < /dev/null > "$LOG" 2>&1 ;;
  dsclaude)  deepseek-claude -p "$P" --permission-mode bypassPermissions \
               --append-system-prompt "$AUTONOMO" < /dev/null > "$LOG" 2>&1 ;;
  agy)       agy --effort high --print-timeout 20m --dangerously-skip-permissions \
               -p "$P" < /dev/null > "$LOG" 2>&1 ;;
  grok)      grok -p "$P" --dangerously-skip-permissions < /dev/null > "$LOG" 2>&1 ;;
  ollama|ollama:*)
    # stdout puro: o plano é o que vier depois do marcador (dispatch.sh:95-108).
    MODELO="${BRACO#ollama}"; MODELO="${MODELO#:}"; MODELO="${MODELO:-qwen2.5-coder:32b}"
    printf '%s\n\nEscreva o plano completo APÓS uma linha contendo apenas [PLANO].\n' "$P" \
      | ollama run "$MODELO" > "$LOG" 2>"${LOG%.log}.err"
    awk '/^\[PLANO\]/{f=1;next} f' "$LOG" > "$PLANO" || true
    ;;
  kimi)
    # A Kimi só produz por sessão tmux; `kimi -p` é single-turn e não escreve (dispatch.sh:67).
    S="iacmd-${MISSAO}"
    tmux kill-session -t "$S" 2>/dev/null || true
    tmux new-session -d -s "$S" -x 200 -y 50 "cd '$(dirname "$PLANO")' && kimi"
    sleep 20
    tmux capture-pane -t "$S" -p > "${LOG%.log}-boot.txt" 2>/dev/null || true
    # grep num ARQUIVO, nunca num pipe: `grep -q` sob pipefail já negou um daemon vivo
    # por SIGPIPE nesta casa (BRIEFING.md, defeitos vividos).
    if grep -q "Trust this folder" "${LOG%.log}-boot.txt" 2>/dev/null; then
      tmux send-keys -t "$S" Up; sleep 1; tmux send-keys -t "$S" Enter; sleep 15
    fi
    tmux send-keys -t "$S" "$P" Enter
    sleep 3; tmux send-keys -t "$S" Enter   # o primeiro Enter morre no menu (lição 15/08)
    fim=$(( $(date +%s) + 1800 ))
    while [ "$(date +%s)" -lt "$fim" ]; do
      [ -s "$PLANO" ] && break
      tmux has-session -t "$S" 2>/dev/null || break
      if tmux capture-pane -t "$S" -p 2>/dev/null | grep -q "Approve"; then
        tmux send-keys -t "$S" 2; sleep 1; tmux send-keys -t "$S" Enter
      fi
      sleep 15
    done
    tmux capture-pane -t "$S" -p -S -500 > "$LOG" 2>/dev/null || true
    tmux kill-session -t "$S" 2>/dev/null || true
    ;;
  *)
    echo "braço sem adaptador: $BRACO (codex qwen kimi qwclaude dsclaude agy grok ollama)" >&2
    exit 3
    ;;
esac

# O plano é o artefato; log não é plano. Quem não escreveu o arquivo não entregou.
[ -s "$PLANO" ]
