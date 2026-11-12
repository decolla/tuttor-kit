# Outras CLIs de IA com o tuttor-kit

O kit nasceu para o Claude Code. Estas páginas descrevem, com base **só na documentação oficial**
de cada ferramenta (consultada em 2026-11-11, fontes em [`fontes.json`](fontes.json)), como levar o
tutor a outras quatro CLIs. Nada de Codex, Gemini CLI e OpenCode foi executado: tudo isso é
**experimental (não testado)**. Essas ferramentas mudam rápido; confira a doc antes de confiar.

## Tabela de CLIs suportadas

| CLI | Tutor interativo | Comandos | Trava de escrita | Vigia | Situação |
|---|---|---|---|---|---|
| Claude Code | plugin, persona (output style) | skills `/tuttor-kit:...` | hook `guard.py` | `claude-cli` | **testado** em sessões reais não interativas (`-p`) em 2026-11-12 (Claude Code 2.1.322, Linux); a tela interativa não foi testada; ver `docs/verificacao.md` |
| [Codex CLI](codex.md) | `AGENTS.md` + `codex --sandbox read-only` | skills em `.agents/skills` (prompts em `~/.codex/prompts` estão obsoletos) | sandbox somente leitura (impede também gravar em `.tutor/`); perfil de permissões (Beta) e hook `PreToolUse` descritos | `codex exec ... -` (stdin) | experimental (não testado) |
| [Gemini CLI](gemini.md) | `GEMINI.md` + `--approval-mode plan` | skills em `.gemini/skills` ou `.agents/skills`; comandos TOML | modo plano + política em `~/.gemini/policies`; hook `BeforeTool` descrito | `gemini -p` (anexado ao stdin) | experimental (não testado); aviso de migração para o Antigravity CLI |
| [OpenCode](opencode.md) | `AGENTS.md` + agente `tutor` | skills e comandos em `.opencode/` | permissões `edit` por agente; hook de plugin sem bloqueio documentado | não: stdin não documentado | experimental (não testado); docs na V2 |
| [Ollama](ollama.md) | `ollama run tuttor` (Modelfile com `SYSTEM`) | nenhum | sem mecanismo equivalente (mas `ollama run` só conversa) | **testado** com `llama3.2:1b`: provedor `openai` (`http://localhost:11434/v1`) e `comando` (`ollama run {modelo}`), ver `docs/vigia.md` | Modelfile validado localmente; vigia testado; tutor com modelo de 1B **desobedeceu** a instrução (escreveu código) |

"Testado" aqui significa executado de verdade. O que está só em documentação fica como experimental.

## O que cada peça precisa

1. **Instruções persistentes** carregam a persona (o gerador do kit troca `{{PERSONA}}` nos arquivos de
   `modelos/<cli>/`).
2. **Trava de escrita**: o kit original usa um hook. Nas outras CLIs só existe o equivalente
   quando a ferramenta tem sandbox, permissões ou hook documentados; cada página diz o que o
   mecanismo garante e o que não garante. Sem mecanismo, a proteção depende só das instruções.
3. **Vigia**: provedor `comando`, que roda sem shell, com o prompt no stdin e a resposta no stdout.
   Atenção: esse provedor **remove do ambiente** variáveis `*_KEY`, `*_TOKEN`, `*_SECRET` e
   `*_PASSWORD` (ver `docs/vigia.md`). Então `CODEX_API_KEY`, `GEMINI_API_KEY` e `OLLAMA_API_KEY` não chegam
   à CLI filha; use o login em cache de cada ferramenta (ou, no Gemini, um arquivo `.env`, que ele
   mesmo lê).

## Arquivos

- `modelos/cli.json`: dados para o lançador (uma entrada por CLI).
- `modelos/<cli>/`: exemplos de configuração, só onde a sintaxe foi verificada na doc oficial,
  cada um com a URL de origem no topo.
- `docs/cli/fontes.json`: cada fato, com URL e data de abertura.

## Aviso sobre domínio da doc do Codex

As páginas `developers.openai.com/codex/...` respondem com redirecionamento permanente (308) para
`learn.chatgpt.com/docs/...`; as fontes citam o endereço final que foi aberto.
