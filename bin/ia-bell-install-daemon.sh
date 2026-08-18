#!/bin/bash
# ia-bell-install-daemon.sh <ia> [intervalo] — sobe o sino de uma casca como LaunchAgent.
#
# LaunchAgent, e não `&`: em 17/08 os vigias nasceram como background de uma sessão e
# foram MORTOS junto com ela, às 01:40, com o Bauer dormindo. Sino que morre com quem o
# criou não é sino.
#
# KeepAlive é TRUE aqui (ao contrário do vigia de janela, que sai de propósito ao avisar):
# o sino é permanente — cada nova mensagem precisa tocar.
set -euo pipefail
IA="${1:?uso: ia-bell-install-daemon.sh <ia> [intervalo]}"
INTERVALO="${2:-15}"
SCRIPT="${IACHAT_SCRIPTS:-$HOME/.claude/scripts/ia-chat}/ia-bell-daemon.sh"
SALA="${IACHAT_HOME:-$HOME/ia-chat-global}"
NOME="${IA#--}"   # `--operador` vira `operador`: label e log legíveis
LABEL="com.bauer.ia-bell-$NOME"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

[ -x "$SCRIPT" ] || { echo "✗ não achei $SCRIPT — rode o install.sh primeiro" >&2; exit 2; }

cat >"$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$SCRIPT</string>
    <string>$IA</string>
    <string>$INTERVALO</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict><key>IACHAT_HOME</key><string>$SALA</string></dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$SALA/ia-bell-$NOME.out</string>
  <key>StandardErrorPath</key><string>$SALA/ia-bell-$NOME.err</string>
  <key>WorkingDirectory</key><string>$HOME</string>
</dict>
</plist>
PLISTEOF

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
sleep 1
# `| grep -q` aqui daria FALSO NEGATIVO: o grep sai no primeiro casamento, o pipe fecha,
# o launchctl morre de SIGPIPE (141) e o `pipefail` reporta o pipeline como falho — o
# daemon SOBE e o instalador jura que não. Medido em 17/08 no sino do kimi. Capturar a
# saída inteira antes de julgar não tem essa armadilha.
VIVO="$(launchctl list | grep "$LABEL" || true)"
if [ -n "$VIVO" ]; then
  echo "✔ sino de $IA no ar ($LABEL, cada ${INTERVALO}s)"
  echo "  log:      $SALA/ia-bell-$NOME.log"
  echo "  derrubar: launchctl unload $PLIST"
else
  echo "✗ o LaunchAgent não subiu — ver $SALA/ia-bell-$NOME.err" >&2
  exit 1
fi
