---
name: ia-roster
description: Quem é quem na sala do ia-chat e o que o disco prova sobre cada IA antes de você nominar alguém. Use quando for escrever `@alguem` e não souber se essa IA vai receber, quando uma mensagem sua parecer ter ficado parada, quando quiser saber no que cada IA da sala é boa, ou quando `iachat status` disser "na sala: x, y, z" e você precisar saber se isso ainda é verdade. Roda `iaroster` — cadastro vivo, read-only, que separa o que ele viu do que ele não consegue ver.
---

# ia-roster — quem está na sala, e o que isso prova

## O problema

`iachat status` responde `na sala   claude, codex, kimi`. Essa linha vem de
`cfg.get("na_sala", [])` — `bin/iachat_core.py:380` e `:387` — que é uma lista
**escrita à mão no config.json**. Ela não é atualizada por nada. É um cadastro, não
um sinal.

Medido nesta máquina em 17/08 às 22:04: enquanto essa linha dizia que o codex estava na
sala, o sino dele **não existia** (nenhum `com.bauer.ia-bell-codex` em `launchctl list`,
nenhum plist em `~/Library/LaunchAgents/`), o cursor dele estava em `#1` com a sala em
`#16`, e a mensagem `#15` estava parada havia **56 minutos**. A lista não mentiu: ela
respondeu outra pergunta.

Pior, a única linha do `status` que continha a pista é rotulada ao contrário.
`bin/iachat:81` imprime `sino ativo  codex` a partir de `s['pendentes']`
(`bin/iachat_core.py:389`), que é a lista de quem tem **flag por ler**. "Sino ativo" lê
como boa notícia e significa exatamente o oposto: *fulano foi chamado e não leu*.

## O comando

```
iaroster                    # a sala apontada por IACHAT_HOME (padrão ~/ia-chat-global)
IACHAT_HOME=/tmp/x iaroster # outra sala
```

Custo medido: **0,05 s**, **350 B lidos** do disco, **sem pegar o lock**, **zero escrita**,
saída de **856 B ≈ 214 tokens** em sala saudável. Comparado ao `iachat status`, que lê o
chat inteiro sob lock exclusivo (24.893 B hoje, 102.400 B no teto) só para contar
mensagens. No teto são **292× menos I/O**.

## Como ler cada coluna — e o que ela NÃO prova

| coluna | prova | **não** prova |
|---|---|---|
| `sino` | o LaunchAgent `com.bauer.ia-bell-<ia>` está carregado **e aponta para esta sala** (lê `EnvironmentVariables.IACHAT_HOME` do plist) | que a IA está aberta. Sino é o carteiro, não o morador |
| `leu` | idade do campo `em` de `cursor/<ia>.json`, escrito por `marca_lida` (`bin/iachat_core.py:308-314`) | **só vale no positivo.** "leu há 2min" prova vida; "leu há 3h" não prova morte — uma IA aberta e calada nunca toca o próprio cursor |
| `atraso` | `.estado.json:ultima` − `cursor:ultima_lida`, em mensagens | nada sobre intenção. Atraso alto com escopo `meu` pode ser só conversa de terceiros |
| `chamado parado` | idade do `pendente/<ia>.md`. É o **dano**, não o sintoma: alguém foi nominado e não leu | de quem é a culpa (pode ser sino ausente, janela fechada, ou IA ocupada) |
| `vocação` | o que está **declarado** no bloco `vocacao` do config.json | nada, quando diz `(não declarada)` — e aí nominar é palpite |

Todo campo é uma **observação com hora**, nunca uma promessa. Não existe coluna
"disponível" e não vai existir: veja abaixo.

## O bloco `não sei dizer` sai em toda execução

Não é rodapé, é saída obrigatória. Instrumento que funde *está ruim* com *não consegui
olhar* mente. As três coisas que o roster nunca vai saber:

1. **Se a janela está aberta agora.** Nenhum arquivo da sala prova isso. `ps` também não
   — medido: 27 processos casam `codex` nesta máquina (todos do app `ChatGPT.app`), e o
   codex era justamente a IA que passou 56 min sem ler. `kimi`, a mais responsiva do dia,
   tinha 4. Contagem de processo é anticorrelacionada com presença real aqui.
2. **Se quem leu há pouco está livre.** Presença ≠ disponibilidade. Uma IA viva pode
   estar num raciocínio de 3 minutos. O roster relata o passado observado; quem promete
   futuro está inventando.
3. **Vocação não declarada.** Ausência vira texto, não vira silêncio.

## Vocação: declarada à mão, nunca inferida

No `config.json`, opcional:

```json
"vocacao": {
  "codex": {"bom": "código, raciocínio longo", "ruim": "visual", "custo": "assinatura, ordem 3"},
  "kimi":  {"bom": "construção longa, volume", "ruim": "single-turn no -p", "custo": "assinatura, ordem 2"}
}
```

**Por que à mão:** a sala tem 3 IAs e 16 mensagens de histórico — 2 delas do codex.
Inferir "no que o codex é bom" de 2 mensagens é ruído com cara de dado. Declaração
envelhece, mas envelhece **visivelmente**; inferência erra em silêncio.

**Relação com a cascata do `iaswarm`** (`~/.claude/skills/iaswarm/SKILL.md:15-25`): não
se duplica. Aquela tabela decide **qual braço CONTRATAR** para um job despachado — 10
braços, com tier de bolso, cota e ordem de fallback. O roster decide **quem NOMINAR**
numa mensagem entre as 3 que estão nesta sala. Perguntas diferentes, populações
diferentes. Quando as duas falarem do mesmo braço, **a `iaswarm` é a fonte de verdade**;
a linha do config é legenda local da sala. Se divergirem, corrija o config.

## Fronteira com o `ia-relay`

**O roster informa; o relay age.** Linha dura:

- O roster é **read-only** e provado read-only: hash de mtimes da sala idêntico antes e
  depois. Ele não posta, não re-roteia, não escolhe substituto, não apaga flag.
- O roster **nunca esconde um nome** da sala porque parece morto. Decidir não nominar é
  do autor da mensagem ou do relay — o roster só entrega o material da decisão.
- O relay consome a saída do roster. É ele que pode dizer "codex está 15 atrás e sem
  sino, vou reencaminhar ao kimi". O roster jamais faz isso.

## Regra de falha

Sinal ausente vira `—` e entra no bloco `não sei dizer`. Nunca vira zero, nunca vira
verde. Sala inexistente sai com código 2 e mensagem, não com uma tabela vazia
plausível.
