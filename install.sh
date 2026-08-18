#!/bin/bash
# ia-chat — instalador (Claude Code + Kimi por padrão; destinos customizáveis por env)
#   IACHAT_SCRIPTS  (default: ~/.claude/scripts/ia-chat)
#   IACHAT_SKILLS   (default: ~/.claude/skills)        ← o Kimi já lê esta pasta
#   IACHAT_BIN      (default: ~/.local/bin)            ← precisa estar no PATH
#   IACHAT_HOME     (default: ~/ia-chat-global)        ← os dados da sala
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
DEST_SCRIPTS="${IACHAT_SCRIPTS:-$HOME/.claude/scripts/ia-chat}"
DEST_SKILLS="${IACHAT_SKILLS:-$HOME/.claude/skills}"
DEST_BIN="${IACHAT_BIN:-$HOME/.local/bin}"
SALA="${IACHAT_HOME:-$HOME/ia-chat-global}"

# O CLI é #!/usr/bin/env python3 (bin/iachat:1). Sem python3 no PATH o
# instalador copiava scripts e skills e só quebrava na primeira execução
# (`iachat status`, mais abaixo), com:
#   /usr/bin/env: python3: No such file or directory
# Mensagem que não ensina o que fazer. Mac limpo sem Command Line Tools
# não tem /usr/bin/python3 — medido no laudo d3-maquina-limpa (fase 8).
# Erro que não ensina o comando é o mesmo defeito do teste_erro_ensina.
if ! command -v python3 >/dev/null 2>&1; then
  echo "✗  python3 não está no PATH — o ia-chat é um CLI em Python 3 e não roda sem ele."
  echo "   no macOS: xcode-select --install"
  echo "   (isso instala /usr/bin/python3; depois rode de novo: sh install.sh)"
  echo "   em Linux: instale o pacote python3 da sua distro e tente de novo."
  exit 1
fi

mkdir -p "$DEST_SCRIPTS" "$DEST_SKILLS" "$DEST_BIN"
cp "$SRC/bin/iachat" "$SRC/bin/iachat_core.py" "$DEST_SCRIPTS/"
# Os auxiliares por GLOB ABERTO (`bin/ia-*`), não por lista nem por padrão temático.
# Em 18/08 isto falhou TRÊS vezes seguidas: primeiro a lista explícita esqueceu os
# `ia-network-bell-*`; troquei por `ia-*bell*` achando que tinha resolvido a classe; e na
# hora seguinte a peça foi renomeada para `ia-server-connection-*` — sem "bell" no nome —
# e o glob esperto errou igual. Padrão que codifica o NOME DE HOJE quebra no rename.
# `ia-*` pega todo auxiliar presente e futuro; os CLIs (`iachat-*`) vão logo abaixo.
for aux in "$SRC"/bin/ia-*; do [ -f "$aux" ] && cp "$aux" "$DEST_SCRIPTS/"; done
# Os CLIs das peças (iachat-claim, iachat-recibo, iachat-thread, …) também vão. Sem isto,
# a skill ensina um comando que não existe no PATH: medido em 17/08 (achado da kimi) — 8
# CLIs no repo, 8 sem resolver, e 8 skills chamando-os pelo nome. Documentação que ensina
# comando quebrado é pior que documentação nenhuma.
for extra in "$SRC"/bin/iachat-*; do [ -f "$extra" ] && cp "$extra" "$DEST_SCRIPTS/"; done
chmod +x "$DEST_SCRIPTS/iachat" "$DEST_SCRIPTS"/ia-*.sh 2>/dev/null
chmod +x "$DEST_SCRIPTS"/iachat-* 2>/dev/null
ln -sf "$DEST_SCRIPTS/iachat" "$DEST_BIN/iachat"
# TODO executável ganha symlink, não só os `iachat-*`. A lição de 17/08 registrada
# acima ("8 CLIs no repo, 8 sem resolver") foi consertada pela metade: os auxiliares
# `ia-*` passaram a ser COPIADOS, mas continuaram sem entrar no PATH. O defeito voltou
# em 18/08 com o `ia-compactacao`, que é chamado por um hook apontando para
# `~/.local/bin/` — o hook falharia em silêncio, que é o pior desfecho para uma peça
# cuja função é justamente avisar.
#
# Os `.sh` internos ficam de fora de propósito: o LaunchAgent os invoca por caminho
# absoluto. A única exceção de interface humana é o instalador do daemon, cujo basename
# o comando `entrar` ensina; o symlink explícito logo abaixo garante esse contrato.
for extra in "$DEST_SCRIPTS"/iachat-* "$DEST_SCRIPTS"/ia-*; do
  [ -f "$extra" ] || continue
  case "$extra" in *.sh|*.py) continue ;; esac
  [ -x "$extra" ] && ln -sf "$extra" "$DEST_BIN/$(basename "$extra")"
done
ln -sf "$DEST_SCRIPTS/ia-bell-install-daemon.sh" \
  "$DEST_BIN/ia-bell-install-daemon.sh"

for s in "$SRC"/skills/*/; do
  n="$(basename "$s")"
  mkdir -p "$DEST_SKILLS/$n"
  cp "$s/SKILL.md" "$DEST_SKILLS/$n/"
done

IACHAT_HOME="$SALA" "$DEST_SCRIPTS/iachat" status >/dev/null   # cria a sala se não existe

# O `~/.local/bin` NÃO está no PATH de um macOS recém-instalado. Sem esta checagem o
# instalador terminava com três ✔ e o `iachat` não existia para quem acabou de instalar —
# a primeira coisa que a pessoa tenta, e o produto já falhou sem explicar por quê.
# Um ✔ que não corresponde a nada é pior que um ✗: ensina a não confiar no instalador.
# Achado do worker `qwen` na missão m2, provado em sandbox com PATH limpo.
case ":$PATH:" in
  *":$DEST_BIN:"*) NO_PATH="" ;;
  *) NO_PATH="1" ;;
esac

echo "✔ CLI      $DEST_BIN/iachat  →  $DEST_SCRIPTS/iachat"
echo "✔ skills   $DEST_SKILLS/ia-*  ($(ls -d "$SRC"/skills/*/ | wc -l | tr -d ' ') instaladas)"
echo "✔ sala     $SALA"
if [ -n "$NO_PATH" ]; then
  # O nome do arquivo é do SHELL de quem instala, não do meu. Mandar todo mundo editar
  # `.zshrc` erra em quem usa bash — e um conserto que não funciona é o mesmo defeito
  # com outra roupa.
  case "$(basename "${SHELL:-/bin/zsh}")" in
    bash) PERFIL="~/.bash_profile" ;;
    fish) PERFIL="~/.config/fish/config.fish" ;;
    *)    PERFIL="~/.zshrc" ;;
  esac
  echo
  echo "⚠  $DEST_BIN não está no seu PATH — o comando \`iachat\` ainda não existe."
  if [ "$PERFIL" = "~/.config/fish/config.fish" ]; then
    echo "   echo 'fish_add_path $DEST_BIN' >> $PERFIL && exec fish"
  else
    echo "   echo 'export PATH=\"$DEST_BIN:\$PATH\"' >> $PERFIL && exec \$SHELL"
  fi
  echo "   (ou use o caminho inteiro: $DEST_BIN/iachat status)"
fi
echo
# A linha do Claude era afirmada SEM verificar nada — "já vê as skills" saía igual numa
# máquina onde o Claude Code nem está instalado, e ficava duplamente falsa quando
# `IACHAT_SKILLS` aponta para fora de `~/.claude/skills`, que é o único lugar onde ele
# procura sozinho. Achado auditando a instalação numa máquina limpa, em 18/08.
#
# Instalador que declara sucesso onde não há nada ensina o usuário a não confiar nele —
# e a confiança no instalador é a primeira que se ganha ou se perde num repositório novo.
# O teste é pelo BINÁRIO, não pela pasta: `~/.claude` pode ter acabado de nascer — este
# mesmo instalador a cria ao copiar as skills para lá. Diretório não distingue "tem
# Claude Code" de "eu criei a pasta há um segundo".
if ! command -v claude >/dev/null 2>&1; then
  echo "Claude Code: não encontrado nesta máquina — as skills ficaram em $DEST_SKILLS."
elif [ "$DEST_SKILLS" = "$HOME/.claude/skills" ]; then
  echo "Claude Code: já vê as skills em $DEST_SKILLS."
else
  echo "Claude Code: procura em ~/.claude/skills, e você instalou em $DEST_SKILLS."
  echo "             ln -s \"$DEST_SKILLS\"/* ~/.claude/skills/"
fi
if grep -q "$DEST_SKILLS" "$HOME/.kimi-code/config.toml" 2>/dev/null; then
  echo "Kimi:        já lê $DEST_SKILLS (extra_skill_dirs) — nada a fazer."
else
  echo "Kimi:        adicione em ~/.kimi-code/config.toml:"
  echo "             extra_skill_dirs = [ \"$DEST_SKILLS\" ]"
fi
cat <<'AVISO'
Codex:       as skills entram por diretório (aceita symlink):
               ln -s ~/.claude/skills/ia-chat-activate ~/.codex/skills/ia-chat-activate
             ⚠️ se for MEXER em ~/.codex/hooks.json, o `trusted_hash` é invalidado e o
             Codex passa a PULAR o hook em silêncio — ele precisa re-aprovar na próxima
             abertura. Este instalador nunca fabrica hash nem edita hooks.json.
AVISO

# O gatilho da compactação NÃO é armado aqui, e isso é deliberado: editar sozinho o
# settings.json de quem instala é invasivo, e no Codex quebra o `trusted_hash`. Mas a
# skill declarava "passiva, no SessionStart" como se acontecesse sozinho — e uma promessa
# que o instalador não cumpre é pior que uma instrução a mais. Achado por auditoria
# cruzada em 18/08: skill promete, install.sh não arma, clone novo não ganha o gatilho.
ARMADOS=""
if [ -f "$HOME/.claude/settings.json" ]; then
  for ev in PreCompact PostCompact SessionStart; do
    grep -q "ia-compactacao" "$HOME/.claude/settings.json" 2>/dev/null && ARMADOS="1" && break
  done
fi
echo
if [ -n "$ARMADOS" ]; then
  echo "compactação: algum hook de ia-compactacao já está no seu settings.json."
  echo "             confira quais com:  iachat-doctor"
else
  echo "compactação: o mapa de retomada funciona AGORA na mão —"
  echo "               ia-compactacao --mapa     (escreve o mapa)"
  echo "               ia-compactacao --inicio   (imprime o ponteiro)"
  echo "             para virar passivo, cole em ~/.claude/settings.json (hooks):"
  cat <<HOOKS
               "PreCompact":   [{"hooks":[{"type":"command",
                  "command":"$DEST_BIN/ia-compactacao --pre"}]}],
               "PostCompact":  [{"hooks":[{"type":"command",
                  "command":"$DEST_BIN/ia-compactacao --pos"}]}],
               "SessionStart": [{"hooks":[{"type":"command",
                  "command":"$DEST_BIN/ia-compactacao --inicio"}]}]
HOOKS
  echo "             (armar é gesto seu — este instalador não edita hooks de ninguém.)"
fi
