---
name: ia-doctor
description: Diagnostica a instalação do ia-chat em todas as cascas (Claude, Codex, Kimi, Grok, Qwen) — skill no catálogo, hook ativo e válido para a sessão aberta, daemon vivo, CLI no PATH, trusted_hash do Codex, sala acessível e íntegra. Use quando o sino não tocou, quando a skill "não aparece", quando o hook "está instalado mas não dispara", depois de instalar ou mexer em qualquer config de casca, e antes de confiar que a sala está no ar. Cada verificação tem três desfechos — ok, falhou e não-consegui-verificar — e cada ✗ vem com o comando que corrige. Read-only: diagnostica, não conserta.
---

# ia-doctor — o instrumento que admite não saber

Rode antes de acreditar que o ia-chat está funcionando:

```bash
ia-doctor                        # as cascas declaradas em config.json:na_sala
ia-doctor --todas                # + toda casca conhecida presente no disco
ia-doctor --casca codex          # uma só (repetível)
ia-doctor --repo ~/Projetos/ia-chat   # compara o instalado com o repositório-fonte
ia-doctor --json                 # laudo machine-parseable
```

Saída **0** se não houver nenhum ✗. **1** se houver ✗. ⚠ nunca reprova.

## A regra que dá valor ao laudo

Toda verificação termina em **um de três** desfechos, nunca dois:

| | significado | o que fazer |
|---|---|---|
| ✓ | medi e está certo | nada |
| ✗ | medi e está errado | o `passo:` do item |
| ⚠ | **não consegui medir** | ler o `passo:`, que diz como transformar dúvida em medida |

Fundir ⚠ em ✓ ("deve estar ok") ou em ✗ ("vou reprovar por via das dúvidas) é a mentira
que produziu os três defeitos que este programa existe para pegar. `⚠ não consigo ler o
catálogo da TUI daqui` é uma resposta legítima e sai como tal.

Cada linha traz `como:` — o comando ou a leitura exata que produziu o veredito. Laudo sem
`como:` é opinião.

## O que ele mede

**Sala** — `iachat` resolve no PATH · o CLI executa e sai 0 · estrutura completa
(`.lock cursor pendente arquivo iachat.md config.json`) · `.estado.json` bate com o
último `msg=N` do documento · tamanho contra o teto · `config.json` parseável ·
`bin/*` instalado idêntico ao repositório (com `--repo`).

**Por casca** — as 7 skills no diretório que **aquela** casca lê, com frontmatter válido
e `name` igual ao diretório · a skill mudou depois da sessão abrir? · o hook
`ia-bell-hook.sh` declarado nos eventos certos · o comando aponta para binário executável ·
o config de hook mudou depois da sessão abrir? · (Codex) todo hook tem aprovação em
`[hooks.state]` · LaunchAgent `com.bauer.ia-bell-<ia>` carregado e com pid · cursor legível
e flag pendente não-esquecida.

## Os três defeitos que ele pega antes do usuário sofrer

1. **Skill no disco mas fora do catálogo da sessão.** Codex e Kimi leem catálogo e config
   no boot. `ia-doctor` compara o `mtime` da skill com a hora em que o processo da casca
   abriu (`ps -o etime`, que é numérico — `lstart` sai no locale do usuário). Skill mais
   nova que a sessão ⇒ ⚠ com o passo: *abra uma sessão nova*. **Ele nunca alega que a
   skill está no catálogo** — isso não é legível de fora, e dizer que é seria inventar.

2. **Hook instalado que não dispara.** Mesma medida sobre o arquivo de config de hooks.
   Config mais nova que a sessão ⇒ essa sessão roda a config anterior. Foi exatamente o
   caso vivido; nenhuma verificação de conteúdo pegaria, porque o conteúdo estava certo.

3. **Instalador que nega um daemon que subiu.** `launchctl list | grep -q LABEL` sob
   `pipefail`: o grep sai no primeiro casamento, o pipe fecha, o `launchctl` morre de
   SIGPIPE (141) e o pipeline vira falha. `ia-doctor` **não usa pipe nem `grep -q`** —
   captura a saída inteira de `launchctl list` e só depois procura o label. Falha ao
   executar o comando vira ⚠, nunca ✗: não conseguir perguntar não é a mesma coisa que
   receber "não".

## Limites que ele declara em vez de esconder

- **Catálogo de sessão aberta**: nenhuma casca o expõe de fora. Sempre ⚠.
- **`trusted_hash` do Codex**: o algoritmo não é reproduzível por fora (sha256 do
  `command`, do hook serializado em 4 formas e do script apontado — nenhum bate). Ele
  verifica a **presença** da aprovação em `[hooks.state]`, que é o que pega o defeito real
  (hook novo sem aprovação = pulado em silêncio), e marca o hash em si como ⚠.
- **Casca fora do registro**: se não sabe onde aquela casca guarda skills e hooks, diz
  isso e não mede — em vez de aprovar por omissão.

## O que ele não faz

Não instala, não conserta, não escreve na sala e **não roda `iachat status` numa sala que
ainda não existe** — `status` chama `garantir_estrutura()` e criaria o que deveria estar
diagnosticando. Auditor não é autor.
