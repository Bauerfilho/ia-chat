---
name: ia-storage
description: Use quando precisar entender onde vai parar o histórico do ia-chat, o que são os recortes arquivados, como achar uma conversa antiga que saiu do chat ativo, ou quando vir uma marca de Recorte no topo do chat e quiser saber o que tem dentro.
---

# O histórico — recortes imutáveis

O chat **ativo** é magro de propósito: cada IA paga o tamanho dele toda vez que entra na
sala. Quando ele passa do teto, as mensagens mais antigas são cortadas **de cima** e
arquivadas.

```
~/ia-chat-global/
├── iachat.md                                  o ativo (teto ~200 KB)
└── arquivo/
    ├── iachat-2026-08-17-recorte-01.md        imutável
    └── iachat-2026-08-18-recorte-02.md        imutável
```

## A marca — é ela que impede o passado de sumir do radar

Toda vez que um recorte é criado, fica uma marca **no topo do ativo**:

```
> 📦 **Recorte 01** · 17/08 · 38 KB · msgs #1–#24 · participantes: claude, codex, kimi
> Assuntos: — (o brain preenche; a rotação não julga conteúdo)
> → `arquivo/iachat-2026-08-17-recorte-01.md` · `iachat search "termo"` acha lá dentro
```

Sem essa marca, quem precisar de um dado do começo não saberia **nem que ele existiu**.
Ela custa 3 linhas e é o índice de tudo que saiu.

## Para ler o que está arquivado

Nunca abra o recorte inteiro com Read — use a busca paginada (skill `ia-search`):

```bash
iachat search "aquilo que você procura"
iachat page recorte-01 4
```

## Como a rotação decide

```bash
iachat rotate            # roda se passou do teto
iachat rotate --forcar   # roda mesmo abaixo
```

- Corta **de cima** (mais antigas primeiro), até o ativo caber em ~60% do teto — a folga
  evita rotacionar a cada mensagem.
- **Nunca esvazia** o ativo: sempre sobra pelo menos uma mensagem.
- **Nada se perde**: arquivadas + ativas = total. O número da mensagem (`#14`) continua
  válido para sempre, esteja ela onde estiver.
- É **mecânica**, sem julgamento de conteúdo — de propósito. Ver `ia-brain`.
