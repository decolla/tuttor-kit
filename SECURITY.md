# Política de segurança

*English: report vulnerabilities privately through GitHub's "private vulnerability reporting" (Security tab of the repository, then "Report a vulnerability"). Do not open a public issue.*

## Como relatar

Use o **relato privado de vulnerabilidade** (*private vulnerability reporting*) do GitHub: na página do repositório <https://github.com/decolla/tuttor-kit>, abra a aba **Security** (em versões recentes da interface aparece como "Security and quality"), clique em **Report a vulnerability** e preencha o formulário (resumo, detalhes, prova de conceito e impacto). Fonte: documentação do GitHub, "Privately reporting a security vulnerability". O recurso precisa estar ativado no repositório pelos mantenedores. **Não abra issue pública** para vulnerabilidades.

## O que conta como vulnerabilidade

- Contornar a trava de escrita (`skills/tuttor-kit/scripts/guard.py`): conseguir que uma escrita fora de pastas `.tutor/` passe sem bloqueio.
- Vazar uma chave de API: imprimir, gravar em arquivo, pôr em linha de comando ou em mensagem de erro.
- Executar algo a partir de `.tutor/` ou de outro arquivo de um repositório clonado, sem que o usuário tenha pedido (por exemplo, o vigia ler comando ou configuração de dentro do projeto).
- Injeção de sequências de escape de terminal por conteúdo vindo de arquivos, do projeto ou da resposta do modelo.

## O que não conta

- O modelo de linguagem desobedecer a persona na conversa (por exemplo, colar código ou ceder à insistência). A trava de escrita é uma lista de permissão de melhor esforço e a persona é só uma instrução; veja as limitações no [README](README.md). Isso pode ir como issue comum ou ideia de melhoria.

## Versões e prazos

Só a versão mais recente (0.1.0, em desenvolvimento) recebe correções. Os mantenedores respondem quando puderem; o projeto não promete prazo de resposta.
