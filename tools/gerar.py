#!/usr/bin/env python3
"""Gera os arquivos derivados do kit a partir de `projeto.env` e das referências da skill.

Uso:
    python3 tools/gerar.py              escreve os arquivos gerados (idempotente)
    python3 tools/gerar.py --conferir   não escreve nada; sai com código 1 se algo estiver
                                        desatualizado (para o CI)
    python3 tools/gerar.py --raiz DIR   usa DIR como raiz do repositório (padrão: a deste arquivo)

Arquivos gerados (a lista é `gerados()`; JSON não aceita comentário, então o aviso "gerado por
tools/gerar.py; não edite à mão" fica registrado aqui e nos tipos que aceitam comentário):
    .claude-plugin/plugin.json, .claude-plugin/marketplace.json, hooks/hooks.json,
    output-styles/tutor.md, skills/<comando>/SKILL.md (um por comando),
    skills/<NOME>/assets/kit.json

Só biblioteca padrão. Compatível com Python 3.9+.
"""
import argparse
import json
import os
import re
import sys

AVISO = "gerado por tools/gerar.py; não edite à mão"
MARCA_MD = "<!-- " + AVISO + " -->"
OBRIGATORIAS = ("NOME", "COMANDO", "VERSAO", "MASCOTE", "DONO", "DESCRICAO")
# Uma referência é comando se tiver estes campos (persona, pedagogia e domínios não têm).
CAMPOS_COMANDO = ("name", "description", "argument-hint")
FERRAMENTAS_DO_GUARD = "Edit|Write|MultiEdit|NotebookEdit|Bash|PowerShell"


class ErroGerador(Exception):
    pass


def ler_env(caminho):
    """Lê linhas CHAVE=valor de projeto.env (comentários com #; aspas opcionais)."""
    dados = {}
    try:
        with open(caminho, encoding="utf-8") as f:
            for linha in f:
                linha = linha.strip()
                if not linha or linha.startswith("#") or "=" not in linha:
                    continue
                chave, valor = linha.split("=", 1)
                dados[chave.strip()] = valor.strip().strip("\"'")
    except OSError as e:
        raise ErroGerador("não consegui ler %s: %s" % (caminho, e))
    faltam = [c for c in OBRIGATORIAS if not dados.get(c)]
    if faltam:
        raise ErroGerador("projeto.env sem: " + ", ".join(faltam))
    return dados


def partir(texto):
    """Separa frontmatter simples (chave: valor) do corpo. Devolve (campos, corpo)."""
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", texto, re.S)
    if not m:
        return None, texto
    campos = {}
    for linha in m.group(1).splitlines():
        chave, _, valor = linha.partition(":")
        valor = valor.strip()
        if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
            valor = valor[1:-1]
        campos[chave.strip()] = valor
    return campos, m.group(2)


def aspas(valor):
    """Escalar YAML entre aspas duplas (JSON é YAML válido): protege ':' e '[' no valor."""
    return json.dumps(valor, ensure_ascii=False)


def como_json(dados):
    return json.dumps(dados, ensure_ascii=False, indent=2) + "\n"


def pasta_skill(raiz, env):
    return os.path.join(raiz, "skills", env["NOME"])


def comandos(raiz, env):
    """Lê as referências que são comandos: frontmatter com name (= arquivo), description e
    argument-hint. Devolve lista ordenada de (nome, description, argument-hint, corpo)."""
    pasta = os.path.join(pasta_skill(raiz, env), "references")
    if not os.path.isdir(pasta):
        raise ErroGerador("não achei a pasta de referências: %s" % pasta)
    achados = []
    for arq in sorted(os.listdir(pasta)):
        if not arq.endswith(".md"):
            continue
        with open(os.path.join(pasta, arq), encoding="utf-8") as f:
            campos, corpo = partir(f.read())
        if not campos or not all(campos.get(c) for c in CAMPOS_COMANDO):
            continue
        if campos["name"] != arq[:-3]:
            continue
        achados.append((campos["name"], campos["description"], campos["argument-hint"],
                        corpo))
    return achados


def manifesto_plugin(env):
    repo = "https://github.com/%s/%s" % (env["DONO"], env["NOME"])
    manifesto = {
        "name": env["NOME"],
        "version": env["VERSAO"],
        "description": env["DESCRICAO"],
        "author": {"name": env["DONO"]},
        "homepage": repo,
        "repository": repo,
    }
    if env.get("LICENCA"):   # opcional; `license` é um identificador SPDX (ex.: MIT)
        manifesto["license"] = env["LICENCA"]
    manifesto["keywords"] = ["tutor", "ensino", "programação", "socrático"]
    return manifesto


def manifesto_marketplace(env):
    return {
        "name": env["NOME"],
        "owner": {"name": env["DONO"]},
        "description": env["DESCRICAO"],
        "plugins": [{
            "name": env["NOME"],
            "source": "./",
            "description": env["DESCRICAO"],
        }],
    }


def hooks_do_plugin(env):
    base = '"${CLAUDE_PLUGIN_ROOT}/skills/%s/scripts/%%s"' % env["NOME"]
    return {"hooks": {
        "PreToolUse": [{
            "matcher": FERRAMENTAS_DO_GUARD,
            "hooks": [{
                "type": "command",
                "command": "python3 " + base % "guard.py",
                "onFailure": "block",
            }],
        }],
        "SessionStart": [{
            "hooks": [{"type": "command", "command": "python3 " + base % "contexto.py"}],
        }],
    }}


def estilo_de_saida(raiz, env):
    caminho = os.path.join(pasta_skill(raiz, env), "references", "persona.md")
    with open(caminho, encoding="utf-8") as f:
        campos, corpo = partir(f.read())
    if not campos or not campos.get("name") or not campos.get("description"):
        raise ErroGerador("persona.md sem frontmatter com name e description")
    linhas = ["---", "name: " + aspas(campos["name"]),
              "description: " + aspas(campos["description"]),
              "keep-coding-instructions: " + campos.get("keep-coding-instructions", "false"),
              "force-for-plugin: true", "---", MARCA_MD, ""]
    return "\n".join(linhas) + "\n" + corpo.lstrip("\n").rstrip("\n") + "\n"


def atalho(env, nome, descricao, dica, corpo):
    """O atalho leva o roteiro do comando inteiro: ler o arquivo de referência em tempo de
    execução exigiria permissão de leitura fora do projeto do aluno (visto em sessão real)."""
    pasta = "${CLAUDE_PLUGIN_ROOT}/skills/%s/references" % env["NOME"]
    return "\n".join([
        "---", "name: " + nome, "description: " + aspas(descricao),
        "argument-hint: " + aspas(dica), "---", MARCA_MD,
        "<!-- origem: `%s/%s.md` -->" % (pasta, nome), "",
        corpo.strip(), "",
        "Arquivos citados acima como `references/...` ficam em `%s/`." % pasta, "",
        "Pedido do aluno (o texto que veio com o comando): $ARGUMENTS", ""])


def gerados(raiz):
    """Mapa caminho relativo (com /) -> conteúdo de todo arquivo gerado."""
    env = ler_env(os.path.join(raiz, "projeto.env"))
    saida = {
        ".claude-plugin/plugin.json": como_json(manifesto_plugin(env)),
        ".claude-plugin/marketplace.json": como_json(manifesto_marketplace(env)),
        "hooks/hooks.json": como_json(hooks_do_plugin(env)),
        "output-styles/tutor.md": estilo_de_saida(raiz, env),
        "skills/%s/assets/kit.json" % env["NOME"]: como_json({
            "nome": env["NOME"], "comando": env["COMANDO"], "versao": env["VERSAO"],
            "mascote": env["MASCOTE"]}),
    }
    for nome, descricao, dica, corpo in comandos(raiz, env):
        saida["skills/%s/SKILL.md" % nome] = atalho(env, nome, descricao, dica, corpo)
    return saida


def orfaos(raiz, esperados):
    """Atalhos gerados que não têm mais referência (SKILL.md com o aviso, fora do mapa)."""
    achados = []
    pasta = os.path.join(raiz, "skills")
    if not os.path.isdir(pasta):
        return achados
    for nome in sorted(os.listdir(pasta)):
        rel = "skills/%s/SKILL.md" % nome
        caminho = os.path.join(raiz, rel)
        if rel in esperados or not os.path.isfile(caminho):
            continue
        with open(caminho, encoding="utf-8") as f:
            if MARCA_MD in f.read():
                achados.append(rel)
    return achados


def main(argv=None):
    ap = argparse.ArgumentParser(description="Gera os arquivos derivados do kit.")
    ap.add_argument("--conferir", action="store_true",
                    help="não escreve; sai com código 1 se algo estiver desatualizado")
    ap.add_argument("--raiz", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    help="raiz do repositório (padrão: a deste arquivo)")
    args = ap.parse_args(argv)
    raiz = os.path.abspath(args.raiz)
    try:
        arquivos = gerados(raiz)
    except ErroGerador as e:
        print("erro: %s" % e, file=sys.stderr)
        return 2
    problemas = []
    for rel, conteudo in sorted(arquivos.items()):
        caminho = os.path.join(raiz, *rel.split("/"))
        atual = None
        if os.path.isfile(caminho):
            with open(caminho, encoding="utf-8", newline="") as f:
                atual = f.read()
        if atual == conteudo:
            continue
        if args.conferir:
            problemas.append("%s (%s)" % (rel, "ausente" if atual is None else "desatualizado"))
            continue
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        with open(caminho, "w", encoding="utf-8", newline="") as f:
            f.write(conteudo)
        print("escrito: " + rel)
    for rel in orfaos(raiz, arquivos):
        problemas.append("%s (órfão: sem referência correspondente)" % rel)
    if args.conferir:
        if problemas:
            print("Arquivos gerados desatualizados; rode `python3 tools/gerar.py`:",
                  file=sys.stderr)
            for p in problemas:
                print("  - " + p, file=sys.stderr)
            return 1
        print("ok: %d arquivos gerados em dia" % len(arquivos))
    elif problemas:
        for p in problemas:
            print("aviso: " + p + "; apague à mão", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
