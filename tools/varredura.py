#!/usr/bin/env python3
"""Varre os arquivos rastreados pelo git atrás de segredos e dados pessoais.

Uso:
    python3 tools/varredura.py [--historico] [--raiz DIR]

Procura: chaves e tokens de provedores conhecidos, blocos PEM de chave privada,
`senha=` ou `token=` com valor, e-mails (fora da lista de permitidos), caminhos `/home/<algo>` e
`/Users/<algo>` e o nome de usuário da máquina (lido do ambiente em tempo de execução: nunca
fica escrito aqui). Com `--historico`, também os autores, committers e mensagens dos commits.
Imprime `arquivo:linha: tipo: trecho` com o trecho mascarado (nunca o segredo inteiro) e sai com
código 1 se achar algo; 0 se estiver limpo; 2 em erro de uso (sem git, por exemplo).

Uma linha pode ser liberada com o comentário `varredura: ok`.
Só biblioteca padrão. Compatível com Python 3.9+.
"""
import argparse
import getpass
import os
import re
import subprocess
import sys

RAIZ_PADRAO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIBERA_LINHA = "varredura: ok"

CHAVES = (
    ("chave AWS", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("token GitHub", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("token GitHub", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("chave Anthropic", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}")),
    ("chave OpenAI", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}")),
    ("chave Google", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("token Slack", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("chave Stripe", re.compile(r"\b[sr]k_live_[0-9A-Za-z]{16,}")),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("chave privada PEM", re.compile(r"-----BEGIN (?:[A-Z]+ )*PRIVATE KEY(?: BLOCK)?-----")),
)
ATRIBUICAO = re.compile(
    r"(?i)\b(senha|password|passwd|secret|token|api[_-]?key)\b[\"']?\s*[=:]\s*[\"']?"
    r"([^\s\"'#,;)}\]]{8,})")
# Valor que obviamente não é segredo: variável, marcador, nome de função ou exemplo.
VALOR_FALSO = re.compile(
    r"^(?:[$<{%\[(]|.*(?:\.\.\.|xxx|\*\*\*|exemplo|example|placeholder|changeme|fake|falso|"
    r"teste|dummy|sua[-_]|seu[-_]|\$\{|os\.environ|getenv|\(\)))", re.I)
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
EMAILS_PERMITIDOS = {"noreply@anthropic.com", "git@github.com"}
DOMINIOS_DE_EXEMPLO = ("exemplo.com", "exemplo.com.br", "exemplo.org", "example.com",
                       "example.org", "example.net", "users.noreply.github.com",
                       "exemplo", "example", "test", "invalid", "localhost")  # RFC 2606
CAMINHO_HOME = re.compile(r"/(?:home|Users)/([A-Za-z0-9._-]+)")
NOMES_DE_EXEMPLO = {"usuario", "user", "nome", "voce", "aluno", "fulano", "exemplo", "example",
                    "seunome", "seu-usuario", "meuusuario", "me", "you", "runner", "ubuntu"}
USUARIOS_GENERICOS = {"root", "user", "runner", "ubuntu", "admin", "home", "nobody", "vscode",
                      "codespace", "docker"}
TIPOS_DE_SEGREDO = {"chave AWS", "token GitHub", "chave Anthropic", "chave OpenAI", "chave Google",
                    "token Slack", "chave Stripe", "JWT", "chave privada PEM",
                    "senha/token com valor"}
# Arquivo (na raiz varrida) que lista, um caminho por linha, os arquivos de teste que guardam
# segredos FALSOS de propósito. Só silencia os tipos de segredo, nunca e-mail, home ou usuário.
ARQUIVO_PERMITIDOS = "tools/varredura-permitidos.txt"
# Onde o dono do projeto (DONO, que pode ser igual ao usuário da máquina) é esperado.
ARQUIVOS_COM_DONO = (".claude-plugin/plugin.json", ".claude-plugin/marketplace.json",
                     "projeto.env")


def mascarar(texto):
    """Mostra só o começo do trecho; o resto vira reticências."""
    texto = texto.strip()
    if len(texto) <= 4:
        return "***"
    return texto[:4] + "..." + " (%d car.)" % len(texto)


def email_permitido(email):
    email = email.lower()
    if email in EMAILS_PERMITIDOS:
        return True
    dominio = email.rsplit("@", 1)[1]
    return any(dominio == d or dominio.endswith("." + d) for d in DOMINIOS_DE_EXEMPLO)


def nomes_de_usuario():
    """Usuário da máquina, lido do ambiente agora (nunca escrito no código)."""
    achados = set()
    for var in ("USER", "LOGNAME", "USERNAME"):
        achados.add(os.environ.get(var, ""))
    try:
        achados.add(getpass.getuser())
    except (KeyError, OSError, ImportError):
        pass
    achados.add(os.path.basename(os.path.expanduser("~").rstrip("/")))
    return sorted(n for n in achados if len(n) >= 3 and n.lower() not in USUARIOS_GENERICOS)


def dono_do_projeto(raiz):
    try:
        with open(os.path.join(raiz, "projeto.env"), encoding="utf-8") as f:
            for linha in f:
                if linha.startswith("DONO="):
                    return linha.split("=", 1)[1].strip().strip("\"'")
    except OSError:
        pass
    return ""


def _dono_publico(linha, ini, fim):
    """O DONO é o usuário PÚBLICO do GitHub: vale em endereço do GitHub, na forma dono/repo
    e na linha de copyright. Em qualquer outro lugar continua sendo achado."""
    antes, depois = linha[:ini], linha[fim:]
    if re.search(r"github\.com/$|@$", antes) or re.match(r"/[A-Za-z0-9._-]+", depois):
        return not re.search(r"/(home|Users)/$", antes)
    return bool(re.search(r"Copyright \(c\) \d{4} $", antes))


def varrer_texto(texto, usuarios, dono="", rel=""):
    """Lista (linha, tipo, trecho mascarado) de um texto."""
    achados = []
    padroes_usuario = [(u, re.compile(r"(?<![A-Za-z0-9_])" + re.escape(u) + r"(?![A-Za-z0-9_])"))
                       for u in usuarios]
    for n, linha in enumerate(texto.splitlines(), 1):
        if LIBERA_LINHA in linha:
            continue
        for tipo, padrao in CHAVES:
            for m in padrao.finditer(linha):
                achados.append((n, tipo, mascarar(m.group(0))))
        for m in ATRIBUICAO.finditer(linha):
            if not VALOR_FALSO.match(m.group(2)):
                achados.append((n, "senha/token com valor", mascarar(m.group(2))))
        for m in EMAIL.finditer(linha):
            if not email_permitido(m.group(0)):
                achados.append((n, "e-mail", m.group(0)[0] + "***@" + m.group(0).split("@")[1]))
        for m in CAMINHO_HOME.finditer(linha):
            if m.group(1).lower() not in NOMES_DE_EXEMPLO:
                achados.append((n, "caminho de home", mascarar(m.group(0))))
        for usuario, padrao in padroes_usuario:
            for m in padrao.finditer(linha):
                if usuario == dono and (rel in ARQUIVOS_COM_DONO
                                        or _dono_publico(linha, m.start(), m.end())):
                    continue
                achados.append((n, "usuário da máquina", mascarar(usuario)))
                break
    return achados


def arquivos_rastreados(raiz):
    r = subprocess.run(["git", "ls-files", "-z"], cwd=raiz, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError("git ls-files falhou: " + r.stderr.decode("utf-8", "replace").strip())
    return [p for p in r.stdout.decode("utf-8", "surrogateescape").split("\0") if p]


def ler_permitidos(raiz):
    try:
        with open(os.path.join(raiz, ARQUIVO_PERMITIDOS), encoding="utf-8") as f:
            linhas = [linha.split("#", 1)[0].strip() for linha in f]
    except OSError:
        return set()
    return {linha for linha in linhas if linha}


def varrer_arquivos(raiz, usuarios):
    dono = dono_do_projeto(raiz)
    permitidos = ler_permitidos(raiz)
    achados = []
    for rel in arquivos_rastreados(raiz):
        caminho = os.path.join(raiz, rel)
        if os.path.islink(caminho) or not os.path.isfile(caminho):
            continue
        try:
            with open(caminho, "rb") as f:
                bruto = f.read()
        except OSError:
            continue
        if b"\0" in bruto:
            continue
        texto = bruto.decode("utf-8", "replace")
        for n, tipo, trecho in varrer_texto(texto, usuarios, dono, rel):
            if rel in permitidos and tipo in TIPOS_DE_SEGREDO:
                continue
            achados.append(("%s:%d" % (rel, n), tipo, trecho))
        for usuario in usuarios:   # o nome do arquivo também conta
            if usuario in rel.split("/"):
                achados.append((rel, "usuário da máquina no nome", mascarar(usuario)))
    return achados


def varrer_historico(raiz, usuarios):
    """Autores, committers e mensagens de todos os commits. O nome igual ao DONO de projeto.env
    (o usuário público do GitHub) é aceito."""
    dono = dono_do_projeto(raiz)
    formato = "--format=%H%x1f%an%x1f%ae%x1f%cn%x1f%ce%x1f%B"
    r = subprocess.run(["git", "log", "--all", "-z", formato], cwd=raiz,
                       capture_output=True)
    if r.returncode != 0:
        raise RuntimeError("git log falhou: " + r.stderr.decode("utf-8", "replace").strip())
    achados = []
    for registro in r.stdout.decode("utf-8", "replace").split("\0"):
        campos = registro.strip("\n").split("\x1f", 5)
        if len(campos) < 6:
            continue
        sha, an, ae, cn, ce, mensagem = campos
        onde = "commit %s" % sha[:8]
        for papel, nome, email in (("autor", an, ae), ("committer", cn, ce)):
            if email and not email_permitido(email):
                achados.append((onde, "histórico: e-mail do %s" % papel,
                                email[0] + "***@" + email.split("@")[-1]))
            for usuario in usuarios:
                if usuario.lower() in nome.lower() and nome != dono:
                    achados.append((onde, "histórico: nome do %s com o usuário da máquina"
                                    % papel, mascarar(nome)))
        for _, tipo, trecho in varrer_texto(mensagem, usuarios):
            achados.append((onde, "histórico: mensagem: " + tipo, trecho))
    return achados


def main(argv=None):
    ap = argparse.ArgumentParser(description="Varre o repositório atrás de segredos e dados "
                                             "pessoais.")
    ap.add_argument("--historico", action="store_true",
                    help="inclui autores e mensagens dos commits")
    ap.add_argument("--raiz", default=RAIZ_PADRAO, help="repositório a varrer (padrão: este)")
    args = ap.parse_args(argv)
    raiz = os.path.abspath(args.raiz)
    usuarios = nomes_de_usuario()
    try:
        achados = varrer_arquivos(raiz, usuarios)
        if args.historico:
            achados += varrer_historico(raiz, usuarios)
    except (RuntimeError, OSError) as e:
        print("erro: %s" % e, file=sys.stderr)
        return 2
    for onde, tipo, trecho in achados:
        print("%s: %s: %s" % (onde, tipo, trecho))
    if achados:
        print("%d achado(s). Corrija, ou marque a linha com `%s` se for exemplo."
              % (len(achados), LIBERA_LINHA), file=sys.stderr)
        return 1
    print("ok: nada suspeito em %s" % ("arquivos e histórico" if args.historico else "arquivos"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
