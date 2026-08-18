#!/bin/bash
# ia-server-connection-install.sh [intervalo] — sobe o sino da INFRAESTRUTURA como LaunchAgent.
#
# Uso:  ia-server-connection-install.sh [intervalo]   # padrão 20s
#       ia-server-connection-install.sh --parar
#
# LaunchAgent, e não `&`: em 17/08 os vigias nasceram como background de uma sessão e
# foram mortos junto com ela, às 01:40, com o dono dormindo. Um vigia que depende de quem
# ele vigia não é vigia. Vale em dobro aqui: este existe justamente para o momento em que
# tudo cai.
set -euo pipefail

LABEL="com.bauer.ia-server-connection"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
SALA="${IACHAT_HOME:-$HOME/ia-chat-global}"

if [ "${1:-}" = "--parar" ]; then
  launchctl unload "$PLIST" 2>/dev/null || true
  rm -f "$PLIST"
  echo "✔ vigília de conexão (energy-bell + connection-bell) desligado"
  exit 0
fi

INTERVALO="${1:-20}"
SCRIPT="${IACHAT_SCRIPTS:-$HOME/.claude/scripts/ia-chat}/ia-server-connection-daemon.sh"
[ -x "$SCRIPT" ] || { echo "✗ não achei $SCRIPT — rode o install.sh primeiro" >&2; exit 2; }

mkdir -p "$SALA/rede"

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
    <string>$INTERVALO</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict><key>IACHAT_HOME</key><string>$SALA</string></dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$SALA/ia-server-connection.out</string>
  <key>StandardErrorPath</key><string>$SALA/ia-server-connection.err</string>
  <key>WorkingDirectory</key><string>$HOME</string>
</dict>
</plist>
PLISTEOF

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
sleep 1

# `| grep -q` aqui daria FALSO NEGATIVO: o grep sai no primeiro casamento, o pipe fecha,
# o launchctl morre de SIGPIPE (141) e o `pipefail` reporta o pipeline como falho — o
# daemon SOBE e o instalador jura que não. Medido em 17/08 no sino do kimi.
VIVO="$(launchctl list 2>/dev/null | grep "$LABEL" || true)"
if [ -n "$VIVO" ]; then
  echo "✔ vigília de conexão (energy-bell + connection-bell) no ar (a cada ${INTERVALO}s)"
  echo "  vigia: energia (pmset) · IP (en0) · alcance de rede"
  echo "  eventos: $SALA/rede/EVENTOS.md"
else
  echo "✗ não subiu — veja $SALA/ia-server-connection.err" >&2
  exit 1
fi
