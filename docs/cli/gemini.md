# Gemini CLI (Google): experimental (não testado)

Fontes consultadas em 2026-11-11: https://geminicli.com/docs/ (a doc não informa número de versão).
Repositório: https://github.com/google-gemini/gemini-cli. Nada aqui foi executado.

**Aviso da própria doc**: as páginas dizem que o Gemini CLI foi substituído pelo Antigravity CLI em
18/06/2026 para usuários sem plano pago e Google One, que o repositório se destina a clientes
Gemini Code Assist corporativos e que o CLI "não é otimizado para o Gemini 4 Argon". A doc pede para
conferir versões atuais; o que segue pode estar desatualizado.

## 1. Instruções persistentes
`GEMINI.md`: global em `~/.gemini/GEMINI.md`; também procura nos diretórios do workspace e pais, e
sob demanda quando uma ferramenta acessa uma pasta. `context.fileName` em `settings.json` aceita outros
nomes (ex.: `["AGENTS.md", "GEMINI.md"]`); `@arquivo.md` importa; `/memory show` e `/memory reload`.
[fonte](https://geminicli.com/docs/cli/gemini-md/). Modelo: `modelos/gemini/GEMINI.md`.

## 2. Skills e comandos
- Skills (padrão agentskills.io): `~/.gemini/skills` ou `~/.agents/skills` (usuário); `.gemini/skills` ou
  `.agents/skills` (projeto; `.agents` vence). `/skills list|enable|disable|reload`.
  [fonte](https://geminicli.com/docs/cli/skills/). Campos do `SKILL.md`: não verificados nesta página.
- Comandos: arquivos TOML em `~/.gemini/commands/` ou `<projeto>/.gemini/commands/`; campos `prompt`
  (obrigatório) e `description`; subpasta vira `/pasta:nome`; `{{args}}`, `!{...}`, `@{...}`;
  `/commands reload`. [fonte](https://geminicli.com/docs/cli/custom-commands/)

## 3. Modo não interativo (vigia)
`-p/--prompt`: "anexado ao stdin, se houver; força modo não interativo". `-m/--model`,
`--approval-mode default|auto_edit|yolo|plan`, `-o/--output-format text|json|stream-json`.
[fonte](https://geminicli.com/docs/cli/cli-reference/). Saída: 0 ok, 1 erro, 42 entrada inválida,
53 limite de turnos. [fonte](https://geminicli.com/docs/cli/headless/). Não verificado: separação
stdout/stderr e se `-p ""` vazio é aceito (por isso o `-p` leva uma frase curta).

```
tuttor-vigia --provedor comando --modelo <modelo> \
  --comando 'gemini --model {modelo} --approval-mode plan --output-format text -p "Responda ao pedido que chegou pela entrada padrao."'
```
Risco: no modo plano não interativo, a doc diz que `exit_plan_mode` é aprovado automaticamente e muda
para YOLO; um modelo que o chame sairia do modo somente leitura. Não verificado se há como proibir isso
só pela linha de comando.

## 4. Trava de escrita
- **Modo plano** (`--approval-mode plan`, ou `general.defaultApprovalMode`): somente leitura; `write_file` e
  `replace` só funcionam em arquivos `.md` do diretório de planos (padrão `~/.gemini/tmp/<projeto>/<sessão>/plans/`;
  `general.plan.directory` pode apontar para dentro do projeto, e a doc diz que então é preciso uma regra de
  política). Funciona com `-p`. Não é sandbox: o que "garante" é só o que a doc descreve (ferramentas de
  leitura); não foi verificado o que acontece com `run_shell_command`.
  [fonte](https://geminicli.com/docs/cli/plan-mode/)
- **Motor de políticas**: `~/.gemini/policies/*.toml`, regras `[[rule]]` com `toolName`, `argsPattern`
  (regex sobre os argumentos em JSON), `commandPrefix`, `decision` (`allow`, `deny`, `ask_user`),
  `priority` (0 a 999), `modes`. **Políticas do projeto (`.gemini/policies`) não têm efeito** segundo a doc.
  `ask_user` vira `deny` em modo não interativo.
  [fonte](https://geminicli.com/docs/reference/policy-engine/). Modelo: `modelos/gemini/policies/tuttor.toml`
  (nega toda escrita por `write_file`/`replace`, **inclusive em `.tutor/`**: um padrão de texto sobre o
  caminho não resolve `..` nem links simbólicos, então liberar `.tutor/` por regex deixaria passar
  `x/.tutor/../../outro`; fazer isso com segurança exige um hook `BeforeTool` que normalize o
  caminho). Política não testada. Ferramentas e parâmetro `file_path`:
  [fonte](https://geminicli.com/docs/reference/tools/). Não cobre `run_shell_command`.
- **Sandbox** (`-s`, `GEMINI_SANDBOX`, `tools.sandbox`): Seatbelt (macOS), Docker/Podman, Windows nativo, gVisor,
  LXC. Na doc, Linux só tem opções em contêiner. A doc diz que "reduz mas não elimina riscos".
  [fonte](https://geminicli.com/docs/cli/sandbox/)
- **Hook `BeforeTool`**: `hooks` em `settings.json` (camadas: projeto `.gemini/settings.json`, usuário
  `~/.gemini/settings.json`, sistema). Cada evento é lista de definições `{matcher, hooks:[{type:"command",
  command, name, timeout em ms}]}`; `matcher` é regex sobre o nome da ferramenta. Entrada (stdin, JSON):
  `session_id`, `transcript_path`, `cwd`, `hook_event_name`, `timestamp`, `tool_name`, `tool_input`,
  `mcp_context`, `original_request_name`. Saída: só JSON no stdout (nada de texto solto); negar com
  `{"decision":"deny","reason":"..."}` (alias `block`; o motivo vai ao agente como erro da ferramenta) ou
  exit code 2 com motivo no stderr; outros códigos só avisam e a ação segue.
  [fonte](https://geminicli.com/docs/hooks/reference/), [exemplo](https://geminicli.com/docs/hooks/).
  Registro de exemplo: `modelos/gemini/settings.json`.
  **Viabilidade de reaproveitar o `guard.py`**: viável. Faltaria um adaptador que traduza `write_file`/
  `replace`/`run_shell_command` para `Write`/`Edit`/`Bash` (o parâmetro é `file_path`, como no Claude Code),
  que troque a saída `hookSpecificOutput` por `decision`/exit 2, e que trate `ask` (não documentado aqui).
  Não verificado: as chaves do `tool_input` de `run_shell_command` e se o hook falha aberto ou fechado.

Resumo: proteção por mecanismo da ferramenta (experimental): modo plano e regras de política em `~/.gemini/policies` impedem toda escrita por `write_file`/`replace`, inclusive em `.tutor/` (política não testada; com ela o tutor não grava trilhas nem materiais); o shell só é coberto por um hook adaptado, que não existe.

## 5. Chave de API
`GEMINI_API_KEY` (AI Studio). Vertex AI: `GOOGLE_API_KEY`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`,
`GOOGLE_APPLICATION_CREDENTIALS`. Variáveis podem vir de `.env` (`.gemini/.env` subindo pelas pastas, depois
`~/.gemini/.env`; só o primeiro arquivo achado). Headless usa credencial em cache ou variáveis.
[fonte](https://geminicli.com/docs/get-started/authentication/). Outro endereço: `GOOGLE_GEMINI_BASE_URL`
(HTTPS, salvo localhost). [fonte](https://geminicli.com/docs/reference/configuration/).
O vigia remove `*_KEY` do ambiente: use login em cache ou `~/.gemini/.env`.

## 6. Interface
`ui.theme` e `/theme` (temas embutidos e `ui.customThemes`), `ui.hideBanner`, `ui.footer.items` (e
`ui.footer.showLabels`, `hideCWD`, `hideSandboxStatus`, `hideModelInfo`, `hideContextPercentage`),
`ui.hideFooter`, `ui.customWittyPhrases`. Não existe chave `statusLine`.
[configuração](https://geminicli.com/docs/reference/configuration/), [temas](https://geminicli.com/docs/cli/themes/)

## 7. Passo a passo
1. `modelos/gemini/GEMINI.md` -> `<projeto>/GEMINI.md` (persona no lugar de `{{PERSONA}}`).
2. Copie `skills/*` para `<projeto>/.agents/skills/`.
3. Copie `modelos/gemini/policies/tuttor.toml` para `~/.gemini/policies/`.
4. Abra com `gemini --approval-mode plan`.

**Trava de escrita:** proteção por mecanismo da ferramenta (experimental): modo plano e política em `~/.gemini/policies` (não testados) bloqueiam a escrita de arquivos pelas ferramentas `write_file` e `replace`; o shell (`run_shell_command`) não é coberto sem um hook adaptado, então a proteção é parcial.
