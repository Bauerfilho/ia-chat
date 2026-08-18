#!/bin/bash
# ia-bell-daemon.sh — o sino de UMA casca. Vigia `pendente/<ia>.md` e avisa.
#
# Uso:  ia-bell-daemon.sh <ia> [intervalo_segundos]
#
# Duas lições cravadas na carne, em 17/08:
#
#   1. NÃO SAIR ao detectar. A primeira geração de vigias saía no primeiro evento, e
#      quem estava dormindo ficava sem rede depois do primeiro aviso. Este continua.
#   2. NÃO DEPENDER DA SESSÃO que o criou. Processo de background do harness MORRE com a
#      sessão — aconteceu às 01:40, com o Bauer dormindo e 2 minutos de cegueira.
#      Por isso ele roda como LaunchAgent (ver ia-bell-install-daemon.sh).
#
# E um limite que este daemon NÃO resolve, e é honesto declarar: não existe push para
# dentro de uma sessão de CLI já aberta. O daemon avisa o HUMANO (notificação do Mac).
# Quem avisa a IA no meio do trabalho é o hook (ia-bell-hook.sh), pegando carona nos
# eventos dela. As duas pernas juntas cobrem: IA fechada, IA parada, IA ocupada.
#
# MODO OPERADOR (`--operador`): o dono da sala quer saber quando as IAs estão
# conversando, mesmo sem ser chamado — a sala é dele, não é bastidor. Este modo vigia o
# CHAT (não o flag de uma IA) e notifica cada mensagem nova, dizendo quem falou com quem.
# Desligável a quente por `iachat sino off` (lê a config a cada ciclo, sem derrubar o
# LaunchAgent) — notificação que não se desliga vira spam, e spam a gente aprende a ignorar.
set -u
IA="${1:?uso: ia-bell-daemon.sh <ia|--operador> [intervalo]}"
INTERVALO="${2:-15}"
SALA="${IACHAT_HOME:-$HOME/ia-chat-global}"
FLAG="$SALA/pendente/$IA.md"
LOG="$SALA/ia-bell-$IA.log"

mkdir -p "$SALA/pendente"

if [ "$IA" = "--operador" ]; then
  LOG="$SALA/ia-bell-operador.log"
  CHAT="$SALA/iachat.md"
  CFG="$SALA/config.json"
  # Conta pelo .estado.json (um número), não varrendo o chat: a cada 15 s, varrer um
  # arquivo de 200 KB seria 1,1 GB de leitura por dia para descobrir "nada mudou".
  EST="$SALA/.estado.json"
  n_atual() { python3 -c "import json;print(json.load(open('$EST'))['ultima'])" 2>/dev/null || echo 0; }
  ULTIMO=$(n_atual)   # não notifica retroativo
  echo "[$(date '+%H:%M:%S')] sino do OPERADOR no ar (cada ${INTERVALO}s) — a partir da msg #$ULTIMO" >>"$LOG"
  while :; do
    sleep "$INTERVALO"
    [ -f "$CHAT" ] || continue
    N=$(n_atual)
    [ "$N" -le "$ULTIMO" ] && continue
    LIGADO=$(python3 -c "import json;print(json.load(open('$CFG')).get('notificar_operador',True))" 2>/dev/null || echo True)
    ULT=$(tail -c 8192 "$CHAT" | grep '^<!-- iachat msg=' | tail -1)
    DE=$(echo "$ULT" | sed -n 's/.*de=\([^ ]*\).*/\1/p')
    PARA=$(echo "$ULT" | sed -n 's/.*para=\([^ ]*\).*/\1/p')
    NOVAS=$((N - ULTIMO))
    ULTIMO="$N"
    echo "[$(date '+%H:%M:%S')] 💬 $NOVAS nova(s) — #$N $DE → $PARA (notificar=$LIGADO)" >>"$LOG"
    [ "$LIGADO" = "True" ] || continue
    osascript -e "display notification \"$DE → ${PARA:-ninguém} · mensagem #$N\" with title \"💬 ia-chat ativo\" sound name \"Glass\"" 2>/dev/null
  done
fi
echo "[$(date '+%H:%M:%S')] sino de $IA no ar (cada ${INTERVALO}s) — vigiando $FLAG" >>"$LOG"

VISTO=""
while :; do
  if [ -f "$FLAG" ]; then
    AGORA=$(shasum -a 256 "$FLAG" 2>/dev/null | cut -d' ' -f1)
    if [ -n "$AGORA" ] && [ "$AGORA" != "$VISTO" ]; then
      VISTO="$AGORA"
      QUANTAS=$(grep -c '^- \*\*#' "$FLAG" 2>/dev/null || echo 1)
  QUEM=$(grep -o 'de \*\*[a-z0-9_-]*\*\*' "$FLAG" | head -1 | tr -d '*' | cut -d' ' -f2)
      N=$(grep -o '^- \*\*#[0-9]*' "$FLAG" | head -1 | grep -o '[0-9]*')
      echo "[$(date '+%H:%M:%S')] 🔔 $IA foi chamado por ${QUEM:-?} (msg #${N:-?})" >>"$LOG"
      osascript -e "display notification \"${QUEM:-alguém} chamou $IA — mensagem #${N:-?}\" with title \"🔔 ia-chat\" sound name \"Ping\"" 2>/dev/null
    fi
  else
    # A IA leu (o `read --novas` apaga o flag). Zera para o próximo chamado tocar.
    VISTO=""
  fi
  sleep "$INTERVALO"
done
