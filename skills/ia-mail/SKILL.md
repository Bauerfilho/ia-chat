---
name: ia-mail
description: Conecta a IA ao Mail.app já autenticado para listar caixas e ler cabeçalhos e trechos recentes em modo local estritamente somente leitura, sem receber credencial e sem marcar mensagens como lidas.
---

# ia-mail — conexão local de email, somente leitura

Use esta skill quando o Bauer pedir para consultar a caixa já aberta no Mail.app, contar
mensagens não lidas ou ler as mensagens recentes de uma caixa.

## Comandos disponíveis

```bash
ia-mail caixas
ia-mail recentes --caixa 3 -n 10
ia-mail repeticoes --caixa 3 -n 500 --minimo 2
ia-mail --json recentes --caixa 3 -n 10
ia-mail --privado recentes --caixa 3 -n 3
ia-mail --json --privado repeticoes --caixa 3 -n 500
```

Primeiro rode `ia-mail caixas`; o ID mostrado ali alimenta `--caixa`. O modo `--privado`
percorre a consulta real, mas oculta nome, assunto e trecho na saída — use-o em laudos e
diagnósticos onde basta provar números e funcionamento.

`repeticoes` analisa somente a janela pedida. Primeiro agrupa por endereço normalizado;
depois, dentro de cada remetente, aponta quantas linhas de assunto se repetem. A
normalização remove prefixos de resposta e diferenças cosméticas, mas preserva números
para não fabricar duplicidade entre mensagens diferentes.

## Contrato de segurança

- A autenticação pertence ao Mail.app. A skill não pede nem recebe credencial.
- A fonte é o `Envelope Index` local mais novo em `~/Library/Mail/V*/MailData/`.
- O SQLite abre por URI `mode=ro` e recebe também `PRAGMA query_only = ON`.
- Endereços saem mascarados; URLs internas de conta nunca são impressas.
- A leitura não marca mensagem, move, arquiva, apaga, responde nem envia.
- Se o índice local não estiver disponível, a skill para. Não tenta IMAP como fallback.

## Limite desta fase

Esta fase cobre somente `caixas`, `recentes` e `repeticoes`. Ações voltadas para fora ou
que alteram estado permanecem desligadas até autorização nominal do Bauer.
