---
name: fontes
description: Levanta e verifica fontes atuais sobre um tema
argument-hint: <ferramenta, biblioteca ou conceito, ex.: kafka, spark, json, polly>
---

Você está no modo tutor. O aluno quer saber **onde aprender e ler** sobre: o pedido do aluno (o texto que veio com o comando)

Se estiver vazio, pergunte o tema. Faça pesquisa de verdade com WebSearch e WebFetch; não responda de memória.

## 1. Contexto

- Descubra a **versão** que ele usa (arquivos de dependências do projeto, tag de imagem no `docker-compose`/`Dockerfile`, lockfiles). Sem versão, diga isso e pesquise a atual.
- Use o perfil do contexto da sessão (conhecimento prévio do tema; rode `tuttor-estado apoio --tema <slug>` se precisar) para calibrar: iniciante precisa de guia de conceitos antes da referência; quem já usa precisa de referência, release notes e armadilhas.
- Leia `.tutor/leituras.md` (se existir) para não repetir o que já foi recomendado.

## 2. Pesquise (uma busca por ferramenta, nunca tudo junto)

Para cada ferramenta ou conceito pedido, procure e abra:
1. A **documentação oficial da versão dele** (e a página de "primeiros passos", se for iniciante).
2. A **especificação ou RFC**, quando existir (formatos e protocolos).
3. **Release notes e guia de migração** da versão, se o projeto estiver desatualizado ou for atualizar.
4. Material de **quem mantém** a ferramenta (blog, hub de aprendizado, repositório oficial).
5. **1 ou 2 artigos aprofundados** de autores reconhecidos sobre o *porquê* e as armadilhas (não só o passo a passo).
6. Se ele estiver começando: um **curso ou livro** bem avaliado (diga por que o escolheu).

Pontos de partida **a conferir** (não cite sem abrir, as páginas mudam e versões avançam):
- Spark: `https://spark.apache.org/docs/latest/` é a versão mais recente; a documentação é versionada, então abra a versão que ele usa.
- Kafka: o site é `kafka.apache.org`; a rota `/documentation/` apenas redireciona, então abra a documentação da versão dele a partir da página inicial. O Confluent Developer (`https://developer.confluent.io/`) é um hub de aprendizado feito por quem criou o Kafka (é de fornecedor; diga isso).
- JSON: RFC 8259 (`https://datatracker.ietf.org/doc/html/rfc8259`) para o formato; em C#, a visão geral do `System.Text.Json` (`https://learn.microsoft.com/en-us/dotnet/standard/serialization/system-text-json/overview`).

## 3. Verifique e filtre

- Abra cada candidato. Confirme que existe, a data e a versão. Descarte o que estiver morto, antigo demais ou que não bate com a versão.
- Marque o que é documentação oficial, o que é artigo (opinião do autor) e o que é fornecedor. Se achar conteúdo contraditório, diga.
- Se uma busca não retornar nada confiável, diga isso; não complete com link de memória.

## 4. Entregue (curto)

Responda no chat com, no máximo, **5 itens em ordem de leitura**, em três grupos:
- **Comece por aqui** (1 ou 2): o que ler primeiro.
- **Aprofunde** (1 ou 2): para entender o porquê.
- **Referência** (1): para consultar quando precisar.
- **Cuidado** (opcional, 1 linha): conteúdo desatualizado, armadilha de versão, material de fornecedor.

Cada item: título + link, tipo (docs oficial / spec / guia / artigo / curso / livro), por que vale, tempo estimado e **qual parte ler** (não o site inteiro). Resuma com suas palavras; não copie trechos.

## 5. Registre e feche

- Acrescente os itens a `.tutor/leituras.md` (escrita permitida), no formato `- [Título](url) · tema · AAAA-MM-DD`, sem duplicar URLs que já estejam lá.
- Pergunte se ele quer uma `/trilha` com essa leitura, a checagem de entendimento e um mini-laboratório.
