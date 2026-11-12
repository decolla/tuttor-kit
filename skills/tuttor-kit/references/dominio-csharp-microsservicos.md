---
name: csharp-microsservicos
description: Mapa de estudo, pré-requisitos, armadilhas e checklist de revisão para C#/.NET e microsserviços. Use ao montar trilhas de estudo, explicar conceitos ou revisar código C#, ASP.NET Core, EF Core, mensageria, resiliência ou arquitetura de microsserviços.
---

Base de conhecimento do tutor para o stack do aluno: **C# / .NET em microsserviços**. Serve para montar trilhas, calibrar o que perguntar e revisar. Não é para despejar no aluno: use o que a situação pede.

## Mapa de conceitos e pré-requisitos

Leia como "para estudar X, antes precisa de Y". Sonde o nível em Y antes de ensinar X.

**C# e .NET (base)**
- `async`/`await` e `Task`: precisa de noção de threads e I/O. Armadilhas: `.Result`/`.Wait()` (deadlock e bloqueio), `async void`, esquecer `await`, não propagar `CancellationToken`, `Task.Run` para "tornar async" algo de I/O.
- Nulos: *nullable reference types*, `?`, `??`, `is null`. Armadilha: silenciar warning com `!` sem entender.
- Coleções e LINQ: execução adiada, múltiplas enumerações, `ToList()` no lugar errado, `IEnumerable` vs `IQueryable` (EF).
- `IDisposable`/`using`, `record`, imutabilidade, exceções (quando lançar, quando capturar, não engolir exceção).
- Injeção de dependência: tempos de vida (*Singleton*, *Scoped*, *Transient*). Armadilha clássica: Singleton dependendo de Scoped (captive dependency), `DbContext` em Singleton.

**ASP.NET Core**
- Pipeline de middlewares (ordem importa), *model binding* e validação, controllers vs minimal APIs, `ProblemDetails` para erros, *Options pattern* e configuração, `ILogger` com logs estruturados (nunca concatenar string), *health checks*, autenticação JWT/OIDC e autorização.
- Armadilhas: lógica de negócio no controller, devolver entidade de banco como DTO, segredo em `appsettings.json`, `catch (Exception)` genérico, status HTTP errados.

**Dados**
- Pré-requisito: SQL básico, índices, transações. EF Core: ciclo de vida do `DbContext` (Scoped), *change tracking* e `AsNoTracking`, N+1 (`Include`), *migrations*, concorrência otimista, `SaveChanges` em lote.
- Armadilhas: consulta dentro de laço, carregar tabela inteira em memória, `ToList()` antes do `Where`, DbContext compartilhado entre threads.

**Comunicação entre serviços**
- Pré-requisito: HTTP/REST bem entendido, serialização, contratos e versionamento.
- HTTP síncrono: `IHttpClientFactory` (nunca `new HttpClient()` por requisição), timeouts, tratar falha parcial. gRPC quando fizer sentido.
- Mensageria (RabbitMQ, Kafka, Azure Service Bus; bibliotecas como MassTransit ou Wolverine): comando vs evento, entrega *at-least-once* (então consumidor **idempotente**), ordem, *dead-letter queue*, *poison messages*, contratos de evento versionados.

**Resiliência**
- Pré-requisito: `async`, `HttpClientFactory`. Timeouts, *retry* com *backoff* exponencial e *jitter*, *circuit breaker*, *bulkhead* (Polly / `Microsoft.Extensions.Http.Resilience`).
- Armadilhas: retry em operação não idempotente, retry sem limite nem jitter (tempestade de retries), sem timeout, retries em camadas empilhadas.

**Consistência distribuída**
- Pré-requisito: transações, mensageria, idempotência. *Eventual consistency*, **Outbox** (gravar o evento na mesma transação do dado), **Saga** (orquestrada vs coreografada, compensação), por que evitar transação distribuída (2PC).
- Armadilha: "salvar no banco e publicar no broker" como duas operações independentes (dual write).

**Arquitetura**
- *Bounded context* (DDD), um banco por serviço (dono do dado), API Gateway/BFF, CQRS (e quando **não** usar), acoplamento por contrato, *service discovery*, camadas (Clean/Hexagonal).
- Pergunta-guia de fronteira: "se este serviço cair, o que para? se este dado mudar, quem precisa saber?" Sinal de alerta: microsserviços que sempre mudam juntos (monólito distribuído).

**Operação e observabilidade**
- Docker (imagem multi-stage, variáveis de ambiente, segredos), docker-compose, noções de Kubernetes, CI/CD.
- Logs estruturados, métricas, *distributed tracing* com OpenTelemetry, **correlation id** propagado entre serviços, health checks (*liveness* vs *readiness*).

**Testes**
- xUnit; *mocks* (Moq, NSubstitute) com moderação; testes de integração com `WebApplicationFactory` e Testcontainers; testes de contrato entre serviços; nomear testes por comportamento; teste de caso de borda e de falha.

## Checklist de revisão (use para priorizar, não para listar tudo)

1. Funciona? Lógica, nulos, caso vazio, limite, concorrência.
2. `async` correto de ponta a ponta, com `CancellationToken`?
3. O que acontece se a chamada a outro serviço falhar, demorar ou for repetida? (timeout, retry seguro, idempotência)
4. Dado e fronteira: quem é dono? DTO separado da entidade? Contrato versionável?
5. Tempo de vida da DI e do `DbContext`/`HttpClient` corretos?
6. Erros: exceção específica, mensagem útil, sem `catch` que engole, `ProblemDetails`/status certos.
7. Segurança: validação de entrada, autorização, segredo fora do código, nada sensível nos logs.
8. Observabilidade: log estruturado com contexto e correlation id, sem log excessivo em laço.
9. Testes cobrindo o comportamento e as falhas.
10. Legibilidade: nomes, métodos pequenos, duplicação, comentários que explicam o porquê.

## Fontes de partida (verificadas em 09/11/2026; confira a versão e pesquise o resto)

- .NET Microservices: Architecture for Containerized .NET Applications — https://learn.microsoft.com/en-us/dotnet/architecture/microservices/
- A pattern language for microservices (catálogo de padrões: saga, outbox, API gateway...) — https://microservices.io/patterns/index.html
- Programação assíncrona em C# — https://learn.microsoft.com/en-us/dotnet/csharp/asynchronous-programming/
- Injeção de dependência no .NET (tempos de vida) — https://learn.microsoft.com/en-us/dotnet/core/extensions/dependency-injection
- ASP.NET Core (documentação) — https://learn.microsoft.com/en-us/aspnet/core/
- Entity Framework Core — https://learn.microsoft.com/en-us/ef/core/
- `IHttpClientFactory` — https://learn.microsoft.com/en-us/dotnet/core/extensions/httpclient-factory
- Polly (resiliência) — https://www.pollydocs.org/
- OpenTelemetry para .NET — https://opentelemetry.io/docs/languages/dotnet/

Estas são só o ponto de partida: para a versão do projeto e para qualquer outro tópico (Kafka, Spark, RabbitMQ, Azure Service Bus, MassTransit, Kubernetes, gRPC, bibliotecas...), pesquise e verifique a página com WebSearch/WebFetch (ou use `/fontes`) antes de citar; não cite URL de memória.

## Ideias de mini-laboratórios (o aluno cria; você não escreve)

- `async`: console que chama duas APIs em sequência e depois em paralelo (`Task.WhenAll`), medindo o tempo; depois provocar um deadlock com `.Result` num contexto de sincronização para entender por quê.
- DI: registrar o mesmo serviço como Singleton, Scoped e Transient e imprimir o `Guid` de instância em duas requisições.
- EF Core: reproduzir N+1 com logs de SQL ligados e corrigir com `Include`/projeção.
- Resiliência: um endpoint que falha 50% das vezes e um cliente com retry + backoff + circuit breaker; observar o breaker abrir.
- Idempotência: consumidor de mensagem que recebe a mesma mensagem duas vezes e não duplica o efeito.
- Outbox: gravar pedido + evento na mesma transação e um *worker* que publica os eventos pendentes.
