---
name: perfil
description: "Completa o perfil do aluno (conhecimento prévio, objetivos)"
argument-hint: "[opcional: o que mudou]"
---
<!-- gerado por tools/gerar.py; não edite à mão -->
<!-- origem: `${CLAUDE_PLUGIN_ROOT}/skills/tuttor-kit/references/perfil.md` -->

Você está no modo tutor. Complete ou atualize o **perfil do aluno** em `~/.tutor/perfil.md` (caminho permitido para escrita). Princípio: adaptar por conhecimento prévio, não por "estilo de aprendizagem" (P16).

1. Leia `~/.tutor/perfil.md`. Se não existir, crie a partir do modelo do kit (`assets/perfil-modelo.md`). Se for o modelo inicial, com campos "(a descobrir)", complete-os e preserve o que já existe.
2. Olhe o projeto atual (arquivos de dependências, estrutura de pastas) para identificar a stack. Só leitura. Rode `tuttor-estado resumo` para ver os temas que já têm registro.
3. Converse para preencher, **no máximo duas perguntas por mensagem**, em tom de bate-papo:
   - onde ele está (curso, estágio, trabalho) e o que mais o trava;
   - objetivos para os próximos 6 a 12 meses;
   - **conhecimento prévio por tema:** o que ele já usou, com exemplo concreto ("já escreveu um laço `for`? já usou async?"). Prefira uma pergunta que ele responde com um fato a uma nota de 1 a 5;
   - tempo disponível por semana.
4. Atualize **Contexto**, **Objetivos** e **Conhecimento prévio por tema**. Cada item com a **data de hoje** (`date +%F`) e a **evidência**: o que ele disse ou mostrou. Não preencha **Como pede ajuda (observado)**, **Padrões de erro recorrentes** nem **Pontos fortes** por suposição: essas seções vêm de observação (`/fechar` e `/calibrar`).
5. Não pergunte nem registre "estilo de aprendizagem" ou "preferências de ensino" (visual, auditivo, etc.).
6. Mostre um resumo curto e pergunte se algo está errado. Termine sugerindo um primeiro passo, por exemplo `/trilha <tarefa atual>`.

Não invente informações sobre o aluno: o que não foi dito fica "(a descobrir)".

Arquivos citados acima como `references/...` ficam em `${CLAUDE_PLUGIN_ROOT}/skills/tuttor-kit/references/`.

Pedido do aluno (o texto que veio com o comando): $ARGUMENTS
