# OpenCode: experimental (não testado)

Fontes consultadas em 2026-11-11: https://opencode.ai/docs/ e https://dev.opencode.ai/v2/docs/.
Repositório: https://github.com/sst/opencode (aberto como `anomalyco/opencode`). Nada aqui foi executado.

**Atenção às versões**: a documentação atual descreve a **V2** (instalação `https://opencode.ai/v2/install`,
pacote `@opencode/cli`). A V2 usa `permissions`, `shell`, `subagent`; a V1 usava `permission`, `bash`,
`task` ("V1 uses different field and action names", [permissões](https://opencode.ai/docs/permissions/)).
A página de integração do Ollama ainda usa chaves de estilo V1 (`provider`, `options.baseURL`),
enquanto a doc da V2 usa `providers` e `settings.baseURL`. Confira qual versão você instalou.

## 1. Instruções persistentes
`AGENTS.md` na raiz do projeto (vale na pasta e subpastas) e `~/.config/opencode/AGENTS.md` (global).
`CLAUDE.md` do projeto só vale se não houver `AGENTS.md`; `~/.claude/CLAUDE.md` só se não houver o global
(desligue com `OPENCODE_DISABLE_CLAUDE_CODE=1`). Procura para cima a partir do diretório atual; "o primeiro
arquivo achado vence em cada categoria". Campo `instructions` em `opencode.json` soma outros arquivos.
[fonte](https://opencode.ai/docs/rules/). Modelo: `modelos/opencode/AGENTS.md`.

## 2. Skills e comandos
- Skills: `.opencode/skills`, `.claude/skills`, `.agents/skills` (projeto, subindo até a raiz), e globais
  `~/.config/opencode/skills`, `~/.claude/skills`, `~/.agents/skills`; frontmatter `name`, `description`;
  ação de permissão `skill`. [fonte](https://opencode.ai/docs/skills/)
- Comandos: Markdown em `.opencode/commands/` ou `~/.config/opencode/commands/`; frontmatter `description`,
  `agent`, `model`, `subagent`; `$ARGUMENTS`, `$1`... [fonte](https://opencode.ai/docs/commands/)
- Agentes: `.opencode/agents/<nome>.md` (corpo = `system`) ou chave `agents`; `mode`, `permissions`;
  `default_agent`. [fonte](https://opencode.ai/docs/agents/)

## 3. Modo não interativo (vigia)
`opencode run "mensagem"` envia e imprime a resposta. Flags documentadas: `--model provider/modelo`,
`--agent`, `--format json` (JSON por linha), `--file`, `--continue`, `--session`, `--auto` ("aprova
permissões que não estejam explicitamente negadas"; **não use**), `--standalone`.
[fonte](https://dev.opencode.ai/v2/docs/cli/commands). **Leitura do prompt pelo stdin: não documentada**, e o
prompt vai como argumento. Como o provedor `comando` do vigia só passa o prompt pelo stdin (sem shell,
sem marcador de argumento), **não há linha verificada** (`vigia_comando` é `null`). Alternativa: provedor
`openai` do vigia apontando para o servidor do modelo que o OpenCode usaria (por exemplo Ollama local).
Não verificado: formato `-m`; saída só com a resposta.

## 4. Trava de escrita
- **Permissões** (V2): lista `permissions` de `{action, resource, effect}`; `effect` = `allow`, `ask`, `deny`;
  a última regra que casa vence; sem regra, `ask`; padrão `*` casa qualquer coisa, inclusive `/`.
  Ações: `read`, `edit`, `glob`, `grep`, `shell`, `subagent`, `skill`, `webfetch`, `external_directory`...
  A ação `edit` cobre as ferramentas `edit`, `write` e `patch`. Por agente: `agents.<id>.permissions`
  (somadas depois das globais). O agente embutido `plan` nega edições, exceto sob `~/.opencode/plan`.
  [fonte](https://opencode.ai/docs/permissions/). Modelo: `modelos/opencode/opencode.jsonc` (nega `edit`,
  libera `.tutor/`; o shell fica em `ask`).
  O que garante: o OpenCode não edita fora de `.tutor/` pelas ferramentas de edição. O que não garante:
  um comando de shell (`shell`) pode gravar arquivos; a doc diz também que blocos `!` de comandos
  personalizados "rodam fora do fluxo de permissão das ferramentas". Não verificado: se `resource` de
  `edit` é caminho relativo ou absoluto; `external_directory` permite por padrão.
- **Hook**: plugins (`.opencode/plugins/`, `~/.config/opencode/plugins/`) registram `execute.before` com
  `ctx.tool.hook`, que recebe `event.tool` e `event.input`; a doc **não** descreve valor de retorno nem
  como bloquear nesse hook. Um hook de permissão (`evaluate`) pode definir `event.effect` como `"deny"`.
  É código TypeScript, não um comando com JSON no stdin: **não é viável reaproveitar o `guard.py`**
  sem escrever um plugin que o chame; contrato de bloqueio não verificado.
  [fonte](https://opencode.ai/docs/build/plugins/server/)

Resumo: proteção por mecanismo da ferramenta (experimental): permissões `edit` por agente negam a edição fora de `.tutor/` (não testado, caminhos não verificados), mas o shell continua capaz de gravar arquivos; não há hook de bloqueio documentado.

## 5. Chave de API
Não há variável única: `/connect` guarda credenciais; alguns provedores leem variáveis (ex.:
`OPENROUTER_API_KEY`); provedor próprio declara `env` e `settings.baseURL` (`providers.<id>`), com
`{env:VAR}` em strings. Ollama local é detectado em `http://127.0.0.1:11434`.
[fonte](https://opencode.ai/docs/providers/), [config](https://opencode.ai/docs/config/).

## 6. Interface
`~/.config/opencode/cli.json` (só global): `theme.name`, `theme.mode`, `mini.splash`, `mini.footer`,
`mini.turn_summary`, `session.tps`. Não encontrei status line nem banner personalizável.
[fonte](https://opencode.ai/docs/cli/config/)

## 7. Passo a passo
1. `modelos/opencode/AGENTS.md` -> `<projeto>/AGENTS.md`; `modelos/opencode/opencode.jsonc` -> `<projeto>/opencode.jsonc`.
2. Copie `skills/*` para `<projeto>/.opencode/skills/`.
3. Abra `opencode` na pasta (o `default_agent` "tutor" vem do arquivo). Flag `--agent` na TUI: não verificada.
4. Vigia: use o provedor `openai` ou `claude-cli`; o provedor `comando` não tem linha verificada para o OpenCode.

**Trava de escrita:** proteção por mecanismo da ferramenta (experimental): permissões `edit` do agente `tutor` negam edições fora de `.tutor/`; comandos de shell não são cobertos, então o modelo ainda pode gravar por eles se o aluno aprovar.
