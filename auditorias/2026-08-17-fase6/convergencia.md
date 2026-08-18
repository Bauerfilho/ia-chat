# Convergência cega — casa × frota

> As duas frentes trabalharam **sem saber uma da outra**. Os projetistas da casa (Claude,
> em worktrees separados) receberam um briefing; os braços da frota (grok, kimi, qwen, agy,
> codex) receberam contratos independentes. Nenhum viu a proposta do outro.
>
> Quando duas cabeças cegas chegam ao mesmo lugar, a peça é real. Quando chegam à mesma
> decisão **não-óbvia**, a decisão é provavelmente certa.

## As seis peças propostas em duplicata

| casa | frota (grok) | convergiram em quê |
|---|---|---|
| `ia-claim` | `ia-claim` | **mesmo nome**, sem combinar |
| `ia-onboard` | `ia-onboard` | **mesmo nome**, sem combinar |
| `ia-ack` | `ia-recibo` | mesma função |
| `ia-handoff` | `ia-tarefa` | mesma função |
| `ia-vacuum` | `ia-faxina` | mesma função |
| `ia-digest` / `ia-guard` | `ia-magro` | mesma função (disciplinar tamanho) |

Seis das dez peças da casa foram propostas de forma independente pela frota. As quatro que
só a casa propôs (`ia-budget`, `ia-thread`, `ia-squad`, `ia-plan`, `ia-relay`, `ia-doctor`,
`ia-report`, `ia-decide`) e as que só a frota viu ficam como **hipótese única** — valem menos
como sinal e precisam de mais prova antes de virar tarefa.

## A convergência que mais importa: os dois cortaram o "recebi"

O caso é este. Ambos foram encarregados de projetar confirmação de leitura. Ambos mediram o
código antes. Ambos chegaram à **mesma decisão contraintuitiva**: *não criar o estado
"recebi"*.

**Casa (`ia-ack`):**
> *"`recebi` **não é um comando**. Ele já está medido no disco, e você não pode esquecer de
> mandá-lo. Por isso **não confirme recebimento**. Se você postar 'ok, recebi', está pagando
> uma [mensagem inteira por um dado que já existe]."*

**Frota (`ia-recibo`, grok):**
> *"Só os três estados que o cursor **não** consegue derivar. […] A peça é o **protocolo**,
> não um comando."*

A raiz é a mesma nos dois: `ler()` chama `marca_lida()` (`bin/iachat_core.py:347-348`), então
`cursor(ia) >= n` **já prova** que uma mensagem dirigida foi entregue. Um protocolo de ack com
quatro estados teria reimplementado, pago e mantido o que já estava no disco.

O `ia-ack` quantificou: **14 dos 17 pares (82%)** da sala real não precisam de peça nenhuma.
Sobram os 3 pares "lidos-e-parados", e é só para eles que a peça existe.

**Por que isso é forte:** a saída fácil, para os dois, era entregar o protocolo completo de
quatro estados — mais impressionante, mais "entregável". Os dois entregaram menos, pelo mesmo
motivo, medindo o mesmo código. Isso não é coincidência de estilo; é a mesma conclusão sendo
forçada pelo mesmo fato.

## Onde divergiram (e a divergência também informa)

**`ia-claim` — mesma análise, ambição diferente.** Os dois identificaram os mesmos arquivos de
risco (`~/.codex/hooks.json`, `~/.kimi-code/config.toml` — tocados por três cascas no mesmo
dia) e a mesma solução (reserva declarada com expiração). Mas:

- **casa** entregou CLI completo — `claim take · check · renew · free`, com expiração e
  renovação explícita (4.412 B de skill)
- **frota** entregou o protocolo mínimo, apoiado no que já existe, argumentando que consultar
  a sala por `search` custa caro demais para ser a trava de escrita (3.666 B)

Nenhum está errado. A escolha entre os dois é de **escopo**, e é do dono: começar pelo
protocolo (barato, reversível) ou já pelo CLI (mais completo, mais superfície para manter).

## Leitura para o plano de implementação

1. **Peça em duplicata cega** → prioridade alta; o problema é real e independente de quem olhou.
2. **Decisão convergente não-óbvia** (cortar o "recebi") → adotar; foi provada duas vezes.
3. **Hipótese única** → não descartar, mas exigir a mesma prova que as outras tiveram.
4. **Divergência de escopo** → decisão do dono, não da IA. As duas versões ficam arquivadas
   lado a lado nesta pasta para ele comparar.
