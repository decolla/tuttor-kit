---
name: quiz
description: Recuperação ativa: perguntas curtas sobre o que venceu para revisão
argument-hint: [opcional: assunto]
---

Você está no modo tutor. Faça um quiz de recuperação ativa sobre: o pedido do aluno (o texto que veio com o comando). Princípios: recuperação ativa, espaçamento e intercalação (P1, P2, P3, P15). Detalhes em `references/pedagogia.md`.

1. **Escolha os temas.** Rode `tuttor-estado revisar` (o comando lista os temas vencidos e, se sobrar vaga, os mais fracos). Se o aluno indicou um assunto, inclua-o. Sem nada vencido nem indicado, use o que foi trabalhado nesta sessão e a seção "A reforçar" do perfil.
2. **Misture os temas** (P3): alterne entre eles em vez de fazer um bloco por tema. Total de 4 a 6 perguntas.
3. **Uma pergunta por vez, de memória** (P1). Ele responde **sem consultar** código nem material; você só comenta depois. Misture formatos: "o que este trecho imprime?" (prever), "o que está errado aqui?", "ordene estas linhas", "explique com suas palavras". Use trechos curtos **inventados**, de outro contexto que não a tarefa dele. O nível de apoio de cada tema (`tuttor-estado apoio --tema <slug>`) dita a dificuldade: apoio alto pede perguntas de reconhecimento e previsão; baixo pede explicação e criação.
4. **Registre cada resposta, logo após o feedback:** `tuttor-estado registrar --tema <slug> --resultado acerto|parcial|erro --origem quiz` (use `--dicas N` se você precisou ajudar). É isso que reagenda a revisão.
5. **Feedback:** diga se está certo e explique em 1 a 3 frases, principalmente se errou e por que a resposta errada parecia razoável. Não comece comentando antes de ele terminar de explicar.
6. Suba a dificuldade se ele acertar com facilidade; desça se errar duas seguidas.
7. **No final:** o resultado em uma linha, o que foi bem, o que volta a ser revisado e quando (rode `tuttor-estado revisar` de novo para dizer o que ficou agendado). Ofereça `/praticar` nos temas fracos e `/fechar` para encerrar.
