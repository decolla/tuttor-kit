"""Testes de provedores.py com CLI falsa e servidor HTTP local (nada de rede real)."""
import json
import os
import stat
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

import provedores
import segredos
from provedores import ErroDeProvedor

CHAVE = "sk-ant-api03-ABCDEFGHIJKLMNOPQRSTUV0123456789"


@pytest.fixture(autouse=True)
def _ambiente(monkeypatch):
    segredos._conhecidas.clear()
    for var in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_HOST"):
        monkeypatch.delenv(var, raising=False)
    yield
    segredos._conhecidas.clear()


# ---------------------------------------------------------------- CLI falsa

FALSA = """#!{py}
import json, os, sys
log = os.environ["FALSA_LOG"]
args = sys.argv[1:]
arq = args[args.index("--system-prompt-file") + 1] if "--system-prompt-file" in args else None
registro = {{"argv": args, "stdin": sys.stdin.read(),
            "sistema": open(arq).read() if arq else None,
            "env_chaves": [k for k in os.environ if k.endswith(("_KEY", "_TOKEN"))]}}
open(log, "w").write(json.dumps(registro))
modo = os.environ.get("FALSA_MODO", "ok")
if modo == "flag":
    sys.stderr.write("error: unknown option '--safe-mode'\\n")
    sys.exit(1)
if modo == "falha":
    sys.stderr.write("Invalid API key " + os.environ.get("ANTHROPIC_API_KEY", "") + "\\n")
    sys.exit(1)
if modo == "texto":
    print("isto nao e json")
    sys.exit(0)
if modo == "stdout":
    print(os.environ.get("FALSA_SAIDA", "resposta"))
    sys.exit(0)
print(json.dumps({{"type": "result", "result": "🟡 L2 — pergunta. [nomes]\\n",
                  "total_cost_usd": 0.0123}}))
"""


@pytest.fixture
def falsa(tmp_path, monkeypatch):
    prog = tmp_path / "claude"
    prog.write_text(FALSA.format(py=sys.executable), encoding="utf-8")
    prog.chmod(prog.stat().st_mode | stat.S_IEXEC)
    log = tmp_path / "registro.json"
    monkeypatch.setenv("FALSA_LOG", str(log))

    class F:
        caminho = str(prog)

        @staticmethod
        def registro():
            return json.loads(log.read_text(encoding="utf-8"))
    return F


def test_claude_cli_linha_exata(falsa):
    p = provedores.criar("claude-cli", binario=falsa.caminho, modelo="haiku")
    r = p.perguntar("SISTEMA", "USUARIO", tempo_limite=20)
    reg = falsa.registro()
    a = reg["argv"]
    assert a[0] == "-p" and a[1] == provedores.INSTRUCAO_CLAUDE
    assert a[2] == "--safe-mode"
    assert a[3] == "--system-prompt-file"
    assert a[5:9] == ["--tools", "", "--output-format", "json"]
    assert a[-2:] == ["--model", "haiku"]
    assert "--allowedTools" not in a and "--dangerously-skip-permissions" not in a
    assert reg["stdin"] == "USUARIO" and reg["sistema"] == "SISTEMA"
    assert not os.path.exists(a[4])  # arquivo temporário apagado
    assert r.texto.startswith("🟡 L2") and r.custo_usd == 0.0123


def test_claude_cli_sem_modelo_nao_passa_model(falsa):
    p = provedores.criar("claude-cli", binario=falsa.caminho)
    p.perguntar("S", "U", tempo_limite=20)
    assert "--model" not in falsa.registro()["argv"]


def test_claude_cli_web_e_ler_ferramentas(falsa):
    p = provedores.criar("claude-cli", binario=falsa.caminho, web=True)
    p.perguntar("S", "U", tempo_limite=20)
    a = falsa.registro()["argv"]
    assert a[a.index("--tools") + 1] == "WebSearch,WebFetch"
    assert a[a.index("--allowedTools") + 1] == "WebSearch,WebFetch"
    p = provedores.criar("claude-cli", binario=falsa.caminho, ler=True)
    p.perguntar("S", "U", tempo_limite=20)
    assert falsa.registro()["argv"][falsa.registro()["argv"].index("--tools") + 1] == "Read"
    with pytest.raises(ErroDeProvedor):
        provedores.criar("claude-cli", web=True, ler=True)


def test_claude_cli_flag_recusada_diz_qual(falsa, monkeypatch):
    monkeypatch.setenv("FALSA_MODO", "flag")
    p = provedores.criar("claude-cli", binario=falsa.caminho)
    with pytest.raises(ErroDeProvedor) as e:
        p.perguntar("S", "U", tempo_limite=20)
    assert "--safe-mode" in str(e.value) and "Atualize o Claude Code" in str(e.value)


def test_claude_cli_erro_nao_vaza_chave(falsa, monkeypatch):
    monkeypatch.setenv("FALSA_MODO", "falha")
    monkeypatch.setenv("ANTHROPIC_API_KEY", CHAVE)
    p = provedores.criar("claude-cli", binario=falsa.caminho)
    with pytest.raises(ErroDeProvedor) as e:
        p.perguntar("S", "U", tempo_limite=20)
    assert CHAVE not in str(e.value)


def test_claude_cli_saida_que_nao_e_json(falsa, monkeypatch):
    monkeypatch.setenv("FALSA_MODO", "texto")
    p = provedores.criar("claude-cli", binario=falsa.caminho)
    with pytest.raises(ErroDeProvedor):
        p.perguntar("S", "U", tempo_limite=20)


def test_binario_inexistente():
    p = provedores.criar("claude-cli", binario="/nao/existe/claude")
    with pytest.raises(ErroDeProvedor):
        p.verificar()
    with pytest.raises(ErroDeProvedor):
        p.perguntar("S", "U", tempo_limite=5)


# ---------------------------------------------------------------- comando

def test_comando_sem_shell_ponto_e_virgula_nao_executa(falsa, tmp_path, monkeypatch):
    marca = tmp_path / "invadido"
    monkeypatch.setenv("FALSA_MODO", "stdout")
    p = provedores.criar("comando", comando=f"{falsa.caminho} {{modelo}} ; touch {marca}",
                         modelo="m1")
    p.perguntar("S", "U", tempo_limite=20)
    assert not marca.exists()
    assert falsa.registro()["argv"] == ["m1", ";", "touch", str(marca)]


def test_comando_stdin_com_sistema_no_inicio_e_resposta_no_stdout(falsa, monkeypatch):
    monkeypatch.setenv("FALSA_MODO", "stdout")
    monkeypatch.setenv("FALSA_SAIDA", "\x1b[2Kolá")
    p = provedores.criar("comando", comando=f"{falsa.caminho} run {{modelo}}", modelo="x")
    r = p.perguntar("SISTEMA", "USUARIO", tempo_limite=20)
    reg = falsa.registro()
    assert reg["stdin"].startswith("SISTEMA") and reg["stdin"].endswith("USUARIO")
    assert reg["argv"] == ["run", "x"] and r.texto == "olá"


def test_comando_marcador_do_arquivo_do_sistema(falsa, monkeypatch):
    monkeypatch.setenv("FALSA_MODO", "stdout")
    p = provedores.criar("comando", comando=f"{falsa.caminho} --system-prompt-file "
                         "{arquivo_do_sistema}")
    p.perguntar("SISTEMA", "USUARIO", tempo_limite=20)
    reg = falsa.registro()
    assert reg["sistema"] == "SISTEMA" and reg["stdin"] == "USUARIO"


def test_comando_nao_repassa_variaveis_de_chave(falsa, monkeypatch):
    monkeypatch.setenv("FALSA_MODO", "stdout")
    monkeypatch.setenv("OPENAI_API_KEY", "valor-secreto-12345")
    p = provedores.criar("comando", comando=falsa.caminho)
    p.perguntar("S", "U", tempo_limite=20)
    assert falsa.registro()["env_chaves"] == []


def test_comando_exige_modelo_se_usa_marcador_e_recusa_chave():
    with pytest.raises(ErroDeProvedor):
        provedores.criar("comando", comando="ollama run {modelo}")
    with pytest.raises(ErroDeProvedor):
        provedores.criar("comando", comando="")
    with pytest.raises(ErroDeProvedor) as e:
        provedores.criar("comando", comando=f"curl -H 'x: {CHAVE}'")
    assert CHAVE not in str(e.value)


# ---------------------------------------------------------------- HTTP

class Servidor:
    def __init__(self):
        self.pedidos = []
        self.status = 200
        self.corpo = b"{}"
        self.cabecalhos = {}
        outer = self

        class H(BaseHTTPRequestHandler):
            def do_POST(self):
                n = int(self.headers.get("Content-Length", 0))
                outer.pedidos.append({"caminho": self.path,
                                      "cab": {k.lower(): v for k, v in self.headers.items()},
                                      "corpo": json.loads(self.rfile.read(n) or b"{}")})
                self.send_response(outer.status)
                for k, v in outer.cabecalhos.items():
                    self.send_header(k, v)
                self.send_header("Content-Length", str(len(outer.corpo)))
                self.end_headers()
                self.wfile.write(outer.corpo)

            def log_message(self, *a):
                pass

        self.httpd = HTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def responder(self, obj, status=200, **cab):
        self.corpo, self.status, self.cabecalhos = json.dumps(obj).encode(), status, cab

    def fechar(self):
        self.httpd.shutdown()
        self.httpd.server_close()


@pytest.fixture
def servidor():
    s = Servidor()
    yield s
    s.fechar()


def test_anthropic_cabecalhos_corpo_e_resposta(servidor, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", CHAVE)
    servidor.responder({"content": [{"type": "text", "text": "oi "}, {"type": "text",
                        "text": "tudo"}], "usage": {"input_tokens": 12, "output_tokens": 6}})
    p = provedores.criar("anthropic", base_url=servidor.url, modelo="modelo-x")
    r = p.perguntar("SIS", "USU", tempo_limite=10)
    ped = servidor.pedidos[0]
    assert ped["caminho"] == "/v1/messages"
    assert ped["cab"]["x-api-key"] == CHAVE
    assert ped["cab"]["anthropic-version"] == provedores.VERSAO_API_ANTHROPIC
    assert ped["cab"]["content-type"] == "application/json"
    assert ped["corpo"] == {"model": "modelo-x", "max_tokens": 1024, "system": "SIS",
                            "messages": [{"role": "user", "content": "USU"}]}
    assert (r.texto, r.tokens_entrada, r.tokens_saida) == ("oi tudo", 12, 6)


def test_openai_cabecalhos_corpo_e_resposta(servidor, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "valor-de-teste-12345678")
    servidor.responder({"choices": [{"message": {"role": "assistant", "content": "ola"}}],
                        "usage": {"prompt_tokens": 7, "completion_tokens": 3}})
    p = provedores.criar("openai", base_url=servidor.url + "/v1", modelo="m")
    r = p.perguntar("SIS", "USU", tempo_limite=10)
    ped = servidor.pedidos[0]
    assert ped["caminho"] == "/v1/chat/completions"
    assert ped["cab"]["authorization"] == "Bearer valor-de-teste-12345678"
    assert ped["corpo"] == {"model": "m", "messages": [
        {"role": "system", "content": "SIS"}, {"role": "user", "content": "USU"}]}
    assert (r.texto, r.tokens_entrada, r.tokens_saida) == ("ola", 7, 3)


def test_openai_local_sem_chave_funciona_sem_cabecalho_de_autorizacao(servidor):
    servidor.responder({"choices": [{"message": {"content": "ok"}}]})
    p = provedores.criar("openai", base_url=servidor.url + "/v1", modelo="m")
    assert p.local
    p.verificar()
    assert p.perguntar("S", "U", tempo_limite=10).texto == "ok"
    assert "authorization" not in servidor.pedidos[0]["cab"]


def test_var_de_chave_configuravel(servidor, monkeypatch):
    monkeypatch.setenv("MINHA_CHAVE_X", "valor-de-teste-12345678")
    servidor.responder({"choices": [{"message": {"content": "ok"}}]})
    p = provedores.criar("openai", base_url=servidor.url + "/v1", modelo="m",
                         var_chave="MINHA_CHAVE_X")
    p.perguntar("S", "U", tempo_limite=10)
    assert servidor.pedidos[0]["cab"]["authorization"].endswith("valor-de-teste-12345678")


def test_chave_ausente_em_host_remoto(monkeypatch):
    p = provedores.criar("anthropic", modelo="m")
    with pytest.raises(ErroDeProvedor) as e:
        p.verificar()
    assert "ANTHROPIC_API_KEY" in str(e.value) and "export" in str(e.value)
    with pytest.raises(ErroDeProvedor):
        p.perguntar("S", "U", tempo_limite=5)


def test_modelo_obrigatorio_nos_http(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "valor-de-teste-12345678")
    with pytest.raises(ErroDeProvedor) as e:
        provedores.criar("openai").verificar()
    assert "modelo" in str(e.value)


@pytest.mark.parametrize("url", ["http://exemplo.com/v1", "ftp://exemplo.com",
                                 "https://u:p@exemplo.org", "sem-esquema",
                                 "https://exemplo.com/v1?key=abc"])
def test_base_url_invalida_recusada(url):
    with pytest.raises(ErroDeProvedor):
        provedores.criar("openai", base_url=url, modelo="m")


@pytest.mark.parametrize("url", ["http://localhost:11434/v1", "http://127.0.0.1:1/v1",
                                 "http://[::1]:8080/v1", "https://api.exemplo.com/v1"])
def test_base_url_aceita_local_e_https(url):
    provedores.criar("openai", base_url=url, modelo="m")


def test_http_nao_local_nunca_chega_a_rede(monkeypatch):
    chamadas = []
    monkeypatch.setattr("urllib.request.OpenerDirector.open",
                        lambda *a, **k: chamadas.append(1))
    with pytest.raises(ErroDeProvedor):
        provedores.criar("anthropic", base_url="http://api.exemplo.com", modelo="m")
    assert not chamadas


def test_redirect_nao_e_seguido(servidor, monkeypatch):
    alvo = Servidor()
    try:
        monkeypatch.setenv("OPENAI_API_KEY", "valor-de-teste-12345678")
        servidor.responder({}, status=307, Location=alvo.url + "/roubo")
        p = provedores.criar("openai", base_url=servidor.url + "/v1", modelo="m")
        with pytest.raises(ErroDeProvedor) as e:
            p.perguntar("S", "U", tempo_limite=10)
        assert "redirecion" in str(e.value)
        assert alvo.pedidos == []
    finally:
        alvo.fechar()


def test_corpo_de_erro_com_a_chave_e_mascarado(servidor, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", CHAVE)
    servidor.responder({"error": {"message": f"chave invalida: {CHAVE}"}}, status=401)
    p = provedores.criar("anthropic", base_url=servidor.url, modelo="m")
    with pytest.raises(ErroDeProvedor) as e:
        p.perguntar("S", "U", tempo_limite=10)
    assert CHAVE not in str(e.value) and "401" in str(e.value)
    assert CHAVE not in repr(e.value)


def test_erro_com_valor_curto_conhecido_tambem_mascarado(servidor, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "curta-123456")
    servidor.responder({"error": "recebi curta-123456"}, status=500)
    p = provedores.criar("openai", base_url=servidor.url + "/v1", modelo="m")
    with pytest.raises(ErroDeProvedor) as e:
        p.perguntar("S", "U", tempo_limite=10)
    assert "curta-123456" not in str(e.value)


def test_resposta_fora_do_formato(servidor, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", CHAVE)
    servidor.responder({"inesperado": True})
    p = provedores.criar("anthropic", base_url=servidor.url, modelo="m")
    with pytest.raises(ErroDeProvedor):
        p.perguntar("S", "U", tempo_limite=10)


def test_servidor_fora_do_ar():
    p = provedores.criar("openai", base_url="http://127.0.0.1:1/v1", modelo="m")
    with pytest.raises(ErroDeProvedor):
        p.perguntar("S", "U", tempo_limite=3)


def test_provedor_desconhecido():
    with pytest.raises(ErroDeProvedor):
        provedores.criar("inexistente")
