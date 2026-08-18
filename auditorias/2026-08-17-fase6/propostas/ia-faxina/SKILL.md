---
name: ia-faxina
description: Limpeza automática e segura dos artefatos que o plugin ia-chat gera (.bak-iachat-* dos instaladores, logs dos daemons de sino, .tmp órfãos, flags de pendente sem dono). Padrão é DRY-RUN; nada some sem linha em faxina.log e backup do mesmo dia nunca se apaga. Use quando a sala acumular lixo, quando um instalador do ia-chat for re-rodado, ou periodicamente (ex.: semanal) — nunca para tocar em iachat.md, arquivo/ ou cursor de IA viva.
---

# IA-FAXINA — limpeza do que o ia-chat deixa para trás

O plugin cria arquivo novo e nunca recolhe. Esta skill é a coleta: roda o
`ia-faxina.py` (nesta pasta) contra a sala `IACHAT_HOME` (default
`~/ia-chat-global`) e as pastas das cascas.

## Quando usar

- Depois de re-rodar `ia-bell-install-hook.py` (cada corrida deixa um `.bak-iachat-*`).
- Quando `iachat status` mostrar a sala saudável mas `du -sh ~/ia-chat-global` crescer.
- Periodicamente (semanal) — a peça é idempotente: sem lixo, ela não faz nada.

## Como usar

```bash
python3 ~/.claude/skills/ia-faxina/ia-faxina.py            # DRY-RUN: só mostra
python3 ~/.claude/skills/ia-faxina/ia-faxina.py --aplicar  # limpa, logando tudo
python3 ~/.claude/skills/ia-faxina/ia-faxina.py --json     # para outra IA/gate ler
```

Teste sem tocar a sala real: `IACHAT_HOME=/tmp/sala-falsa python3 ia-faxina.py`.

## Política de retenção (declarada, não negociada em runtime)

| Categoria | Regra |
|---|---|
| `*.bak-iachat-*` por config | mantém os **3** mais recentes, só com **1+ dia** de idade; **backup do mesmo dia nunca se apaga** |
| `ia-bell-*.log` | acima de **500** linhas → apara para as últimas **200**; nunca apaga o arquivo (o daemon appenda nele) |
| `*.tmp` na sala | só com **5+ minutos**: é órfão certo de escrita atômica; mais novo pode ser escrita em curso |
| `pendente/<ia>.md` | remove **só** se `<ia>` não está mais em `na_sala`; flag de IA viva é intocável |
| `cursor/<ia>.json` órfão | **retido e relatado**: é estado (posição de leitura), não lixo |
| `arquivo/` (recortes) | **nunca**: histórico imutável e paginável |
| `iachat.md`, `config.json`, `.estado.json`, `.lock/` | **nunca** |

## Garantias

1. **Dry-run obrigatório como padrão** — `--aplicar` é opt-in explícito.
2. **Nada some sem log** — cada remoção deixa linha em `<sala>/faxina.log`
   (timestamp, caminho, bytes, motivo); dry-run também loga, marcado `[DRY-RUN]`.
3. **Idempotente** — a segunda corrida seguida reporta "nada a limpar".
4. **Sem race com o núcleo** — truncamento de log usa a mesma escrita atômica
   (tmp+replace) do `iachat_core.py`; lock do chat não é necessário porque a
   faxina não toca em nada que o `iachat` lê escrevendo.

## Risco declarado

- **Baixo, reversível até o log**: o único risco real é apagar um `.bak-iachat-*`
  que o dono ainda queria — mitigado por reter 3 + nunca tocar o do dia. Recortes
  de `arquivo/` e a sala viva estão fora do alcance por construção.
- Custo: uma varredura de diretórios; numa sala real mediu-se **< 0,1 s** e
  ~60 KB liberados na primeira corrida (2 bak excedentes + logs aparados).
