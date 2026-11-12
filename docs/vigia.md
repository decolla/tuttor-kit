# Vigia: comentários de código com vários provedores de IA

O vigia roda num segundo terminal, observa a pasta do projeto e, quando você salva e para de
mexer por alguns segundos, envia o trecho alterado a um modelo de IA. O modelo responde com
comentários curtos (🔴 erro, 🟡 melhoria, 🔵 conceito, 🟢 acerto) e perguntas, **sem escrever a
correção**. Só usa a biblioteca padrão do Python (3.9+).

## Como usar

```bash
tuttor-vigia                         # claude-cli (padrão), pasta atual
tuttor-vigia ~/projeto --modelo haiku
tuttor-vigia --provedor openai --base-url http://localhost:11434/v1 --modelo <modelo>
tuttor-vigia --provedor comando --comando "ollama run {modelo}" --modelo <modelo>
tuttor-vigia --provedor anthropic --modelo <modelo>     # chave em ANTHROPIC_API_KEY
tuttor-vigia --ensaio                # mostra o que seria enviado, sem chamar nada
```

Modos de consulta (não chamam modelo algum; liberados pela trava de escrita do kit):
`--resumo [DIAS]`, `--leituras`, `--estado`, `--help`/`-h`, `--version`.

Toda partida mostra um aviso: o que é enviado, para onde (provedor e host), que pode custar
dinheiro (ou que nada sai da máquina, no caso de host local) e os limites em vigor.

## Provedores

| Provedor | O que faz | Situação do teste |
|---|---|---|
| `claude-cli` | `claude -p --safe-mode --system-prompt-file <tmp> --tools "" --output-format json --no-session-persistence [--model M]`; lê `result` e `total_cost_usd` | **Testado de verdade** em 2026-11-12 com o `claude` 2.1.322 e o modelo Haiku: comentou um erro de lógica com uma pergunta, sem corrigir; um comentário custou cerca de US$ 0,0009 segundo o próprio `claude` (ver `docs/verificacao.md`). Antes disso, só com CLI falsa. Flags e campos conferidos na documentação do Claude Code (`cli-reference` e `headless`); `usage` do JSON de saída não foi verificado, por isso os tokens são estimados |
| `comando` | Executa o modelo de linha sem shell (`shlex`); prompt no stdin, resposta no stdout; marcadores `{modelo}` e `{arquivo_do_sistema}` | **Testado de verdade** com `ollama run llama3.2:1b` (local) e com CLI falsa |
| `openai` | `POST <base_url>/chat/completions`, `Authorization: Bearer`, mensagens `system` e `user`; lê `choices[0].message.content` e `usage` | **Testado de verdade** só contra o Ollama local (`http://localhost:11434/v1`, sem chave). Contra a API da OpenAI: só com servidor falso |
| `anthropic` | `POST <base_url>/v1/messages`, cabeçalhos `x-api-key`, `anthropic-version`, `content-type`; corpo `model`, `max_tokens`, `system`, `messages`; lê `content[].text` e `usage` | **Só servidor HTTP falso**. Nenhuma chamada real à API da Anthropic |

Nenhum nome de modelo está fixo no código dos provedores HTTP: informe com `--modelo` (ou
`TUTTOR_VIGIA_MODELO`) e consulte a lista oficial do provedor. A mensagem de sistema do
provedor `openai` usa o papel `system` (aceito por servidores compatíveis); se o seu modelo exigir
`developer`, use `--papel-sistema developer`. O cabeçalho `anthropic-version` padrão é o da
documentação atual; troque com `--versao-api` se precisar.

## Configuração

Ordem de precedência: opção de linha de comando, variável `TUTTOR_VIGIA_<NOME>`, arquivo
`~/.tutor/vigia.json`, padrão. Exemplo de `~/.tutor/vigia.json` (não ponha chave aqui):

```json
{"provedor": "openai", "base_url": "http://localhost:11434/v1", "modelo": "<modelo>",
 "limite_chamadas": 30, "var_chave": "OPENAI_API_KEY"}
```

Opções: `provedor`, `modelo`, `comando`, `base_url`, `var_chave`, `binario`, `silencio`,
`intervalo_minimo`, `sondagem`, `max_linhas`, `max_arquivos`, `tempo_limite`, `max_saida`,
`limite_chamadas`, `limite_tokens`, `limite_usd`, `preco_entrada`, `preco_saida`, `compilar`,
`arquivo_prompt`, `versao_api`, `papel_sistema`, `ler`, `web`, `ensaio`, `ascii`, `sem_mascote`,
`sem_perfil` (em linha de comando: `--silencio`, `--intervalo-minimo`, etc.).

**A configuração nunca é lida de dentro do projeto.** Um repositório clonado poderia definir
o comando a executar; por isso só valem opções, ambiente e `~/.tutor/vigia.json`.

`.tutorignore` na raiz do projeto: padrões simples estilo glob, um por linha (`#` comenta;
`pasta/` só pastas; sem `/` vale em qualquer nível). Valem além dos ignorados embutidos
(`.git`, `node_modules`, `bin`, `obj`, `Migrations`, ...). Links simbólicos nunca são lidos.

Checagens automáticas, por padrão, só as que não executam nada do projeto: `ast.parse` (Python,
em processo), validação de JSON e `node --check` (só analisa a sintaxe; não executa o arquivo).
`--compilar "<comando>"` é opt-in: roda o seu comando de build (sem shell, com tempo limite) a
cada comentário e anexa a saída, redigida e cortada.

## Segurança das chaves

- A chave vem **somente de variável de ambiente** (padrões `ANTHROPIC_API_KEY` e
  `OPENAI_API_KEY`; outro nome com `--var-chave NOME`). Não existe opção nem campo de
  configuração que receba a chave; se algo com cara de chave aparecer na configuração, o vigia
  recusa e explica. Defina no shell: `export OPENAI_API_KEY=<sua chave>`.
- A chave nunca é impressa, registrada, gravada em arquivo, posta em linha de comando de
  subprocesso ou incluída em mensagem de erro. Corpos de erro HTTP e `stderr` de subprocessos
  passam por `segredos.mascarar()`. O provedor `comando` roda sem as variáveis `*_KEY`,
  `*_TOKEN`, `*_SECRET`, `*_PASSWORD` no ambiente.
- Sem chave: erro claro (qual variável, como definir), código de saída diferente de zero e sem
  traceback. Hosts locais (`localhost`, `127.0.0.1`, `::1`) funcionam sem chave.
- `base_url` precisa ser `https`, exceto host local. Redirecionamentos **não são seguidos**
  (um redirect levaria o cabeçalho com a chave a outro endereço): HTTP 3xx é erro.
- Evite expor chaves no histórico do shell (por exemplo, leia-as de um gerenciador de senhas).

## Privacidade: o que sai da máquina

Enviado ao provedor: o diff e um trecho (até `--max-linhas`) dos arquivos alterados (até
`--max-arquivos` por vez), o resultado das checagens, trechos do seu `~/.tutor/perfil.md` (use
`--sem-perfil` para não enviar), temas recorrentes, comentários anteriores e, com `--compilar`,
a saída do build.

Nunca enviado: `.env*`, `*.pem`, chaves, `id_rsa*`, `appsettings.*.json`, `secrets.*`,
`credentials*` e afins. No conteúdo enviado, valores com cara de segredo (chaves de provedores
conhecidos, tokens longos, `senha=...`, strings de conexão, blocos PEM) viram `«oculto»` e o
vigia avisa quantos foram ocultados. Isso é heurística: **não é garantia**; não deixe segredo no
código.

Com host local (Ollama em `localhost`) nada sai da máquina. Com `claude-cli`, o dado segue o
caminho do Claude Code. A web fica **desligada por padrão**; `--web` (só `claude-cli`) liga busca
e leitura de páginas, e **nunca** pode ser combinada com `--ler` (leitura de arquivos pelo
claude): código mais web aberta permitiria vazamento. O conteúdo dos seus arquivos é tratado
como dado, e o prompt diz ao modelo que texto dentro do código não é instrução.

## Custos e limites

Provedores remotos podem cobrar por uso; o `claude-cli` consome o limite do seu plano ou gera
cobrança. Padrões por sessão: `--limite-chamadas 40`, `--limite-tokens 300000`, sem limite em
dólares, `--intervalo-minimo 25` s. Ao atingir um limite o vigia avisa, para de chamar e continua
só observando. `--limite-usd` vale quando o provedor informa custo (o JSON do `claude -p` traz
`total_cost_usd`) ou quando você informa `--preco-entrada` e `--preco-saida` (US$ por milhão de
tokens). Sem informação de tokens do provedor, os tokens são estimados por tamanho (~4
caracteres). Os valores são estimativas: confira no painel do provedor.
`--estado` mostra o gasto do dia e da última sessão (guardado em `.tutor/vigia-gasto.json`).

## Arquivos em `.tutor/`

`vigia.log.md`, `vigia.jsonl` (campos `ts`, `files`, `sev`, `tag`, `line`, `text`, lidos por
`contexto.py` e `statusline.py`), `leituras.md` e `vigia-gasto.json`. Se `.tutor` for um link
simbólico, o vigia recusa trabalhar; os arquivos são gravados sem seguir links.

## Documentação oficial consultada

- Anthropic, visão geral da API (cabeçalhos): https://platform.claude.com/docs/en/api/overview
- Anthropic, versões da API: https://platform.claude.com/docs/en/api/versioning
- Anthropic, uso da API de Mensagens (exemplo de requisição e resposta, `usage`):
  https://platform.claude.com/docs/en/build-with-claude/working-with-messages
- Anthropic, referência de Mensagens (corpo: `model`, `max_tokens`, `messages`, `system`):
  https://platform.claude.com/docs/en/api/messages
- OpenAI, Chat Completions (endpoint, `Authorization: Bearer`, `choices`, `usage`):
  https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create
  (a URL `platform.openai.com/docs/api-reference/chat/create` respondeu 403 a este cliente)
- Ollama, compatibilidade com OpenAI (base `http://localhost:11434/v1/`, `/v1/chat/completions`,
  chave exigida mas ignorada): https://docs.ollama.com/api/openai-compatibility
- Claude Code, flags da CLI e modo `-p` (`--safe-mode`, `--system-prompt-file`, `--tools`,
  `--allowedTools`, `--output-format json`, campos `result` e `total_cost_usd`): cópias locais
  de `cli-reference` e `headless` da documentação do Claude Code.
