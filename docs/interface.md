# Interface: o que o Claude Code deixa personalizar e o que o kit usa

Tudo abaixo vem da documentação oficial do Claude Code, baixada para consulta (as páginas citadas
são os arquivos dessa cópia: `statusline.md`, `settings-reference.md`, `hooks.md`, `cli-reference.md`,
`permissions.md`, `plugins_components.md`, `plugins_mods_*.md`). O que não está nessas páginas aparece
como "não verificado". O kit **não altera o binário nem o pacote do Claude Code**: só usa os pontos de
extensão que a documentação descreve.

## O que o kit usa

### Linha de status

- **O que é**: uma barra abaixo do prompt que roda um comando seu, recebe o JSON da sessão no stdin e
  mostra o que o comando imprime. Aceita várias linhas e cores ANSI. Não gasta tokens.
  Documentação oficial do Claude Code, página `statusline.md`, seções "Manually configure a status
  line", "How status lines work" e "What your script can output".
- **Campo**: `statusLine` com `type: "command"`, `command` e, opcionais, `padding`, `refreshInterval`
  e `hideVimModeIndicator`. Documentação oficial do Claude Code, página `settings-reference.md`,
  seção `statusLine`.
- **Largura**: o script não lê o tamanho do terminal por `tput`; o Claude Code define `COLUMNS` e
  `LINES` antes de rodar. Documentação oficial do Claude Code, página `statusline.md`, seção "Size
  output to the terminal".
- **No kit**: `statusline.py` imprime uma linha: mini do Lume, nome do kit, trilha em andamento com
  progresso, tema de erro mais recorrente (vigia, 14 dias) e quantos temas vencem para revisão.
  Usa `COLUMNS` para cortar com reticências (sem `COLUMNS`, teto fixo de 100 colunas, escolha do
  kit). Nunca falha (em erro imprime só o nome do kit), não usa rede, não segue links simbólicos em
  `.tutor/` e limpa caracteres de controle do que lê do projeto. Só usa o campo `workspace.project_dir`
  / `workspace.current_dir` / `cwd` do JSON de entrada (statusline.md, seção "Available data").
- **Cuidados da doc**: com uma linha de status personalizada, o Claude Code deixa de mostrar a maior
  parte das dicas de teclado do rodapé (statusline.md, introdução). `disableAllHooks` também
  desliga a linha de status (settings-reference.md, seções `statusLine` e `disableAllHooks`).

### Output style

- **O que é**: um conjunto salvo de instruções que muda o papel, o tom e o formato das respostas.
  Selecionado pelo campo `outputStyle` (nome do estilo). Documentação oficial do Claude Code, página
  `settings-reference.md`, seção `outputStyle`.
- **Em plugin**: arquivo `output-styles/<name>.md`, com `name` e `description` no frontmatter,
  aparece em `/output-style` como `<plugin>:<name>`. Documentação oficial do Claude Code, página
  `plugins_components.md`, seção "Themes and output styles".
- **No kit**: `output-styles/tutor.md` (gerado de `references/persona.md`). A página própria de output
  styles não foi baixada: o que mais ela diz (por exemplo outros campos do frontmatter) é "não
  verificado" aqui.

### Hook de início de sessão (SessionStart)

- **O que faz**: roda quando a sessão começa, retoma, limpa ou compacta. Pode devolver
  `additionalContext` (texto que entra no contexto do Claude) e `systemMessage` (aviso mostrado ao
  usuário). Documentação oficial do Claude Code, página `hooks.md`, seções "SessionStart", "SessionStart
  decision control" e "JSON output".
- **Limite**: cada string (`additionalContext`, `systemMessage`) tem teto de 10.000 caracteres
  (hooks.md, "JSON output"). O hook roda em segundo plano mas a primeira resposta espera por ele
  (hooks.md, "SessionStart").
- **No kit**: `contexto.py` devolve o contexto do aluno (rotulado como dados, não instruções) e uma
  mensagem curta com o mini do Lume ("<kit>: modo tutor ativo, N tema(s) para revisar").
  Onde exatamente o `systemMessage` aparece na tela do SessionStart: não verificado (a página só o
  descreve como "warning message shown to the user").

### Verbos e dicas do spinner

- **`spinnerVerbs`**: `{"mode": "append" | "replace", "verbs": [...]}`. Com `replace`, só os verbos
  do kit aparecem; `replace` com lista vazia mantém os verbos de fábrica. Documentação oficial do Claude
  Code, página `settings-reference.md`, seção `spinnerVerbs`.
- **`spinnerTipsOverride`**: `tips` (texto ou objeto com `id`, `text`, `cooldownSessions`,
  `priority`), `tipsFile`, `label` (até 40 caracteres) e `excludeDefault`. Tips em objeto, `label` e
  `excludeDefault` exigem v2.1.247 ou mais novo e só valem em configurações de usuário, `--settings` ou
  gerenciadas (de projeto/local só entram textos simples). Documentação oficial do Claude Code, página
  `settings-reference.md`, seção `spinnerTipsOverride`.
- **No kit**: verbos em português ("Iluminando", "Formulando a pergunta", ...) em modo `replace`, e
  dicas do tutor ("Travou? /dica dá o próximo degrau, depois de você tentar") com `excludeDefault`.
  Com `--sem-mascote`, os verbos de farol saem. `spinnerTipsEnabled: false` esconde todas as dicas,
  inclusive as do kit (mesma seção).

### `--settings`

- **O que é**: flag que recebe um arquivo JSON ou um JSON inline; os valores sobrepõem as mesmas
  chaves dos arquivos de configuração só nesta sessão e as chaves omitidas mantêm os valores dos
  arquivos. Arquivo: comum e até 2 MiB. Documentação oficial do Claude Code, página `cli-reference.md`,
  tabela de flags (`--settings`).
- **No kit**: `configuracoes.py` imprime esse JSON (`statusLine`, `spinnerVerbs`,
  `spinnerTipsOverride` e `permissions.allow`) com caminhos absolutos calculados em tempo de execução;
  o comando do `statusLine` vai entre aspas (o campo `command` "roda em um shell", statusline.md,
  seção "Manually configure a status line"). Não grava nada: o lançador decide onde usar.
  `configuracoes.py --sem-mascote` tira o que é do mascote.
- **Por que não vai em `settings.json` do plugin**: a doc diz que um `settings.json` na raiz do plugin
  só aplica duas chaves, `agent` e `subagentStatusLine`, e descarta as outras (documentação oficial do
  Claude Code, página `plugins_components.md`, seção "Default settings"). Por isso `statusLine` e spinner
  chegam por `--settings`.

### Permissões (`permissions.allow`)

- **Sintaxe**: `Bash(comando)` casa o comando exato; `*` casa qualquer texto; um ` *` final também
  casa o comando sem argumentos; comandos compostos (`&&`, `;`, `|`...) exigem permissão para cada
  parte. Documentação oficial do Claude Code, página `permissions.md`, seções "Wildcard patterns" e
  "Compound commands".
- **No kit**: só `tuttor-estado registrar|dica|apoio|revisar|resumo *`, `tuttor-estado caminho` e os
  dois usos exatos `tuttor-vigia --resumo` e `tuttor-vigia --leituras` (sem curinga: `--resumo 7`,
  `--web` e `--read` continuam pedindo permissão). O prefixo vem de `COMANDO` em `projeto.env`.
  Limite da própria doc: uma regra de Bash casa o texto do comando, não é uma fronteira de segurança
  (permissions.md, "What a Bash rule doesn't match"); a trava de escrita continua sendo o `guard.py`.
  Não verificado: se regras de `permissions.allow` vindas de `--settings` passam pela confirmação de
  confiança da pasta (a página só descreve isso para `.claude/settings.json` do projeto, seção
  "Project allow rules and workspace trust").

### Plugin: `bin/`, skills, output styles, hooks

- **`bin/`**: arquivos executáveis do plugin entram no `PATH` da ferramenta Bash enquanto o plugin
  está habilitado, depois das entradas do `PATH` do usuário. Documentação oficial do Claude Code,
  página `plugins_components.md`, seção "Executables". É assim que `tuttor`, `tuttor-vigia` e
  `tuttor-estado` ficam disponíveis ao tutor.
- **Skills, hooks**: `plugins_components.md`, seções "Skills" e "Hooks" (`hooks/hooks.json`).
- **`--plugin-dir`**: carrega um plugin de uma pasta (ou `.zip`) só nesta sessão; um caminho por
  flag, repetível. Documentação oficial do Claude Code, página `cli-reference.md`, tabela de flags.

## O que não dá para fazer

Esta seção diz o que procurei nas páginas baixadas e não encontrei. "Não encontrei suporte
documentado" não é o mesmo que "é impossível": significa só que a cópia da documentação que li não
descreve.

| Procurei | Resultado |
|---|---|
| Trocar a tela de abertura ou o logotipo do Claude Code | Não encontrei suporte documentado. A única mensagem de início que achei é `companyAnnouncements` (texto de anúncio da organização mostrado na abertura; settings-reference.md, seção `companyAnnouncements`), que é só texto. O kit não a usa. |
| Desenhar o mascote dentro da interface com configuração, hook ou plugin comum | Não encontrei suporte documentado nos pontos de extensão acima (linha de status, spinner, output style, hooks). A linha de status aceita texto e cores, e é onde o mini do Lume aparece. |
| Animar o mascote durante a resposta | Não encontrei suporte documentado em configuração ou hook. Para o spinner, a doc só descreve trocar verbos e dicas de texto (`spinnerVerbs`, `spinnerTipsOverride`). A linha de status pode rodar de novo a cada `refreshInterval` segundos (statusline.md, "Manually configure a status line"), mas o kit não a usa para animação (há também `prefersReducedMotion`, settings-reference.md). |
| Mudar o binário ou o pacote do Claude Code | O kit não faz isso e não depende disso. |

### Mods: possibilidade futura, não implementada

As páginas `plugins_mods_*.md` descrevem "mods": plugins com um módulo de hooks em JavaScript ou
TypeScript que o Claude Code chama quando acontecem eventos. Segundo essas páginas, um mod pode
desenhar painéis (`Pane`), uma faixa acima do prompt e o spinner (`plugins_mods_interface.md`,
"Draw in the interface with a mod" e tabela de render sites), e há um elemento `Client` para
"animação e entrada do ponteiro" (tabela de elementos, nos terminais e no app Desktop). Elas pedem
Claude Code v2.1.287 ou mais novo (`plugins_mods_create.md`, "Create a mod"). Ou seja, a doc que li
**descreve** um caminho para um mascote desenhado dentro da interface.

O kit **não implementa mods**. Não verificado: se os mods estão disponíveis em cada instalação (a
página de solução de problemas, que diz como checar, não foi baixada), como a aprovação de um mod
funciona na prática e se há restrições de distribuição. Por isso, por enquanto, o kit usa a
alternativa abaixo.

### Alternativa adotada

- O **lançador `tuttor` mostra o banner com o Lume antes de abrir a CLI** (e `--ascii` /
  `NO_COLOR` são respeitados, ver `docs/mascote.md`).
- **`tuttor --tmux` abre painéis**: o tutor e o vigia lado a lado.
- Dentro da sessão, o Lume aparece em miniatura na mensagem de início e na linha de status.

Situação da verificação (2026-11-12, Linux, Claude Code 2.1.322): o lançador `tuttor` agora mostra o
banner e tem `--tmux`. **Testado de verdade**, em sessões não interativas (`-p`): o isolamento dos
plugins de usuário e a abertura do Claude Code pelo lançador. **Não testado:** a sessão interativa
na tela (linha de status, verbos e dicas do spinner, banner do mascote junto do Claude Code,
mensagem de início de sessão) e `tuttor --tmux` (só com um tmux falso). Detalhes em
[verificacao.md](verificacao.md).
