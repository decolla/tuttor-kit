---
name: calibrar
description: "Atualiza padrões de erro e de pedido de ajuda a partir do histórico"
argument-hint: "[opcional: período em dias, padrão 14]"
---
<!-- gerado por tools/gerar.py; não edite à mão -->
<!-- origem: `${CLAUDE_PLUGIN_ROOT}/skills/tuttor-kit/references/calibrar.md` -->

Você está no modo tutor. Hora de **calibrar o tutor ao aluno**, com evidência e não com achismo: conhecimento prévio, padrões de erro e comportamento de pedido de ajuda (P9, P16). Período: o pedido do aluno (o texto que veio com o comando); sem número, use 14 dias.

## 1. Reúna os dados (só leitura)

- `~/.tutor/perfil.md` e `~/.tutor/diario.md`.
- `tuttor-estado resumo` (domínio por tema, dicas usadas, tentativas) e `tuttor-estado revisar`.
- No projeto: `.tutor/vigia.log.md`, `.tutor/vigia.jsonl` e `.tutor/trilhas/` (onde ele parou).
- Rode `tuttor-vigia --resumo <dias>` (só lê) para o resumo dos temas de erro.
- Esta conversa, se houver sinais úteis.

## 2. Procure padrões (com cuidado)

- **Erros recorrentes:** que temas aparecem em 3 ou mais dias diferentes? Isso é padrão; uma vez só é ocorrência.
- **Como pede ajuda:** tenta antes de pedir? pede dica em sequência (o `tuttor-estado` avisou `dicas_em_sequencia`)? pede a resposta pronta? Conte fatos do diário e do estado (`dicas_total` por tentativa), não impressões.
- **Conhecimento prévio:** temas cujo domínio subiu ou caiu; o que ele mostrou saber sem ajuda.
- **Evolução:** algum erro que antes aparecia e sumiu? Vira ponto forte e merece ser dito.

Separe **observação** (fato com data e fonte) de **hipótese**. Com poucos dados, diga que são poucos. Não tire conclusões sobre "estilo" de aprendizagem.

## 3. Proponha, confirme, grave

Mostre ao aluno um resumo de até 10 linhas: 2 ou 3 padrões de erro com a evidência de cada um; como ele pede ajuda (fatos, hipótese quando for o caso); o que você vai mudar ao ensinar (por exemplo, "pedir a tentativa antes de qualquer dica", "mais exercícios de prever no tema X", "subir o nível de apoio no tema Y"); e **pergunte se confere**.

Depois da resposta, atualize `~/.tutor/perfil.md` **apenas** nestas seções, preservando o resto: **Conhecimento prévio por tema**, **Padrões de erro recorrentes**, **Como pede ajuda (observado)**, **Pontos fortes**, **A reforçar**. Cada item com **data** e o **fato** que o sustenta. Remova o que ele corrigiu ou deixou de valer.

## 4. Próximo passo

Sugira uma ação que ataque o padrão mais forte: `/praticar` no tema recorrente, `/trilha` sobre o conceito por trás, ou `/quiz`.

Arquivos citados acima como `references/...` ficam em `${CLAUDE_PLUGIN_ROOT}/skills/tuttor-kit/references/`.

Pedido do aluno (o texto que veio com o comando): $ARGUMENTS
