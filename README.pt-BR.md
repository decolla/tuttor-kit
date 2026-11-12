[English](README.md) · **Português (Brasil)**

```text
    ▄█▄
   ╔═══╗
   ║◦ ◦║ ═══╸
   ╚═╤═╝
    ║ ║
   ▄███▄
```

# tuttor-kit

**Transforma uma CLI de IA em tutor de programação: guia com perguntas e dicas e não escreve o código do aluno.**

[![CI](https://github.com/decolla/tuttor-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/decolla/tuttor-kit/actions/workflows/ci.yml) [![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE) ![version 0.1.0](https://img.shields.io/badge/version-0.1.0-informational)

## O que é

O tuttor-kit é um plugin do Claude Code e uma Agent Skill que põe a IA em modo tutor. Quando você pede código, ele pergunta o que você tentou, dá dicas um degrau por vez e só mostra exemplos curtos de **outro** problema. Uma trava de escrita (um hook do Claude Code) bloqueia a gravação de arquivos fora de pastas `.tutor/`. O kit também lembra seus temas mais fracos em `~/.tutor/`, agenda revisões espaçadas e traz um vigia (`tuttor-vigia`) que comenta seu código em um segundo terminal, com perguntas em vez de correções. O mascote é o Lume, um farolzinho ("eu ilumino, você pilota").

**Situação: versão 0.1.0. O kit nunca foi avaliado em estudo controlado com alunos.** Os recursos são escolhas de projeto inspiradas em pesquisa publicada, com a evidência e suas lacunas descritas em [`docs/pesquisa/`](docs/pesquisa/README.md). Veja [Limitações](#limitações) e [O que foi e o que não foi testado](#o-que-foi-e-o-que-não-foi-testado).

## Demonstração

Não há GIF nem vídeo: a demonstração é texto de sessões reais (Claude Code 2.1.322, modelo Sonnet no tutor, Haiku no vigia, verificação de 2026-11-12), cortado com `[...]`. A conversa está em português porque a sessão foi em português.

**Saída real de sessão, cortada: o tutor diante de um pedido de código pronto.** O `fizz.py` do aluno ficou inalterado.

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

**Saída real do vigia, cortada:** o aluno salvou um FizzBuzz com os testes na ordem errada.

```text
[OO]! ━━ fizz.py ━━
🔴 L5 — a ordem dos testes está errada: `i % 3 == 0` captura os múltiplos de 15 antes do `elif`,
   então o caso "FizzBuzz" nunca é alcançado. Pergunta: o que acontece com i = 15?  #logica
🔵 Estrutura de decisão — quando condições se sobrepõem, a ordem dos if/elif define o resultado [...]
```

## Início rápido

Requisitos: Python 3.9 ou mais novo, Claude Code 2.1.295 ou mais novo, git.

```bash
# 1
git clone https://github.com/decolla/tuttor-kit && cd tuttor-kit
# 2
./install.sh
# 3
cd <seu projeto> && tuttor
```

O instalador cria só três links simbólicos (`tuttor`, `tuttor-vigia`, `tuttor-estado`) em `~/.local/bin` (ou em `TUTTOR_BIN_DIR`); confira que essa pasta está no `PATH`. `./install.sh --dry-run` mostra o que faria sem gravar nada e `./install.sh --verificar` confere o ambiente.

O vigia roda em **outro terminal**, na mesma pasta do projeto:

```bash
tuttor-vigia            # provedor padrão: claude-cli
tuttor-vigia --ensaio   # mostra o que seria enviado, sem chamar nada
```

`tuttor --tmux` abre os dois painéis de uma vez (testado só com um tmux falso). `tuttor --ajuda` lista as opções.

### Instalação pelo marketplace de plugins (não testada)

O repositório tem um `.claude-plugin/marketplace.json`. Pela documentação oficial do Claude Code ("Install and manage plugins", <https://code.claude.com/docs/en/plugins/install.md>), dentro de uma sessão do `claude` seriam:

```text
/plugin marketplace add decolla/tuttor-kit
/plugin install tuttor-kit@tuttor-kit
```

**Não testado.** Por esse caminho **não há o lançador `tuttor`**: sem linha de status e sem isolamento dos seus outros plugins. A persona e a trava continuam vindo do plugin.

## Como funciona

```text
  aluno ──► tuttor (lançador) ──► claude (isolado, só com o plugin do kit)
                                  │
              persona do tutor ───┤  responde com perguntas e dicas
              comandos /dica ... ─┤  (11 comandos)
              trava (hook) ───────┤  escrita só em .tutor/
              tuttor-estado ──────┴► ~/.tutor/  (perfil, temas, revisões)

  outro terminal:  tuttor-vigia ──► observa os arquivos salvos ──► comenta com perguntas
```

- **Persona.** Um output style gerado a partir de `skills/tuttor-kit/references/persona.md`. Regra de ouro: o tutor não escreve nem edita o código do aluno; os exemplos são curtos e sempre de outro problema.
- **11 comandos** (skills; o nome completo é `/tuttor-kit:<comando>`, o nome curto também funciona):

| Comando | O que faz |
|---|---|
| `/trilha` | monta e conduz uma trilha de estudo antes de implementar algo novo |
| `/praticar` | propõe um exercício no nível certo de apoio (prever, ordenar, completar, modificar, criar) |
| `/dica` | dá o próximo degrau da escada de dicas, depois de uma tentativa, sem entregar a solução |
| `/duvida` | explica um conceito com exemplo mínimo e checagem de entendimento |
| `/revisar` | revisa o código do aluno com perguntas guiadas, sem corrigir |
| `/quiz` | recuperação ativa: perguntas curtas sobre o que venceu para revisão |
| `/material` | gera material de estudo de apoio com fontes verificadas |
| `/fontes` | levanta e verifica fontes atuais sobre um tema |
| `/fechar` | encerra a sessão: o aluno resume, o tutor registra domínio e próximos passos |
| `/perfil` | completa o perfil do aluno (conhecimento prévio, objetivos) |
| `/calibrar` | atualiza padrões de erro e de pedido de ajuda a partir do histórico |

- **Trava de escrita.** Um hook `PreToolUse` (`guard.py`) que só permite escrever dentro de pastas `.tutor/` e bloqueia as outras escritas, inclusive redirecionamentos no shell. É uma lista de permissão de melhor esforço, não um sandbox (veja [Limitações](#limitações)).
- **Memória do aluno** em `~/.tutor/` (perfil, temas com nível de apoio, agenda de revisão), lida e gravada pelo `tuttor-estado`. Sem rótulos de estilo de aprendizagem.
- **Vigia.** O `tuttor-vigia` observa a pasta do projeto e, depois que você salva e para de mexer, envia o trecho alterado a um provedor de IA e imprime comentários curtos (vermelho: erro, amarelo: melhoria, azul: conceito, verde: acerto) com perguntas, sem escrever a correção.
- **Mascote.** O Lume tem quatro estados, distinguíveis pela forma mesmo sem cor (`python3 skills/tuttor-kit/scripts/mascote.py --todos`; `--ascii` para só ASCII):

```text
    ▄█▄               ▄█▄  ∙ ∙ ∙      ▄█▄   ✦ ✦       ▄█▄    ! !
   ╔═══╗            ╔═══╗ ╌╌╌╌╸     ╔═══╗ ╲ ╱       ╔═══╗   ! !
   ║◦ ◦║ ═══╸      ║∙ ∙║            ║◠ ◠║ ═══✦      ║O O║ ╲
   ╚═╤═╝            ╚═╤═╝            ╚═╤═╝ ╱ ╲       ╚═╤═╝  ╲═╸
    ║ ║               ║ ║               ║ ║   ✦         ║ ║
   ▄███▄            ▄███▄            ▄███▄            ▄███▄    !
    atento         pensando      comemorando        alerta
```

## Base científica

O projeto parte de pesquisa publicada, resumida com fontes em [`docs/pesquisa/`](docs/pesquisa/README.md) (53 referências verificadas). Princípios principais: (1) recuperação ativa em vez de reler; (2) revisão espaçada; (3) autoexplicação a cada passo; (4) exemplos resolvidos de **outro** problema, com apoio que diminui conforme o domínio cresce; (5) tentativa curta antes da dica, com escada de dicas de quatro degraus; (6) adaptar ao conhecimento prévio, não a "estilos de aprendizagem", que a literatura não sustenta. **Onde a evidência é fraca:** os resultados mais fortes vêm de memória verbal, texto e matemática, não de programação; vários estudos são com crianças ou adolescentes; tentar antes da instrução é disputado; os intervalos de revisão, a contagem de domínio de 0 a 4 e a regra de dicas em sequência são heurísticas de engenharia, não modelos validados; os estudos de IA no ensino são recentes, curtos e heterogêneos. **O kit em si nunca foi avaliado**, e nada aqui promete resultado de aprendizagem. Veja [`limitacoes.md`](docs/pesquisa/limitacoes.md).

## CLIs suportadas

| CLI | Situação |
|---|---|
| Claude Code | **Testado** em sessões reais não interativas (`-p`) no Linux; a tela interativa não foi testada. Detalhes em [`docs/verificacao.md`](docs/verificacao.md) |
| Ollama | O **vigia** foi testado com `llama3.2:1b` (provedores `openai` e `comando`); um modelo de 1B comenta mal. O tutor interativo (Modelfile) foi validado localmente, mas o modelo de 1B desobedeceu à instrução e escreveu código |
| Codex CLI, Gemini CLI, OpenCode | **Experimental, não testado**: configuração escrita só a partir da documentação oficial. Veja [`docs/cli/README.md`](docs/cli/README.md) |

## Vigia e provedores

| Provedor | Situação |
|---|---|
| `claude-cli` (padrão) | Testado ao vivo com Haiku; um comentário custou cerca de US$ 0,0009, segundo o próprio `claude` |
| `comando` | Testado com `ollama run llama3.2:1b` (local) |
| `openai` (HTTP compatível com OpenAI) | Testado só contra o Ollama local (`http://localhost:11434/v1`); contra a API paga da OpenAI, só com servidor falso |
| `anthropic` (HTTP) | Só servidor falso; nenhuma chamada real à API paga |

```bash
tuttor-vigia --provedor openai --base-url http://localhost:11434/v1 --modelo <modelo>
tuttor-vigia --provedor comando --comando "ollama run {modelo}" --modelo <modelo>
tuttor-vigia --provedor anthropic --modelo <modelo>   # ANTHROPIC_API_KEY
```

### Privacidade e custos

- **O que sai da máquina:** o diff e um trecho (até `--max-linhas`, padrão 400 linhas) dos arquivos alterados (até `--max-arquivos`, padrão 3), o resultado das checagens, trechos do seu `~/.tutor/perfil.md` (use `--sem-perfil` para não enviar), temas recorrentes e comentários anteriores. Toda partida mostra um aviso com o que é enviado, para onde e os limites em vigor.
- **Nunca enviado:** `.env*`, `*.pem`, chaves, `id_rsa*`, `secrets.*`, `credentials*` e afins. Valores com cara de segredo viram `«oculto»`. Isso é heurística, **não é garantia**: não deixe segredo no código.
- **Host local** (Ollama em `localhost`): nada sai da máquina. Com `claude-cli`, o dado segue o caminho do Claude Code.
- **A chave de API vem só de variável de ambiente** (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY` ou outro nome com `--var-chave`). Não existe opção nem campo de configuração que receba a chave, e ela nunca é impressa nem gravada em arquivo.
- **Limites padrão por sessão:** 40 chamadas (`--limite-chamadas`), 300000 tokens (`--limite-tokens`), no mínimo 25 s entre chamadas (`--intervalo-minimo`); sem limite em dólares, a menos que você defina `--limite-usd`. Provedores remotos podem cobrar por uso; o `claude-cli` consome o limite do seu plano ou gera cobrança. Os valores são estimativas: confira no painel do provedor. `tuttor-vigia --estado` mostra o gasto acumulado.
- **A web fica desligada por padrão.** `--web` (só com `claude-cli`) liga e nunca pode ser combinada com `--ler`.
- O vigia nunca lê configuração de dentro do projeto: só opções, variáveis de ambiente e `~/.tutor/vigia.json`. Mais em [`docs/vigia.md`](docs/vigia.md).

## FAQ

**Ele nunca escreve código?**

O tutor é instruído a não escrever nem editar seu código, e a trava bloqueia a gravação de arquivos fora de `.tutor/`. Mas a trava não impede o modelo de colar código na conversa; isso depende da persona. No teste real o tutor recusou, deu um exemplo de outro problema e fez duas perguntas.

**E se eu precisar entregar?**

O tutor recusa mesmo assim, oferece o próximo degrau de dica e diz uma única vez que você pode sair do modo tutor. Sair é simples: rode o `claude` direto em vez do `tuttor`.

**Funciona sem o Claude Code?**

A trava de escrita só existe no Claude Code. Para Codex CLI, Gemini CLI, OpenCode e Ollama há configurações experimentais em `docs/cli/` (não testadas, exceto o vigia com Ollama), e a persona passa a depender só das instruções.

**Quanto custa?**

O kit é gratuito (MIT). O tutor usa o seu plano do Claude Code. O vigia com `claude-cli` custou cerca de US$ 0,0009 por comentário com Haiku no teste; com Ollama local não há cobrança. Veja [Privacidade e custos](#privacidade-e-custos).

**Meus dados vão para onde?**

A memória do aluno fica em `~/.tutor/`, na sua máquina. O vigia envia trechos ao provedor que você escolher; veja [Privacidade e custos](#privacidade-e-custos).

**Como desinstalo?**

`./install.sh --uninstall` remove só os três links simbólicos que o instalador registrou e que ainda apontam para este clone. Não apaga `~/.tutor/`; apague essa pasta você mesmo se quiser limpar o histórico.

**Posso usar para outra linguagem?**

Sim: a persona não é presa a uma linguagem de programação. Só há mapa de domínio para C# e microsserviços (`skills/tuttor-kit/references/dominio-csharp-microsservicos.md`); para outros assuntos o tutor pesquisa do zero.

**Por que o tutor não usa estilos de aprendizagem?**

Porque a revisão da literatura não achou evidência adequada para justificar ajustar o ensino a avaliações de estilos de aprendizagem. O kit adapta ao conhecimento prévio, aos padrões de erro e ao jeito de pedir ajuda. Veja [`docs/pesquisa/`](docs/pesquisa/README.md).

## Limitações

- A trava de escrita é uma **lista de permissão de melhor esforço, não um sandbox**.
- Ela **não** impede o modelo de colar código na conversa; isso depende da persona, e um modelo de linguagem pode errar, ceder à insistência ou ignorar uma regra.
- Depende dos hooks do Claude Code, e o kit exige o Claude Code 2.1.295 ou mais novo.
- O kit **nunca foi avaliado com alunos**.
- O domínio por tema é uma heurística (uma contagem simples de 0 a 4), não um diagnóstico validado.
- Veja abaixo o que não foi testado.

### O que foi e o que não foi testado

Verificação de 2026-11-12 (Linux, Claude Code 2.1.322, Python 3.12). **Testado de verdade:** a trava bloqueou `Write` fora de `.tutor/` e um redirecionamento no shell, e permitiu `Write` dentro de `.tutor/`; o isolamento (só o plugin do kit carregado); a persona aplicada pelo plugin; a recusa mostrada acima; `/dica` e `/praticar` sem o prefixo do plugin; o vigia ao vivo com `claude-cli`; o vigia com Ollama local; a instalação em HOME limpa (`--dry-run`, duas vezes, `--verificar`, `--uninstall`); 991 testes automatizados, ruff, shellcheck, vermin (alvo 3.9) e `claude plugin validate`.

**Não testado:** a sessão interativa na tela (linha de status, verbos e dicas do spinner, banner do mascote junto do Claude Code, mensagem de início); `tuttor --tmux` (só com tmux falso); Codex CLI, Gemini CLI e OpenCode (nada executado); os provedores HTTP `anthropic` e `openai` contra as APIs pagas reais; macOS e Windows; execução real em Python 3.9 (só análise estática); instalação pelo marketplace de plugins; o CI no GitHub (ainda não rodou). Relatório completo: [`docs/verificacao.md`](docs/verificacao.md).

## Como contribuir

Veja [`CONTRIBUTING.md`](CONTRIBUTING.md) (testes, ruff, shellcheck, gerador e varredura) e o [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md). Vulnerabilidades: [`SECURITY.md`](SECURITY.md). Alterações: [`CHANGELOG.md`](CHANGELOG.md).

## Licença

[MIT](LICENSE), Copyright (c) 2026 decolla.
