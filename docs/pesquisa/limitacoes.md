# Limitações

Este documento diz o que a pesquisa por trás do tuttor-kit não permite concluir. Voltar ao [README](README.md).

**O kit nunca foi avaliado em estudo controlado.** Não há estudo, piloto nem dado de aprendizagem com alunos usando o tuttor-kit. Tudo aqui é projetado a partir de literatura, não comprovado por ela.

## Limitações

1. O kit não foi avaliado. Os recursos são escolhas de projeto inspiradas em fontes publicadas.
2. Quase toda a evidência forte (P1 a P3) vem de memória verbal, texto e matemática, não de programação [1](bibliografia.md#f1), [2](bibliografia.md#f2), [3](bibliografia.md#f3).
3. Vários estudos são com crianças ou adolescentes [8](bibliografia.md#f8), [38](bibliografia.md#f38), [44](bibliografia.md#f44), [46](bibliografia.md#f46); o público do kit é universitário ou estagiário.
4. As heurísticas do kit (escada de intervalos, contagem de domínio de 0 a 4, regra de dicas em sequência) são escolhas de engenharia. Não são os modelos validados dos artigos, como o Knowledge Tracing [32](bibliografia.md#f32) ou o detector de gaming [29](bibliografia.md#f29).
5. O tutor é um modelo de linguagem seguindo instruções: pode errar o conteúdo, ceder à insistência ou ignorar uma regra. A trava de escrita é a única garantia mecânica, e só no Claude Code.
6. Há debate em aberto entre instrução guiada [18](bibliografia.md#f18), falha produtiva [21](bibliografia.md#f21), [22](bibliografia.md#f22), [23](bibliografia.md#f23) e PBL com andaime [19](bibliografia.md#f19), [20](bibliografia.md#f20).
7. Os estudos de IA no ensino são recentes, curtos e heterogêneos; [52](bibliografia.md#f52) e [53](bibliografia.md#f53) são da própria Anthropic.
8. Fontes cujo texto integral não foi lido (só metadados ou resumo, ou nem isso): [4](bibliografia.md#f4), [5](bibliografia.md#f5), [6](bibliografia.md#f6), [7](bibliografia.md#f7), [13](bibliografia.md#f13), [24](bibliografia.md#f24), [25](bibliografia.md#f25), [30](bibliografia.md#f30), [31](bibliografia.md#f31), [32](bibliografia.md#f32), [40](bibliografia.md#f40), [43](bibliografia.md#f43).
9. Tudo foi verificado por resumo (abstract), não por leitura integral dos artigos, exceto os dois textos da Anthropic, lidos na página [52](bibliografia.md#f52), [53](bibliografia.md#f53).

## Onde a evidência é fraca ou disputada

- **Recuperação, espaçamento e intercalação:** efeitos medidos em memória verbal, prosa e matemática [1](bibliografia.md#f1), [2](bibliografia.md#f2), [3](bibliografia.md#f3), [6](bibliografia.md#f6), [7](bibliografia.md#f7); pouca evidência direta em programação. A escada de intervalos é do kit, não de [3](bibliografia.md#f3).
- **Autoexplicação:** [8](bibliografia.md#f8) tem 14 e 10 alunos, adolescentes e biologia; [1](bibliografia.md#f1) considera a evidência em contextos educacionais limitada para autoexplicação e interrogação elaborativa.
- **Exemplos resolvidos e reversão da expertise:** boa em domínios bem estruturados; o benefício do esmaecimento em [15](bibliografia.md#f15) é na transferência próxima; a medida de domínio do kit é uma contagem simples [14](bibliografia.md#f14), [15](bibliografia.md#f15), [16](bibliografia.md#f16), [17](bibliografia.md#f17).
- **Tentativa antes da instrução:** disputada. [18](bibliografia.md#f18) defende instrução guiada; [21](bibliografia.md#f21), [22](bibliografia.md#f22), [23](bibliografia.md#f23) defendem tentar antes, com tendência oposta para a 2ª à 5ª série e habilidades gerais em [23](bibliografia.md#f23); [19](bibliografia.md#f19), [20](bibliografia.md#f20) contestam a equiparação de PBL a descoberta sem guia.
- **Andaimes:** [24](bibliografia.md#f24) e [25](bibliografia.md#f25) são de origem conceitual e não foram lidos na íntegra.
- **Busca de ajuda:** [29](bibliografia.md#f29) é correlacional; [30](bibliografia.md#f30) e [31](bibliografia.md#f31) não têm resumo nos registros.
- **Feedback:** revisão conceitual ampla [33](bibliografia.md#f33); a distinção tarefa, processo e pessoa não foi verificada no resumo, e o formato do kit não foi testado.
- **Ensino de programação:** [38](bibliografia.md#f38) é ensino fundamental e médio; [41](bibliografia.md#f41) mostra ganho de eficiência sem diferença de aprendizagem; [39](bibliografia.md#f39) é um framework a partir de observações; [37](bibliografia.md#f37) é um estudo exploratório.
- **IA:** [46](bibliografia.md#f46) é matemática do ensino médio; [52](bibliografia.md#f52) é pré-publicação com 52 pessoas, medida logo após a tarefa; [44](bibliografia.md#f44) não achou prejuízo em novatos jovens; [47](bibliografia.md#f47), [48](bibliografia.md#f48), [49](bibliografia.md#f49) e [51](bibliografia.md#f51) medem uso e percepção, não aprendizagem; [53](bibliografia.md#f53) mede o que os alunos delegam, com falsos positivos e negativos declarados e duas versões do percentual de Ciência da Computação (38,6% e 36,8%) na mesma página.
- **Estilos de aprendizagem:** [34](bibliografia.md#f34) mostra falta de evidência, não prova de inexistência.
- **Prática deliberada:** [11](bibliografia.md#f11) mostra que explica bem menos do que se dizia (4% em educação).
- **Tutoria:** [27](bibliografia.md#f27) revisou a expectativa de [26](bibliografia.md#f26) para d = 0,79; nenhum dos dois trata de tutores baseados em modelos de linguagem.

## Fontes com marca especial

- Sem resumo nos registros consultados ([4](bibliografia.md#f4), [6](bibliografia.md#f6), [7](bibliografia.md#f7), [13](bibliografia.md#f13), [30](bibliografia.md#f30), [31](bibliografia.md#f31), [32](bibliografia.md#f32)): citadas só como origem de conceito, sem números.
- [24](bibliografia.md#f24): o resumo que o OpenAlex devolve para o DOI é de outro artigo e foi ignorado.
- [5](bibliografia.md#f5), [25](bibliografia.md#f25), [43](bibliografia.md#f43): só dados parciais verificados (ver [bibliografia.md](bibliografia.md)).
- [40](bibliografia.md#f40): link não verificado; a página na ACM DL devolveu 403 a acesso automático.
- [52](bibliografia.md#f52) e [53](bibliografia.md#f53): sem revisão por pares, da empresa que faz o Claude.
