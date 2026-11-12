# Guia para quem mexe neste repositório

O tuttor-kit transforma uma CLI de IA em tutor de programação: guia com perguntas e dicas e
**não escreve o código do aluno**. É ao mesmo tempo um plugin do Claude Code e uma Agent Skill
(`skills/tuttor-kit/`). Este arquivo é para agentes de IA e pessoas que vão alterar o kit; para
usar o tutor em outra CLI, veja `docs/cli/README.md`.

## Mapa

| Pasta ou arquivo | O que é |
|---|---|
| `projeto.env` | Fonte única de nome, comando, versão, mascote, dono e descrição |
| `skills/tuttor-kit/` | A skill principal: `SKILL.md` (à mão), `references/` (persona, pedagogia, comandos, domínios), `scripts/` (hooks, estado, vigia), `assets/` |
| `skills/<comando>/SKILL.md` | Atalhos finos, um por comando. **Gerados** |
| `.claude-plugin/`, `hooks/hooks.json`, `output-styles/tutor.md`, `skills/tuttor-kit/assets/kit.json` | **Gerados** |
| `tools/gerar.py` | O gerador |
| `tools/varredura.py` | Varredura de segredos e dados pessoais nos arquivos rastreados (`--historico` inclui os commits); lista de exceções em `tools/varredura-permitidos.txt` |
| `tools/renomear.py` | Renomeia o kit (nome e comando): `python3 tools/renomear.py [--dry-run] <novo_nome> <novo_comando>` |
| `pyproject.toml` | Só configuração de ferramentas (ruff, pytest); o kit não é um pacote Python |
| `.github/workflows/ci.yml` | CI: ruff, shellcheck, vermin (3.9), `gerar.py --conferir`, `varredura.py` e pytest, em Python 3.9 e na versão estável mais nova |
| `install.sh` | Instalador idempotente: links de `bin/` em `~/.local/bin` (`--dry-run`, `--forcar`, `--uninstall`, `--verificar`) |
| `bin/` | `tuttor` (o lançador: abre o Claude Code isolado, com banner; `--tmux`, `--cli`), `tuttor-vigia` e `tuttor-estado`; entram no PATH quando o plugin está ativo |
| `modelos/`, `docs/cli/` | Configuração do tutor em Codex CLI, Gemini CLI, OpenCode e Ollama |
| `docs/pesquisa/` | Base de pesquisa pedagógica e limitações |
| `tests/` | Suíte pytest |

## Comandos

```bash
python3 -m pytest tests -q -p no:cacheprovider   # testes
python3 tools/gerar.py                           # regenera os arquivos gerados
python3 tools/gerar.py --conferir                # só confere (o CI usa); sai com 1 se atrasado
python3 tools/varredura.py                       # segredos e dados pessoais (o CI usa)
```

Mudou `projeto.env`, uma referência de comando ou `references/persona.md`? Rode o gerador e
inclua os arquivos gerados no mesmo commit.

## Regras

1. **Nunca enfraqueça a trava.** `scripts/guard.py` e a regra de ouro da persona (o tutor não
   escreve o código do aluno) só podem ficar mais estritos. Mudança nelas exige teste novo em
   `tests/test_guard.py`.
2. **Arquivo gerado não se edita à mão.** Altere a origem (`projeto.env`, `references/*.md`,
   `tools/gerar.py`) e regenere. Cada gerado traz o aviso "gerado por tools/gerar.py; não edite à
   mão"; os JSON, que não aceitam comentário, estão listados em `gerados()` no gerador.
3. **Nada pessoal.** Sem e-mail, sem caminho de home (`/home/<usuario>`), sem nome real. O único
   identificador permitido é o usuário do GitHub, e só em `projeto.env` (`DONO`).
4. **Toda afirmação pedagógica precisa de apoio em `docs/pesquisa/`.** Se não houver, acrescente a
   fonte lá ou escreva como escolha de projeto, sem dizer que a literatura prova.
5. **Nada de campo de manifesto, chave de frontmatter ou variável do Claude Code inventados.**
   Confira na documentação oficial (`https://code.claude.com/docs/llms.txt`) e deixe de fora o que
   não achar.
6. Python só com biblioteca padrão, compatível com 3.9+, linhas até 100 colunas; identificadores
   e mensagens em português do Brasil.
