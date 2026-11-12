# Codex CLI (OpenAI): experimental (não testado)

Fontes consultadas em 2026-11-11 (a doc não informa versão da página; cita a 0.134.0 numa nota).
Base: https://learn.chatgpt.com/docs/ (redirecionamento permanente de `developers.openai.com/codex/`).
Repositório oficial: https://github.com/openai/codex. Nada aqui foi executado.

## 1. Instruções persistentes
Arquivo `AGENTS.md` (e `AGENTS.override.md`, que vem primeiro). Global: `~/.codex` (ou `CODEX_HOME`),
usa só o primeiro arquivo não vazio. Projeto: da raiz (normalmente a raiz do Git) até o diretório
atual, um arquivo por pasta; os mais próximos vêm depois e prevalecem. Limite: `project_doc_max_bytes`
(padrão 32 KiB). Nomes extras: `project_doc_fallback_filenames` em `~/.codex/config.toml`.
[fonte](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
Modelo: `modelos/codex/AGENTS.md`.

## 2. Skills e comandos
- Agent Skills: pasta com `SKILL.md` (`name` e `description` obrigatórios). Procura em `.agents/skills`
  (diretório atual até a raiz do repositório), `$HOME/.agents/skills`, `/etc/codex/skills` e as embutidas.
  [fonte](https://learn.chatgpt.com/docs/build-skills)
- Prompts personalizados (`~/.codex/prompts/*.md`, chamados com `/prompts:nome`) estão **obsoletos**;
  a doc manda usar skills. [fonte](https://learn.chatgpt.com/docs/custom-prompts)
- Não verificado: se uma skill vira comando `/nome` no Codex. As skills do kit (`skills/*/SKILL.md`)
  seguem o padrão; copie-as para `.agents/skills/`.

## 3. Modo não interativo (vigia)
`codex exec` lê o prompt do stdin se você omitir o argumento ou usar `-`; o progresso vai para
stderr e só a mensagem final para stdout; sandbox padrão é somente leitura. Flags: `--model/-m`,
`--sandbox/-s`, `--ephemeral`, `--skip-git-repo-check`, `--color always|never|auto`, `-o`.
[fonte](https://learn.chatgpt.com/docs/non-interactive-mode),
[flags](https://learn.chatgpt.com/docs/developer-commands?surface=cli)

Modelo de linha para o provedor `comando`:
```
tuttor-vigia --provedor comando --modelo <modelo> \
  --comando "codex exec --sandbox read-only --ephemeral --skip-git-repo-check --color never --model {modelo} -"
```
Sem `{arquivo_do_sistema}`, o vigia junta sistema e usuário no stdin. Uma chave `model_instructions_file`
existe, mas não foi testada para isto. Não verificado: nomes de modelos válidos (a doc só dá exemplos).

## 4. Trava de escrita
- **Sandbox** (`--sandbox`, `sandbox_mode`): `read-only`, `workspace-write` (padrão em pasta com Git),
  `danger-full-access`. Em `read-only` o Codex lê e roda comandos dentro da sandbox; a doc não lista
  cada restrição. Rede desligada por padrão. Protegidos mesmo com escrita: `.git`, `.codex`, `.agents`,
  `.aws`. [fonte](https://learn.chatgpt.com/docs/agent-approvals-security)
  **Consequência**: `read-only` também impede o tutor de gravar em `.tutor/` (trilhas, notas). O que
  garante: comandos do modelo não gravam no disco. O que não garante: a doc não afirma que o modelo
  não possa pedir aprovação para sair da sandbox; com `--ask-for-approval on-request` o aluno decide.
  `-a never` não pergunta, mas continua limitado pela sandbox.
- **Perfis de permissão (Beta)**: `default_permissions`, `[permissions.<nome>.filesystem]` com `read`,
  `write`, `deny`; `":workspace_roots"`; a doc diz que `deny` vence `write` e `write` vence `read`, e o
  mais específico vence. Não funcionam junto com `sandbox_mode`. Um perfil "leitura geral, escrita só
  em `.tutor`" é **inferência**, não exemplo da doc: `modelos/codex/config.toml`.
  [fonte](https://learn.chatgpt.com/docs/permissions)
- **Hook `PreToolUse`**: registro em `~/.codex/hooks.json`, `~/.codex/config.toml`, `<repo>/.codex/hooks.json`
  ou `<repo>/.codex/config.toml`; hooks do projeto só carregam com `.codex/` confiável e precisam ser
  aprovados em `/hooks`. Entrada (stdin, JSON): `session_id`, `transcript_path`, `cwd`, `hook_event_name`,
  `model`, `turn_id`, `tool_name`, `tool_use_id`, `tool_input` (para Bash e `apply_patch`, o texto está em
  `tool_input.command`). Saída para negar: `{"hookSpecificOutput":{"hookEventName":"PreToolUse",
  "permissionDecision":"deny","permissionDecisionReason":"..."}}`, ou `{"decision":"block","reason":"..."}`,
  ou saída com código 2 e motivo no stderr. Casa Bash, `apply_patch` (também como `Edit`/`Write`) e
  ferramentas MCP; não casa ferramentas hospedadas como `WebSearch`. `ask` **não é suportado**; campos
  não suportados marcam o hook como falho e **a chamada segue**. A própria doc chama os hooks de
  "guardrail, não fronteira de aplicação completa". [fonte](https://learn.chatgpt.com/docs/hooks)
  Exemplo de registro: `modelos/codex/hooks.json`.
  **Viabilidade de reaproveitar o `guard.py`**: o formato de negação (`hookSpecificOutput` com
  `permissionDecision`) é o mesmo do Claude Code, então a ideia é viável. Faltaria um adaptador que:
  (1) trate `apply_patch` (o `tool_input.command` é o texto do patch, não um caminho: é preciso extrair
  os arquivos); (2) converta `ask` (que o `guard.py` emite) em `deny`, pois `ask` faz o hook falhar e
  a chamada passar; (3) mapeie nomes de ferramentas. Não verificado: formato exato do patch.

Resumo: proteção por mecanismo da ferramenta (experimental): sandbox `read-only` impede gravações do
modelo no disco (inclusive em `.tutor/`); perfil de permissões e hook permitiriam liberar só `.tutor/`,
mas o perfil é inferido e o hook é descrito como guardrail, não fronteira.

## 5. Chave de API
`CODEX_API_KEY` para `codex exec`/`review` (defina só na invocação). Outro provedor:
`model_provider` + `[model_providers.<id>]` com `base_url` e `env_key`, ou `openai_base_url` (ignorado
em `.codex/config.toml` de projeto). Local: `--oss` com `--local-provider ollama` ou `oss_provider`.
[fonte](https://learn.chatgpt.com/docs/config-file/config-advanced),
[referência](https://learn.chatgpt.com/docs/config-file/config-reference).
A variável `OPENAI_BASE_URL` não aparece na doc: não verificado. Lembrete: o vigia remove `*_KEY` do ambiente.

## 6. Interface
`tui.status_line` (lista ordenada de identificadores do rodapé; `null` desliga), `tui.theme`
(tema de realce de sintaxe), `tui.terminal_title`, `tui.animations`, `tui.notifications`. Não há chave
de banner. Os identificadores válidos de `status_line` não foram verificados.

## 7. Passo a passo
1. `cp modelos/codex/AGENTS.md <projeto>/AGENTS.md` (com a persona no lugar de `{{PERSONA}}`).
2. Copie `skills/*` para `<projeto>/.agents/skills/`.
3. Abra: `codex --sandbox read-only --ask-for-approval on-request`.
4. Vigia: linha da seção 3. Faça `codex login` antes (a chave em variável não chega ao filho).

**Trava de escrita:** proteção por mecanismo da ferramenta (experimental): o sandbox `read-only` do Codex impede o modelo de gravar no disco (também em `.tutor/`); a liberação só de `.tutor/` depende de perfil (Beta, inferido) ou de hook (guardrail), ambos não testados.
