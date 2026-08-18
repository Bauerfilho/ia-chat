# Auditorias do ia-chat

Cada rodada de auditoria vive numa pasta datada `AAAA-MM-DD-<nome>`. A ideia é que o
histórico de como o projeto foi checado cresça junto com ele — quem chegar depois consegue
ver **o que foi questionado, por quem, e o que foi confirmado contra o código**.

## Como ler uma rodada

```
AAAA-MM-DD-<nome>/
├── README.md                 o que foi a rodada, quem participou, veredito
├── BRIEFING.md               o contexto que os auditores receberam (eles são cegos ao resto)
├── frota/                    laudos das IAs externas — cada uma auditou um ângulo
├── propostas/                peças novas propostas, com SKILL.md e nota de custo
├── achados-confirmados.md    o que foi CONFERIDO contra o código, com arquivo:linha
└── logs/                     os contratos que cada auditor recebeu
```

## Regra que vale para toda rodada

**Laudo não é veredito.** Todo achado de auditor é verificado contra o código antes de virar
tarefa — inclusive (e principalmente) os que soam convincentes. O que sobrevive à conferência
vai para `achados-confirmados.md` com `arquivo:linha`; o que não sobrevive fica registrado
como não-confirmado, com o motivo.

**Auditor ≠ autor.** Quem escreveu o código não julga o próprio código.

## Rodadas

| data | rodada | auditores | achados confirmados |
|---|---|---|---|
| 2026-08-17 | [fase6](2026-08-17-fase6/) | codex · kimi · grok · qwen · agy (frota) + 17 projetistas (casa) | em andamento |
