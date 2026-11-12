# Lume, o mascote do kit

**Lume** é um farolzinho. Personalidade em uma linha: calmo e curioso; "eu ilumino, você pilota". Ele
ilumina o caminho (faz a pergunta, mostra o próximo degrau) e nunca pega o leme (não escreve o
código do aluno). Combina com o resto do kit: o tutor guia com perguntas e o aluno escreve.

O desenho vive em `skills/tuttor-kit/scripts/mascote.py` (só biblioteca padrão). Os blocos abaixo foram
copiados da saída real do script (`mascote.py <estado> --sem-cor`, `mascote.py <estado> --ascii`).

## Os quatro estados

Os estados se distinguem **pela forma** (olhos, posição e formato do facho, sinais como `...`,
`*`, `!`), então continuam distinguíveis sem cor e em ASCII. A cor ANSI é só reforço.

### `atento`

Estado de repouso. Banner do tutor (`tuttor`) e do vigia ao abrir; mensagem de início de sessão (hook SessionStart); linha de status quando está tudo bem. O facho aponta reto, para frente: "estou olhando com você".

Unicode:

```text
    ▄█▄
   ╔═══╗
   ║◦ ◦║ ═══╸
   ╚═╤═╝
    ║ ║
   ▄███▄
```

ASCII (`--ascii`):

```text
    _^_
   /===\
   |o o| ===>
   \_|_/
    | |
   /###\
```

Mini: `[◦◦]═` (Unicode) · `[oo]=` (ASCII)

### `pensando`

O tutor ou o vigia está formulando uma pergunta ou analisando um salvamento (o vigia entre o salvamento e o comentário). Facho para cima, pontinhos de reticências, olhos pequenos.

Unicode:

```text
    ▄█▄  ∙ ∙ ∙
   ╔═══╗ ╌╌╌╌╸
   ║∙ ∙║
   ╚═╤═╝
    ║ ║
   ▄███▄
```

ASCII (`--ascii`):

```text
    _^_  . . .
   /===\ ---->
   |. .|
   \_|_/
    | |
   /###\
```

Mini: `[∙∙]..` (Unicode) · `[..]..` (ASCII)

### `comemorando`

Marcos: trilha concluída, tema que chegou ao domínio máximo, sessão fechada com `/fechar`. Facho aberto em leque com faíscas; olhos sorrindo.

Unicode:

```text
    ▄█▄   ✦ ✦
   ╔═══╗ ╲ ╱
   ║◠ ◠║ ═══✦
   ╚═╤═╝ ╱ ╲
    ║ ║   ✦
   ▄███▄
```

ASCII (`--ascii`):

```text
    _^_   * *
   /===\ \ /
   |^ ^| ===*
   \_|_/ / \
    | |   *
   /###\
```

Mini: `[◠◠]✦` (Unicode) · `[^^]*` (ASCII)

### `alerta`

Erro que se repete (3 ou mais vezes, na linha de status), erro de execução avisado pelo vigia, trava de escrita acionada. Olhos arregalados, facho baixo e inclinado, `!` ao redor. É um aviso de atenção, não de culpa.

Unicode:

```text
    ▄█▄    ! !
   ╔═══╗   ! !
   ║O O║ ╲
   ╚═╤═╝  ╲═╸
    ║ ║
   ▄███▄    !
```

ASCII (`--ascii`):

```text
    _^_    ! !
   /===\   ! !
   |O O| \
   \_|_/  \=>
    | |
   /###\    !
```

Mini: `[OO]!` (Unicode) · `[OO]!` (ASCII)

Lado a lado, com o nome de cada um: `mascote.py --todos` (em sequência se o terminal for estreito).

## Com fala

`--fala TEXTO` põe a fala à direita da arte; se não couber na largura, vai para baixo:

```text
    ▄█▄  ∙ ∙ ∙
   ╔═══╗ ╌╌╌╌╸
   ║∙ ∙║         O que você espera que esta linha imprima?
   ╚═╤═╝
    ║ ║
   ▄███▄
```

## Quando cada estado aparece

| Onde | Estado |
|---|---|
| Banner do tutor (`tuttor`, antes de abrir a CLI) e do vigia | `atento` |
| Mensagem de início de sessão (hook SessionStart, em versão mini) | `atento` |
| Vigia entre um salvamento e o comentário | `pensando` |
| Trilha concluída, tema dominado, `/fechar` | `comemorando` |
| Erro que se repete, erro de execução, trava de escrita | `alerta` |
| Linha de status do Claude Code (mini) | `atento`; `alerta` com 3+ ocorrências do mesmo erro em 14 dias |

Hoje, o que já usa o mascote no código: o `contexto.py` (mini `atento` na mensagem de início) e o
`statusline.py` (mini). Os banners do lançador e do vigia, e os marcos, são o desenho previsto: a
arte e a CLI (`mascote.py <estado> --fala ...`) já existem para eles; a ligação é feita por quem
implementa o lançador e o vigia.

## Acessibilidade

- **Nunca depender de cor.** Cada estado tem uma forma própria, em Unicode e em ASCII, e no `mini`.
  A cor só reforça (amarelo, ciano, verde, vermelho em negrito).
- **`NO_COLOR`**: qualquer valor não vazio desliga a cor. `TERM=dumb` também. Saída que não é um
  terminal (pipe, arquivo) também sai sem cor. Parâmetros explícitos (`cor=`, `--sem-cor`)
  vencem a detecção.
- **`--ascii`**: só ASCII, sem caracteres de caixa. Também é o modo automático quando o locale não é
  UTF-8, quando `TERM=dumb` e em locales CJK (`ja`, `zh`, `ko`), onde caracteres de caixa podem ocupar
  duas colunas. O Unicode usa caracteres de caixa e bloco, que o Unicode classifica como de largura
  "ambígua" (1 coluna na maioria dos terminais), mais alguns de largura neutra; sem emoji.
- **Terminal estreito**: se a largura é menor que a arte mais a fala, a fala vai para baixo; se é
  menor que a arte (14 colunas), cai para o `mini` (uma linha, até 6 colunas). A largura vem de
  `--largura`, de `COLUMNS` ou do terminal.
- **Fala limpa**: caracteres de controle e sequências de escape são removidos da fala antes de
  imprimir.
- **Leitor de tela**: a documentação do Claude Code descreve a flag `--ax-screen-reader` (cli-reference,
  tabela de flags, que cita a variável `CLAUDE_AX_SCREEN_READER` e a configuração `axScreenReader`)
  e `prefersReducedMotion` (settings-reference). O kit ainda não lê nenhum dos três; não verificado se
  o processo da linha de status recebe essa variável (a página de variáveis de ambiente não foi
  baixada). Quem usa leitor de tela deve usar `--ascii` e pode tirar o mascote com `--sem-mascote`
  (ver `docs/interface.md`).

## Originalidade

O Lume foi desenhado para este kit. Não imita mascote, logotipo ou personagem de nenhum produto ou
ferramenta existente (inclusive de ferramentas de IA); é um farol, de caracteres de terminal comuns.
Fora a ideia geral de "farol" (um objeto comum), nada foi copiado de outra obra.
