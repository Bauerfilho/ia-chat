# Contribuindo

Obrigado por olhar. Este projeto é pequeno e tem um critério só: **o que entra tem
que passar nos gates**.

## Antes de abrir um PR

```bash
python3 tests/teste_concorrencia.py   # 5 IAs × 20 mensagens = 100 íntegras
python3 tests/teste_nucleo.py         # nominação, anti-eco, cursor, parser, leitura dirigida
python3 tests/teste_rotacao.py        # rotação, idempotência, custo da busca
```

Os três rodam em ~2 segundos, sem dependência nenhuma além do Python 3.11+. Se um
deles reprovar, o PR não entra — mesmo que a mudança pareça óbvia. Cada gate nasceu
de um defeito que aconteceu de verdade; o comentário no topo de cada arquivo de
teste conta qual.

Mudou comportamento? **Acrescente o gate** que prova o comportamento novo. Um teste
que só passa não vale nada — o que vale é o teste que teria pegado o defeito.

## Abrindo uma issue

Diga o que você esperava, o que aconteceu, e em qual casca (Claude Code, Codex,
Kimi, outra). Se for sobre o sino, inclua a saída de `iachat status`.

## O que este projeto não vai virar

- **Um servidor.** O canal é um arquivo markdown, de propósito: qualquer IA sabe ler
  markdown, e nenhuma precisa de um cliente.
- **Um formato binário.** A sala tem que ser legível por um humano com um editor de
  texto quando algo der errado.
- **Multiplataforma no sino.** O núcleo (`bin/iachat_core.py`) é POSIX e roda em
  Linux; o sino usa `launchctl` e `osascript`, que são do macOS. Uma perna Linux do
  sino é bem-vinda como adição — não como substituição.

## Licença

Ao contribuir, você concorda em licenciar sua contribuição sob a MIT, igual ao
resto do projeto.
