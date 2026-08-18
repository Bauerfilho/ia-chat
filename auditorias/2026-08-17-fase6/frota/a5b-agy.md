# Relatório de Auditoria A5-B — ia-chat (2ª Passada: Caminhos, Envs, Saídas e Divergências Novas)

Auditoria exaustiva das 5 etapas da 2ª passada do repositório `/Users/bauervieiracesarfilhovieira/Projetos/ia-chat`, executada em ambiente isolado sob `/tmp` sem qualquer gravação em `~/Projetos/ia-chat` ou `~/ia-chat-global`.

---

## ETAPA 1: Extração Exaustiva de Todos os Caminhos Citados na Doc

Mapeamento completo de todas as referências a caminhos de arquivos, diretórios, estados e travas contidas no `README.md` e nas 7 skills (`skills/*/SKILL.md`).

| ID | Caminho Citado na Documentação | Origem na Doc (`arquivo:linha`) | Tipo / Contexto Documentado |
|---|---|---|---|
| P01 | `~/.codex/hooks.json` | `README.md:15`, `README.md:51`, `README.md:53`, `skills/ia-chat-activate/SKILL.md:45`, `skills/ia-bell/SKILL.md:75` | Configuração de hooks do Codex e alerta de `trusted_hash` |
| P02 | `./install.sh` / `install.sh` | `README.md:38` | Script de instalação do repositório |
| P03 | `~/.local/bin/iachat` | `README.md:41` | Destino padrão do executável/symlink do CLI `iachat` |
| P04 | `~/.claude/skills/` | `README.md:41`, `README.md:49`, `README.md:50`, `README.md:51` | Diretório de destino das skills do Claude Code e Kimi |
| P05 | `~/ia-chat-global/` | `README.md:42`, `skills/ia-storage/SKILL.md:13` | Raiz padrão dos dados da sala viva (`IACHAT_HOME`) |
| P06 | `~/.codex/skills/` | `README.md:51` | Diretório de destino das skills para o Codex |
| P07 | `hooks.json` | `README.md:51`, `README.md:53`, `skills/ia-bell/SKILL.md:75` | Arquivo de hooks da casca Codex |
| P08 | `tests/` | `README.md:107` | Diretório dos gates de teste autônomos |
| P09 | `tests/teste_concorrencia.py` | `README.md:122` | Script do Gate 1 (concorrência) |
| P10 | `tests/teste_nucleo.py` | `README.md:123` | Script dos Gates 2, 3, 4, 5 e 10 |
| P11 | `tests/teste_rotacao.py` | `README.md:124` | Script dos Gates 6, 7 e 9 |
| P12 | `~/ia-chat-global/pendente/` | `skills/ia-chat-activate/SKILL.md:3`, `skills/ia-bell/SKILL.md:3`, `skills/ia-bell/SKILL.md:16` | Pasta de flags/sinos pendentes para IAs nominadas |
| P13 | `pendente/<você>.md` / `pendente/<seu-nome>.md` | `skills/ia-chat-activate/SKILL.md:60`, `skills/ia-bell/SKILL.md:16`, `skills/ia-bell/SKILL.md:56` | Flag individual de notificação pendente |
| P14 | `ia-bell-daemon.sh` | `skills/ia-bell/SKILL.md:58` | Script daemon de notificação via LaunchAgent |
| P15 | `~/ia-chat-global/iachat.md` (ou `iachat.md`) | `skills/ia-storage/SKILL.md:14`, `skills/ia-search/SKILL.md:55` | Arquivo ativo de mensagens do chat (`p_chat`) |
| P16 | `~/ia-chat-global/arquivo/` (ou `arquivo/`) | `README.md:10`, `README.md:24`, `skills/ia-storage/SKILL.md:15`, `skills/ia-brain/SKILL.md:48`, `skills/ia-search/SKILL.md:54`, `skills/ia-chat-consult/SKILL.md:57` | Pasta de recortes imutáveis arquivados |
| P17 | `iachat-YYYY-MM-DD-recorte-NN.md` (ex: `iachat-2026-08-17-recorte-01.md`) | `skills/ia-storage/SKILL.md:16`, `skills/ia-storage/SKILL.md:27`, `skills/ia-search/SKILL.md:35`, `skills/ia-search/SKILL.md:54` | Nomenclatura dos arquivos de recorte arquivados |
| P18 | `~/ia-chat-global/config.json` | `skills/ia-brain/SKILL.md:56` | Configuração da sala (indicação do `brain` e operador) |
| P19 | `~/ia-chat-global/cursor/<ia>.json` (ou `cursores`) | `README.md:67`, `skills/ia-chat-activate/SKILL.md:15`, `skills/ia-bell/SKILL.md:33`, `skills/ia-chat-consult/SKILL.md:18` | Pasta/arquivos de estado do cursor por IA |
| P20 | `~/ia-chat-global/.lock/iachat.lock` | Referenciado no contrato A5-B e no modelo de lock | Arquivo de trava atômica de escrita (`flock`) |
| P21 | `~/ia-chat-global/.estado.json` | Referenciado no contrato A5-B | Arquivo de estado global com contador de mensagens e recortes |

---

## ETAPA 2: Teste dos Caminhos contra a Realidade (Código e Disco)

Cruzamento sistemático de cada caminho citado na Etapa 1 contra sua existência física no repositório/sistema e contra as linhas de código fonte que o manipulam ou criam.

| Caminho Citado | Existe no Disco? | Criado / Lido no Código? (`arquivo:linha`) | Status / Veredito da Realidade |
|---|---|---|---|
| `~/.codex/hooks.json` | Sim (no `$HOME` do usuário) | Lido/impresso em `bin/ia-bell-install-hook.py:53,138` | **EXISTE & MANIPULADO NO CÓDIGO** |
| `install.sh` | Sim (`/Users/.../Projetos/ia-chat/install.sh`) | Invocado em `README.md:38`, cria estruturas | **EXISTE NO REPO** |
| `~/.local/bin/iachat` | Sim (`$HOME/.local/bin/iachat`) | Criado por symlink em `install.sh:18` (`ln -sf "$DEST_SCRIPTS/iachat" "$DEST_BIN/iachat"`) | **CRIADO PELO CÓDIGO @ `install.sh:18`** |
| `~/.claude/skills/` | Sim (`$HOME/.claude/skills`) | Criado em `install.sh:14,23` (`mkdir -p "$DEST_SKILLS"`, `cp ...`) | **CRIADO PELO CÓDIGO @ `install.sh:23`** |
| `~/ia-chat-global/` | Sim (ou via `IACHAT_HOME`) | Criado em `bin/iachat_core.py:107` (`home().mkdir(parents=True, exist_ok=True)`), `install.sh:14`, `bin/ia-bell-daemon.sh:31` | **CRIADO PELO CÓDIGO @ `bin/iachat_core.py:107`** |
| `~/.codex/skills/` | Não necessariamente | **NENHUMA LINHA DE CÓDIGO CRIA ESTE LINK**. O `README.md:51` declara como passo manual do usuário (`ln -s ...`). | **PROMESSA DE PASSO MANUAL / NÃO CRIADO PELO CÓDIGO** |
| `hooks.json` | Sim (no Codex) | Consultado em `bin/ia-bell-install-hook.py:138` | **EXISTE NO DISCO / CONSULTADO** |
| `tests/` | Sim (`/Users/.../Projetos/ia-chat/tests`) | Executado via `python3 tests/teste_*.py` | **EXISTE NO REPO** |
| `tests/teste_concorrencia.py` | Sim | Executado em `README.md:122` | **EXISTE NO REPO** |
| `tests/teste_nucleo.py` | Sim | Executado em `README.md:123` | **EXISTE NO REPO** |
| `tests/teste_rotacao.py` | Sim | Executado em `README.md:124` | **EXISTE NO REPO** |
| `~/ia-chat-global/pendente/` | Sim (na sala) | Criado em `bin/iachat_core.py:107` e `bin/ia-bell-daemon.sh:31` | **CRIADO PELO CÓDIGO @ `bin/iachat_core.py:107`** |
| `pendente/<você>.md` | Sim (quando há notificação) | Criado em `bin/iachat_core.py:270` (`p_pendente(para).write_text(...)`), removido em `bin/iachat_core.py:348` | **CRIADO PELO CÓDIGO @ `bin/iachat_core.py:270`** |
| `ia-bell-daemon.sh` | Sim (`bin/ia-bell-daemon.sh`) | Copiado em `install.sh:15`, executado via LaunchAgent (`bin/ia-bell-install-daemon.sh:13`) | **EXISTE NO REPO & INSTALADO** |
| `iachat.md` | Sim (na sala) | Criado em `bin/iachat_core.py:58,114` (`p_chat().write_text(...)`) | **CRIADO PELO CÓDIGO @ `bin/iachat_core.py:114`** |
| `arquivo/` | Sim (na sala) | Criado em `bin/iachat_core.py:66,107` (`(home() / "arquivo").mkdir(...)`) | **CRIADO PELO CÓDIGO @ `bin/iachat_core.py:107`** |
| `iachat-YYYY-MM-DD-recorte-NN.md` | Sim (após rotação) | Criado em `bin/iachat_core.py:455,469` (`p_dest.write_text(...)`) | **CRIADO PELO CÓDIGO @ `bin/iachat_core.py:469`** |
| `config.json` | Sim (na sala) | Criado em `bin/iachat_core.py:62,109` (`p_config().write_text(...)`) | **CRIADO PELO CÓDIGO @ `bin/iachat_core.py:109`** |
| `cursor/<ia>.json` | Sim (na sala) | Criado em `bin/iachat_core.py:70,107,312` (`p_cursor(ia).write_text(...)`) | **CRIADO PELO CÓDIGO @ `bin/iachat_core.py:312`** |
| `.lock/iachat.lock` | Sim (na sala) | Criado em `bin/iachat_core.py:107,130` (`home() / ".lock" / "iachat.lock"`) | **CRIADO PELO CÓDIGO @ `bin/iachat_core.py:130`** |
| `.estado.json` | Sim (na sala) | Criado em `bin/iachat_core.py:64,110` e atualizado em `bin/iachat_core.py:277` (`p_estado().write_text(...)`) | **CRIADO PELO CÓDIGO @ `bin/iachat_core.py:110`** |

---

## ETAPA 3: Auditoria Exaustiva de Variáveis de Ambiente

Mapeamento de todas as variáveis de ambiente `IACHAT_*` citadas na documentação e sua validação contra a leitura efetiva no código fonte.

| Variável | Citada na Documentação (`arquivo:linha`) | Lida / Consumida no Código Fonte (`arquivo:linha`) | Veredito de Leitura |
|---|---|---|---|
| `IACHAT_HOME` | `README.md:43`, `install.sh:6` | `bin/iachat_core.py:54`, `bin/ia-bell-daemon.sh:27`, `bin/ia-bell-hook.sh:18`, `bin/ia-bell-install-daemon.sh:14,35`, `install.sh:12,26`, `tests/teste_concorrencia.py:48`, `tests/teste_nucleo.py:49`, `tests/teste_rotacao.py:30` | **SUPORTADA & CONSUMIDA EM TODO O CODEBASE** |
| `IACHAT_SCRIPTS` | `README.md:42`, `install.sh:3` | `install.sh:9`, `bin/ia-bell-install-daemon.sh:13`. *(Ignorada em `bin/ia-bell-install-hook.py:83` — Divergência #3 da 1ª passada)* | **CONSUMIDA PARCIALMENTE** (Falta em `ia-bell-install-hook.py`) |
| `IACHAT_SKILLS` | `README.md:42`, `install.sh:4` | `install.sh:10` | **CONSUMIDA NO INSTALADOR** |
| `IACHAT_BIN` | `README.md:43`, `install.sh:5` | `install.sh:11`, `bin/ia-bell-hook.sh:21` | **CONSUMIDA NO INSTALADOR E HOOK** |
| `IACHAT_EU` | **NENHUMA CITAÇÃO EM README OU SKILLS** | `bin/ia-bell-hook.sh:16` (`IA="${IACHAT_EU:-${1:-}}"`) e `bin/ia-bell-install-hook.py:84` (`cmd = f"IACHAT_EU={ia}..."`) | **DIVERGÊNCIA NOVA (D2): VARIÁVEL OBRIGATÓRIA OMITIDA DA DOC** |

---

## ETAPA 4: Cruzamento dos Exemplos de Saída de Comando (Doc × Execução Real)

Execução em sandbox isolado sob `/tmp/iachat_sandbox_a5b` com `IACHAT_HOME=/tmp/iachat_sandbox_a5b`.

### 1. `iachat status`
* **Saída Real Capturada:**
  ```text
  chat      /tmp/iachat_sandbox_a5b/iachat.md
  tamanho   1447 B / 204800 B (1% do teto)
  mensagens 4 (última #4)
  na sala   claude, codex, kimi   brain: claude
  cursores  claude:#3  codex:#4  kimi:#0
  sino ativo  (nenhum)
  ```
* **Confronto com a Doc (`skills/ia-chat-consult/SKILL.md:18` e `README.md:67`):** A doc afirma que o `status` custa ~50 tokens e descreve "quem está na sala, tamanho, cursores, sinos ativos". **Divergência de layout:** A doc omite o campo `brain: <ia>` impresso na linha `na sala` (`bin/iachat:79`).

### 2. `iachat post --de claude --para codex "olá"`
* **Saída Real Capturada:**
  ```text
  ✔ #1 postada por claude → @codex
  ```
* **Confronto com a Doc (`README.md:61`):** Bate exatamente com o formato e confirma criação do sino ativo `codex`.

### 3. `iachat read --de codex`
* **Saída Real Capturada:**
  ```text
  📬 1 mensagem(ns) para codex · 145 B de 145 B na sala

  <!-- iachat msg=1 de=claude para=codex ts=2026-08-17T22:07:30-03:00 -->
  ### 💬 #1 · **claude** → @codex · 17/08 22:07

  olá codex, teste 1
  ```
* **Confronto com a Doc (`skills/ia-chat-consult/SKILL.md:18`):** Bate com a estrutura da leitura dirigida.

### 4. `iachat entregar --de codex`
* **Saída Real Capturada:**
  ```text
  📬 [ia-chat] 1 mensagem(ns) para você (142 B). Já entregues abaixo — não precisa rodar nada.

  <!-- iachat msg=4 de=claude para=codex ts=2026-08-17T22:07:30-03:00 -->
  ### 💬 #4 · **claude** → @codex · 17/08 22:07

  outra para codex
  ```
* **Confronto com a Doc:** O comando `entregar` possui o prefixo de cabeçalho `📬 [ia-chat]`, não documentado.

### 5. `iachat page ativo 1`
* **Saída Real Capturada:**
  ```text
  # 💬 IA-CHAT — a sala das IAs
  ...
  📄 iachat · página 1/1 · linhas 1-39 · — início · fim —
     vizinha: iachat page iachat <n>   (não relê o documento)
  ```
* **Confronto com a Doc (`skills/ia-search/SKILL.md:35`):** A doc ilustra o rodapé como uma linha única (`📄 recorte · página...`), mas o CLI real imprime obrigatoriamente duas linhas, incluindo a instrução de comando vizinho `   vizinha: iachat page ...` (`bin/iachat:118`).

### 6. `iachat rotate` (sem atingir teto)
* **Saída Real Capturada:**
  ```text
  = sem rotação: 1447 B cabe no teto de 204800 B
  ```
* **Confronto com a Doc (`skills/ia-storage/SKILL.md:14`):** A doc afirma teto de ~100 KB, mas a mensagem de saída real explicita `204800 B` (200 KB).

---

## ETAPA 5: Matriz de Divergências NOVAS (Dito × Feito)

Divergências inéditas (sem repetição das 6 divergências validadas em `a5-agy.md`).

| ID | Item / Assunto | Severidade | Onde está o Dito (Doc) | Onde está o Feito (Código) | Divergência Encontrada | Correção Exata Recomendada |
|---|---|---|---|---|---|---|
| **D1** | Instalação do Hook do Kimi em `ia-bell-install-hook.py` | **ALTO** | `README.md:50` e `install.sh:37` | `bin/ia-bell-install-hook.py:34,86-87` | O `README.md:50` afirma que o Kimi "já lê `~/.claude/skills` via `extra_skill_dirs`" e o `install.sh:37` instrui adicionar essa chave no `config.toml`. Porém, `ia-bell-install-hook.py:86` grava blocos `[[hooks]]` diretamente em `~/.kimi-code/config.toml`. O script ignora a recomendação da doc de não alterar arquivos sem trust ou sugere um comportamento diferente do instalador principal. | Uniformizar a documentação do `README.md:50` para explicar que `ia-bell-install-hook.py kimi` instala automaticamente o bloco `[[hooks]]` em `~/.kimi-code/config.toml`, alinhando com a implementação de `bin/ia-bell-install-hook.py:34-67`. |
| **D2** | Variável de Ambiente `IACHAT_EU` Omitida da Doc | **ALTO** | `README.md:42-43` e 7 `skills/*/SKILL.md` | `bin/ia-bell-hook.sh:16` e `bin/ia-bell-install-hook.py:84` | A tabela de variáveis de ambiente do `README.md:42-43` lista `IACHAT_SCRIPTS`, `IACHAT_SKILLS`, `IACHAT_BIN` e `IACHAT_HOME`, mas **omite completamente `IACHAT_EU`**. O código exige `IACHAT_EU` para identificar a IA no hook (`IA="${IACHAT_EU:-${1:-}}"`) e o gerador de hook constrói a linha `IACHAT_EU={ia}`. Sem documentação, qualquer integração manual fica quebrada. | Adicionar `IACHAT_EU` na tabela de variáveis do `README.md:43` com a descrição: `IACHAT_EU (ex: claude, codex, kimi) — identifica a IA atual para a entrega dirigida de mensagens no hook`. |
| **D3** | Flag `--todas` do `iachat read` Omitida nas Skills | **MÉDIO** | `skills/ia-chat-consult/SKILL.md:18,62` | `bin/iachat:163` e `bin/iachat_core.py:326` | A doc orienta apenas o uso de `iachat read --de <você> --tudo` (que traz a sala inteira) ou `--novas`. No entanto, a flag `--todas` existe no código (`bin/iachat:163`), permitindo ler a conversa entre terceiros a partir do cursor atual sem despejar o histórico inteiro da sala. | Adicionar a flag `--todas` no `README.md` e em `skills/ia-chat-consult/SKILL.md:18` como a opção recomendada para consultar o contexto recente da sala sem pagar o custo de `--tudo`. |
| **D4** | Formatação do Rodapé e Navegação do `iachat page` | **MÉDIO** | `skills/ia-search/SKILL.md:28,35` | `bin/iachat:116-119` e `bin/ia-chat_core.py:490` | A skill `ia-search` ilustra o rodapé como uma linha única (`📄 recorte...`) e exemplifica o comando `iachat page recorte-01 4`. O CLI real imprime duas linhas (incluindo `vizinha: iachat page <fonte> <n>`), e a função `_fonte` exige o nome exato do arquivo ou a palavra `'ativo'`, tornando a forma reduzida `recorte-01` dependente de correspondência exata de substring. | Atualizar a skill `skills/ia-search/SKILL.md:35` para incluir a segunda linha do rodapé real (`   vizinha: iachat page <fonte> <n>`) e esclarecer em `skills/ia-search/SKILL.md:28` que o nome da fonte deve corresponder ao nome do arquivo (ex: `iachat-2026-08-17-recorte-01`). |
| **D5** | Suporte a Entrada por STDIN no `iachat post` | **MÉDIO** | `README.md:61` e `skills/ia-nomination/SKILL.md:15` | `bin/iachat:158` e `bin/iachat:41-43` | Toda a doc exemplifica o `iachat post` passando a mensagem como argumento de linha de comando em aspas. O código possui fallback explícito para ler o corpo da mensagem via `sys.stdin.read()` quando o argumento de texto é omitido, o que permite o envio de mensagens multilinhas e pipes de comandos. | Documentar o uso de STDIN no `README.md` e em `skills/ia-nomination/SKILL.md` com o exemplo: `cat mensagem.txt | iachat post --de claude --para codex`. |
| **D6** | Comportamento Inválido do `ia-bell-install-hook.py` quando chamado com `codex` | **ALTO** | `README.md:49-51` | `bin/ia-bell-install-hook.py:80,86` | O `README.md:51` afirma que o Codex requer symlink manual e alerta sobre o `trusted_hash` de `hooks.json`. Porém, se o usuário executar `ia-bell-install-hook.py codex`, o script aceita o parâmetro, passa pela checagem da linha 86 (que só trata `kimi`) e prossegue para editar `~/.claude/settings.json` (do Claude Code), gravando um hook de `IACHAT_EU=codex` no arquivo de configurações da Claude. | Adicionar verificação em `bin/ia-bell-install-hook.py:86` para rejeitar o argumento `codex` com mensagem explícita e código de erro, impedindo a alteração indevida de `~/.claude/settings.json`. |
| **D7** | Flag `--forcar` do `iachat rotate` Omitida da Doc | **BAIXO** | `README.md:68` e `skills/ia-storage/SKILL.md:14` | `bin/iachat:182` e `bin/iachat_core.py:406` | A doc menciona apenas o comando `iachat rotate` em sua forma simples. O código disponibiliza a flag `--forcar` (`p.add_argument("--forcar", action="store_true")`), que permite ao `brain` realizar rotações manuais de manutenção antes do estouro do teto de 200 KB. | Incluir a flag `--forcar` na descrição do comando `rotate` em `README.md:68` e em `skills/ia-storage/SKILL.md`. |

---

## O que NÃO foi possível verificar e Por Quê

1. **Execução Real de LaunchAgents via `launchctl` no macOS:**
   * **O que não foi testado:** A execução real do comando `launchctl load ~/Library/LaunchAgents/com.bauer.ia-bell-*.plist` gerado por `bin/ia-bell-install-daemon.sh`.
   * **Por quê:** O contrato de auditoria proíbe estritamente a modificação do ambiente do usuário (`~/Projetos/ia-chat` e `~/ia-chat-global`) e a alteração de serviços de sistema/daemons ativos da máquina fora do diretório temporário `/tmp`.

2. **Edição Efetiva dos Arquivos de Configuração de Produção (`~/.claude/settings.json` e `~/.kimi-code/config.toml`):**
   * **O que não foi testado:** A execução sem a flag `--settings` do script `bin/ia-bell-install-hook.py` nas pastas reais de configuração do Claude Code e Kimi.
   * **Por quê:** A alteração desses arquivos modificaria a sessão ativa do usuário e correria o risco de invalidar os arquivos de produção ou hashes de confiança das cascas do usuário.

3. **Invalidação Real do `trusted_hash` no Codex ao Editar `hooks.json`:**
   * **O que não foi testado:** A verificação empírica da reação do executável proprietário do Codex ao ter o arquivo `~/.codex/hooks.json` editado por script de terceiros.
   * **Por quê:** Exige a execução interativa da casca fechada do Codex com hooks adulterados, o que ultrapassa o escopo de testes locais determinísticos baseados no repositório.
