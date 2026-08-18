---
name: ia-vacuum
description: Recolhe o lixo que o ia-chat produz — backups .bak-iachat-* dos instaladores, logs append-only do sino e .tmp órfãos da escrita atômica. Dry-run por padrão; apagar exige --apagar. Nunca toca arquivo/ (recorte é histórico) nem flag de pendente/ de IA que está na sala (é recado não lido).
---

# iachat-vacuum — a faxina do ia-chat

O plugin produz resto em três lugares e ninguém recolhe. Esta peça recolhe, e recolhe
**declarando o que preserva e por quê** — porque neste projeto quase todo arquivo que
parece lixo é dado de alguém.

```
iachat-vacuum                    # dry-run: mostra o plano, não toca em nada
iachat-vacuum --apagar           # executa exatamente o plano que o dry-run mostrou
iachat-vacuum --incluir-hoje     # deixa recolher backup do próprio dia (ver política)
iachat-vacuum --manter N         # cota de backups por família (padrão 8)
iachat-vacuum --json             # plano machine-parseable
```

## POLÍTICA DE RETENÇÃO — declarada

| Zona | Alvo | Verbo | Regra |
|---|---|---|---|
| **backup** | `~/.claude/settings.json.bak-iachat-*`<br>`~/.kimi-code/config.toml.bak-iachat-*` | apagar | guarda os **8 mais recentes** por família; o **#1 nunca sai**; **do dia não sai** sem `--incluir-hoje` |
| **log** | `$IACHAT_HOME/ia-bell-*.log` | recortar | guarda as **últimas 200 linhas** |
| **log** | `$IACHAT_HOME/ia-bell-*.{out,err}` | **zerar** | só acima de **64 KB**; trunca, **nunca apaga** |
| **tmp** | `$IACHAT_HOME/**/*.tmp` | apagar | só se **>60 min** de idade **E** o alvo final existe |
| **pendente** | `$IACHAT_HOME/pendente/<ia>.md` | apagar | **só** se `<ia>` não está em `config.json:na_sala` |
| **arquivo** | `$IACHAT_HOME/arquivo/*.md` | — | **nunca**, sob nenhuma flag |

### Por que 8, e por que a ordem não é por mtime

8 é o número da casa: `~/.claude/scripts/backup-claude.sh:17` (`KEEP_LOCAL=8`);
`backup.sh:43` guarda 10. Retenção por **contagem**, não por idade.

Mas a ordenação é por **carimbo no nome**, não por `mtime` — e essa é uma diferença
que importa. `ia-bell-install-hook.py:61` usa `shutil.copy2`, que **preserva o mtime do
original**. Medido no disco em 17/08: o backup `settings.json.bak-iachat-20260817-204719`
tem mtime `16 ago 18:44` — um dia de diferença. Um `ls -t`, como os scripts da casa
fazem, ordenaria essa família errado e apagaria o backup errado.

### Por que a regra "do mesmo dia não sai" é o padrão — e por que ela custa

Está declarada como inegociável e é o default. Mas ela precisa ser entendida com o
número: **todo o acúmulo de backup acontece dentro do mesmo dia**, durante depuração do
instalador (medido: 6 backups em 6 segundos, ver NOTA §2). Preservar tudo do dia faz o
vacuum ser um no-op exatamente na hora em que ele seria útil.

A saída é `--incluir-hoje`: fica **desligada** por padrão (a regra vale à risca, sem
exceção silenciosa) e o dono liga de olho aberto, com o dry-run na frente mostrando
arquivo por arquivo o que vai sair. O `#1 mais recente` continua protegido mesmo com a
flag ligada — essa não tem override.

## O QUE ELE NUNCA TOCA

**`arquivo/*.md` — recorte é histórico, e apagar corrompe a numeração.**
`iachat_core.py:480 rotate()` faz `nn = len(_recortes()) + 1` e grava com `write_text`
puro, sem checar existência. Apagar o `recorte-01` faz a rotação seguinte renumerar
para `02` e **sobrescrever em silêncio** o `recorte-02` do mesmo dia. Além disso, cada
recorte tem uma marca viva no ativo apontando `arquivo/<nome>`: apagar o alvo deixa
ponteiro pendurado e quebra o `iachat search`.

**`pendente/<ia>.md` de IA na sala — é mensagem não lida.**
`post()` grava uma por nominado (`iachat_core.py:254`) e `marca_lida()` apaga ao ler
(`:308-315`). É **limitada a uma por IA**: não acumula, logo não é problema de espaço.
Só vira órfã quando a IA sai de `config.json:na_sala` — aí `post()` nunca mais a
reescreve (destinos são filtrados por `x in sala`), `status()` nem a lista, e nenhum
`read` a consome. Está estruturalmente morta. **Mesmo essa** tem o conteúdo copiado
inteiro para o registro antes de sumir: o recado muda de lugar, não se perde.

**`.bak` sem `-iachat-` — é backup de outro dono.**
Medido em 17/08: **17 arquivos `.bak*` em `~/.claude` + `~/.kimi-code`, e só 2 são do
ia-chat**. Um glob `*.bak*` levaria junto `config.toml.bak-antes-oauth-20260813`. O
glob aqui é `<base>.bak-iachat-<8dígitos>-<6dígitos>` e o nome ainda é reconferido
contra a regex antes de qualquer ação.

**`.out`/`.err` — são do launchd, não nossos.**
`ia-bell-install-daemon.sh:38-39` define `StandardOutPath`/`StandardErrorPath`, e o
`lsof` de 17/08 mostrou `bash 49797` segurando **fd 1u e 2u** nesses inodes. Apagar não
libera byte nenhum: o inode fica preso ao descritor e o arquivo só reaparece no próximo
restart do daemon. Por isso o verbo é **zerar** (`truncate(0)`, inode preservado).

## GARANTIAS

- **Dry-run é o padrão.** Sem `--apagar`, escreve zero bytes — nem o registro.
- **O ensaio não pode divergir do ato.** `planejar()` devolve uma lista de `Acao`; o
  dry-run imprime essa lista e a execução consome **a mesma lista**. Não há dois
  caminhos de código para diferir.
- **Idempotente.** A 2ª rodada não acha nada e diz por quê, com a data da anterior
  (`.vacuum.json`) — mesmo contrato do `rotate()` (`iachat_core.py:480`), que devolve
  `{"rodou": False, "motivo": ...}`.
- **Nada sai sem registro.** `$IACHAT_HOME/.vacuum.log`, append-only + `fsync`: uma
  linha por ação com caminho, bytes e motivo.
- **A zona proibida aparece no relatório.** `arquivo/` é listado como preservado em
  toda rodada. Proteção que não se enxerga não se audita.

## TESTE

`IACHAT_HOME` desvia a sala (`iachat_core.py:57-59`) e `HOME` desvia os diretórios de
backup — as duas costuras que permitem testar sem encostar em nada real. Bateria: `python3 tests/teste_vacuum.py` (dry-run, apagar, idempotência
e o vermelho de propósito, em sala falsa dentro de /tmp).

## LIMITE CONHECIDO

O recorte de `.log` é `read` + `os.replace`. O daemon reabre o arquivo a cada `echo >>`
(`ia-bell-daemon.sh:69`), então ele passa a escrever no inode novo — mas **uma linha
escrita na janela entre o read e o replace se perde**. Aceito: a perda máxima é uma
linha de aviso já entregue por notificação, e o alvo nunca é o chat, só o log do sino.
