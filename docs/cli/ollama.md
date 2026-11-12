# Ollama (local)

Fontes de 2026-11-11: https://docs.ollama.com/ (sem versão/data nas páginas). Versão local usada nos
testes: Ollama 0.34.1. O Ollama roda modelos; **não é um agente**: não tem skills, comandos nem
ferramentas de arquivo próprias. Para agente de código com Ollama, veja `ollama launch` abaixo.

## 1. Instruções persistentes
Não há arquivo de projeto. A persona vai num **Modelfile** com `SYSTEM """..."""`, e `ollama create`
gera um modelo novo. [fonte](https://docs.ollama.com/modelfile). Modelo: `modelos/ollama/Modelfile`.

## 2. Skills e comandos
Não suporta Agent Skills nem comandos personalizados (não encontrados na doc consultada). Dentro de
`ollama run`, os comandos `/set parameter ...` existem ([faq](https://docs.ollama.com/faq)); o resto: não verificado.

## 3. Modo não interativo (vigia)
`ollama run MODELO [PROMPT]`; o prompt pode vir pelo stdin ([cli](https://docs.ollama.com/cli)).
Confirmado localmente com `ollama run --help`. Linha para o provedor `comando` (**testada** com
`llama3.2:1b`, ver `docs/vigia.md`):
```
tuttor-vigia --provedor comando --comando "ollama run {modelo}" --modelo llama3.2:1b
```
Saída observada ao redirecionar: vieram sequências de controle ANSI (spinner); o provedor `comando` do vigia
as remove. Também testado: provedor `openai` com base `http://localhost:11434/v1`. O contexto padrão
é 4096 tokens (`OLLAMA_CONTEXT_LENGTH`; `PARAMETER num_ctx` no Modelfile).
Sem ferramentas: `ollama run` é só conversa.

## 4. Trava de escrita
Não há sandbox, permissões nem hooks no Ollama. A doc de chamada de ferramentas diz que o modelo só
devolve `tool_calls` e **quem executa é o código chamador**; a página não afirma o que o `ollama run` faz
com ferramentas (não verificado). Na prática, `ollama run` não tem como editar arquivos do aluno, mas
isso decorre de ser só um chat, e não de uma trava. Se você usar um agente em cima do Ollama, vale a trava
daquele agente: `ollama launch` oferece integrações (`claude`, `codex`, `opencode`, entre outras, confirmado
em `ollama launch --help`); ver `codex.md` e `opencode.md`, e `docs/interface.md` para o Claude Code.
Ressalva observada em teste: um modelo pequeno (`llama3.2:1b`) com o `SYSTEM` "responda com uma
pergunta guia e sem escrever código" **escreveu código mesmo assim**. Modelos pequenos desobedecem.

**Trava de escrita:** **sem mecanismo equivalente: a proteção depende só das instruções; o modelo pode desobedecer** (o `ollama run` não edita arquivos por si, mas não há trava que impeça o modelo de dar a solução pronta no chat).

## 5. Chave de API
Local: nenhuma, a API em `http://localhost:11434` não exige autenticação. Nuvem (`https://ollama.com`):
`OLLAMA_API_KEY` em `Authorization: Bearer`. Outro servidor: `OLLAMA_HOST` (padrão `127.0.0.1:11434`).
[auth](https://docs.ollama.com/api/authentication), [faq](https://docs.ollama.com/faq)

## 6. Interface
Nada de status line, tema ou banner encontrado: não verificado. `ollama run --hidethinking` e `--nowordwrap`
existem (`ollama run --help`).

## 7. Passo a passo
1. Gere o Modelfile com a persona (troque `{{PERSONA}}`) e escolha um modelo: `ollama create tuttor -f Modelfile`.
2. Converse: `ollama run tuttor`.
3. Vigia: linha da seção 3.

## O que foi executado de verdade (Ollama 0.34.1)
`ollama --help`, `run --help`, `show --help`, `create --help`, `launch --help`, `list`;
`ollama create tuttor-teste -f Modelfile` (a partir de `llama3.2:1b`, com um `SYSTEM` de teste curto)
terminou com `success`; `ollama show tuttor-teste --system` devolveu o texto; `echo "..." | ollama run
tuttor-teste` respondeu em português, mas escrevendo um exemplo de código; `ollama rm tuttor-teste` removeu o
modelo e `ollama list` voltou a mostrar só os modelos que já existiam. A persona completa do kit **não** foi testada.
