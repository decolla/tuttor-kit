"""Provedores de IA do vigia: `claude-cli`, `comando`, `anthropic` e `openai`.

    criar(nome, **config) -> Provedor
    Provedor.perguntar(sistema, usuario, *, tempo_limite) -> Resposta
    erros: ErroDeProvedor (mensagem já sem segredos)

As chaves vêm só do ambiente (segredos.chave). Nenhuma chave entra em linha de comando de
subprocesso, em mensagem de erro ou em log. Os provedores HTTP usam só `urllib` e NÃO seguem
redirecionamentos (um redirect levaria o cabeçalho com a chave a outro endereço).
"""
import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

import segredos

HOSTS_LOCAIS = ("localhost", "127.0.0.1", "::1")
NOMES = ("claude-cli", "comando", "anthropic", "openai")
VAR_CHAVE_PADRAO = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}
URL_PADRAO = {"anthropic": "https://api.anthropic.com", "openai": "https://api.openai.com/v1"}
VERSAO_API_ANTHROPIC = "2026-10-21"
INSTRUCAO_CLAUDE = "Comente a mudança descrita na entrada, seguindo suas instruções."
FERRAMENTAS_WEB = ("WebSearch", "WebFetch")
LIMITE_CORPO = 2_000_000
_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07]*\x07")


class ErroDeProvedor(Exception):
    """Falha ao consultar o provedor. A mensagem não contém segredos."""


@dataclass
class Resposta:
    texto: str
    custo_usd: object = None
    tokens_entrada: object = None
    tokens_saida: object = None


def _limpa(texto, limite=400):
    texto = segredos.mascarar(_ANSI.sub("", str(texto or ""))).strip()
    return texto if len(texto) <= limite else texto[:limite] + "…"


def _ultimas_linhas(texto, n=3):
    linhas = [l for l in _limpa(texto, 2000).splitlines() if l.strip()]
    return " | ".join(linhas[-n:])


def _numero(valor):
    return valor if isinstance(valor, (int, float)) and not isinstance(valor, bool) else None


def _host_local(host):
    return (host or "").strip("[]").lower() in HOSTS_LOCAIS


class Provedor:
    nome = ""
    local = False

    def destino(self):
        return self.nome

    def verificar(self):
        """Checagem antes de começar (binário, chave...). Levanta ErroDeProvedor."""

    def perguntar(self, sistema, usuario, *, tempo_limite):  # pragma: no cover
        raise NotImplementedError


# ---------------------------------------------------------------- subprocessos

def _env_filtrado():
    """Ambiente do filho sem variáveis com cara de chave (para o provedor `comando`)."""
    saida = {}
    for nome, valor in os.environ.items():
        if nome.upper().endswith(segredos._SUFIXOS_SEGREDO):
            continue
        saida[nome] = valor
    return saida


class _ArquivoTemporario:
    """Arquivo temporário 0600 com o prompt de sistema; apagado ao sair."""

    def __init__(self, texto):
        fd, self.caminho = tempfile.mkstemp(prefix="vigia-sistema-", suffix=".md")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(texto)

    def __enter__(self):
        return self.caminho

    def __exit__(self, *_):
        try:
            os.unlink(self.caminho)
        except OSError:
            pass


def _rodar(cmd, entrada, tempo_limite, cwd=None, env=None):
    try:
        return subprocess.run(cmd, input=entrada, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=tempo_limite,
                              cwd=cwd, env=env, shell=False)
    except FileNotFoundError:
        raise ErroDeProvedor(f"não encontrei o comando '{os.path.basename(cmd[0])}'. "
                             "Ele está instalado e no PATH?") from None
    except PermissionError:
        raise ErroDeProvedor(f"sem permissão para executar '{os.path.basename(cmd[0])}'.") \
            from None
    except subprocess.TimeoutExpired:
        raise ErroDeProvedor(f"o comando '{os.path.basename(cmd[0])}' demorou mais de "
                             f"{tempo_limite}s (use --tempo-limite para aumentar).") from None
    except OSError as e:
        raise ErroDeProvedor(f"não consegui executar '{os.path.basename(cmd[0])}': "
                             f"{_limpa(e.strerror or e.__class__.__name__)}") from None


class ClaudeCli(Provedor):
    """`claude -p` isolado: sem personalizações, sem ferramentas (só as pedidas)."""
    nome = "claude-cli"
    local = False

    def __init__(self, binario="claude", modelo=None, web=False, ler=False, diretorio=None,
                 **_):
        self.binario = binario or "claude"
        self.modelo = modelo or None
        self.web = bool(web)
        self.ler = bool(ler)
        self.diretorio = diretorio
        if self.web and self.ler:
            raise ErroDeProvedor("web e leitura de arquivos não podem ficar ligadas juntas: "
                                 "código do projeto + web aberta permitiria vazamento.")

    def destino(self):
        return "Claude Code (claude -p), que fala com a Anthropic"

    def verificar(self):
        if not shutil.which(self.binario):
            raise ErroDeProvedor(f"não encontrei o comando '{os.path.basename(self.binario)}'. "
                                 "O Claude Code está instalado e no PATH?")

    def ferramentas(self):
        ferr = []
        if self.web:
            ferr += list(FERRAMENTAS_WEB)
        if self.ler:
            ferr.append("Read")
        return ",".join(ferr)

    def linha(self, arquivo_do_sistema):
        ferr = self.ferramentas()
        cmd = [self.binario, "-p", INSTRUCAO_CLAUDE, "--safe-mode",
               "--system-prompt-file", arquivo_do_sistema, "--tools", ferr]
        if ferr:
            cmd += ["--allowedTools", ferr]
        cmd += ["--output-format", "json", "--no-session-persistence"]
        if self.modelo:
            cmd += ["--model", self.modelo]
        return cmd

    def perguntar(self, sistema, usuario, *, tempo_limite):
        with _ArquivoTemporario(sistema) as arq:
            r = _rodar(self.linha(arq), usuario, tempo_limite, cwd=self.diretorio)
        if r.returncode != 0:
            raise ErroDeProvedor(self._erro(r))
        try:
            dados = json.loads(r.stdout)
        except ValueError:
            raise ErroDeProvedor("o claude devolveu algo que não é JSON; confira a versão "
                                 "instalada (`claude --version`) e atualize o Claude Code.") \
                from None
        if not isinstance(dados, dict) or not isinstance(dados.get("result"), str):
            raise ErroDeProvedor("a resposta do claude não trouxe o campo 'result'; atualize "
                                 "o Claude Code.")
        return Resposta(dados["result"].strip(), custo_usd=_numero(dados.get("total_cost_usd")))

    @staticmethod
    def _erro(r):
        saida = (r.stderr or "") + "\n" + (r.stdout or "")
        recusadas = ("--safe-mode", "--system-prompt-file", "--tools", "--allowedTools",
                     "--output-format", "--no-session-persistence", "--model")
        if re.search(r"(?i)unknown (option|argument)|unrecognized|invalid (option|flag)|"
                     r"no such option|unexpected argument", saida):
            achada = next((f for f in recusadas if f in saida), None)
            if achada:
                return (f"a sua versão do claude não aceitou a opção {achada}. "
                        "Atualize o Claude Code e tente de novo.")
            return ("a sua versão do claude recusou uma das opções usadas pelo vigia. "
                    "Atualize o Claude Code e tente de novo. Detalhe: "
                    + _ultimas_linhas(saida, 2))
        detalhe = _ultimas_linhas(r.stdout) or _ultimas_linhas(r.stderr)
        return f"erro do claude (código {r.returncode}): {detalhe}"


class Comando(Provedor):
    """Comando genérico: prompt pelo stdin, resposta pelo stdout, sem shell."""
    nome = "comando"
    local = False

    def __init__(self, comando=None, modelo=None, **_):
        if not comando or not str(comando).strip():
            raise ErroDeProvedor('informe o comando, por exemplo --comando "ollama run {modelo}" '
                                 "--modelo <nome do modelo>.")
        try:
            segredos.recusar_se_parece_chave("comando", comando)
        except segredos.ErroDeChave as e:
            raise ErroDeProvedor(str(e)) from None
        try:
            self.tokens = shlex.split(str(comando))
        except ValueError as e:
            raise ErroDeProvedor(f"não consegui interpretar o comando: {e}") from None
        if not self.tokens:
            raise ErroDeProvedor("comando vazio.")
        self.modelo = modelo or None
        usa_modelo = any("{modelo}" in t for t in self.tokens)
        if usa_modelo and not self.modelo:
            raise ErroDeProvedor("o comando usa {modelo}: informe --modelo.")
        self.usa_arquivo = any("{arquivo_do_sistema}" in t for t in self.tokens)
        programa = os.path.basename(self.tokens[0])
        host = os.environ.get("OLLAMA_HOST", "")
        self.local = programa == "ollama" and (
            not host or _host_local(urllib.parse.urlparse("//" + host.split("//")[-1]).hostname))

    def destino(self):
        programa = os.path.basename(self.tokens[0])
        return (f"comando local '{programa}' (ele decide para onde os dados vão"
                + ("; o ollama costuma ser local" if programa == "ollama" else "") + ")")

    def verificar(self):
        if not shutil.which(self.tokens[0]):
            raise ErroDeProvedor(f"não encontrei o comando '{os.path.basename(self.tokens[0])}'. "
                                 "Ele está instalado e no PATH?")

    def linha(self, arquivo_do_sistema):
        return [t.replace("{modelo}", self.modelo or "")
                 .replace("{arquivo_do_sistema}", arquivo_do_sistema) for t in self.tokens]

    def perguntar(self, sistema, usuario, *, tempo_limite):
        with _ArquivoTemporario(sistema) as arq:
            entrada = usuario if self.usa_arquivo else f"{sistema}\n\n---\n\n{usuario}"
            r = _rodar(self.linha(arq), entrada, tempo_limite, env=_env_filtrado())
        if r.returncode != 0:
            raise ErroDeProvedor(f"o comando terminou com código {r.returncode}: "
                                 + (_ultimas_linhas(r.stderr) or _ultimas_linhas(r.stdout)))
        return Resposta(_ANSI.sub("", r.stdout).strip())


# ---------------------------------------------------------------- HTTP

class _SemRedirecionar(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def validar_base_url(base_url):
    """Devolve (url sem barra final, host, local). https obrigatório, salvo host local."""
    bruto = (base_url or "").strip()
    try:
        u = urllib.parse.urlparse(bruto)
        host = u.hostname
        u.port  # noqa: B018  (a propriedade levanta ValueError se a porta for inválida)
    except ValueError:
        raise ErroDeProvedor("base_url inválida.") from None
    if u.scheme not in ("http", "https") or not host:
        raise ErroDeProvedor("base_url deve começar com https:// (ou http:// só para "
                             "localhost).")
    if u.username or u.password or segredos.parece_segredo(bruto):
        raise ErroDeProvedor("a base_url não pode conter usuário, senha ou chave. Chaves só por "
                             "variável de ambiente.")
    if u.query or u.fragment:
        raise ErroDeProvedor("a base_url não deve ter parâmetros (?...).")
    local = _host_local(host)
    if u.scheme == "http" and not local:
        raise ErroDeProvedor(f"o host '{host}' não é local: só aceito https para ele (a chave "
                             "e o código viajariam sem criptografia com http).")
    return bruto.rstrip("/"), host, local


class _Http(Provedor):
    caminho = ""

    def __init__(self, modelo=None, base_url=None, var_chave=None, max_saida=1024,
                 versao_api=None, papel_sistema="system", **_):
        self.base_url, self.host, self.local = validar_base_url(
            base_url or URL_PADRAO[self.nome])
        self.var_chave = segredos.validar_nome_de_variavel(
            var_chave or VAR_CHAVE_PADRAO[self.nome])
        self.modelo = modelo or None
        self.max_saida = int(max_saida)
        self.versao_api = versao_api or VERSAO_API_ANTHROPIC
        self.papel_sistema = papel_sistema or "system"
        if self.local and not self.base_url.startswith("http"):
            raise ErroDeProvedor("base_url inválida.")

    def destino(self):
        return f"{self.nome} em {self.host}" + (" (local)" if self.local else "")

    def _chave(self):
        """Chave do ambiente; em host local pode faltar (devolve None)."""
        try:
            return segredos.chave(self.var_chave)
        except segredos.ErroDeChave:
            if self.local:
                return None
            raise

    def verificar(self):
        if not self.modelo:
            raise ErroDeProvedor("informe o modelo (--modelo ou variável de ambiente "
                                 "TUTTOR_VIGIA_MODELO); consulte a lista oficial do provedor.")
        try:
            self._chave()
        except segredos.ErroDeChave as e:
            raise ErroDeProvedor(str(e)) from None

    def _montar(self, sistema, usuario, chave):  # pragma: no cover
        raise NotImplementedError

    def _ler(self, dados):  # pragma: no cover
        raise NotImplementedError

    def perguntar(self, sistema, usuario, *, tempo_limite):
        if not self.modelo:
            raise ErroDeProvedor("informe o modelo (--modelo ou variável de ambiente "
                                 "TUTTOR_VIGIA_MODELO); consulte a lista oficial do provedor.")
        try:
            chave = self._chave()
        except segredos.ErroDeChave as e:
            raise ErroDeProvedor(str(e)) from None
        url, cabecalhos, corpo = self._montar(sistema, usuario, chave)
        req = urllib.request.Request(url, data=json.dumps(corpo).encode("utf-8"),
                                     headers=cabecalhos, method="POST")
        manipuladores = [_SemRedirecionar()]
        if self.local:
            manipuladores.append(urllib.request.ProxyHandler({}))
        abridor = urllib.request.build_opener(*manipuladores)
        try:
            with abridor.open(req, timeout=tempo_limite) as resp:
                bruto = resp.read(LIMITE_CORPO)
        except urllib.error.HTTPError as e:
            raise ErroDeProvedor(self._erro_http(e)) from None
        except urllib.error.URLError as e:
            raise ErroDeProvedor(f"não consegui falar com {self.host}: "
                                 f"{_limpa(getattr(e, 'reason', e))}") from None
        except (TimeoutError, OSError) as e:
            raise ErroDeProvedor(f"{self.host} não respondeu a tempo ou a conexão caiu "
                                 f"({_limpa(e.__class__.__name__)}).") from None
        try:
            dados = json.loads(bruto.decode("utf-8", errors="replace"))
        except ValueError:
            raise ErroDeProvedor(f"{self.host} devolveu algo que não é JSON.") from None
        try:
            return self._ler(dados)
        except (KeyError, IndexError, TypeError, AttributeError):
            raise ErroDeProvedor(f"a resposta de {self.host} não tem o formato esperado "
                                 f"da API '{self.nome}'.") from None

    def _erro_http(self, e):
        if 300 <= e.code < 400:
            return (f"{self.host} respondeu com redirecionamento (HTTP {e.code}). Não sigo "
                    "redirecionamentos, para não enviar a chave a outro endereço; confira a "
                    "base_url.")
        try:
            corpo = e.read(4000).decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001 - o corpo é só um detalhe
            corpo = ""
        detalhe = corpo
        try:
            obj = json.loads(corpo)
            if isinstance(obj, dict):
                err = obj.get("error", obj)
                detalhe = err.get("message") if isinstance(err, dict) else str(err)
        except ValueError:
            pass
        dica = ""
        if e.code in (401, 403):
            dica = f" Confira a chave na variável {self.var_chave}."
        elif e.code == 404:
            dica = " Confira o modelo e a base_url."
        elif e.code == 429:
            dica = " Limite de uso atingido; espere um pouco."
        return f"{self.host} respondeu HTTP {e.code}: {_limpa(detalhe)}{dica}"


class Anthropic(_Http):
    nome = "anthropic"

    def _montar(self, sistema, usuario, chave):
        cab = {"content-type": "application/json", "anthropic-version": self.versao_api,
               "x-api-key": chave}
        corpo = {"model": self.modelo, "max_tokens": self.max_saida, "system": sistema,
                 "messages": [{"role": "user", "content": usuario}]}
        return self.base_url + "/v1/messages", cab, corpo

    def _ler(self, dados):
        texto = "".join(b.get("text", "") for b in dados["content"]
                        if isinstance(b, dict) and b.get("type") == "text")
        uso = dados.get("usage") or {}
        return Resposta(texto.strip(), tokens_entrada=_numero(uso.get("input_tokens")),
                        tokens_saida=_numero(uso.get("output_tokens")))


class OpenAI(_Http):
    nome = "openai"

    def _montar(self, sistema, usuario, chave):
        cab = {"content-type": "application/json"}
        if chave:
            cab["Authorization"] = "Bearer " + chave
        corpo = {"model": self.modelo,
                 "messages": [{"role": self.papel_sistema, "content": sistema},
                              {"role": "user", "content": usuario}]}
        return self.base_url + "/chat/completions", cab, corpo

    def _ler(self, dados):
        texto = dados["choices"][0]["message"]["content"] or ""
        uso = dados.get("usage") or {}
        return Resposta(str(texto).strip(), tokens_entrada=_numero(uso.get("prompt_tokens")),
                        tokens_saida=_numero(uso.get("completion_tokens")))


def criar(nome, **config):
    """Cria o provedor `nome` (claude-cli, comando, anthropic, openai)."""
    classes = {"claude-cli": ClaudeCli, "comando": Comando, "anthropic": Anthropic,
               "openai": OpenAI}
    if nome not in classes:
        raise ErroDeProvedor(f"provedor desconhecido: '{_limpa(nome, 40)}'. Use um de: "
                             + ", ".join(NOMES) + ".")
    return classes[nome](**config)
