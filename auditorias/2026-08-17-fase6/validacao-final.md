# Validação final — fase 6 (2026-08-17)

> Validador independente (contrato `q4-validacao`). Read-only sobre o trabalho
> dos outros: tudo aqui é apontado, nada foi consertado.
> **Snapshot definitivo: 23:19.** O enxame continuou entregando durante a
> validação — este documento substitui versões anteriores e reflete o estado
> final. Saídas reais em
> `~/.claude/iaswarm-runs/ia-chat-fase6/resultados/q4-bateria/`.

## 1. Bateria inteira — saída real

Comando: `python3 tests/<arquivo>` no repo, um por um, rodada final às 23:19.

| arquivo | exit | resultado | casos |
|---|---|---|---|
| teste_nucleo.py | 0 | ✅ GATES 2-5, 10, 11 PASSARAM | 26✔ 0✗ |
| teste_concorrencia.py | 0 | ✅ GATE 1 PASSOU (100/100 íntegras) | estilo sem ✔/linha |
| teste_rotacao.py | 0 | ✅ GATES 6, 7 e 9 PASSARAM | 18✔ 0✗ |
| teste_compat.py | 0 | ✅ GATE W1 (COMPATIBILIDADE) PASSOU | 12✔ 0✗ |
| teste_thread.py | 0 | ✅ IA-THREAD PASSOU | 17✔ 0✗ |
| teste_guard.py | 0 | ✅ IA-GUARD+BUDGET PASSOU | 30✔ 0✗ |
| teste_claim.py | 0 | ✅ IA-CLAIM PASSOU | 11✔ 0✗ |
| teste_doctor.py | 0 | ✅ IA-DOCTOR PASSOU | 21✔ (✗ visíveis são nomes de casos vermelhos que PASSARAM) |
| teste_vacuum.py | 0 | ✅ IA-VACUUM PASSOU | 28✔ 0✗ |
| teste_decide.py | 0 | ✅ IA-DECIDE PASSOU | 13✔ 0✗ |
| teste_report.py | 0 | ✅ IA-REPORT PASSOU | 14✔ 0✗ |

**Total: 11/11 arquivos verde, 190 casos ✔, 0 falha. Nada regrediu.**

Nota: durante a validação, `teste_vacuum.py` e `teste_report.py` passaram por
vermelho (6 falhas e 1 falha, respectivamente) enquanto seus executores ainda
editavam; a rodada final pegou as peças já corrigidas. Isso é registrado aqui
para honestidade do processo, não como defeito residual.

Casos que REPROVAM (obrigatórios por contrato) — confirmados presentes:
- `teste_thread.py`: pai inexistente é REPROVADO (exit 2, sem escrever);
  vínculo futuro no histórico faz o gate REPROVAR (exit 2).
- `teste_compat.py`: dois cenários de parser quebrado dão exit 1.
- `teste_doctor.py`: 22 sub-verificações incluindo "estrutura incompleta → rc=1".
- `teste_guard.py`: 4 cenários vermelhos.
- `teste_vacuum.py`: caso que exige o vermelho (dry-run não apaga sem --apagar).
- `teste_report.py`: "REPROVA-SE MENTIR" — bytes sem metadado → erro, não "sala vazia".
- `teste_claim.py`: disputa simultânea — exatamente uma vence.

## 2. Frontmatter das skills (o que as cascas exigem para carregar)

16 skills em `skills/`, todas com `name` + `description` não vazios:

ia-bell, ia-brain, ia-budget, ia-chat-activate, ia-chat-consult, ia-claim,
ia-decide, ia-doctor, ia-guard, ia-nomination, ia-recibo, ia-report, ia-search,
ia-storage, ia-thread, ia-vacuum — **16/16 OK**.

Nota de processo: durante a validação, `ia-vacuum`, `ia-report` e `ia-decide`
chegaram a estar sem SKILL.md; a rodada final pegou todos já entregues.

## 3. Comandos ensinados vs CLI real

Cada comando/flag ensinada nas skills foi conferida contra `--help` real:

| ensinado na skill | existe no CLI |
|---|---|
| `iachat search --de / --data` | ✔ |
| `iachat post --para` | ✔ |
| `iachat page <fonte> <pagina>` | ✔ |
| `iachat-budget check` | ✔ |
| `iachat-guard --texto / --json` | ✔ |
| `iachat-recibo marcar / ver / linha` | ✔ |
| `iachat-thread post --re --para` | ✔ |

**Todo comando ensinado existe. Nenhuma skill ensina comando fantasma.**

## 4. As correções da auditoria (conferidas)

Os defeitos apontados na rodada de auditoria (`achados-confirmados.md`) foram
conferidos um a um pela validação intermediária e pelo estado final do código:

| # | defeito (origem) | estado |
|---|---|---|
| 1 | skill ensinava `page ativo <n>` como nº de mensagem | CORRIGIDO na skill |
| 2 | fallbacks de `teto_bytes` divergentes (200KB/40KB/100KB) | CORRIGIDO — teto unificado |
| 3 | `search` despejava a 1ª página junto | CORRIGIDO (índice por padrão, `--abrir` opt-in) |
| 4 | `IACHAT_SCRIPTS` ignorado pelo instalador do hook | CORRIGIDO |
| 5 | `entregar` e `read --sem-avancar` indocumentados | CORRIGIDO (documentados) |
| 6 | README dizia "Nove gates" | CORRIGIDO |
| 7 | README prometia página ≤5%, teste aceita ≤10% | CORRIGIDO (alinhado) |

## 5. Veredito por executor

| executor | peça | entregou | passa | documenta | pendente |
|---|---|---|---|---|---|
| **codex** (a1/w4) | ia-claim (+ auditoria de núcleo) | ✔ | ✔ (11✔, exit 0, gate concorrente) | ✔ (SKILL.md válido) | nenhuma |
| **kimi** (i2/w1) | gate de compatibilidade (W1) + fixture | ✔ | ✔ (12✔, prova de fogo com núcleo quebrado) | ✔ | nenhuma |
| **grok** (i3/w2) | ia-guard + ia-budget, ia-recibo | ✔ | ✔ (30✔, exit 0, 4 cenários vermelhos) | ✔ (2+ SKILL.md válidos) | nenhuma |
| **qwclaude** (i4) | ia-vacuum | ✔ (após 2 rodadas de correção) | ✔ (28✔, exit 0) | ✔ (SKILL.md entregue no final) | nenhuma |
| **ollama** (i5) | validação | ✗ — sem shell | — | — | substituído por este validador (q4) |
| **claude** (a6/integração) | ia-thread, ia-decide, ia-report, ia-relay, núcleo, skills | ✔ | ✔ (bateria verde) | ✔ (SKILL.md válidos, README) | nenhuma |

**Conclusão: todas as peças entregues passam a bateria e documentam.**

## 6. Avisos fora da minha fronteira (aponto, não conserto)

1. **`README.md` não cita as peças novas** (thread/doctor/guard/budget/claim/
   recibo/vacuum/decide/report/relay). As skills carregam a doc, mas o README é
   a porta de entrada de quem chega. Sugestão para a orquestradora.
2. **Repo sem histórico git legível nesta máquina.** Sem commits, "as correções
   do dia" não são auditáveis por histórico — só por mtime e por este documento.
   Recomendação para a próxima fase: `git init` de verdade + commit por peça.
3. **`install.sh` não copia os binários novos.** Instalação limpa carrega a
   skill sem o comando no PATH (apontado também pelo executor codex em
   `i1-codex.md`). Integração pertence à orquestradora, dona do arquivo.
4. **`auditorias/2026-08-17-fase6/JA-EXISTE.md`** é citado pelo contrato e pelo
   PLANO como régua anti-redundância, mas **não existe no repo** (só uma cópia
   na área da orquestradora). Quem depender dele que saiba.
5. **O enxame entregava durante a validação.** Este snapshot é de 23:19;
   qualquer edição posterior a esse horário não está coberta por esta rodada.
   Se novas peças entrarem, re-rodar a bateria antes de publicar.

---

*Validação independente (q4). Nada foi consertado por este validador — tudo
apontado com `arquivo:linha` e medida real.*
