#!/bin/bash
# Teste do ia-faxina.py em sala fabricada — nunca toca a sala real.
# Fabrica lixo de cada categoria, roda dry-run, roda --aplicar, e confere
# invariante por invariante (o que some, o que NÃO pode sumir, idempotência).
set -euo pipefail

AQUI="$(cd "$(dirname "$0")" && pwd)"
SALA="/tmp/faxina-sala-$$"
SHELLS="/tmp/faxina-shells-$$"
FAXINA="python3 $AQUI/ia-faxina.py"
PASSOU=0; FALHOU=0

confere() {  # confere "<descrição>" <condição: 0=ok>
  if [ "$2" -eq 0 ]; then echo "  ✔ $1"; PASSOU=$((PASSOU+1));
  else echo "  ✘ $1"; FALHOU=$((FALHOU+1)); fi
}

# ── fabrica a sala falsa ─────────────────────────────────────────────────────
mkdir -p "$SALA"/{pendente,cursor,arquivo,.lock} "$SHELLS/claude" "$SHELLS/kimi"
echo "# sala falsa" > "$SALA/iachat.md"
# codex SAIU da sala → pendente/codex.md vira sem dono; claude e kimi ficam
echo '{"na_sala": ["claude", "kimi"], "brain": "claude", "teto_bytes": 102400}' > "$SALA/config.json"
echo '{"ultima": 3, "em": "2026-08-17T21:00:00-03:00"}' > "$SALA/.estado.json"

echo "chamado velho" > "$SALA/pendente/codex.md"     # sem dono → sai
echo "chamado vivo" > "$SALA/pendente/claude.md"      # viva → fica
echo '{"ultima_lida": 9}' > "$SALA/cursor/codex.json" # órfão → RETIDO (estado)
echo '{"ultima_lida": 3}' > "$SALA/cursor/claude.json"
for i in $(seq 1 600); do echo "[$i] linha de log fabricada"; done > "$SALA/ia-bell-claude.log"
for i in $(seq 1 5);   do echo "[$i] log pequeno";        done > "$SALA/ia-bell-kimi.log"
: > "$SALA/ia-bell-claude.out"; : > "$SALA/ia-bell-claude.err"   # alvos do launchd, vazios
echo "recorte histórico" > "$SALA/arquivo/iachat-2026-08-01-recorte-01.md"
RECORTE_HASH=$(shasum "$SALA/arquivo/iachat-2026-08-01-recorte-01.md" | cut -d' ' -f1)

# .tmp: um órfão velho (09:00 de hoje) e um fresco (agora → pode ser escrita em curso)
echo '{"ultima": 2}' > "$SALA/.estado.json.tmp";  touch -t 202608170900 "$SALA/.estado.json.tmp"
echo '{"ultima_lida": 1}' > "$SALA/cursor/kimi.json.tmp"   # mtime de agora

# baks: 1 de hoje + 4 velhos na pasta claude (esperado: hoje fica, 3 recentes
# ficam, 2 mais velhos saem); 1 velho na kimi (o único → fica)
for n in 11 12 13 14; do echo bak > "$SHELLS/claude/settings.json.bak-iachat-202608$n-100000"; done
touch -t 202608162000 "$SHELLS/claude/settings.json.bak-iachat-20260811-100000"
touch -t 202608152000 "$SHELLS/claude/settings.json.bak-iachat-20260812-100000"
touch -t 202608142000 "$SHELLS/claude/settings.json.bak-iachat-20260813-100000"
touch -t 202608132000 "$SHELLS/claude/settings.json.bak-iachat-20260814-100000"
echo bak-hoje > "$SHELLS/claude/settings.json.bak-iachat-20260817-210000"
# REGRESSÃO (achado em sala real): shutil.copy2 preserva mtime da fonte — este
# backup é de HOJE no nome, mas carrega mtime de 13/08. A idade tem que vir do
# carimbo no nome, senão a trava de "mesmo dia" fura.
echo bak-hoje-mtime-velho > "$SHELLS/claude/settings.json.bak-iachat-20260817-090000"
touch -t 202608132000 "$SHELLS/claude/settings.json.bak-iachat-20260817-090000"
echo bak > "$SHELLS/kimi/config.toml.bak-iachat-20260810-100000"
touch -t 202608102000 "$SHELLS/kimi/config.toml.bak-iachat-20260810-100000"

export IACHAT_HOME="$SALA"
ARGS="--pasta-shell $SHELLS/claude --pasta-shell $SHELLS/kimi"

echo "═══ 1) DRY-RUN ═══"
$FAXINA $ARGS

echo; echo "═══ 2) conferindo que dry-run NÃO tocou em nada ═══"
[ "$(ls "$SHELLS/claude" | wc -l | tr -d ' ')" -eq 6 ]; confere "dry-run não apagou baks" $?
[ "$(wc -l < "$SALA/ia-bell-claude.log" | tr -d ' ')" -eq 600 ]; confere "dry-run não aparou log" $?
[ -f "$SALA/pendente/codex.md" ]; confere "dry-run não removeu flag" $?

echo; echo "═══ 3) APLICAR ═══"
$FAXINA $ARGS --aplicar

echo; echo "═══ 4) conferindo o que devia acontecer ═══"
[ -f "$SHELLS/claude/settings.json.bak-iachat-20260817-210000" ]; confere "bak do MESMO DIA preservado" $?
[ -f "$SHELLS/claude/settings.json.bak-iachat-20260817-090000" ]; confere "REGRESSÃO: bak de hoje com mtime velho preservado (idade pelo nome)" $?
[ "$(ls "$SHELLS/claude" | wc -l | tr -d ' ')" -eq 4 ]; confere "retidos 4 baks (2 de hoje + 2 velhos recentes)" $?
[ ! -f "$SHELLS/claude/settings.json.bak-iachat-20260813-100000" ] && [ ! -f "$SHELLS/claude/settings.json.bak-iachat-20260814-100000" ]; confere "os 2 baks mais velhos saíram" $?
[ -f "$SHELLS/kimi/config.toml.bak-iachat-20260810-100000" ]; confere "bak único da kimi retido" $?
[ "$(wc -l < "$SALA/ia-bell-claude.log" | tr -d ' ')" -eq 200 ]; confere "log de 600 linhas aparado para 200" $?
grep -q "linha de log fabricada" "$SALA/ia-bell-claude.log"; confere "cauda do log preservada (conteúdo recente)" $?
[ "$(wc -l < "$SALA/ia-bell-kimi.log" | tr -d ' ')" -eq 5 ]; confere "log pequeno intocado" $?
[ ! -f "$SALA/.estado.json.tmp" ]; confere ".tmp órfão (velho) removido" $?
[ -f "$SALA/cursor/kimi.json.tmp" ]; confere ".tmp fresco preservado (escrita em curso?)" $?
[ ! -f "$SALA/pendente/codex.md" ]; confere "flag sem dono (codex fora da sala) removida" $?
[ -f "$SALA/pendente/claude.md" ]; confere "flag de IA viva preservada" $?
[ -f "$SALA/cursor/codex.json" ]; confere "cursor órfão RETIDO (estado, não lixo)" $?
[ "$(shasum "$SALA/arquivo/iachat-2026-08-01-recorte-01.md" | cut -d' ' -f1)" = "$RECORTE_HASH" ]; confere "recorte em arquivo/ intacto (hash)" $?
[ -f "$SALA/faxina.log" ]; confere "faxina.log criado" $?
[ "$(grep -c 'APLICADO.*removido\|APLICADO.*aparado' "$SALA/faxina.log")" -ge 5 ]; confere "toda remoção deixou linha de log" $?

echo; echo "═══ 5) IDEMPOTÊNCIA: segunda rodada ═══"
SAIDA=$($FAXINA $ARGS)
echo "$SAIDA"
echo "$SAIDA" | grep -q "nada a limpar"; confere "segunda rodada: 'nada a limpar'" $?

echo; echo "═══ faxina.log (conteúdo) ═══"
cat "$SALA/faxina.log"

echo; echo "RESULTADO: $PASSOU passaram, $FALHOU falharam"
[ "$FALHOU" -eq 0 ]
