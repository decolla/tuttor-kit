**English** · [Português (Brasil)](README.pt-BR.md)

```text
    ▄█▄
   ╔═══╗
   ║◦ ◦║ ═══╸
   ╚═╤═╝
    ║ ║
   ▄███▄
```

# tuttor-kit

**Turns an AI CLI into a programming tutor: it guides with questions and hints and does not write the student's code.**

[![CI](https://github.com/decolla/tuttor-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/decolla/tuttor-kit/actions/workflows/ci.yml) [![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE) ![version 0.1.0](https://img.shields.io/badge/version-0.1.0-informational)

> The detailed documentation in `docs/` is written in Portuguese (pt-BR). This README is the English entry point; the tutor itself answers in the student's language (Portuguese by default).

## What it is

tuttor-kit is a Claude Code plugin and an Agent Skill that puts the AI in tutor mode. When you ask for code, it asks what you tried, gives hints one step at a time, and only shows short examples of a *different* problem. A write lock (a Claude Code hook) blocks file writes outside `.tutor/` folders. The kit also remembers your weak topics in `~/.tutor/`, schedules spaced reviews, and ships a watcher (`tuttor-vigia`) that comments on your code in a second terminal, with questions instead of fixes. The mascot is Lume, a small lighthouse ("I light the way, you steer").

**Status: version 0.1.0. The kit has never been evaluated in a controlled study with students.** The features are design choices inspired by published research, with the evidence and its gaps laid out in [`docs/pesquisa/`](docs/pesquisa/README.md). See [Limitations](#limitations) and [What was and was not tested](#what-was-and-was-not-tested).

## Demo

There is no GIF or video: the demo is text from real sessions (Claude Code 2.1.322, Sonnet as the tutor, Haiku as the watcher, verified 2026-11-12), trimmed with `[...]`. The conversation is in Portuguese because the session was in Portuguese.

**Real session output, trimmed: the tutor facing a request for ready-made code.** The student's `fizz.py` was left unchanged.

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

**Real watcher output, trimmed:** the student saved a FizzBuzz with the tests in the wrong order.

```text
[OO]! ━━ fizz.py ━━
🔴 L5 — a ordem dos testes está errada: `i % 3 == 0` captura os múltiplos de 15 antes do `elif`,
   então o caso "FizzBuzz" nunca é alcançado. Pergunta: o que acontece com i = 15?  #logica
🔵 Estrutura de decisão — quando condições se sobrepõem, a ordem dos if/elif define o resultado [...]
```

## Quick start

Requirements: Python 3.9 or newer, Claude Code 2.1.295 or newer, git.

```bash
# 1
git clone https://github.com/decolla/tuttor-kit && cd tuttor-kit
# 2
./install.sh
# 3
cd <your project> && tuttor
```

The installer creates only three symlinks (`tuttor`, `tuttor-vigia`, `tuttor-estado`) in `~/.local/bin` (or `TUTTOR_BIN_DIR`); make sure that folder is on your `PATH`. `./install.sh --dry-run` shows what it would do without writing anything, and `./install.sh --verificar` checks the environment.

The watcher runs in **another terminal**, in the same project folder:

```bash
tuttor-vigia            # default provider: claude-cli
tuttor-vigia --ensaio   # shows what would be sent, without calling anything
```

`tuttor --tmux` opens both panes at once (tested only with a fake tmux). `tuttor --ajuda` lists the options (in Portuguese).

### Install through the plugin marketplace (not tested)

The repository has a `.claude-plugin/marketplace.json`. According to the official Claude Code documentation ("Install and manage plugins", <https://code.claude.com/docs/en/plugins/install.md>), inside a `claude` session the commands would be:

```text
/plugin marketplace add decolla/tuttor-kit
/plugin install tuttor-kit@tuttor-kit
```

**Not tested.** This path has **no `tuttor` launcher**: no status line and no isolation from your other plugins. The persona and the write lock still come from the plugin.

## How it works

```text
  student ──► tuttor (launcher) ──► claude (isolated, only the kit plugin)
                                      │
              tutor persona ──────────┤  answers with questions and hints
              /dica ... commands ─────┤  (11 commands)
              write lock (hook) ──────┤  writes only inside .tutor/
              tuttor-estado ──────────┴► ~/.tutor/  (profile, topics, reviews)

  other terminal:  tuttor-vigia ──► watches saved files ──► comments with questions
```

- **Persona.** An output style generated from `skills/tuttor-kit/references/persona.md`. Golden rule: the tutor does not write or edit the student's code; examples are short and always of a different problem.
- **11 commands** (skills; the full name is `/tuttor-kit:<command>`, the short name also works). The command names are in Portuguese:

| Command | What it does |
|---|---|
| `/trilha` | builds and runs a study path before implementing something new |
| `/praticar` | proposes an exercise at the right support level (predict, order, complete, modify, create) |
| `/dica` | gives the next step of the hint ladder, after an attempt, without handing over the solution |
| `/duvida` | explains a concept with a minimal example and a comprehension check |
| `/revisar` | reviews the student's code with guiding questions, without fixing it |
| `/quiz` | active recall: short questions on topics due for review |
| `/material` | generates supporting study material with checked sources |
| `/fontes` | finds and checks current sources on a topic |
| `/fechar` | ends the session: the student summarizes, the tutor records mastery and next steps |
| `/perfil` | completes the student profile (prior knowledge, goals) |
| `/calibrar` | updates error and help-seeking patterns from the history |

- **Write lock.** A `PreToolUse` hook (`guard.py`) that allows writes only inside `.tutor/` folders and blocks other writes, including shell redirections. It is a best-effort allowlist, not a sandbox (see [Limitations](#limitations)).
- **Student memory** in `~/.tutor/` (profile, topics with support level, review schedule), read and written through `tuttor-estado`. No learning-style labels.
- **Watcher.** `tuttor-vigia` watches the project folder and, after you save and pause, sends the changed excerpt to an AI provider and prints short comments (red: error, yellow: improvement, blue: concept, green: success) with questions, without writing the fix.
- **Mascot.** Lume has four states, distinguishable by shape even without color (`python3 skills/tuttor-kit/scripts/mascote.py --todos`; add `--ascii` for ASCII only):

```text
    ▄█▄               ▄█▄  ∙ ∙ ∙      ▄█▄   ✦ ✦       ▄█▄    ! !
   ╔═══╗            ╔═══╗ ╌╌╌╌╸     ╔═══╗ ╲ ╱       ╔═══╗   ! !
   ║◦ ◦║ ═══╸      ║∙ ∙║            ║◠ ◠║ ═══✦      ║O O║ ╲
   ╚═╤═╝            ╚═╤═╝            ╚═╤═╝ ╱ ╲       ╚═╤═╝  ╲═╸
    ║ ║               ║ ║               ║ ║   ✦         ║ ║
   ▄███▄            ▄███▄            ▄███▄            ▄███▄    !
    atento         pensando      comemorando        alerta
```

## Scientific basis

The design draws on published research, summarized with sources in [`docs/pesquisa/`](docs/pesquisa/README.md) (53 checked references; the pages are in Portuguese). Main principles: (1) retrieval practice instead of rereading; (2) spaced review; (3) self-explanation after each step; (4) worked examples of *another* problem with support that fades as mastery grows; (5) a short attempt before a hint, with a four-step hint ladder; (6) adapting to prior knowledge, not to "learning styles", which the literature does not support. **Where the evidence is weak:** most strong results come from verbal memory, text and mathematics, not programming; many studies are with children or teenagers; trying before instruction is disputed; the review intervals, the 0 to 4 mastery count and the consecutive-hints rule are engineering heuristics, not validated models; studies of AI in teaching are recent, short and mixed. **The kit itself was never evaluated**, and nothing here promises a learning outcome. See [`limitacoes.md`](docs/pesquisa/limitacoes.md).

## Supported CLIs

| CLI | Status |
|---|---|
| Claude Code | **Tested** in real non-interactive sessions (`-p`) on Linux; the interactive screen was not tested. Details in [`docs/verificacao.md`](docs/verificacao.md) |
| Ollama | The **watcher** was tested with `llama3.2:1b` (`openai` and `comando` providers); a 1B model comments poorly. The interactive tutor (Modelfile) was validated locally, but the 1B model disobeyed the instruction and wrote code |
| Codex CLI, Gemini CLI, OpenCode | **Experimental, not tested**: configuration written from the official documentation only. See [`docs/cli/README.md`](docs/cli/README.md) |

## Watcher and providers

| Provider | Status |
|---|---|
| `claude-cli` (default) | Tested live with Haiku; one comment cost about US$ 0.0009, as reported by `claude` itself |
| `comando` | Tested with `ollama run llama3.2:1b` (local) |
| `openai` (OpenAI-compatible HTTP) | Tested only against local Ollama (`http://localhost:11434/v1`); against the paid OpenAI API only with a fake server |
| `anthropic` (HTTP) | Fake server only; no real call to the paid API |

```bash
tuttor-vigia --provedor openai --base-url http://localhost:11434/v1 --modelo <model>
tuttor-vigia --provedor comando --comando "ollama run {modelo}" --modelo <model>
tuttor-vigia --provedor anthropic --modelo <model>   # ANTHROPIC_API_KEY
```

### Privacy and costs

- **What leaves your machine:** the diff and an excerpt (up to `--max-linhas`, default 400 lines) of the changed files (up to `--max-arquivos`, default 3), the result of the checks, excerpts of your `~/.tutor/perfil.md` (use `--sem-perfil` to skip), recurring topics and previous comments. Every start prints a notice with what is sent, where, and the limits in force.
- **Never sent:** `.env*`, `*.pem`, keys, `id_rsa*`, `secrets.*`, `credentials*` and similar. Values that look like secrets are replaced by `«oculto»`. This is a heuristic, **not a guarantee**: do not leave secrets in code.
- **Local host** (Ollama on `localhost`): nothing leaves the machine. With `claude-cli`, data follows Claude Code's path.
- **API keys come only from environment variables** (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or another name via `--var-chave`). There is no option or config field that takes a key, and the key is never printed or written to a file.
- **Default limits per session:** 40 calls (`--limite-chamadas`), 300000 tokens (`--limite-tokens`), at least 25 s between calls (`--intervalo-minimo`); no dollar limit unless you set `--limite-usd`. Remote providers may charge per use; `claude-cli` consumes your plan's allowance or generates charges. Figures are estimates: check the provider's dashboard. `tuttor-vigia --estado` shows accumulated spend.
- **Web is off by default.** `--web` (only with `claude-cli`) turns it on and can never be combined with `--ler`.
- The watcher never reads its configuration from inside the project: only options, environment variables and `~/.tutor/vigia.json`. More in [`docs/vigia.md`](docs/vigia.md) (Portuguese).

## FAQ

**Does it never write code?**

The tutor is instructed not to write or edit your code, and the write lock blocks file writes outside `.tutor/`. But the lock cannot stop the model from pasting code into the chat; that depends on the persona. In the real test the tutor refused, gave an example of a different problem and asked two questions.

**What if I have a deadline?**

The tutor refuses even then, offers the next hint step, and tells you once that you can leave tutor mode. Leaving is simple: run `claude` directly instead of `tuttor`.

**Does it work without Claude Code?**

The write lock exists only in Claude Code. For Codex CLI, Gemini CLI, OpenCode and Ollama there are experimental configurations in `docs/cli/` (untested, except the watcher with Ollama), and the persona then depends only on instructions.

**How much does it cost?**

The kit is free (MIT). The tutor uses your Claude Code plan. The watcher with `claude-cli` cost about US$ 0.0009 per comment with Haiku in the test; with a local Ollama nothing is charged. See [Privacy and costs](#privacy-and-costs).

**Where does my data go?**

The student memory stays in `~/.tutor/` on your machine. The watcher sends excerpts to the provider you choose; see [Privacy and costs](#privacy-and-costs).

**How do I uninstall?**

`./install.sh --uninstall` removes only the three symlinks the installer recorded and that still point to this clone. It does not delete `~/.tutor/`; delete that folder yourself if you want to erase your history.

**Can I use it for another language?**

Yes: the persona is not tied to any programming language. There is a domain map only for C# and microservices (`skills/tuttor-kit/references/dominio-csharp-microsservicos.md`); for other subjects the tutor researches from scratch. The tutor answers in your language.

**Why doesn't the tutor use learning styles?**

Because the literature review found no adequate evidence to justify matching instruction to learning-style assessments. The kit adapts to prior knowledge, error patterns and help-seeking behavior instead. See [`docs/pesquisa/`](docs/pesquisa/README.md).

## Limitations

- The write lock is a best-effort **allowlist, not a sandbox**.
- It does **not** stop the model from pasting code into the conversation; that depends on the persona, and a language model can err, give in to insistence or ignore a rule.
- It depends on Claude Code hooks, and the kit requires Claude Code 2.1.295 or newer.
- The kit was **never evaluated with students**.
- Per-topic mastery is a heuristic (a simple 0 to 4 count), not a validated diagnosis.
- See below for what was not tested.

### What was and was not tested

Verification of 2026-11-12 (Linux, Claude Code 2.1.322, Python 3.12). **Tested for real:** the lock blocked `Write` outside `.tutor/` and a shell redirection, and allowed `Write` inside `.tutor/`; isolation (only the kit plugin loaded); persona applied by the plugin; the refusal shown above; `/dica` and `/praticar` without the plugin prefix; the live watcher with `claude-cli`; the watcher with local Ollama; clean-HOME install (dry run, twice, `--verificar`, `--uninstall`); 991 automated tests, ruff, shellcheck, vermin (target 3.9) and `claude plugin validate`.

**Not tested:** the interactive screen session (status line, spinner verbs and tips, mascot banner with Claude Code, start message); `tuttor --tmux` (only with a fake tmux); Codex CLI, Gemini CLI and OpenCode (nothing executed); the `anthropic` and `openai` HTTP providers against the real paid APIs; macOS and Windows; real execution on Python 3.9 (static analysis only); install through the plugin marketplace; the GitHub CI (it has not run yet). Full report: [`docs/verificacao.md`](docs/verificacao.md) (Portuguese).

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) (tests, ruff, shellcheck, generator and scan; written in Portuguese with an English summary) and the [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md). Vulnerabilities: [`SECURITY.md`](SECURITY.md). Changes: [`CHANGELOG.md`](CHANGELOG.md).

## License

[MIT](LICENSE), Copyright (c) 2026 decolla.
