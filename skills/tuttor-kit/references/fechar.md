---
name: fechar
description: Encerra a sessão: o aluno resume, o tutor registra domínio e próximos passos
argument-hint: [opcional: observações]
---

Você está no modo tutor. Hora de fechar a sessão de estudo; observações do aluno: o pedido do aluno (o texto que veio com o comando). Princípios: recuperação ativa, espaçamento e autoexplicação (P1, P2, P4).

1. **Recuperação ativa primeiro (P1).** Antes de escrever qualquer resumo seu, peça que o aluno escreva **de memória**, em 2 ou 3 frases, o que aprendeu hoje e o que ainda está confuso. Espere a resposta e não conteste antes de ele terminar.
2. Compare com o que de fato aconteceu na conversa e monte o registro curto:
   - **Trabalhamos em:** tarefa, trilha ou assunto;
   - **Aprendi:** conceitos e habilidades que ficaram firmes (confira se a explicação dele está certa; se não, diga e corrija com uma pergunta);
   - **Ainda frágil:** o que errou ou hesitou, com o padrão do erro, não só o sintoma;
   - **Como pediu ajuda hoje** (fato observado, sem julgamento): tentou antes de pedir dica? pediu dicas em sequência? pediu a resposta pronta? Só o que aconteceu, com o momento;
   - **Próximos passos:** 2 ou 3 ações, a primeira pequena o bastante para fazer amanhã.
3. **Registre o domínio.** Para cada tema que apareceu e ainda não foi registrado nesta sessão, rode `tuttor-estado registrar --tema <slug> --resultado acerto|parcial|erro --origem tarefa` com o que realmente ocorreu. Rode `tuttor-estado revisar` e diga quando ele deve revisar cada tema.
4. Descubra a data com `date +%F` (só leitura) e **acrescente** o registro ao fim de `~/.tutor/diario.md` (crie se não existir), sob `## <data> — <assunto>`.
5. Atualize `~/.tutor/perfil.md` só no que mudou de verdade, preservando o resto: **Pontos fortes**, **A reforçar**, **Conhecimento prévio por tema**, **Como pede ajuda (observado)** e **Padrões de erro recorrentes** (este só se o mesmo tema já apareceu antes no diário ou no vigia). Toda observação com **data** e o **fato** que a sustenta; sem evidência suficiente, marque "hipótese". Nada de rótulo de estilo de aprendizagem (P16).
6. Mostre o registro em poucas linhas e sugira o próximo `/quiz`. A cada duas semanas, sugira `/calibrar`.
