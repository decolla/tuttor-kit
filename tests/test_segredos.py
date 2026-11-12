"""Testes de segredos.py: chave só do ambiente, máscara, redação e arquivos sensíveis."""
import pytest

import segredos

CHAVE_FALSA = "sk-ant-api03-ABCDEFGHIJKLMNOPQRSTUV0123456789"


@pytest.fixture(autouse=True)
def _limpa(monkeypatch):
    segredos._conhecidas.clear()
    for var in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "MINHA_CHAVE"):
        monkeypatch.delenv(var, raising=False)
    yield
    segredos._conhecidas.clear()


def test_chave_vem_do_ambiente(monkeypatch):
    monkeypatch.setenv("MINHA_CHAVE", "valor-qualquer-123")
    assert segredos.chave("MINHA_CHAVE") == "valor-qualquer-123"


def test_chave_ausente_explica_sem_mostrar_valor():
    with pytest.raises(segredos.ErroDeChave) as e:
        segredos.chave("OPENAI_API_KEY")
    msg = str(e.value)
    assert "OPENAI_API_KEY" in msg and "export OPENAI_API_KEY=" in msg


def test_nome_de_variavel_que_e_a_propria_chave_e_recusado():
    with pytest.raises(segredos.ErroDeChave) as e:
        segredos.chave(CHAVE_FALSA)
    assert CHAVE_FALSA not in str(e.value)
    with pytest.raises(segredos.ErroDeChave):
        segredos.validar_nome_de_variavel("nome com espaço")


def test_recusa_valor_com_cara_de_chave_sem_ecoar():
    with pytest.raises(segredos.ErroDeChave) as e:
        segredos.recusar_se_parece_chave("api", CHAVE_FALSA)
    assert CHAVE_FALSA not in str(e.value)
    segredos.recusar_se_parece_chave("modelo", "llama3.2:1b")  # não levanta


def test_mascarar_remove_valor_conhecido_mesmo_sem_padrao(monkeypatch):
    monkeypatch.setenv("MINHA_CHAVE", "abc")  # curto demais para padrão
    monkeypatch.setenv("OUTRA_CHAVE_X", "valor-curto-12")
    segredos.chave("MINHA_CHAVE")
    assert "abc" not in segredos.mascarar("erro com abc no corpo")
    monkeypatch.setenv("OPENAI_API_KEY", "segredo-sem-formato-9")
    segredos.chave("OPENAI_API_KEY")
    assert "segredo-sem-formato-9" not in segredos.mascarar("x segredo-sem-formato-9 y")


def test_mascarar_padroes_conhecidos():
    texto = f"falhou com {CHAVE_FALSA} e Bearer abcdefghijklmnop1234"
    saida = segredos.mascarar(texto)
    assert CHAVE_FALSA not in saida and "abcdefghijklmnop1234" not in saida
    assert segredos.OCULTO in saida


@pytest.mark.parametrize("codigo", [
    'api = "sk-proj-abcdefghijklmnopqrstu12345"',
    'token = "ghp_abcdefghijklmnopqrstuvwxyz0123456789"',
    'aws = "AKIAABCDEFGHIJKLMNOP"',
    'password = "hunter22"',
    'senha: "minhasenha"',
    '{"password": "abc12345"}',
    "Server=db;User=sa;Password=abc123xyz;Database=x",
    'conn = "postgres://admin:p4ssw0rd@db.exemplo/app"',
    "-----BEGIN RSA PRIVATE KEY-----\nMIIEabc\n-----END RSA PRIVATE KEY-----",
    'x = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"',
])
def test_redigir_oculta_segredos(codigo):
    saida, n = segredos.redigir(codigo)
    assert n >= 1 and segredos.OCULTO in saida
    for pedaco in ("hunter22", "minhasenha", "abc12345", "p4ssw0rd", "MIIEabc",
                   "abcdefghijklmnopqrstu12345", "AKIAABCDEFGHIJKLMNOP", "abc123xyz"):
        assert pedaco not in saida


def test_redigir_preserva_codigo_comum():
    codigo = ('senha = input("Senha: ")\ndef gera_token(usuario):\n    return token\n'
              "nome_muito_longo_de_variavel_sem_digitos_nenhum = 1\n")
    saida, n = segredos.redigir(codigo)
    assert (saida, n) == (codigo, 0)


@pytest.mark.parametrize("caminho", [
    ".env", "app/.env.local", "chave.pem", "a/b/id_rsa", "id_rsa.pub", "x.key",
    "appsettings.Production.json", "src/Secrets.json", "secrets.yml", "credentials.json",
    ".ssh/config", "infra/prod.tfvars", ".npmrc", "Client_Secret_1.json",
])
def test_arquivo_sensivel_sim(caminho):
    assert segredos.arquivo_sensivel(caminho)


@pytest.mark.parametrize("caminho", ["Program.cs", "src/app.py", "appsettings.json",
                                     "README.md", "environment.py", "keys.py", "docs/chaves.md"])
def test_arquivo_sensivel_nao(caminho):
    assert not segredos.arquivo_sensivel(caminho)
