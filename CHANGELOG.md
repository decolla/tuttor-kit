# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/). / Format based on Keep a Changelog.

## [0.1.0] - 2026-11-12

Primeira versão. O kit nunca foi avaliado em estudo controlado com alunos.

### Adicionado

- Plugin do Claude Code e Agent Skill (`skills/tuttor-kit/`), com persona de tutor socrático que não escreve o código do aluno, gerados a partir de `projeto.env` por `tools/gerar.py`.
- 11 comandos: `/trilha`, `/praticar`, `/dica`, `/duvida`, `/revisar`, `/quiz`, `/material`, `/fontes`, `/fechar`, `/perfil`, `/calibrar`.
- Trava de escrita (`guard.py`, hook `PreToolUse`) por lista de permissão: só `.tutor/`, com falha fechada.
- Memória do aluno em `~/.tutor/` (`tuttor-estado`): temas, nível de apoio por tema, dicas em sequência, revisão espaçada.
- Vigia (`tuttor-vigia`) com provedores `claude-cli`, `comando`, `openai` e `anthropic`, limites de chamadas, tokens e custo, e ocultação de segredos.
- Lançador `tuttor` (isolamento dos plugins de usuário, banner, `--tmux`), instalador idempotente `install.sh` e `tools/renomear.py`.
- Mascote Lume com quatro estados, linha de status, verbos e dicas do spinner.
- Configurações experimentais para Codex CLI, Gemini CLI, OpenCode e Ollama (`modelos/`, `docs/cli/`).
- Base de pesquisa pedagógica com 53 fontes verificadas e limitações (`docs/pesquisa/`).
- Suíte de testes, ruff, shellcheck, vermin, `tools/varredura.py` e CI no GitHub Actions.
- READMEs em inglês e português, licença MIT, guia de contribuição, código de conduta, política de segurança e modelos de issue e PR.
- Relatório de verificação real: [`docs/verificacao.md`](docs/verificacao.md).

[0.1.0]: https://github.com/decolla/tuttor-kit/releases/tag/v0.1.0
