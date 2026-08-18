#!/bin/bash
# gate-onboard.sh — critério binário do ia-onboard. Roda em IACHAT_HOME temporário.
#   uso: IACHAT_CORE_DIR=~/Projetos/ia-chat/bin ./gate-onboard.sh
# Sai 0 só se os 6 gates passarem. Fail-closed: qualquer gate ruim reprova o conjunto.
set -u
AQUI="$(cd "$(dirname "$0")" && pwd)"
CORE="${IACHAT_CORE_DIR:-$HOME/Projetos/ia-chat/bin}"
ONB="$AQUI/iachat-onboard"
export IACHAT_CORE_DIR="$CORE"
SALA_REAL="${SALA_REAL:-$HOME/ia-chat-global/iachat.md}"
FALHAS=0

ok()  { printf '  ✔ %s\n' "$1"; }
bad() { printf '  ✗ %s\n' "$1"; FALHAS=$((FALHAS+1)); }

nova_sala() {
    export IACHAT_HOME="$(mktemp -d)/sala"
    mkdir -p "$IACHAT_HOME"/{cursor,pendente,arquivo,.lock}
    cp "$SALA_REAL" "$IACHAT_HOME/iachat.md"
    printf '{"na_sala":["claude","codex","kimi","grok"],"brain":"claude","teto_bytes":%s,"notificar_operador":false}\n' \
        "${1:-204800}" > "$IACHAT_HOME/config.json"
}

echo "G1 · o briefing respeita o teto de 4096 B"
nova_sala
N=$("$ONB" briefing --de grok | wc -c | tr -d ' ')
[ "$N" -le 4096 ] && ok "sala de 24 KB: $N B" || bad "sala de 24 KB: $N B > 4096"

echo "G2 · respeita o teto com a sala NO teto de 200 KB e 6 IAs"
nova_sala
python3 - <<'PY'
import sys, os, json
sys.path.insert(0, os.environ["IACHAT_CORE_DIR"])
import iachat_core as c
cfg = json.load(open(c.p_config())); cfg["na_sala"] = ["claude","codex","kimi","grok","agy","copilot"]
json.dump(cfg, open(c.p_config(), "w"))
enche = "Medição autocontida, caminho /Users/bauer/x/y.py:118, número 4096 B. " * 20
n = 0
while os.path.getsize(c.p_chat()) < 204800:
    n += 1
    c.post(cfg["na_sala"][n % 6], f"@{cfg['na_sala'][(n+2) % 6]} Assunto {n}. " + enche)
PY
N=$("$ONB" briefing --de grok | wc -c | tr -d ' ')
[ "$N" -le 4096 ] && ok "sala no teto: $N B" || bad "sala no teto: $N B > 4096"

echo "G3 · respeita o teto com DECISOES.md inflado (60 entradas)"
for i in $(seq 1 60); do
    "$ONB" decidir --de kimi "Decisão $i com caminho /Users/bauer/proj/a-$i.py:$i e número $((i*137)) B, longa o bastante para forçar o corte." >/dev/null
done
N=$("$ONB" briefing --de grok | wc -c | tr -d ' ')
D=$(wc -c < "$IACHAT_HOME/DECISOES.md" | tr -d ' ')
[ "$N" -le 4096 ] && ok "DECISOES de $D B → briefing $N B" || bad "briefing $N B > 4096"

echo "G4 · gerar é read-only: sem --marcar não muda 1 byte de conteúdo"
# `.lock/iachat.lock` fica de fora e isso NÃO é afrouxar: é o mutex, tem 0 B, e um
# `iachat status` — que só lê — cria exatamente o mesmo arquivo (iachat_core.py:129-131).
# Medido: sala limpa + `iachat status` ⇒ .lock/iachat.lock, 0 B. O gate mede conteúdo.
conteudo() { find "$IACHAT_HOME" -type f ! -path '*/.lock/*' -exec shasum {} \; | shasum; }
nova_sala
A=$(conteudo)
"$ONB" briefing --de grok >/dev/null
B2=$(conteudo)
LOCK=$(wc -c < "$IACHAT_HOME/.lock/iachat.lock" | tr -d ' ')
{ [ "$A" = "$B2" ] && [ "$LOCK" -eq 0 ]; } \
    && ok "nenhum conteúdo tocado (lock com $LOCK B, como em qualquer comando)" \
    || bad "a sala mudou depois de um briefing (lock=$LOCK B)"

echo "G5 · o hook entrega 1× e nunca repete"
nova_sala
BIN=$(mktemp -d); cp "$CORE/iachat" "$CORE/iachat_core.py" "$ONB" "$BIN/"; chmod +x "$BIN"/iachat*
export IACHAT_BIN="$BIN" IACHAT_EU=grok
U=$("$AQUI/ia-bell-hook.patch.sh" | wc -c | tr -d ' ')
D2=$("$AQUI/ia-bell-hook.patch.sh" | wc -c | tr -d ' ')
{ [ "$U" -gt 500 ] && [ "$D2" -eq 0 ]; } && ok "1ª vez $U B · 2ª vez $D2 B" || bad "1ª=$U B 2ª=$D2 B (esperado >500 e 0)"
unset IACHAT_BIN IACHAT_EU

echo "G6 · decisão sobrevive à rotação (a mensagem não sobrevive)"
nova_sala 16384
"$ONB" decidir --de claude "Regra que tem de sobreviver à rotação: o operador tem precedência." >/dev/null
"$CORE/iachat" rotate >/dev/null
grep -q "precedência sobre qualquer coisa" "$IACHAT_HOME/iachat.md" \
    && bad "a msg #9 continuou no ativo — teste inválido" \
    || ok "a msg #9 saiu do ativo, como esperado"
"$ONB" briefing --de grok | grep -q "tem de sobreviver à rotação" \
    && ok "a decisão continua no briefing depois da rotação" \
    || bad "a decisão sumiu junto com as mensagens"

echo
[ "$FALHAS" -eq 0 ] && echo "GATE ia-onboard: PASS (6/6)" || echo "GATE ia-onboard: FAIL ($FALHAS falha(s))"
exit "$FALHAS"
