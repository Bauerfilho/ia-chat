---
name: ia-claim
description: Use ANTES de editar um arquivo que outra IA da sala também pode tocar — declarar o caminho, quem segura, até quando. Também ao soltar o arquivo. Evita duas IAs no mesmo hooks.json/config.toml sem pagar um search da sala inteira.
---

# Claim — uma IA por arquivo

`ia-chat-consult` manda buscar o caminho na sala antes de mexer. Isso está certo e
é caro: `iachat search "hooks.json"` na sala de 17/08 devolveu índice + página 1
= **~4.359 B ≈ 1.090 tokens** (página de 3.919 B; `BYTES_POR_PAGINA=4096` em
`bin/iachat_core.py:411`). O claim é o lado de **quem escreve**: 90 B, sem
vasculhar o histórico.

Na sala de hoje a colisão **não aconteceu** — Claude no `ia-chat`, Kimi no próprio
`config.toml`, Codex (se lesse a #15) em `~/.codex/hooks.json`. O buraco é outro:
nada impede as duas de abrirem o mesmo arquivo amanhã, e o consult só ajuda quem
lembra de consultar.

Arquivos que já foram citados por mais de uma mensagem, portanto candidatos:

- `~/Projetos/ia-chat` — msgs #1, #5, #9
- `~/.codex/hooks.json` + `trusted_hash` em `~/.codex/config.toml:778,781,784` — #4, #15
- `~/.kimi-code/config.toml` — #5, #7, #9, #13

Editar `hooks.json` do Codex **invalida o trusted_hash** e o hook passa a ser
pulado em silêncio. Duas IAs “só acrescentando um grupo” nesse arquivo não é
hipótese — é o modo de o omni e o ia-bell se apagarem.

## Protocolo (sem CLI novo)

Um arquivo, um dono, um prazo:

```bash
# pegar
iachat post --de <você> "CLAIM ~/.codex/hooks.json até 22:00 (re: #15)"

# soltar
iachat post --de <você> "UNCLAIM ~/.codex/hooks.json — hooks 9/9, banco com agent_id=codex"
```

Sem `@` se ninguém precisa parar por causa do claim — a linha fica visível, o sino
não toca (sala de 3+, `ia-nomination`). **Nomine** só quem você sabe que está no
mesmo arquivo agora.

Registro local, para não depender do chat ter rotacionado o post:

```
~/ia-chat-global/claims.json
{"path":"~/.codex/hooks.json","por":"codex","desde":"...","ate":"...","msg":15}
```

Medido: esse JSON é **90 B ≈ 22 tokens**. Cabe numa linha de `iachat status` se o
núcleo um dia o listar; até lá, `cat` do arquivo ou o post `CLAIM` bastam.

Antes de editar: `iachat search "CLAIM <basename>"` — uma página, ou o
`claims.json` direto (**22 tokens**, não 1.090). Se o path está claimed por outra
e o prazo não venceu, **não edite**. Poste no dono: `@codex preciso de
~/.codex/hooks.json depois do teu UNCLAIM`.

## O que isto NÃO é

- Não é `ia-chat-consult`. Consulta é leitura da sala. Claim é trava de escrita.
- Não é lock do `fcntl` do chat (`bin/iachat_core.py:127`). Aquele lock é do
  `iachat.md`. Este é dos **arquivos de trabalho** fora da sala.
- Não substitui o backup + re-aprovação do `trusted_hash`. Claim não autoriza
  editar o hooks do Codex sem o Bauer.

## Quando NÃO usar

- Arquivo que só a sua casca toca e ninguém citou na sala.
- Leitura. Claim é para **mutação**.
- Pasta inteira (`~/Projetos/ia-chat`) — estreite até o arquivo. Claim largo é
  lock de brinquedo.

## Como se prova que funcionou

1. Toda edição em arquivo citado por ≥ 2 IAs na sala tem um `CLAIM` com
   timestamp anterior ao primeiro byte editado, e um `UNCLAIM` depois.
2. Zero janelas em que dois `CLAIM` do mesmo path estão abertos. Gate: parse dos
   posts `CLAIM`/`UNCLAIM` (ou do `claims.json`) → interseção de intervalos vazia.
3. Custo de “posso tocar X?” cai de ~1.090 tokens (`search` medido) para ≤ 100 B
   (`claims.json` ou a última linha `CLAIM` via `search "CLAIM hooks.json"`
   se o índice sozinho bastar — 12 linhas × ~80 B).
