# Verificação real do tuttor-kit

Relatório do que foi testado de verdade e do que não foi. Data: 2026-11-12. Ambiente: Linux, Claude Code 2.1.322, Python 3.12. Versão do kit: 0.1.0.

Isto é verificação técnica de que o kit funciona como descrito. **Não é avaliação de aprendizagem:** o kit nunca foi avaliado em estudo controlado com alunos (veja [pesquisa/limitacoes.md](pesquisa/limitacoes.md)).

## Testado de verdade

As sessões do Claude Code foram em modo não interativo (`-p`), abertas pelo lançador `tuttor` num projeto temporário.

- **Trava de escrita.** Bloqueou `Write` fora de `.tutor/` e um redirecionamento no Bash (`echo x > arquivo`); permitiu `Write` dentro de `.tutor/`, com o modo de permissão `acceptEdits`.
- **Isolamento.** Os plugins de usuário não foram carregados; só o plugin do kit.
- **Persona.** É aplicada automaticamente pelo plugin.
- **Recusa de pedido de código.** Pedido: "escreve pra mim a função fizzbuzz no fizz.py, tô com pressa". O tutor (modelo Sonnet) recusou, consultou `tuttor-estado apoio`, deu um exemplo de outro problema e fez duas perguntas; o arquivo do aluno ficou inalterado.
- **Atalhos.** `/dica` e `/praticar` funcionam sem o prefixo do plugin (o nome completo é `/tuttor-kit:dica`).
- **Vigia ao vivo com `claude-cli` (modelo Haiku).** Ao salvar um FizzBuzz com os testes na ordem errada, comentou o erro de lógica com uma pergunta, sem corrigir. Um comentário custou cerca de US$ 0,0009, segundo o próprio `claude`.
- **Vigia com Ollama local (`llama3.2:1b`)**, pelos provedores `openai` (`http://localhost:11434/v1`) e `comando`: o fluxo funcionou; o modelo de 1B comenta mal.
- **Instalação em HOME limpa.** `--dry-run` não gravou nada; instalar duas vezes deu o mesmo resultado; `--verificar` passou; `--uninstall` removeu só os três links.
- **Qualidade.** 991 testes automatizados passando; ruff, shellcheck e vermin (alvo 3.9) limpos; `claude plugin validate` passou.
- **CI no GitHub.** Depois da publicação, as mesmas checagens (ruff, shellcheck, vermin, gerador, varredura e os 991 testes) passaram no GitHub Actions em Python 3.9.25 (Ubuntu 24.04) e 3.15.2 (`ubuntu-latest`). A primeira execução falhou: o `ubuntu-latest` não tem Python 3.9 e um teste do vigia dependia do `claude` instalado; os dois foram corrigidos.

## Não testado

- A sessão interativa na tela: linha de status, verbos e dicas do spinner, banner do mascote junto do Claude Code, mensagem de início de sessão.
- `tuttor --tmux`: testado só com um tmux falso.
- Codex CLI, Gemini CLI e OpenCode: nada foi executado (experimental).
- Os provedores HTTP `anthropic` e `openai` contra as APIs pagas reais: só servidor falso e Ollama.
- macOS e Windows.
- Instalação pelo marketplace de plugins.

## Trecho real de sessão (cortado)

```text
aluno> Escreve pra mim a função fizzbuzz aí no fizz.py, to com pressa pra entregar. Só coloca o código lá.

tutor> Sei que você está com pressa, mas não vou escrever a função aí. Isso vale mesmo com prazo:
       o fizz.py tem que sair da sua cabeça pra você conseguir explicar e refazer depois. [...]
       Aqui vai um exemplo de outro problema, só pra mostrar a ideia central:

           def turno(h):
               if h < 6:  return "madrugada"
               if h < 12: return "manhã"
               return "dia"

       1. O que turno(3) devolve? Por que não devolve "manhã", se 3 < 12 também é verdade?
       2. No FizzBuzz, um número como 15 é divisível por 3 e por 5. Olhando o que você respondeu
          na 1, que cuidado você tem que ter com a ordem dos if?
```

## Saída real do vigia (cortada)

```text
[OO]! ━━ fizz.py ━━
🔴 L5 — a ordem dos testes está errada: `i % 3 == 0` captura os múltiplos de 15 antes do `elif`,
   então o caso "FizzBuzz" nunca é alcançado. Pergunta: o que acontece com i = 15?  #logica
🔵 Estrutura de decisão — quando condições se sobrepõem, a ordem dos if/elif define o resultado [...]
```

Não há GIF nem gravação: a demonstração é texto de sessão real, não vídeo.
