# Princípios e recursos do kit

Cada linha liga um princípio pedagógico a um recurso do tuttor-kit, ao lugar onde ele está e às fontes de [bibliografia.md](bibliografia.md). Os recursos são escolhas de projeto inspiradas na literatura; nenhum deles foi testado neste kit em estudo com alunos. Voltar ao [README](README.md).

| # | Princípio | Recurso do kit | Onde está | Fontes | Ressalva |
|---|---|---|---|---|---|
| P1 | Recuperação ativa (testar em vez de reler) | `/quiz` e a abertura do `/fechar` pedem que o aluno lembre e explique antes de qualquer resumo do tutor | references/quiz.md, fechar.md | [1](bibliografia.md#f1), [2](bibliografia.md#f2) | Forte em laboratório com texto e memória verbal; pouca evidência direta em programação |
| P2 | Prática espaçada | `estado.py` agenda revisão por tema em intervalos crescentes (1, 3, 7, 14, 30, 60 dias); a sessão abre avisando o que venceu | scripts/estado.py, contexto.py | [1](bibliografia.md#f1), [3](bibliografia.md#f3) | Efeito robusto em memória verbal; a escada de intervalos do kit é heurística, não derivada de [3] |
| P3 | Intercalar temas | `/quiz` mistura temas vencidos em vez de blocos | references/quiz.md | [1](bibliografia.md#f1), [6](bibliografia.md#f6), [7](bibliografia.md#f7) | Moderada em [1]; estudos de origem em matemática; não testado em programação aqui |
| P4 | Autoexplicação | Todo checkpoint e todo passo concluído pedem "explique por que funciona" com as palavras do aluno | references/persona.md, trilha.md, fechar.md | [1](bibliografia.md#f1), [8](bibliografia.md#f8), [9](bibliografia.md#f9) | Moderada; [8] é amostra pequena e conteúdo de biologia |
| P5 | Exemplo resolvido para novato, com retirada gradual | Nível de apoio por tema: alto (exemplo análogo + completar), médio (ordenar/completar), baixo (problema aberto) | scripts/estado.py (`apoio`), references/praticar.md, pedagogia.md | [12](bibliografia.md#f12), [14](bibliografia.md#f14), [15](bibliografia.md#f15), [16](bibliografia.md#f16) | Boa em domínios bem estruturados; os exemplos do kit são sempre de OUTRO problema, não da tarefa do aluno |
| P6 | Efeito de reversão por perícia (o que ajuda o novato atrapalha o avançado) | O apoio diminui conforme o domínio do tema sobe; quem domina recebe só perguntas | scripts/estado.py, references/persona.md | [17](bibliografia.md#f17) | Revisão; a medida de "domínio" do kit é uma contagem simples, não um diagnóstico validado |
| P7 | Tentativa antes da instrução (falha produtiva) | `/dica` e `/duvida` pedem primeiro o que o aluno tentou e sua hipótese; na trilha, o aluno prevê antes de rodar | references/dica.md, trilha.md | [21](bibliografia.md#f21), [22](bibliografia.md#f22), [23](bibliografia.md#f23) | DISPUTADO: [18] defende instrução guiada para novatos; [23] acha efeito oposto em crianças e habilidades gerais. O kit usa a tentativa curta e com apoio, não descoberta sem guia |
| P8 | Andaime que some (scaffolding e aprendizado cognitivo) | Escada de dicas de 4 degraus; o tutor modela o raciocínio e vai retirando a ajuda | references/dica.md, persona.md | [24](bibliografia.md#f24), [25](bibliografia.md#f25), [19](bibliografia.md#f19) | Origem conceitual clássica; [24] e [25] não foram lidos na íntegra |
| P9 | Buscar ajuda bem é uma habilidade; abuso de dica prejudica | Um degrau por vez, sempre depois de uma ação do aluno; `estado.py dica` detecta dicas em sequência e o tutor pede uma tentativa em vez de descer | scripts/estado.py, references/dica.md | [28](bibliografia.md#f28), [29](bibliografia.md#f29), [30](bibliografia.md#f30), [31](bibliografia.md#f31) | [29] é correlacional; o detector do kit é uma regra simples, não o detector validado dos estudos |
| P10 | IA sem salvaguarda vira muleta | O tutor não escreve o código do aluno; a trava (hook) bloqueia escrita fora de `.tutor/`; o vigia comenta, não corrige | scripts/guard.py, references/persona.md, vigia-prompt.md | [46](bibliografia.md#f46), [52](bibliografia.md#f52), [44](bibliografia.md#f44), [45](bibliografia.md#f45), [47](bibliografia.md#f47), [48](bibliografia.md#f48) | [46] é matemática do ensino médio; [52] é pré-publicação com 52 pessoas; [44] não achou prejuízo em novatos jovens: a evidência não é unânime |
| P11 | Feedback sobre a tarefa e o processo, não sobre a pessoa | Comentários do vigia e do `/revisar`: onde, o quê, por quê, e uma pergunta; máximo de 5 itens | references/revisar.md, vigia-prompt.md | [33](bibliografia.md#f33) | Revisão conceitual ampla; o formato específico do kit não foi testado |
| P12 | Ler e rastrear código antes de escrever | PRIMM (prever, rodar, investigar, modificar, criar) como formato das atividades da trilha | references/trilha.md, praticar.md | [36](bibliografia.md#f36), [37](bibliografia.md#f37), [38](bibliografia.md#f38) | [38] é quase-experimento com alunos de 11 a 14 anos; generalizar para universitários é extrapolação |
| P13 | Problemas de Parsons | Exercícios de ordenar linhas embaralhadas (com distratores) no nível médio de apoio | references/praticar.md | [40](bibliografia.md#f40), [41](bibliografia.md#f41), [42](bibliografia.md#f42) | [41]: mais rápido, sem diferença de aprendizagem; o ganho é de eficiência, não de resultado |
| P14 | Usar, modificar, criar | Progressão das atividades dentro de uma trilha | references/trilha.md | [39](bibliografia.md#f39) | Framework descritivo, não teste de eficácia |
| P15 | Prática deliberada nos pontos fracos | A sessão abre com os temas mais fracos e os erros que mais se repetem; `/praticar` mira neles | scripts/contexto.py, estado.py | [10](bibliografia.md#f10), [11](bibliografia.md#f11) | [11] mostra que prática deliberada explica bem menos do que se dizia (4% em educação) |
| P16 | Adaptar por conhecimento prévio, não por "estilo de aprendizagem" | Perfil sem rótulos de estilo: registra conhecimento prévio, padrões de erro e comportamento de pedido de ajuda, sempre com data e evidência | assets/perfil-modelo.md, references/perfil.md, calibrar.md | [34](bibliografia.md#f34), [17](bibliografia.md#f17), [28](bibliografia.md#f28) | [34] é sobre falta de evidência, não prova de que estilos não existam |
| P17 | Expectativa realista sobre tutoria | A documentação não promete "2 sigma" | README, docs/pesquisa | [26](bibliografia.md#f26), [27](bibliografia.md#f27) | [27] revisou o efeito para d ≈ 0,79 |

As ressalvas usam `[n]` para citar a fonte; todas as entradas estão em [bibliografia.md](bibliografia.md).

## Decisão de projeto por princípio

### P1. Recuperação ativa (testar em vez de reler)

O kit pede que o aluno lembre e explique com as próprias palavras antes de o tutor resumir qualquer coisa, no `/quiz` e na abertura do `/fechar`. A decisão se apoia na classificação de utilidade alta do teste prático em [1](bibliografia.md#f1) e no experimento com prosa de [2](bibliografia.md#f2). A transposição para programação é uma escolha de projeto, não algo testado neste kit.

### P2. Prática espaçada

O `estado.py` agenda a revisão de cada tema em intervalos crescentes, e a sessão abre avisando o que venceu. A decisão se apoia em [1](bibliografia.md#f1) e na meta-análise de [3](bibliografia.md#f3), que mostra que o intervalo ótimo cresce com o intervalo de retenção. Os valores da escada (1, 3, 7, 14, 30, 60 dias) são uma heurística de engenharia do kit, não saem de [3](bibliografia.md#f3).

### P3. Intercalar temas

O `/quiz` mistura temas vencidos em vez de revisá-los em blocos. A decisão é inspirada na prática intercalada de utilidade moderada em [1](bibliografia.md#f1) e nos estudos de origem [6](bibliografia.md#f6), [7](bibliografia.md#f7), dos quais só os títulos foram verificados. É uma escolha de projeto; a intercalação não foi testada em programação aqui.

### P4. Autoexplicação

Cada checkpoint e cada passo concluído pedem que o aluno explique por que funciona. A base é a autoexplicação de [1](bibliografia.md#f1), o experimento de [8](bibliografia.md#f8) e o framework ICAP de [9](bibliografia.md#f9). O experimento é pequeno e de biologia, então a transferência para programação é uma aposta de projeto.

### P5. Exemplo resolvido para novato, com retirada gradual

O nível de apoio por tema vem do `estado.py apoio`: exemplo análogo mais completar para domínio baixo, ordenar ou completar no médio e problema aberto no alto domínio. Combina a carga cognitiva de [12](bibliografia.md#f12), os princípios de exemplos resolvidos de [14](bibliografia.md#f14), o esmaecimento de [15](bibliografia.md#f15) e [16](bibliografia.md#f16). Os exemplos do kit são sempre de outro problema, nunca da tarefa do aluno; essa regra é decisão do kit.

### P6. Efeito de reversão por perícia (o que ajuda o novato atrapalha o avançado)

O apoio diminui à medida que o domínio do tema sobe, e quem domina recebe só perguntas. A inspiração é o efeito de reversão da expertise descrito em [17](bibliografia.md#f17). A contagem de domínio de 0 a 4 do kit é uma heurística simples, não um diagnóstico validado.

### P7. Tentativa antes da instrução (falha produtiva)

O `/dica` e o `/duvida` pedem primeiro o que o aluno tentou e qual é sua hipótese, e na trilha o aluno prevê antes de rodar. Os estudos de [21](bibliografia.md#f21), [22](bibliografia.md#f22), [23](bibliografia.md#f23) sustentam o valor de tentar antes, mas [18](bibliografia.md#f18) defende instrução guiada para novatos e [23](bibliografia.md#f23) acha efeito oposto em crianças e habilidades gerais. O kit escolheu a tentativa curta e com apoio, não a descoberta sem guia; é uma escolha de projeto num debate aberto.

### P8. Andaime que some (scaffolding e aprendizado cognitivo)

A escada de dicas tem 4 degraus, e o tutor modela o raciocínio e vai retirando a ajuda. A origem conceitual é [24](bibliografia.md#f24) e [25](bibliografia.md#f25), e a defesa de que métodos como PBL são fortemente andaimados vem de [19](bibliografia.md#f19). As fontes [24](bibliografia.md#f24) e [25](bibliografia.md#f25) não foram lidas na íntegra; a escada de 4 degraus em si é um desenho do kit.

### P9. Buscar ajuda bem é uma habilidade; abuso de dica prejudica

O tutor dá um degrau por vez, sempre depois de uma ação do aluno, e o `estado.py dica` avisa quando há dicas em sequência, caso em que o tutor pede uma tentativa em vez de descer. Isso se inspira em [28](bibliografia.md#f28), [29](bibliografia.md#f29), [30](bibliografia.md#f30), [31](bibliografia.md#f31). O detector do kit é uma regra simples, não o detector validado dos estudos, e [29](bibliografia.md#f29) é correlacional.

### P10. IA sem salvaguarda vira muleta

O tutor não escreve o código do aluno; a trava (`guard.py`) bloqueia escrita fora de `.tutor/` e o vigia comenta, não corrige. A decisão pesa os resultados mistos de [46](bibliografia.md#f46), [52](bibliografia.md#f52), [44](bibliografia.md#f44), [45](bibliografia.md#f45), [47](bibliografia.md#f47), [48](bibliografia.md#f48). A trava é uma garantia mecânica, mas a evidência de que isso melhora a aprendizagem não é unânime e não foi medida com este kit.

### P11. Feedback sobre a tarefa e o processo, não sobre a pessoa

Os comentários do vigia e do `/revisar` dizem onde, o quê, por quê e fazem uma pergunta, com no máximo 5 itens. A inspiração é [33](bibliografia.md#f33), que mostra que o tipo de feedback e a forma como é dado mudam o efeito. O formato específico do kit é uma escolha de projeto e não foi testado.

### P12. Ler e rastrear código antes de escrever

As atividades da trilha seguem o PRIMM: prever, rodar, investigar, modificar, criar. A base é o diagnóstico de leitura e rastreamento de [36](bibliografia.md#f36), a teoria de [37](bibliografia.md#f37) e o quase-experimento de [38](bibliografia.md#f38). Esse último é com alunos de 11 a 14 anos, então estendê-lo a universitários é extrapolação.

### P13. Problemas de Parsons

No nível médio de apoio, o `/praticar` propõe exercícios de ordenar linhas embaralhadas, com distratores. O formato vem de [40](bibliografia.md#f40), e as evidências de [41](bibliografia.md#f41), [42](bibliografia.md#f42). Em [41](bibliografia.md#f41) o ganho é de eficiência, sem diferença de aprendizagem, e é por isso que o kit usa o formato como degrau intermediário, não como garantia de resultado.

### P14. Usar, modificar, criar

A progressão das atividades dentro de uma trilha segue a ordem usar, modificar, criar. A fonte é [39](bibliografia.md#f39), um framework descritivo construído a partir de observações, não um teste de eficácia. É uma escolha de projeto inspirada nele.

### P15. Prática deliberada nos pontos fracos

A sessão abre com os temas mais fracos e os erros mais repetidos, e o `/praticar` mira neles. A ideia deriva de [10](bibliografia.md#f10), mas [11](bibliografia.md#f11) mostra que a prática deliberada explica bem menos do que se dizia (4% em educação). Por isso o kit não promete um efeito grande dessa escolha.

### P16. Adaptar por conhecimento prévio, não por "estilo de aprendizagem"

O perfil do aluno não usa rótulos de estilo: registra conhecimento prévio, padrões de erro e comportamento de pedido de ajuda, sempre com data e evidência. A decisão se apoia em [34](bibliografia.md#f34), na reversão da expertise [17](bibliografia.md#f17) e na revisão de busca de ajuda [28](bibliografia.md#f28). [34](bibliografia.md#f34) indica falta de evidência, não prova de que estilos não existam.

### P17. Expectativa realista sobre tutoria

A documentação do kit não promete o efeito de "2 sigma". [26](bibliografia.md#f26) originou essa expectativa, e [27](bibliografia.md#f27) revisou o efeito da tutoria humana para d = 0,79. Esta é uma decisão de comunicação: prometer menos do que a literatura sustenta.
