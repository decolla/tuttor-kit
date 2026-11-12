# Pesquisa pedagógica do tuttor-kit

Esta pasta reúne a base de pesquisa por trás das decisões pedagógicas do tuttor-kit: de onde vem cada recurso, o que a fonte realmente mostra e o que ela não mostra. O texto não afirma que o kit funciona. Afirma que os recursos foram projetados a partir de literatura publicada e diz onde essa literatura é forte, fraca ou disputada. O kit em si nunca foi avaliado em estudo controlado.

## Arquivos

- [bibliografia.md](bibliografia.md): as 53 fontes, numeradas de 1 a 53, cada uma com tipo de evidência, o que sustenta, o que não sustenta e a situação da verificação. As citações `[n]` deste README levam à entrada correspondente.
- [principios-e-recursos.md](principios-e-recursos.md): a tabela princípio, recurso do kit, onde fica, fontes e ressalva (P1 a P17), com a decisão de projeto de cada princípio.
- [limitacoes.md](limitacoes.md): as limitações honestas e os pontos em que a evidência é fraca ou disputada.

## Como a verificação foi feita

Cada fonte com DOI foi consultada pelo DOI no Crossref (metadados: autores, título, ano, periódico, volume, páginas) e no OpenAlex (resumo). As fontes sem DOI tiveram as páginas abertas e lidas (a página do laboratório Bjork, a página da editora do livro de Hermans, a pré-publicação de Shen e Tamkin e o texto de divulgação da Anthropic, e o relatório de educação da Anthropic), e a que não abriu para acesso automático ([40]) está marcada como link não verificado.

A verificação foi feita sobre o resumo (abstract) de cada registro, não sobre a leitura integral dos artigos; as exceções são os dois textos da Anthropic ([52] e [53]), lidos na página. Quando o resumo não estava disponível, a fonte é citada só como origem de um conceito, sem números. Nenhum resultado, tamanho de efeito ou nome de periódico foi completado de memória.

## Resumo por tema

### Prática de recuperação e espaçamento

A revisão de [1](bibliografia.md#f1) classifica o teste prático e a prática distribuída como as duas técnicas de utilidade alta entre dez, porque beneficiam alunos de idades e capacidades diferentes e diversas tarefas. Em dois experimentos com passagens em prosa [2](bibliografia.md#f2), o teste final após 5 min favoreceu reestudar, mas após 2 dias e após 1 semana ter sido testado rendeu mais retenção, embora reestudar aumentasse a confiança dos alunos. A meta-análise de [3](bibliografia.md#f3) (839 avaliações em 317 experimentos de 184 artigos) indica que o intervalo entre sessões que maximiza a retenção cresce com o intervalo de retenção. O conceito de dificuldades desejáveis [4](bibliografia.md#f4), [5](bibliografia.md#f5) dá o pano de fundo: condições que parecem difíceis no treino, mas rendem mais a longo prazo.

Onde a evidência é fraca ou indireta: os resultados vêm de laboratório, com texto e memória verbal; há pouca evidência direta em programação. A escada de intervalos do kit (1, 3, 7, 14, 30, 60 dias) é uma heurística de projeto, não é derivada de [3](bibliografia.md#f3). [4](bibliografia.md#f4) não tem resumo nos registros e [5](bibliografia.md#f5) foi verificada só no título, autores e ano e pela página do laboratório; nenhum número é citado delas.

### Intercalação

Em [1](bibliografia.md#f1), a prática intercalada recebe utilidade moderada, e os autores dizem que seus benefícios estavam só começando a ser explorados de forma sistemática. As fontes de origem são [6](bibliografia.md#f6) (embaralhar problemas de matemática) e [7](bibliografia.md#f7) (intercalar ajuda a distinguir conceitos parecidos), mas nenhuma das duas tem resumo nos registros consultados, então não citamos resultados.

Onde a evidência é fraca: moderada em [1](bibliografia.md#f1), com estudos de origem em matemática, e não testada em programação neste kit.

### Autoexplicação e engajamento ativo

Em [1](bibliografia.md#f1), autoexplicação e interrogação elaborativa têm utilidade moderada. O experimento de [8](bibliografia.md#f8) comparou 14 alunos de 8ª série orientados a se autoexplicar com 10 que leram o texto duas vezes (sistema circulatório) e achou ganho maior no grupo orientado. O framework ICAP [9](bibliografia.md#f9) propõe que o aprendizado aumenta do engajamento passivo ao ativo, construtivo e interativo, e examina estudos sobre anotações, mapas conceituais e autoexplicação.

Onde a evidência é fraca: [8](bibliografia.md#f8) é uma amostra pequena, com adolescentes e conteúdo de biologia; [1](bibliografia.md#f1) diz que autoexplicação e interrogação elaborativa não tinham sido bem avaliadas em contextos educacionais; ICAP é uma hipótese com validação indireta.

### Exemplos resolvidos, esmaecimento do apoio e efeito de reversão da expertise

Na linha da carga cognitiva, [12](bibliografia.md#f12) argumenta que resolver problemas de modo convencional consome capacidade que faria falta para aprender esquemas, e [13](bibliografia.md#f13) é citado como origem do enquadramento teórico (sem resumo disponível). A revisão de [14](bibliografia.md#f14) reúne princípios de design de exemplos resolvidos, associados às fases iniciais de aprendizagem. [16](bibliografia.md#f16) afirma que exemplos resolvidos são muito eficazes no início e que resolver problemas é superior depois, e propõe esmaecer o exemplo. [15](bibliografia.md#f15) testou isso em um experimento de campo e dois de laboratório: a retirada gradual favoreceu a aprendizagem, ao menos na transferência próxima, e retirar os passos de trás para frente foi mais favorável. O efeito de reversão da expertise [17](bibliografia.md#f17) resume que técnicas eficazes com iniciantes podem perder eficácia e até prejudicar alunos mais experientes.

Onde a evidência é fraca: boa em domínios bem estruturados, mas o benefício demonstrado em [15](bibliografia.md#f15) é na transferência próxima. A medida de domínio do kit é uma contagem simples de 0 a 4, não um diagnóstico validado.

### Tentativa produtiva versus instrução direta

Este é um debate em aberto. De um lado, [18](bibliografia.md#f18) defende que instrução com pouca orientação é menos eficaz e menos eficiente do que a guiada, e que a vantagem da orientação recua só quando o aluno tem conhecimento prévio suficiente. Do outro, [21](bibliografia.md#f21) (11º ano, física, atribuição aleatória) e [22](bibliografia.md#f22) (dois estudos randomizados em matemática) acharam que tentar resolver antes da instrução rendeu maior compreensão conceitual e transferência. A meta-análise [23](bibliografia.md#f23) (53 estudos, 166 comparações) achou g = 0,36 [0,20; 0,51] a favor de resolver antes, mais forte com alta fidelidade a Productive Failure, mas com tendência oposta para alunos da 2ª à 5ª série e para habilidades gerais de domínio; g = 0,87 é a estimativa dos autores após correção de viés de publicação.

Há ainda uma terceira posição: [19](bibliografia.md#f19) e [20](bibliografia.md#f20) respondem a [18](bibliografia.md#f18) dizendo que PBL e aprendizagem por investigação são fortemente andaimadas e não equivalem a descoberta sem guia. O kit usa uma tentativa curta e com apoio, não descoberta sem guia. A evidência é disputada, em grande parte de matemática e ciências, e não de programação.

### Andaimes e tutoria

A ideia de andaime vem de estudos de tutoria [24](bibliografia.md#f24) e do modelo de aprendizado cognitivo [25](bibliografia.md#f25) (modelar, orientar, dar andaime e retirá-lo); nenhum dos dois textos foi lido na íntegra e nenhum resultado é citado deles. [26](bibliografia.md#f26) sintetiza duas teses de doutorado que comparam instrução convencional, aprendizagem por domínio e tutoria. A revisão de [27](bibliografia.md#f27) concluiu que a tutoria humana tem d = 0,79 (não os 2,0 que se acreditava) e que sistemas tutores inteligentes têm d = 0,76. Por isso a documentação do kit não promete o efeito de "2 sigmas".

Onde a evidência é fraca: [24](bibliografia.md#f24) e [25](bibliografia.md#f25) são de origem conceitual e foram verificados só por metadados; [27](bibliografia.md#f27) compara tutoria com ausência de tutoria e não trata de tutores baseados em modelos de linguagem.

### Busca de ajuda e "gaming the system"

[28](bibliografia.md#f28) revisa que a busca de ajuda eficaz se relaciona a melhor aprendizagem, mas os alunos usam mal a ajuda. Em salas com software de tutoria inteligente [29](bibliografia.md#f29), "gaming the system" foi o comportamento mais associado a menor aprendizagem, com correlação com o pós-teste comparável à do conhecimento prévio. [30](bibliografia.md#f30) (dilema da assistência) e [31](bibliografia.md#f31) (feedback metacognitivo para busca de ajuda) não têm resumo nos registros; [32](bibliografia.md#f32) é a origem do Knowledge Tracing e serve só para contraste.

Onde a evidência é fraca: [29](bibliografia.md#f29) é correlacional. O detector de dicas em sequência do kit é uma regra simples, não o detector validado dos estudos, e o kit não implementa Knowledge Tracing.

### Feedback

[33](bibliografia.md#f33) é uma revisão conceitual: o feedback está entre as maiores influências sobre a aprendizagem, mas o efeito pode ser positivo ou negativo conforme o tipo e a forma como é dado. O kit procura dar comentários sobre a tarefa e o processo, não sobre a pessoa. A distinção entre tarefa, processo e pessoa não consta no resumo lido e não foi verificada nesta pasta.

Onde a evidência é fraca: revisão conceitual ampla; o formato específico do kit (onde, o quê, por quê e uma pergunta, no máximo 5 itens) não foi testado.

### Ensino de programação

Ler e rastrear antes de escrever: em [36](bibliografia.md#f36), alunos de sete países foram fracos em prever o resultado de código curto e em escolher a conclusão correta de um código quase completo, o que sugere compreensão frágil de pré-requisitos. [37](bibliografia.md#f37) propõe que quatro habilidades sejam ensinadas incrementalmente e, num estudo exploratório, a abordagem melhorou a taxa de conclusão, reduziu erros e melhorou a compreensão no pós-teste. PRIMM [38](bibliografia.md#f38) (prever, rodar, investigar, modificar, criar) foi avaliado em 13 escolas com 493 alunos de 11 a 14 anos, por 8 a 12 semanas, com pós-teste melhor que o controle. Os problemas de Parsons vêm de [40](bibliografia.md#f40); em [41](bibliografia.md#f41), os problemas 2D com distratores levaram menos tempo do que corrigir ou escrever código, sem diferença significativa em aprendizagem nem em retenção após 1 semana, e [42](bibliografia.md#f42) é a revisão de literatura do grupo de trabalho. O framework usar-modificar-criar [39](bibliografia.md#f39) descreve fases de atividade, sem testar eficácia. [35](bibliografia.md#f35) é uma revisão sistemática da programação introdutória (só o resumo-motivação foi verificado) e [43](bibliografia.md#f43) é um livro de divulgação, usado como leitura de apoio.

Onde a evidência é fraca: [38](bibliografia.md#f38) é de ensino fundamental e médio; generalizar para universitários é extrapolação. Em [41](bibliografia.md#f41) o ganho dos problemas de Parsons é de eficiência, não de aprendizagem. [39](bibliografia.md#f39) é um framework a partir de observações.

### IA e aprendizagem de programação

A evidência não é unânime. Em [44](bibliografia.md#f44), 69 novatos de 10 a 17 anos fizeram 45 tarefas de Python; com Codex a taxa de conclusão foi 1,15 vez maior e as notas, 1,8 vez maiores, sem piora nas tarefas de modificação manual, e a diferença no pós-teste de 1 semana não foi significativa. Em [45](bibliografia.md#f45) (21 sessões), 20 de 21 concluíram, mas quem teve dificuldade terminou com ilusão de competência. Em [46](bibliografia.md#f46), com quase mil alunos de matemática do ensino médio, a nota na prática subiu 48% (GPT Base) e 127% (GPT Tutor); sem acesso depois, o GPT Base ficou 17% abaixo de quem nunca teve acesso, e o efeito negativo foi em grande parte mitigado no GPT Tutor. [52](bibliografia.md#f52) é um ensaio randomizado com 52 engenheiros de software: 50% no questionário com IA contra 67% sem (d = 0,738, p = 0,01); notas altas apareceram em quem perguntou para entender. [50](bibliografia.md#f50) é um ensaio randomizado em que um tutor de IA superou uma aula de aprendizagem ativa. [47](bibliografia.md#f47), [48](bibliografia.md#f48) e [49](bibliografia.md#f49) relatam implantações em sala de ferramentas que não entregam a solução, e [51](bibliografia.md#f51) e [53](bibliografia.md#f53) são, respectivamente, autorrelato de trabalhadores e análise descritiva de uso.

Onde a evidência é fraca ou disputada: [46](bibliografia.md#f46) é de matemática do ensino médio; [52](bibliografia.md#f52) é pré-publicação, com 52 pessoas, medida logo após a tarefa e da empresa que faz o Claude; [44](bibliografia.md#f44) não achou prejuízo em novatos jovens. [47](bibliografia.md#f47), [48](bibliografia.md#f48), [49](bibliografia.md#f49) e [51](bibliografia.md#f51) medem uso e percepção, não aprendizagem; [53](bibliografia.md#f53) mede o que os alunos delegam e também é da Anthropic, sem revisão por pares. Os estudos são recentes, curtos e heterogêneos.

### Estilos de aprendizagem (por que o kit não os usa)

[34](bibliografia.md#f34) concluiu que não há base de evidência adequada para justificar o uso de avaliações de estilos de aprendizagem na prática educacional geral: encontrou preferências e aptidões diferentes entre pessoas, mas praticamente nenhuma evidência do padrão de interação exigido para validar instrução ajustada ao estilo. Por isso o perfil do aluno no kit não tem rótulos de estilo; ele registra conhecimento prévio [17](bibliografia.md#f17), padrões de erro e comportamento de pedido de ajuda [28](bibliografia.md#f28), sempre com data e evidência.

Ressalva: os autores de [34](bibliografia.md#f34) dizem que nem todas as versões da hipótese foram testadas; a fonte mostra falta de evidência, não prova de que estilos não existam.

### Prática deliberada

[10](bibliografia.md#f10) propôs a prática deliberada como explicação de desempenho de especialistas. A meta-análise [11](bibliografia.md#f11) achou que ela explicou 26% da variância em jogos, 21% em música, 18% em esportes, 4% em educação e menos de 1% em profissões, e concluiu que é importante, mas menos do que se argumentava. O kit abre a sessão com os temas mais fracos e os erros mais repetidos, mas sem prometer um efeito grande.

Onde a evidência é fraca: o efeito foi revisto para baixo e nenhum dos dois trabalhos trata de aprendizes de programação.
