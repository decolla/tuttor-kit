#!/usr/bin/env python3
"""Renomeia o kit: novo nome (NOME) e novo comando (COMANDO) em todo o repositório.

Uso:
    python3 tools/renomear.py <novo-nome> <novo-comando> [--dry-run] [--raiz DIR]

O que faz: atualiza `projeto.env`; troca as ocorrências literais do nome antigo e do comando
antigo (e as variantes MAIÚSCULA e Capitalizada do comando, como TUTTOR_BIN_DIR) nos textos;
renomeia arquivos e pastas cujo nome contém o nome ou o comando antigo (`skills/<NOME>/`,
`bin/<COMANDO>*`, ...); e roda o gerador. Não mexe em `.git/` (o histórico fica como está).
`--dry-run` só lista o que mudaria.

Só biblioteca padrão. Compatível com Python 3.9+.
"""
import argparse
import os
import re
import subprocess
import sys

RAIZ_PADRAO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTAS_IGNORADAS = {".git", "__pycache__", ".pytest_cache", ".ruff_cache", ".venv", "venv"}
RESERVADOS = ("claude-", "anthropic-", "anthropics-", "cc-plugin-")
PADRAO_NOME = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")


class ErroRenomear(Exception):
    pass


def ler_env(raiz):
    dados = {}
    caminho = os.path.join(raiz, "projeto.env")
    try:
        with open(caminho, encoding="utf-8") as f:
            for linha in f:
                linha = linha.strip()
                if linha and not linha.startswith("#") and "=" in linha:
                    chave, valor = linha.split("=", 1)
                    dados[chave.strip()] = valor.strip().strip("\"'")
    except OSError as e:
        raise ErroRenomear("não consegui ler %s: %s" % (caminho, e))
    for chave in ("NOME", "COMANDO"):
        if not dados.get(chave):
            raise ErroRenomear("projeto.env sem " + chave)
    return dados


def validar(nome, comando):
    for rotulo, valor in (("nome", nome), ("comando", comando)):
        if not PADRAO_NOME.match(valor):
            raise ErroRenomear("%s inválido (%r): use letras minúsculas, dígitos e hífens"
                               % (rotulo, valor))
        if valor.startswith(RESERVADOS) or valor in ("claude", "anthropic", "claude-code"):
            raise ErroRenomear("%s %r é reservado: o Claude Code rejeita nomes de plugin que "
                               "parecem os da Anthropic" % (rotulo, valor))


def montar_trocas(antigo_nome, antigo_comando, novo_nome, novo_comando):
    """Mapa texto antigo -> novo. A troca é feita em uma passada só, do mais longo ao mais curto,
    para que `tuttor-kit` não vire (nome novo) + (comando novo)."""
    def maiuscula(valor):
        return re.sub(r"[^A-Za-z0-9]", "", valor).upper()

    trocas = {
        antigo_nome: novo_nome,
        antigo_comando: novo_comando,
        antigo_comando.capitalize(): novo_comando.capitalize(),
    }
    if maiuscula(antigo_comando):
        trocas[maiuscula(antigo_comando)] = maiuscula(novo_comando)
    return {k: v for k, v in trocas.items() if k and k != v}


def aplicar(trocas, texto):
    if not trocas:
        return texto
    padrao = re.compile("|".join(re.escape(k) for k in sorted(trocas, key=len, reverse=True)))
    return padrao.sub(lambda m: trocas[m.group(0)], texto)


def _eh_texto(caminho):
    try:
        with open(caminho, "rb") as f:
            bruto = f.read()
    except OSError:
        return None
    if b"\0" in bruto:
        return None
    try:
        return bruto.decode("utf-8")
    except UnicodeDecodeError:
        return None


def arquivos_do_repositorio(raiz):
    for pasta, subpastas, nomes in os.walk(raiz):
        subpastas[:] = sorted(d for d in subpastas if d not in PASTAS_IGNORADAS)
        for nome in sorted(nomes):
            yield os.path.join(pasta, nome)


def planejar(raiz, trocas):
    """Devolve (textos a reescrever [(caminho, novo texto, n)], renomeações [(de, para)])."""
    textos, nomes = [], []
    for caminho in arquivos_do_repositorio(raiz):
        if os.path.islink(caminho):
            continue
        original = _eh_texto(caminho)
        if original is not None:
            novo = aplicar(trocas, original)
            if novo != original:
                textos.append((caminho, novo, sum(1 for _ in re.finditer(
                    "|".join(re.escape(k) for k in trocas), original))))
    for pasta, subpastas, arquivos in os.walk(raiz, topdown=False):
        subpastas[:] = [d for d in subpastas if d not in PASTAS_IGNORADAS]
        if any(p in PASTAS_IGNORADAS for p in os.path.relpath(pasta, raiz).split(os.sep)):
            continue
        for nome in subpastas + arquivos:
            novo = aplicar(trocas, nome)
            if novo != nome:
                nomes.append((os.path.join(pasta, nome), os.path.join(pasta, novo)))
    return textos, nomes


def renomear(raiz, novo_nome, novo_comando, simulacao=False, saida=print):
    validar(novo_nome, novo_comando)
    env = ler_env(raiz)
    trocas = montar_trocas(env["NOME"], env["COMANDO"], novo_nome, novo_comando)
    if not trocas:
        raise ErroRenomear("o nome e o comando novos são iguais aos atuais")
    textos, nomes = planejar(raiz, trocas)
    for caminho, _, n in textos:
        saida("%s %s (%d ocorrência(s))" % ("[dry-run] trocaria em" if simulacao else "texto:",
                                              os.path.relpath(caminho, raiz), n))
    for de, para in nomes:
        saida("%s %s -> %s" % ("[dry-run] renomearia" if simulacao else "renomeado:",
                               os.path.relpath(de, raiz), os.path.relpath(para, raiz)))
    if simulacao:
        saida("[dry-run] rodaria tools/gerar.py")
        return 0
    for caminho, novo, _ in textos:
        with open(caminho, "w", encoding="utf-8", newline="") as f:
            f.write(novo)
    for de, para in nomes:   # de baixo para cima: o filho sai antes de a pasta mudar de nome
        if os.path.lexists(para):
            raise ErroRenomear("já existe %s" % os.path.relpath(para, raiz))
        os.rename(de, para)
    gerador = os.path.join(raiz, "tools", "gerar.py")
    r = subprocess.run([sys.executable, gerador, "--raiz", raiz])
    if r.returncode != 0:
        raise ErroRenomear("o gerador falhou (código %d)" % r.returncode)
    saida("pronto: %s / %s. Confira com `python3 tools/gerar.py --conferir` e rode os testes."
          % (novo_nome, novo_comando))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Renomeia o kit (nome e comando).")
    ap.add_argument("novo_nome", help="novo NOME (ex.: meu-tutor-kit)")
    ap.add_argument("novo_comando", help="novo COMANDO (ex.: meututor)")
    ap.add_argument("--dry-run", action="store_true", help="só lista o que mudaria")
    ap.add_argument("--raiz", default=RAIZ_PADRAO, help="raiz do repositório (padrão: a deste)")
    args = ap.parse_args(argv)
    try:
        return renomear(os.path.abspath(args.raiz), args.novo_nome, args.novo_comando,
                        args.dry_run)
    except ErroRenomear as e:
        print("erro: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
