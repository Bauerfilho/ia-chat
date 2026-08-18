#!/usr/bin/env bash
# iachat-despacho.sh — o braço que EXECUTA um pedido de plano numa IA da frota.
#
# Uso: iachat-despacho.sh <braco> <missao> <prompt.txt> <log> <plano-saida.md>
#      iachat-despacho.sh --vigiar <pid> <plano> <log>
#
# O `<missao>` vai na linha de comando DE PROPÓSITO: é a marca que o `iachat-comando
# parar` procura em `ps -o command=` antes de matar. Sem ela, matar por PID é apostar
# que o número não foi reciclado — e PID reciclado é o pior desfecho de um /parar.
#
# Adaptadores portados de ~/.claude/scripts/iaswarm/dispatch.sh:37-127 (os mesmos que
# rodaram a frota nas fases 6-7). Duas lições vêm junto do código de lá:
#   1. Casca Claude Code (qwclaude/dsclaude) SEM --append-system-prompt autônomo entra em
#      modo conversa e devolve "me diga o objetivo" — medido 17/08 (dispatch.sh:16-20).
#   2. `kimi -p` NÃO combina com `--auto` (erro explícito, medido 18/08). `kimi -p`
#      sozinho pendurou 25s no hook UserPromptSubmit. Autônomo = tmux + `kimi --auto`.
#
# Este script roda em sessão própria (o chamador usa setsid): matar o grupo mata a
# árvore inteira. Matar só a casca deixaria o `codex`/`agy` filho vivo — que foi
# exatamente a dor da madrugada de 18/08.
#
# Teto CPU+escrita (18/08): o /plan recusa com worker "vivo", e vivo() só olha PID.
# sleep medido → 0,0% CPU; busy-loop → 96–99%; iacmd-m2 ficou 1h a 0,0% no prompt `>`
# depois de entregar. Sinal = CPU da árvore + mtime/tamanho do plano/log (+ hash do
# pane, na Kimi). Avisa aos 8 min; mata aos 12. Quem pensa (CPU ou pane/log andando)
# não toma o tiro. Teste injeta IACHAT_PENDURADO_SEG=3.
set -uo pipefail

PEND_SEG="${IACHAT_PENDURADO_SEG:-720}"
AVISO_SEG="${IACHAT_PENDURADO_AVISO_SEG:-480}"
CPU_LIMIAR="${IACHAT_PENDURADO_CPU:-1.0}"
case "$PEND_SEG" in ''|*[!0-9]*) PEND_SEG=720 ;; esac
case "$AVISO_SEG" in ''|*[!0-9]*) AVISO_SEG=480 ;; esac
[ "$PEND_SEG" -ge 1 ] || PEND_SEG=720
VIGIA_SESSAO=""

cpu_arvore() {
  python3 - "$1" <<'PY'
import subprocess, sys
raiz = int(sys.argv[1])
r = subprocess.run(["ps", "-Ao", "pid=,ppid=,pcpu="], capture_output=True, text=True)
filhos, cpus = {}, {}
for ln in r.stdout.splitlines():
    p = ln.split()
    if len(p) < 3:
        continue
    try:
        pid, ppid, cpu = int(p[0]), int(p[1]), float(p[2].replace(",", "."))
    except ValueError:
        continue
    filhos.setdefault(ppid, []).append(pid)
    cpus[pid] = cpu
seen, stack, mx = set(), [raiz], 0.0
while stack:
    p = stack.pop()
    if p in seen:
        continue
    seen.add(p)
    mx = max(mx, cpus.get(p, 0.0))
    stack.extend(filhos.get(p, []))
print(f"{mx:.2f}")
PY
}

assinatura_escrita() {
  python3 - "${PLANO:-}" "${LOG:-}" <<'PY'
import os, sys
out = []
for p in sys.argv[1:]:
    if not p:
        out.append("-:0:0")
        continue
    try:
        st = os.stat(p)
        out.append(f"{p}:{st.st_size}:{int(st.st_mtime)}")
    except OSError:
        out.append(f"{p}:0:0")
print("|".join(out))
PY
}

pane_hash() {
  [ -n "${VIGIA_SESSAO:-}" ] || { echo ""; return 0; }
  tmux capture-pane -t "$VIGIA_SESSAO" -p 2>/dev/null | cksum | awk '{print $1"-"$2}'
}

marca_vigia() {
  local dest="${LOG%.log}.vigia"
  mkdir -p "$(dirname "$dest")" 2>/dev/null || true
  printf '%s\n' "$1" >> "$dest"
  printf '%s\n' "$1" >&2
}

mata_arvore() {
  python3 - "$1" <<'PY'
import os, signal, subprocess, sys, time
raiz = int(sys.argv[1])
r = subprocess.run(["ps", "-Ao", "pid=,ppid="], capture_output=True, text=True)
filhos = {}
for ln in r.stdout.splitlines():
    p = ln.split()
    if len(p) >= 2 and p[0].isdigit() and p[1].isdigit():
        filhos.setdefault(int(p[1]), []).append(int(p[0]))
seen, stack, ordem = set(), [raiz], []
while stack:
    p = stack.pop()
    if p in seen:
        continue
    seen.add(p)
    for k in filhos.get(p, []):
        ordem.append(k)
        stack.append(k)
for sig in (signal.SIGTERM, signal.SIGKILL):
    for p in reversed(ordem + [raiz]):
        try:
            os.kill(p, sig)
        except OSError:
            pass
    if sig == signal.SIGTERM:
        time.sleep(0.2)
PY
}

cpu_acima() {
  python3 - "${1:-0}" "${CPU_LIMIAR}" <<'PY'
import sys
try:
    cpu = float(sys.argv[1].replace(",", "."))
    lim = float(sys.argv[2].replace(",", "."))
except ValueError:
    raise SystemExit(1)
raise SystemExit(0 if cpu >= lim else 1)
PY
}

vigiar_pid() {
  local pid=$1 last_act now idle cpu sig last_sig pane last_pane aviso_feito=0 passo primeira=1 ativo
  last_act=$(date +%s)
  last_sig="$(assinatura_escrita)"
  last_pane="$(pane_hash)"
  if [ "$PEND_SEG" -le 20 ]; then passo=1; else passo=5; fi
  while kill -0 "$pid" 2>/dev/null; do
    [ -n "${PLANO:-}" ] && [ -s "$PLANO" ] && return 0
    cpu="$(cpu_arvore "$pid")"
    sig="$(assinatura_escrita)"
    pane="$(pane_hash)"
    now=$(date +%s)
    ativo=0
    if cpu_acima "${cpu:-0}"; then ativo=1; fi
    if [ "$sig" != "$last_sig" ]; then ativo=1; last_sig=$sig; fi
    if [ -n "${VIGIA_SESSAO:-}" ] && [ "$pane" != "$last_pane" ]; then ativo=1; last_pane=$pane; fi
    # Primeira amostra não conta: o ps do macOS atrasa o %cpu (medido: 0,1% no
    # primeiro instante de um loop que um segundo depois está a 97%). Sem esta
    # graça o detector mata quem acabou de começar a pensar.
    if [ "$primeira" -eq 1 ]; then
      last_act=$now
      primeira=0
    elif [ "$ativo" -eq 1 ]; then
      last_act=$now
    fi
    idle=$((now - last_act))
    if [ "$AVISO_SEG" -ge 1 ] && [ "$idle" -ge "$AVISO_SEG" ] && [ "$aviso_feito" -eq 0 ]; then
      marca_vigia "AVISO: pid $pid sem CPU>=${CPU_LIMIAR}% e sem escrita há ${idle}s; mata aos ${PEND_SEG}s"
      aviso_feito=1
    fi
    if [ "$idle" -ge "$PEND_SEG" ]; then
      marca_vigia "PENDURADO: pid $pid sem CPU>=${CPU_LIMIAR}% e sem escrita há ${idle}s (teto ${PEND_SEG}s, medido 18/08)"
      return 1
    fi
    sleep "$passo"
  done
  return 0
}

if [ "${1:-}" = "--vigiar" ]; then
  [ "$#" -eq 4 ] || { echo "uso: $0 --vigiar <pid> <plano> <log>" >&2; exit 2; }
  case "$2" in ''|*[!0-9]*) echo "pid inválido: $2" >&2; exit 2 ;; esac
  PLANO=$3
  LOG=$4
  if vigiar_pid "$2"; then
    exit 0
  fi
  exit 4
fi

BRACO="${1:?braco}"; MISSAO="${2:?missao}"; PROMPT="${3:?prompt}"; LOG="${4:?log}"; PLANO="${5:?plano}"

[ -f "$PROMPT" ] || { echo "prompt inexistente: $PROMPT" >&2; exit 2; }
P="$(cat "$PROMPT")"

# Sobrepõe a doutrina de conversa da casa só para este worker (dispatch.sh:20).
AUTONOMO='Você é um WORKER DE PLANEJAMENTO em modo não-interativo. NÃO existe humano nesta sessão: ninguém vai responder pergunta sua. NÃO peça esclarecimento, NÃO peça aprovação, NÃO proponha plano para aprovação — o plano PEDIDO é a entrega. Execute o pedido do começo ao fim e escreva o arquivo pedido. Se algo estiver ambíguo, escolha a interpretação mais conservadora, ANOTE a escolha no plano e siga. Sua sessão só termina depois de o arquivo de plano existir no disco.'

executa_e_vigia() {
  "$@" < /dev/null > "$LOG" 2>&1 &
  local child=$!
  if ! vigiar_pid "$child"; then
    mata_arvore "$child"
    exit 4
  fi
  wait "$child" || true
}

case "$BRACO" in
  codex)     executa_e_vigia codex exec "$P" ;;
  qwen)      executa_e_vigia env QWEN_CODE_SUPPRESS_YOLO_WARNING=1 qwen -y -p "$P" ;;
  qwclaude)  executa_e_vigia qwclaude -p "$P" --permission-mode bypassPermissions \
               --append-system-prompt "$AUTONOMO" ;;
  dsclaude)  executa_e_vigia deepseek-claude -p "$P" --permission-mode bypassPermissions \
               --append-system-prompt "$AUTONOMO" ;;
  agy)       executa_e_vigia agy --effort high --print-timeout 20m --dangerously-skip-permissions \
               -p "$P" ;;
  grok)      executa_e_vigia grok -p "$P" --dangerously-skip-permissions ;;
  ollama|ollama:*)
    MODELO="${BRACO#ollama}"; MODELO="${MODELO#:}"; MODELO="${MODELO:-qwen2.5-coder:32b}"
    (
      printf '%s\n\nEscreva o plano completo APÓS uma linha contendo apenas [PLANO].\n' "$P" \
        | ollama run "$MODELO" > "$LOG" 2>"${LOG%.log}.err"
      awk '/^\[PLANO\]/{f=1;next} f' "$LOG" > "$PLANO" || true
    ) &
    child=$!
    if ! vigiar_pid "$child"; then
      mata_arvore "$child"
      exit 4
    fi
    wait "$child" || true
    ;;
  kimi)
    # A Kimi só produz por sessão tmux. Medido 18/08 (contrato K):
    #   `kimi --auto -p` → "Cannot combine --prompt with --auto" (rc=1)
    #   `kimi -p`        → pendurou 25s no hook UserPromptSubmit; não é single-turn
    #                      confiável nesta máquina.
    #   `tmux` + `kimi --auto` → iacmd-m2 escreveu planos/kimi.md sem humano.
    # Sem `--auto` a TUI pede aprovação a cada ferramenta e espera um humano
    # que não vai chegar — foi o que travou o /plan do dono.
    # IACHAT_KIMI: caminho absoluto da casca (teste injeta um mock; produção = kimi).
    KIMI_CMD="${IACHAT_KIMI:-kimi}"
    S="iacmd-${MISSAO}"
    tmux kill-session -t "$S" 2>/dev/null || true
    # Sem trap, o despacho pode sair e a sessão fica no prompt `>` a 0% CPU
    # (medido: iacmd-m2 viva 1h depois do plano, pids 21618/21767 a 0,0%).
    trap 'tmux kill-session -t "$S" 2>/dev/null || true' EXIT
    tmux new-session -d -s "$S" -x 200 -y 50 "cd '$(dirname "$PLANO")' && \"$KIMI_CMD\" --auto"
    BOOT_SEG="${IACHAT_KIMI_BOOT_SEG:-20}"
    POLL_SEG="${IACHAT_KIMI_POLL_SEG:-15}"
    [ "$BOOT_SEG" -ge 0 ] 2>/dev/null || BOOT_SEG=20
    [ "$POLL_SEG" -ge 1 ] 2>/dev/null || POLL_SEG=15
    sleep "$BOOT_SEG"
    tmux capture-pane -t "$S" -p > "${LOG%.log}-boot.txt" 2>/dev/null || true
    # grep num ARQUIVO, nunca num pipe: `grep -q` sob pipefail já negou um daemon vivo
    # por SIGPIPE nesta casa (BRIEFING.md, defeitos vividos).
    if grep -q "Trust this folder" "${LOG%.log}-boot.txt" 2>/dev/null; then
      tmux send-keys -t "$S" Up; sleep 1; tmux send-keys -t "$S" Enter; sleep "$BOOT_SEG"
    fi
    tmux send-keys -t "$S" "$P" Enter
    sleep 1; tmux send-keys -t "$S" Enter   # o primeiro Enter morre no menu (lição 15/08)
    VIGIA_SESSAO=$S
    PP=$(tmux list-panes -t "$S" -F '#{pane_pid}' 2>/dev/null | head -1)
    (
      while tmux has-session -t "$S" 2>/dev/null; do
        [ -s "$PLANO" ] && exit 0
        if tmux capture-pane -t "$S" -p 2>/dev/null | grep -q "Approve"; then
          tmux send-keys -t "$S" 2; sleep 1; tmux send-keys -t "$S" Enter
        fi
        sleep "$POLL_SEG"
      done
    ) &
    BABA=$!
    if [ -n "${PP:-}" ] && ! vigiar_pid "$PP"; then
      kill "$BABA" 2>/dev/null || true
      tmux kill-session -t "$S" 2>/dev/null || true
      exit 4
    fi
    kill "$BABA" 2>/dev/null || true
    wait "$BABA" 2>/dev/null || true
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
