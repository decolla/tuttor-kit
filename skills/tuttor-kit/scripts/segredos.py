"""Chaves de API e segredos: ler só do ambiente, nunca mostrar, nunca enviar código com segredo.

Regras (todas obrigatórias):
- a chave vem SOMENTE de variável de ambiente (`chave`); não há opção de linha de comando
  nem campo de configuração que a receba (`recusar_se_parece_chave`);
- `mascarar` limpa qualquer texto antes de tela/log/exceção (valores conhecidos da chave
  e padrões de segredo);
- `redigir` troca por «oculto» valores com cara de segredo no código do aluno, antes de sair;
- `arquivo_sensivel` diz quais arquivos nunca são enviados.
"""
import fnmatch
import os
import re

OCULTO = "«oculto»"
_NOME_VAR = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,127}$")
_SUFIXOS_SEGREDO = ("KEY", "TOKEN", "SECRET", "PASSWORD", "PASSWD", "CREDENTIALS")
_conhecidas = set()   # valores reais lidos por `chave`: removidos de qualquer texto


class ErroDeChave(Exception):
    """Falta a chave, ou o nome da variável é inválido. A mensagem nunca traz o valor."""


# ---------------------------------------------------------------- padrões

_PEM = re.compile(r"-----BEGIN [A-Z0-9 ]*(?:PRIVATE KEY|CERTIFICATE|PGP[A-Z ]*BLOCK)-----"
                  r".*?(?:-----END [A-Z0-9 ]*-----|\Z)", re.S)
_CHAVES_CONHECIDAS = re.compile(
    r"\b(?:sk-ant-[A-Za-z0-9_\-]{8,}|sk-(?:proj-|svcacct-|admin-)?[A-Za-z0-9_\-]{16,}"
    r"|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}"
    r"|(?:AKIA|ASIA)[0-9A-Z]{16}|AIza[0-9A-Za-z_\-]{30,}|xox[abprs]-[A-Za-z0-9\-]{10,}"
    r"|glpat-[A-Za-z0-9_\-]{16,}|hf_[A-Za-z0-9]{20,}|SG\.[A-Za-z0-9_\-]{16,}\.[A-Za-z0-9_\-]{16,}"
    r"|eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,})")
_BEARER = re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=\-]{12,}")
_URL_COM_SENHA = re.compile(r"(?i)\b([a-z][a-z0-9+.\-]*://[^\s:/@\"']+:)[^\s@/\"']+(@)")
_ATRIBUICAO = re.compile(
    r"(?i)((?:\b|_)[\w.\-]*(?:password|passwd|pwd|senha|secret|segredo|token|api[_\-]?key|"
    r"apikey|chave[_\-]?(?:api|secreta|privada)|access[_\-]?key|private[_\-]?key)[\w.\-]*"
    r"[\"']?\s*(?:=>|:=|[:=])\s*)"
    r"(?:(\"[^\"\n]{3,}\"|'[^'\n]{3,}')|([^\s\"'();,\[\]{}<>$%]{6,}))")
_LONGO = re.compile(r"(?<![A-Za-z0-9_\-/.])[A-Za-z0-9_\-]{32,}(?![A-Za-z0-9_\-])")


def _tem_ar_de_token(s):
    """Token longo: letras e dígitos misturados (identificador comum não tem os dois)."""
    return bool(re.search(r"[A-Za-z]", s) and re.search(r"[0-9]", s)
                and not re.fullmatch(r"[A-Za-z_]+", s))


def _valores_do_ambiente():
    saida = []
    for nome, valor in os.environ.items():
        if len(valor) >= 8 and nome.upper().endswith(_SUFIXOS_SEGREDO):
            saida.append(valor)
    return saida


def _aplicar_padroes(texto):
    """Troca os padrões de segredo. Devolve (texto, quantidade)."""
    total = 0

    def conta(sub):
        def f(m):
            nonlocal total
            novo = sub(m)
            if novo != m.group(0):
                total += 1
            return novo
        return f

    texto = _PEM.sub(conta(lambda m: OCULTO), texto)
    texto = _CHAVES_CONHECIDAS.sub(conta(lambda m: OCULTO), texto)
    texto = _BEARER.sub(conta(lambda m: f"{m.group(1)} {OCULTO}"), texto)
    texto = _URL_COM_SENHA.sub(conta(lambda m: m.group(1) + OCULTO + m.group(2)), texto)

    def atribuicao(m):
        valor = m.group(2) or m.group(3) or ""
        if OCULTO in valor:
            return m.group(0)
        aspas = valor[0] if valor[:1] in "\"'" else ""
        return m.group(1) + aspas + OCULTO + aspas
    texto = _ATRIBUICAO.sub(conta(atribuicao), texto)
    texto = _LONGO.sub(conta(lambda m: OCULTO if _tem_ar_de_token(m.group(0)) else m.group(0)),
                       texto)
    return texto, total


def mascarar(texto):
    """Remove de `texto` (tela, log, mensagem de erro) a chave conhecida e padrões de segredo."""
    if not texto:
        return texto or ""
    texto = str(texto)
    for valor in sorted(_conhecidas.union(_valores_do_ambiente()), key=len, reverse=True):
        texto = texto.replace(valor, OCULTO)
    texto, _ = _aplicar_padroes(texto)
    return texto


def redigir(conteudo):
    """Troca por «oculto» o que tem cara de segredo no código. Devolve (texto, quantos)."""
    if not conteudo:
        return conteudo or "", 0
    texto = str(conteudo)
    n_valores = 0
    for valor in sorted(_conhecidas.union(_valores_do_ambiente()), key=len, reverse=True):
        if valor in texto:
            n_valores += texto.count(valor)
            texto = texto.replace(valor, OCULTO)
    texto, n = _aplicar_padroes(texto)
    return texto, n_valores + n


def parece_segredo(texto):
    """True se `texto` tem cara de chave/token (usado para recusar chave na configuração)."""
    if not isinstance(texto, str) or not texto:
        return False
    _, n = _aplicar_padroes(texto)
    return n > 0


# ---------------------------------------------------------------- chave

def nome_de_variavel_valido(nome):
    return isinstance(nome, str) and bool(_NOME_VAR.match(nome)) and not parece_segredo(nome)


def validar_nome_de_variavel(nome):
    """Garante que o que foi dado como 'nome da variável' é mesmo um nome (e não a chave)."""
    if parece_segredo(nome) or not (isinstance(nome, str) and _NOME_VAR.match(nome)):
        raise ErroDeChave(
            "O valor de --var-chave (ou var_chave) deve ser o NOME de uma variável de ambiente, "
            "por exemplo OPENAI_API_KEY, e não a chave. A chave nunca é aceita em opção de "
            "linha de comando nem em arquivo de configuração; defina-a no shell com "
            "`export NOME_DA_VARIAVEL=<sua chave>`.")
    return nome


def chave(nome_da_variavel):
    """Lê a chave da variável de ambiente. Levanta ErroDeChave (sem o valor) se faltar."""
    nome = validar_nome_de_variavel(nome_da_variavel)
    valor = os.environ.get(nome, "").strip()
    if not valor:
        raise ErroDeChave(
            f"Falta a chave: defina a variável de ambiente {nome} no shell antes de abrir o "
            f"vigia, com `export {nome}=<sua chave>` (digite no terminal; não escreva a chave "
            "em arquivos do projeto nem na linha de comando do vigia).")
    _conhecidas.add(valor)
    return valor


def recusar_se_parece_chave(nome_do_campo, valor):
    """Para configuração: se `valor` parece uma chave, recusa com explicação (sem ecoá-lo)."""
    if parece_segredo(valor):
        raise ErroDeChave(
            f"O campo '{nome_do_campo}' parece conter uma chave ou segredo. Chaves só são "
            "aceitas por variável de ambiente (`export NOME=<sua chave>`); configure apenas o "
            "NOME da variável em var_chave.")


# ---------------------------------------------------------------- arquivos sensíveis

_PADROES_NOME = (
    ".env", ".env.*", "*.env", "*.pem", "*.key", "*.p12", "*.pfx", "*.jks", "*.keystore",
    "*.ppk", "*.kdbx", "*.gpg", "*.asc", "*.crt", "*.cer", "*.der",
    "id_rsa*", "id_dsa*", "id_ecdsa*", "id_ed25519*",
    "appsettings.*.json", "secrets.*", "secret.*", "*.secret", "*.secrets", "credentials*",
    "*.tfvars", "*.tfstate", "*.tfstate.*", ".npmrc", ".pypirc", ".netrc", ".htpasswd",
    ".git-credentials", "kubeconfig", "service-account*.json", "serviceaccount*.json",
    "*-credentials.json", "client_secret*.json", "google-services.json", "*.mobileprovision",
    "wp-config.php", "local.settings.json", "settings.local.json",
)
_PASTAS_SENSIVEIS = {".ssh", ".aws", ".gnupg", ".kube", ".azure", ".docker"}


def arquivo_sensivel(caminho):
    """True para arquivos que nunca devem ser enviados (.env, chaves, credenciais...)."""
    partes = [p for p in re.split(r"[\\/]+", str(caminho)) if p and p != "."]
    if not partes:
        return False
    if any(p.lower() in _PASTAS_SENSIVEIS for p in partes[:-1]):
        return True
    nome = partes[-1].lower()
    return any(fnmatch.fnmatchcase(nome, padrao.lower()) for padrao in _PADROES_NOME)
