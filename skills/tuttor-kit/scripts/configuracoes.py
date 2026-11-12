#!/usr/bin/env python3
"""Imprime no stdout o JSON de configurações do kit para a flag `--settings` do Claude Code.

Contém: statusLine (aponta para statusline.py), spinnerVerbs e spinnerTipsOverride (verbos e
dicas do tutor em português) e permissions.allow mínimo (tuttor-estado e dois usos exatos do
tuttor-vigia). Os caminhos são absolutos e calculados a partir deste arquivo, em tempo de
execução. Não grava nada em disco: quem chama (o lançador) decide onde usar o JSON.

Uso: configuracoes.py [--sem-mascote]
"""
import argparse
import json
import os
import re
import shlex
import sys

COMANDO_PADRAO = "tuttor"

VERBOS_MASCOTE = [
    "Iluminando", "Formulando a pergunta", "Acendendo o facho", "Procurando o próximo degrau",
    "Pensando em voz baixa", "Olhando o caminho", "Separando o que importa",
    "Preparando uma boa pergunta", "Conferindo o mapa",
]
VERBOS_NEUTROS = [
    "Formulando a pergunta", "Procurando o próximo degrau", "Pensando em voz baixa",
    "Separando o que importa", "Preparando uma boa pergunta", "Conferindo o mapa",
    "Organizando o raciocínio",
]
DICAS = [
    "Travou? /dica dá o próximo degrau, depois de você tentar",
    "Tente primeiro: escreva o que você espera que aconteça antes de rodar o código",
    "Ficou em dúvida sobre um conceito? /duvida explica com um exemplo mínimo",
    "/trilha monta um caminho de estudo antes de você implementar algo novo",
    "/quiz traz perguntas curtas sobre o que está na hora de rever",
    "/fechar encerra a sessão: você resume o que aprendeu e o tutor registra",
    "O tutor pergunta e você escreve o código: o erro é parte do caminho",
]
ROTULO_DICAS = "Dica do tutor"


def _raiz_do_kit():
    """Raiz do repositório: scripts/ -> <skill>/ -> skills/ -> raiz."""
    pasta = os.path.abspath(__file__)
    for _ in range(4):
        pasta = os.path.dirname(pasta)
    return pasta


def comando_do_kit():
    """Prefixo dos comandos (COMANDO de projeto.env na raiz); padrão: tuttor."""
    try:
        with open(os.path.join(_raiz_do_kit(), "projeto.env"), encoding="utf-8") as f:
            for linha in f.read(4096).splitlines():
                m = re.match(r"\s*COMANDO\s*=\s*([A-Za-z0-9_-]+)\s*(?:#.*)?$", linha)
                if m:
                    return m.group(1)
    except OSError:
        pass
    return COMANDO_PADRAO


def comando_da_status_line(sem_mascote=False):
    """Linha de comando do statusLine, com python3 e o caminho do script entre aspas."""
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "statusline.py")
    partes = ["python3", shlex.quote(script)]
    if sem_mascote:
        partes.append("--sem-mascote")
    return " ".join(partes)


def regras_de_permissao(comando=None):
    """Só o que o tutor precisa rodar sem perguntar. Sem `*` onde a regra deve ser exata."""
    c = comando or comando_do_kit()
    subcomandos = ("registrar", "dica", "apoio", "revisar", "resumo")
    regras = [f"Bash({c}-estado {s} *)" for s in subcomandos] + [f"Bash({c}-estado caminho)"]
    regras += [f"Bash({c}-vigia --resumo)", f"Bash({c}-vigia --leituras)"]
    # Leitura das referências do próprio kit (pedagogia, domínios): ficam fora do projeto do
    # aluno e, sem esta regra, cada leitura pede permissão. `//` é caminho absoluto.
    pasta_da_skill = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    regras.append("Read(/%s/**)" % pasta_da_skill.replace(os.sep, "/"))
    return regras


def configuracoes(sem_mascote=False, comando=None):
    return {
        "statusLine": {"type": "command", "command": comando_da_status_line(sem_mascote)},
        "spinnerVerbs": {"mode": "replace",
                         "verbs": list(VERBOS_NEUTROS if sem_mascote else VERBOS_MASCOTE)},
        "spinnerTipsOverride": {"label": ROTULO_DICAS, "excludeDefault": True,
                                "tips": list(DICAS)},
        "permissions": {"allow": regras_de_permissao(comando)},
    }


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="configuracoes.py",
        description="Imprime o JSON do kit para `claude --settings` (não grava nada).")
    ap.add_argument("--sem-mascote", action="store_true",
                    help="tira o que é do mascote (status line sem o Lume, verbos neutros)")
    args = ap.parse_args(argv)
    print(json.dumps(configuracoes(args.sem_mascote), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
