#!/bin/bash
# ia-server-connection-daemon.sh — UMA vigília, DOIS sinos, TRÊS decisões.
#
# Uso:  ia-server-connection-daemon.sh [intervalo_segundos]
#       ia-server-connection-daemon.sh --uma-vez [intervalo]   # um ciclo e sai (bateria)
#       ia-server-connection-daemon.sh --gatilho               # chamado por quem tentou conectar
#
# DESENHO (do dono, 18/08): uma skill só, porque quem lê o aviso não quer escolher entre
# três documentos — quer saber o que fazer. Mas DOIS sinos, porque a conduta é diferente:
#
#   ⚡ energy-bell      — a energia caiu. Você tem SEGUNDOS. Salve o parcial agora.
#   📡 connection-bell  — o fluxo para os provedores caiu. O trabalho local segue; o que
#                         fala com API remota, não. Não redispare para fora.
#
# E TRÊS grupos de decisão, sendo o terceiro a parte mais importante:
#
#   🔕 no-bell — detectei, MEDI, e decidi NÃO tocar. Uma piscada de Wi-Fi de 20 segundos
#      não acorda ninguém. Vigia que toca a cada oscilação vira ruído, e ruído todo mundo
#      aprende a ignorar — aí, no dia real, ninguém olha. O `no-bell` fica REGISTRADO no
#      dossiê justamente para ser auditável: dá para conferir depois se ele calou algo que
#      devia ter falado. Silêncio medido é decisão; silêncio não registrado é omissão.
#
# GATILHO DUPLO, e é o furo que o desenho por-conexão sozinho teria: se a energia cai e
# nada tenta conectar naquele instante, ninguém detecta. Então vale por BATIMENTO (o laço,
# a cada N segundos) E por EVENTO (`--gatilho`, chamado por quem acabou de falhar ao
# conectar). Os dois caem no mesmo classificador — a decisão é uma só.
#
# POR QUE ELE EXISTE: na madrugada de 18/08 a energia caiu DUAS vezes. Um worker tinha
# 123 KB de raciocínio no log e ZERO byte no disco: perdeu tudo, porque ninguém o avisou
# de que o chão tinha sumido debaixo dele.
set -u

UMA_VEZ=0
GATILHO=0
case "${1:-}" in
  --uma-vez) UMA_VEZ=1; shift ;;
  --gatilho) GATILHO=1; UMA_VEZ=1; shift ;;
esac
INTERVALO="${1:-20}"

SALA="${IACHAT_HOME:-$HOME/ia-chat-global}"
ESTADO="$SALA/.rede-estado.json"
AVISOS="$SALA/rede/EVENTOS.md"
LOG="$SALA/ia-server-connection.log"

mkdir -p "$SALA/pendente" "$SALA/rede"

# ── os três sensores ────────────────────────────────────────────────────────
# Cada um devolve SEMPRE um valor, inclusive "?" — o terceiro desfecho ("não consegui
# olhar") nunca é fundido em "está tudo bem". Sensor mudo que finge normalidade é pior
# que sensor nenhum, porque acrescenta confiança falsa.
ler_energia() {
  local s
  s="$(pmset -g batt 2>/dev/null | head -1)" || { echo "?"; return; }
  case "$s" in
    *"AC Power"*)      echo "tomada" ;;
    *"Battery Power"*) echo "bateria" ;;
    *)                 echo "?" ;;
  esac
}

ler_ip() { ipconfig getifaddr en0 2>/dev/null || echo "-"; }

# Distingue TRÊS estados de rede, não dois: "a casa caiu" e "a nuvem caiu" levam a
# decisões opostas. Quem funde os dois manda redisparar worker numa rede que não existe.
ler_rede() {
  if curl -sS -I --max-time 3 https://api.anthropic.com >/dev/null 2>&1; then
    echo "no-ar"
  elif ping -c1 -t2 1.1.1.1 >/dev/null 2>&1; then
    echo "so-lan"
  else
    echo "fora"
  fi
}

# ── o classificador: qual dos três grupos ───────────────────────────────────
# `tocar <sino> <titulo> <corpo>` — sino ∈ energy | connection | no-bell
tocar() {
  local sino="$1" titulo="$2" corpo="$3" ts glifo
  ts="$(date '+%d/%m %H:%M:%S')"
  case "$sino" in
    energy)     glifo="⚡" ;;
    connection) glifo="📡" ;;
    *)          glifo="🔕" ;;
  esac

  {
    echo ""
    echo "## $ts · $glifo \`$sino-bell\` · $titulo"
    echo ""
    echo "$corpo"
  } >> "$AVISOS"
  echo "[$ts] $sino | $titulo | $corpo" >> "$LOG"

  # no-bell PARA AQUI, e é o ponto do desenho: registrado no dossiê, auditável, e
  # sem acordar ninguém.
  [ "$sino" = "no-bell" ] && return 0

  SALA="$SALA" AVISOS="$AVISOS" TITULO="$titulo" TS="$ts" GLIFO="$glifo" SINO="$sino" python3 - <<'PY'
import json, os, pathlib

sala = pathlib.Path(os.environ["SALA"])
try:
    ias = json.loads((sala / "config.json").read_text()).get("na_sala", [])
except Exception:
    ias = []

linha = (f"- {os.environ['GLIFO']} **{os.environ['TS']} · {os.environ['SINO']}-bell · "
         f"{os.environ['TITULO']}** — leia o contrato (skill `ia-server-connection`) e o "
         f"histórico em `{os.environ['AVISOS']}` ANTES de continuar o que estava fazendo.")

for ia in ias:
    f = sala / "pendente" / f"{ia}.md"
    if f.exists():
        # O flag ACUMULA, nunca sobrescreve: um sino que apaga o chamado anterior faz a
        # IA anunciar o último e perder os outros. Já aconteceu com o flag do Codex.
        texto = f.read_text()
        if linha not in texto:
            f.write_text(texto.rstrip() + "\n" + linha + "\n")
    else:
        f.write_text(
            f"# 🔔 {ia}, o chão se moveu no ia-chat\n\n"
            f"Ler tudo de uma vez: `iachat read --de {ia}`\n"
            f"Chat: `{sala}/iachat.md`\n\n"
            f"## Chamados pendentes\n\n{linha}\n"
        )
PY

  osascript -e "display notification \"$corpo\" with title \"$glifo $titulo\" sound name \"Submarine\"" 2>/dev/null || true
}

# ── estado anterior ─────────────────────────────────────────────────────────
# Primeira execução não toca: sem estado anterior não há transição, e sino que toca ao
# nascer treina todo mundo a ignorá-lo.
le_estado() { python3 -c "import json;print(json.load(open('$ESTADO')).get('$1','$2'))" 2>/dev/null || echo "$2"; }

if [ -f "$ESTADO" ]; then
  ANT_E="$(le_estado energia '?')"; ANT_I="$(le_estado ip '-')"
  ANT_R="$(le_estado rede '?')";    FALHAS="$(le_estado falhas 0)"
else
  ANT_E="$(ler_energia)"; ANT_I="$(ler_ip)"; ANT_R="$(ler_rede)"; FALHAS=0
  printf '{"energia":"%s","ip":"%s","rede":"%s","falhas":0}\n' "$ANT_E" "$ANT_I" "$ANT_R" > "$ESTADO"
fi

ciclo() {
  local E I R
  E="$(ler_energia)"; I="$(ler_ip)"; R="$(ler_rede)"

  # ── ⚡ ENERGY-BELL — nunca é no-bell ──────────────────────────────────────
  # Sair da tomada é o sinal MAIS PRECOCE que existe: o Mac aguenta na bateria, o
  # roteador não. Os segundos ganhados aqui separam "salvei o parcial" de "perdi tudo".
  # Por isso não há tolerância nem contador: energia mudou, energia avisa.
  if [ "$E" != "$ANT_E" ] && [ "$E" != "?" ] && [ "$ANT_E" != "?" ]; then
    if [ "$E" = "bateria" ]; then
      tocar energy "ENERGIA CAIU — o Mac está na bateria" \
        "SALVE O PARCIAL AGORA. O Mac aguenta; o roteador não. Quem fala com API remota cai em segundos."
    else
      tocar energy "ENERGIA VOLTOU — de volta à tomada" \
        "Remapeie ANTES de retomar: worker morto, IP possivelmente novo, servidor no endereço errado."
    fi
  fi

  # ── 📡 CONNECTION-BELL — com tolerância a piscada ─────────────────────────
  # Uma queda que dura um ciclo é oscilação; duas é evento. O contador é o que separa
  # o `no-bell` do sino de verdade.
  if [ "$R" != "no-ar" ]; then
    FALHAS=$((FALHAS + 1))
  else
    if [ "$FALHAS" -ge 2 ] && [ "$ANT_R" != "no-ar" ]; then
      tocar connection "CONEXÃO VOLTOU — após $FALHAS ciclos fora" \
        "Remapeie contra o DISCO e redispare só o que comprovadamente morreu. Log grande sem artefato = morreu sem salvar."
    fi
    FALHAS=0
  fi

  if [ "$R" != "$ANT_R" ] && [ "$R" != "?" ] && [ "$ANT_R" != "?" ]; then
    case "$R" in
      fora|so-lan)
        if [ "$FALHAS" -ge 2 ]; then
          if [ "$R" = "fora" ]; then
            tocar connection "CONEXÃO FORA — $FALHAS ciclos" \
              "NÃO redispare nada para fora. Trabalho local segue; o que fala com API remota vai morrer. Grave e espere."
          else
            tocar connection "CONEXÃO PARCIAL — LAN sim, provedores não" \
              "A casa está de pé e a nuvem não. NÃO conclua que um worker falhou: ele está sem linha."
          fi
        else
          tocar no-bell "oscilação de rede ($ANT_R → $R)" \
            "Um ciclo fora. Abaixo do limiar de 2: registrado e sem acordar ninguém."
        fi
        ;;
    esac
  fi

  # ── 📡 IP — mudança silenciosa, e por isso traiçoeira ─────────────────────
  # Nada quebra na hora: toda URL de servidor simplesmente para de existir, sem erro.
  if [ "$I" != "$ANT_I" ] && [ "$I" != "-" ] && [ "$ANT_I" != "-" ]; then
    tocar connection "O IP MUDOU — $ANT_I → $I" \
      "As URLs de servidor viraram pó, em silêncio. Reinicie os servidores e refaça o link do celular."
  fi

  ANT_E="$E"; ANT_I="$I"; ANT_R="$R"
  printf '{"energia":"%s","ip":"%s","rede":"%s","falhas":%s,"visto":"%s"}\n' \
    "$E" "$I" "$R" "$FALHAS" "$(date '+%Y-%m-%dT%H:%M:%S')" > "$ESTADO"
}

# `--gatilho`: quem tentou conectar e falhou chama isto. Mesmo classificador, sem esperar
# o próximo batimento — é a diferença entre saber agora e saber em 20 segundos.
if [ "$GATILHO" = "1" ]; then FALHAS=$((FALHAS + 1)); fi

while :; do
  ciclo
  [ "$UMA_VEZ" = "1" ] && exit 0
  sleep "$INTERVALO"
done
