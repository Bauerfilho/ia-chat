# PROJETO `groupchat` — o segundo chat: várias IAs, um lugar, o ruído dobrado

> Síntese de três laudos independentes (25 KB + 11 KB + 4 KB) mais o padrão que o dono
> apontou dentro do próprio Claude Code. **Nada foi construído ainda.**

## O que ele quer

> *"complementar o app com um segundo chat que roteia as mensagens do terminal de todos
> que eu ativar para lá é o meu objetivo final"* · *"cada IA vai trabalhar no seu terminal
> independente usando a sua janela"* · *"todo processo que eu solicitar a IA fazer ela vai
> me devolver apenas o resultado"*

E o layout, ditado por ele:

> *"abre uma linha em cima e outra embaixo, nome da IA com a corzinha dela e a janelinha
> de contexto se expressando numa barrinha… a cada resposta vai mostrar o contexto **da
> IA**, e não do chat, assim podemos saber melhor **a quem cabe mais tarefas antes de
> compactar**"*

⭐ **Essa última frase é o produto.** A barra não é enfeite: é gestão de recurso visível.
Hoje se descobre que um braço está no limite quando ele morre — a Qwen estourou a cota e
só apareceu no log.

---

## 1. A decisão de arquitetura, e ela vem de uma frase do laudo

> *"Se a barra deve representar 'contexto da IA, não do chat', cada IA precisa de um
> **`session_id` próprio e persistente**. Alternar apenas `/model` dentro de uma sessão
> única produz uma **única janela comum** — exatamente o oposto da barra por IA. **O log
> comum da sala deve ser separado dos buffers model-facing individuais.**"*

```
        ┌──────────────── a SALA (o que ele vê) ────────────────┐
        │  append-only, imutável, um registro só                │
        └───────┬───────────────┬───────────────┬───────────────┘
                │               │               │
        ┌───────▼──────┐ ┌──────▼───────┐ ┌─────▼────────┐
        │ sessão codex │ │ sessão kimi  │ │ sessão grok  │   ← N buffers
        │ janela dela  │ │ janela dela  │ │ janela dela  │     independentes
        └──────────────┘ └──────────────┘ └──────────────┘
```

⛔ **Nunca derivar "contexto de A" do tamanho da sala.** São grandezas diferentes, e
confundi-las é exatamente o erro que a barra existe para evitar.

---

## 2. Como o hermes entrega mais contexto do que a janela permite

**Resposta curta:** ele **não** manda mais de uma janela por chamada. "Mais de 1M" é o
**corpus acessível ao longo da conversa**, não o prompt. Quatro camadas:

| # | camada | o que faz |
|---|---|---|
| 1 | **compactação em lote** | ao bater o limiar, poda resultado antigo de ferramenta, **preserva o começo e uma cauda recente** por orçamento, e resume o miolo. Local: limiar `0.5`, alvo `0.2`, 3 protegidas no início, 20 no fim |
| 2 | **persistência não destrutiva** | compacta *in place*, mesmo `session_id`; o antigo vira `active=0, compacted=1` e **continua no SQLite** |
| 3 | **reidratação sob demanda** | o arquivado fica no FTS5; `session_search` traz o trecho de volta — **sem chamada de LLM** |
| 4 | **memória durável pequena** | `MEMORY.md` e `USER.md` injetados no system prompt |

**Provado no estado real:** 51 sessões, 2.226 mensagens, **1.921 ativas e 305 já
compactadas**. Não é código morto.

---

## 3. A barra — o número existe, e há cinco regras para ela não mentir

| peça | onde |
|---|---|
| **numerador** | `ContextCompressor.last_prompt_tokens` — do `usage.prompt_tokens` que o provedor devolve |
| **denominador** | `context_length` por modelo, persistido em `context_length_cache.yaml` (8 rotas, 272 mil a 1.050.000) |
| **já desenhada** | `/context` mostra barra de **24 células** + headroom + limiar + nº de compressões |
| **RPC pronta** | `session.context_breakdown` → `context_used`, `context_max`, `context_percent`, `estimated_total` |

### As cinco regras (do laudo, e viram gate nosso)

1. `last_prompt_tokens` só vale **se `> 0`** — **`-1` significa "acabou de compactar, ainda
   não mediu"**.
2. ⛔ **Nunca** usar `session_input_tokens` / `session_total_tokens` / `insights`: são
   **throughput acumulado**, não ocupação atual. Confundir os dois é a barra mentir bonito.
3. Se o provedor não informa `prompt_tokens`: mostrar **estimativa**, com selo, e **não
   pintar como exato**.
4. Ao trocar de modelo: **recalcular o denominador** antes de desenhar.
5. Depois de compactar: deixar a barra em **"medindo"** — nunca inventar 0%.

⇒ **Três estados, nunca dois:** `exato` · `estimado` · `desconhecido`. É a mesma doutrina
dos gates da casa, e aqui ela chega escrita por outro projeto.

---

## 4. O ruído não se filtra: dobra-se

O dono viu isso no controle remoto do próprio Claude Code e apontou:

> *"talvez já tenhamos a resposta… está em você, no codex, e se chama controle remoto,
> exatamente a conversa que eu tenho com você aqui, mas várias IAs dentro"*

O que aquela interface faz, e que resolve o "só o resultado sobe":

- a conversa é **prosa legível**;
- cada ação vira **uma linha com a descrição em português** — *"Adicionar guarda de
  recursão ao meta-gate"* — mais o tipo (`Shell`) e o **estado** (`Concluído` / `Falhou`);
- o comando e a saída ficam **atrás de um toque** (`Executando ›`);
- há um contador honesto: **"Concluídas 74"**, "1 tarefa em execução".

| eu havia proposto | o controle remoto faz |
|---|---|
| só o arquivo de resultado sobe | **tudo sobe, dobrado** |
| a IA decide o que é "resultado" | a IA só **nomeia a intenção**; ele decide o que abrir |
| o resto se perde | o resto fica a um toque, com estado visível |

⇒ **Adotar isto.** E note por que funciona: o sistema **obriga** a IA a nomear a ação em
linguagem humana antes de executá-la. A lista é legível porque a descrição é requisito,
não cortesia.

---

## 5. Microssessão — já existe, e é copiável

O pedido: *"não quero que vocês leiam toda a conversa, apenas uma microssessão, e só abram
mais coisa se precisarem"*. O hermes implementa por granularidade de busca:

- **por relevância** — `session_search(query)` devolve o trecho achado **±5 mensagens**,
  mais 3 do começo e 3 do fim da sessão;
- **expansão incremental** — `session_search(session_id, around_message_id, window=N)`,
  com `N ≤ 20`; a IA ancora de novo no primeiro ou último `message_id` para rolar;
- **leitura por id** — sessão pequena vem inteira; grande vem 20 primeiras + 10 últimas,
  com instrução de rolar o miolo.

Não existe "meia-sessão" nominal — a granularidade é **a janela da busca**.

---

## 6. Plano de implementação, em ordem de valor

| # | componente | resultado observável |
|---|---|---|
| 1 | **sessão durável por IA** | trocar A → B → A restaura o fio de A **sem misturar** a janela de B |
| 2 | **adaptador de eventos estruturados** | a bolha mostra só a resposta final; ferramenta, raciocínio, stderr e progresso ficam separados |
| 3 | **snapshot de contexto por fala** | as duas linhas mostram nome/cor + janela **daquela IA**, com selo exato/estimado/desconhecido |
| 4 | **broker de microssessão** | a IA começa com fatia pequena e pede expansão por âncora |
| 5 | **compactação + arquivo pesquisável** | a conversa passa da janela ao longo do tempo **sem apagar** o texto antigo |
| 6 | **supervisor de processo** | fechar e reabrir a interface **não mata** o agente nem duplica entrega |
| 7 | **plan mode** | planeja sem executar, com artefato rastreável |

### O esquema durável (do laudo)

- `rooms` / `room_messages` — a conversa comum, append-only
- `agent_sessions` — `agent_id`, `session_id`, modelo, provedor, cwd, token de attach, último `seq`
- `agent_messages` — buffer model-facing, com `active` e `compacted`
- `agent_events` — stream bruto por agente, sequencial e **idempotente**
- `context_snapshots` — `prompt_tokens`, `context_length`, percentual, **fonte da medição**, instante

---

## 7. Onde ele nasce

**Recomendação: terceiro modo da janela que já existe** — sala · enxame · **groupchat**.

Motivo: a janela do enxame já tem cor por IA (45 marcas + apelidos), malha dourada, cartões,
barras que respiram no ritmo do braço, doca de detalhe e **o controle remoto por worker com
dados + cauda de terminal + parar/redisparar com previsão e recibo**. É uns 60% do
groupchat, já aprovado por ele visualmente.

Custo da alternativa (tela própria): reconstruir chassi, paleta e remoto, e manter duas
interfaces em sincronia.

---

---

## 8. A tela — existe, e dá para abrir: `docs/desenho/groupchat.html`

Desenho self-contained (527 linhas, sem fonte/script/imagem externa). Abra no navegador.
Mostra as três IAs falando, os quatro casos da barra, a ação dobrada, a falha, o vazio, o
erro e a microssessão. Diz de si mesmo **"amostra estática"** — não finge telemetria viva.

### O contrato mínimo por atualização de sessão

```json
{
  "ia_id": "codex", "session_id": "cx_7f2a", "model_id": "gpt-5.6-sol",
  "context": {
    "state": "exact",                       // exact · estimated · unknown
    "last_prompt_tokens": 168000,
    "estimated_prompt_tokens": null,
    "context_window_tokens": 250000,
    "source": "provider.usage.prompt_tokens",
    "sampled_at": "2026-08-18T15:42:08-03:00",
    "reason": null                          // ex.: compacted_waiting_measurement
  },
  "liveness": { "last_signal_at": "...", "session_state": "running" }
}
```

`session_id` é **por IA**, nunca da sala. Trocou de modelo, o denominador chega de novo
antes do desenho. `last_prompt_tokens: -1` vira `state: unknown` + texto **"medindo"** —
nunca 0%.

### Como os três estados aparecem sem depender de cor

Barra sólida = `exato` · hachurada com `≈` = `estimado` · trilho tracejado que respira =
`desconhecido`. **A cor da IA diz quem fala; a cor semântica diz como vai.** As duas nunca
no mesmo elemento — é a lei do `DESIGN.md` aplicada.

### Auditoria visual — o que eu medi, não o que o laudo disse

O laudo declarou honestamente que **não** houve render nem prova de layout (o contrato
proibiu navegador por RAM). Então medi eu, e achei um defeito real:

| viewport | estouro horizontal **antes** | **depois** |
|---|---|---|
| 360px | 185px (129 elementos) | **0** |
| 390px | 155px (125 elementos) | **0** |
| 430px | 115px (121 elementos) | **0** |

⭐ **Causa-raiz, e ela se repete:** `grid-template-columns:1fr` nos dois breakpoints.
`1fr` é `minmax(auto,1fr)`, e o `auto` **não encolhe abaixo do min-content** — um bloco
largo travava a coluna em 545px e os cinco filhos herdavam; no cabeçalho, o
`white-space:nowrap` do subtítulo virava o piso da coluna e o `text-overflow:ellipsis`
nunca chegava a agir. Conserto: `minmax(0,1fr)` nos dois lugares. **Levar isto para o
`sala.js` quando o modo nascer** — o app tem a mesma grade de três colunas.

Mobile é o uso principal dele: sem esse conserto, a tela cortava no celular.

**O que NÃO se sustentou:** achei que o compositor cobria a última fala (321px). Medi de
novo separando clip-de-rolagem de cobertura — sobreposição **0px**, conteúdo inalcançável
**0px**. A primeira medição mentiu porque `scroll-behavior:smooth` não avança em tempo
virtual no headless. Não havia defeito.

---

## 9. O que ainda não sei

- se o `token_count` das mensagens (nulo no hermes) tem equivalente utilizável em **cada
  CLI da frota** — o codex imprime tokens no fim, o kimi mostra `context: 24% (236k/1M)` no
  rodapé. **Parser por braço quebra quando o braço muda de formato**; o contrato acima
  existe para isso, mas precisa ser provado braço a braço.
- **quem mantém o catálogo `model_id → context_window_tokens`.** Sem essa autoridade no
  backend, a regra de recalcular o denominador ao trocar de modelo não é verificável.
- o algoritmo de estimativa não foi escolhido. A tela define como **receber e rotular** uma
  estimativa sem fingir exatidão — não como produzi-la.
- não foram provados em runtime: contraste no pixel, navegação por teclado e prova em
  iPhone real. O HTML traz `progressbar`, rótulos, foco e movimento reduzido — mas isso é
  promessa de marcação, não medida.
- o laudo de omniroute/obsidian (11 KB) ainda não foi integrado aqui.
