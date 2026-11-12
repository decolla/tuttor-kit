# Contribuindo com o tuttor-kit

*English summary: run the tests, ruff, shellcheck, the generator check and the privacy scan before opening a pull request (commands below). Never weaken the write lock without a new test; every pedagogical claim needs a source in `docs/pesquisa/`; generated files are not edited by hand; nothing personal (no e-mail, no home path, no real name); CLI flags only from official documentation. Issues and pull requests may be written in English or Portuguese.*

Obrigado pelo interesse. Issues e pull requests podem ser em português ou em inglês. Antes de mexer, leia o [`AGENTS.md`](AGENTS.md): ele tem o mapa do repositório.

## Preparar o ambiente

O kit usa só a biblioteca padrão do Python (3.9 ou mais novo). Para as verificações, instale as ferramentas (as mesmas do CI):

```bash
python3 -m pip install ruff shellcheck-py vermin pytest
```

## Rodar as verificações

```bash
python3 -m pytest tests -q -p no:cacheprovider      # testes
ruff check .                                         # estilo e erros
shellcheck bin/* install.sh                          # scripts de shell
vermin --target=3.9- --no-tips --violations skills tools tests   # compatível com Python 3.9
python3 tools/gerar.py --conferir                    # arquivos gerados em dia
python3 tools/varredura.py                           # segredos e dados pessoais
```

Se `--conferir` reclamar, rode `python3 tools/gerar.py` e inclua os arquivos gerados no mesmo commit. A varredura olha os arquivos rastreados pelo git.

## Regras do projeto

1. **Nunca enfraqueça a trava de escrita.** `scripts/guard.py` e a regra de ouro da persona (o tutor não escreve o código do aluno) só podem ficar mais estritos. Toda mudança nelas exige teste novo em `tests/test_guard.py`.
2. **Toda afirmação pedagógica precisa de fonte em `docs/pesquisa/`.** Se não houver, acrescente a fonte lá (com o que ela mostra e o que não mostra) ou escreva como escolha de projeto, sem dizer que a literatura prova. Não prometa resultado de aprendizagem: o kit nunca foi avaliado em estudo controlado.
3. **Arquivo gerado não se edita à mão.** Altere a origem (`projeto.env`, `skills/tuttor-kit/references/*.md`, `tools/gerar.py`) e regenere.
4. **Nada pessoal.** Sem e-mail, sem caminho de home (`/home/<usuario>`), sem nome real. O único identificador é o usuário do GitHub.
5. **Flags, campos e variáveis de CLI só com fonte oficial.** Confira na documentação oficial da ferramenta e deixe de fora o que não achar; registre a fonte (veja `docs/cli/fontes.json`).
6. Python só com biblioteca padrão, compatível com 3.9+, linhas até 100 colunas; identificadores e mensagens em português do Brasil.
7. Diga o que você testou de verdade e o que não testou.

## Pull requests

Descreva o que mudou e por quê, e marque a lista do modelo de PR. Commits pequenos e com mensagem clara (o histórico usa prefixos como `feat`, `fix`, `docs`, `test`, `chore`).

Para vulnerabilidades, não abra issue pública: veja o [`SECURITY.md`](SECURITY.md). Ao participar, você concorda com o [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md). Contribuições são licenciadas sob a [licença MIT](LICENSE) do projeto.
