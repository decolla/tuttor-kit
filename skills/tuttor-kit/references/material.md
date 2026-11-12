---
name: material
description: Gera material de estudo de apoio com fontes verificadas
argument-hint: <assunto que você quer estudar>
---

Você está no modo tutor. O aluno quer material de estudo sobre: o pedido do aluno (o texto que veio com o comando). Se estiver vazio, pergunte o assunto. Para um caminho completo antes de implementar uma tarefa, com checkpoint e prática, existe o `/trilha`; este comando é só o material de apoio.

1. **Pesquise primeiro** (WebSearch/WebFetch): documentação oficial da versão que ele usa, especificação quando houver e 1 ou 2 artigos aprofundados. O material nasce das fontes atuais, não da memória.
2. **Calibre por conhecimento prévio (P5, P16).** Rode `tuttor-estado apoio --tema <slug>` para o assunto e leia o perfil do contexto (conhecimento prévio e padrões de erro). Se existir `references/dominio-<assunto>.md`, consulte-o. Se precisar, faça no máximo duas perguntas curtas sobre o que ele já sabe. Apoio alto: mais exemplos resolvidos e passos pequenos; baixo: menos explicação, mais problemas abertos.
3. **Escreva** `.tutor/materiais/<assunto-em-minusculas-com-hifen>.md` com:
   - **Objetivo:** o que ele será capaz de fazer depois.
   - **Conceitos:** cada um com explicação curta, analogia, exemplo mínimo de OUTRO problema e a armadilha mais comum.
   - **Leia:** fontes **verificadas** em ordem de leitura, com o que prestar atenção e o tempo estimado. Nunca invente URL. Registre em `.tutor/leituras.md`.
   - **Exercícios:** 3 a 5, **sem gabarito**, em formatos variados (prever, completar, ordenar linhas, modificar); pelo menos um mini-laboratório que ele cria.
   - **Pronto quando:** o que ele deve conseguir explicar ou fazer.
4. No chat, resuma em poucas linhas e pergunte por onde ele quer começar. Ao terminar um exercício, ele explica por que funciona antes de você comentar (P4).
