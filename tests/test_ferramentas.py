"""Testes das ferramentas de manutenção: tools/renomear.py e tools/varredura.py."""
import hashlib
import importlib.util
import os
import shutil
import subprocess
import sys

import pytest

import kit

RAIZ = kit.raiz_do_kit()
FERRAMENTAS = os.path.join(RAIZ, "tools")
IGNORAR_NA_COPIA = shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", ".ruff_cache",
                                          ".venv", "venv")


def carregar(nome):
    spec = importlib.util.spec_from_file_location(nome, os.path.join(FERRAMENTAS, nome + ".py"))
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def rodar(script, *args, cwd=None, env=None):
    return subprocess.run([sys.executable, os.path.join(FERRAMENTAS, script), *args], cwd=cwd,
                          env=env, capture_output=True, text=True)


def impressao(raiz):
    """Hash do conteúdo e dos nomes de todos os arquivos (para provar que nada mudou)."""
    h = hashlib.sha256()
    for pasta, dirs, nomes in os.walk(raiz):
        dirs.sort()
        for nome in sorted(nomes):
            caminho = os.path.join(pasta, nome)
            h.update(os.path.relpath(caminho, raiz).encode())
            with open(caminho, "rb") as f:
                h.update(f.read())
    return h.hexdigest()


# ---------------------------------------------------------------- renomear

@pytest.fixture(scope="module")
def copia_renomeada(tmp_path_factory):
    copia = tmp_path_factory.mktemp("renomear") / "copia"
    shutil.copytree(RAIZ, copia, ignore=IGNORAR_NA_COPIA)
    r = rodar("renomear.py", "meu-kit", "meucmd", "--raiz", str(copia))
    assert r.returncode == 0, r.stdout + r.stderr
    return copia


def test_renomear_atualiza_projeto_e_nomes(copia_renomeada):
    env = (copia_renomeada / "projeto.env").read_text(encoding="utf-8")
    assert "NOME=meu-kit" in env and "COMANDO=meucmd" in env and "VERSAO=" in env
    assert (copia_renomeada / "skills" / "meu-kit" / "SKILL.md").is_file()
    assert not (copia_renomeada / "skills" / kit.NOME).exists()
    for nome in ("meucmd", "meucmd-vigia", "meucmd-estado"):
        assert os.access(copia_renomeada / "bin" / nome, os.X_OK)
    assert not [p for p in os.listdir(copia_renomeada / "bin") if kit.COMANDO in p]


def test_renomear_gerados_em_dia(copia_renomeada):
    r = rodar("gerar.py", "--conferir", "--raiz", str(copia_renomeada))
    assert r.returncode == 0, r.stderr
    plugin = (copia_renomeada / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
    assert '"name": "meu-kit"' in plugin and '"license": "MIT"' in plugin


def test_renomear_nao_sobra_nome_antigo(copia_renomeada):
    sobras = []
    for pasta, dirs, nomes in os.walk(copia_renomeada):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
        for nome in nomes:
            caminho = os.path.join(pasta, nome)
            rel = os.path.relpath(caminho, copia_renomeada).replace(os.sep, "/")
            if kit.COMANDO in rel.lower():
                sobras.append(rel)
            with open(caminho, "rb") as f:
                bruto = f.read()
            if kit.COMANDO.encode() in bruto.lower():
                sobras.append(rel)
    assert sobras == []


def test_renomear_suite_da_copia_passa(copia_renomeada):
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                        "--ignore=tests/test_ferramentas.py", "tests"], cwd=copia_renomeada,
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-3000:]


def test_renomear_dry_run_nao_muda_nada(tmp_path):
    copia = tmp_path / "copia"
    shutil.copytree(RAIZ, copia, ignore=IGNORAR_NA_COPIA)
    antes = impressao(copia)
    r = rodar("renomear.py", "meu-kit", "meucmd", "--dry-run", "--raiz", str(copia))
    assert r.returncode == 0 and "[dry-run]" in r.stdout
    assert impressao(copia) == antes


@pytest.mark.parametrize("nome,comando", [("Meu Kit", "meucmd"), ("meu-kit", "claude"),
                                          ("claude-tutor", "meucmd"), (kit.NOME, kit.COMANDO)])
def test_renomear_recusa_nomes_ruins(tmp_path, nome, comando):
    copia = tmp_path / "copia"
    copia.mkdir()
    shutil.copy(os.path.join(RAIZ, "projeto.env"), copia)
    r = rodar("renomear.py", nome, comando, "--raiz", str(copia))
    assert r.returncode == 1 and "erro" in r.stderr
    assert (copia / "projeto.env").read_text() == open(os.path.join(RAIZ, "projeto.env")).read()


# ---------------------------------------------------------------- varredura

USUARIO = "aluno" + "falso"   # montado aqui: o literal não existe no arquivo
CHAVE_AWS = "AKIA" + "ABCDEFGHIJKLMNOP"
TOKEN_GH = "ghp_" + "a1B2c3D4e5F6g7H8i9J0" * 2
CHAVE_ANT = "sk-" + "ant-" + "x1y2z3" * 6
SENHA = "senha" + "=" + "Tr0ub4dor&3xyz"
PEM = "-----BEGIN " + "RSA PRIVATE KEY-----"
EMAIL_REAL = "pessoa" + "@" + "empresa.com.br"
CAMINHO_REAL = "/home/" + "maria"


def git(repo, *args, **env):
    e = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    e.update({"GIT_AUTHOR_NAME": "Autor", "GIT_AUTHOR_EMAIL": "noreply@anthropic.com",
              "GIT_COMMITTER_NAME": "Autor", "GIT_COMMITTER_EMAIL": "noreply@anthropic.com",
              "HOME": str(repo.parent)})
    e.update(env)
    subprocess.run(["git", "-c", "commit.gpgsign=false", *args], cwd=repo, env=e, check=True,
                   capture_output=True)


@pytest.fixture
def repo(tmp_path):
    pasta = tmp_path / "repo"
    pasta.mkdir()
    git(pasta, "init", "-q")
    (pasta / "projeto.env").write_text("NOME=x\nDONO=donofalso\n")
    return pasta


def varrer(repo, *args, usuario=USUARIO):
    env = {k: v for k, v in os.environ.items() if k not in ("USER", "LOGNAME", "USERNAME")}
    env.update({"USER": usuario, "LOGNAME": usuario, "USERNAME": usuario,
                "HOME": str(repo.parent / "home" / usuario)})
    return rodar("varredura.py", "--raiz", str(repo), *args, env=env)


def commitar(repo, mensagem="inicio", **env):
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", mensagem, **env)


def test_varredura_repositorio_limpo(repo):
    (repo / "a.txt").write_text("nada de mais\nnome@exemplo.com\n/home/usuario/x\n")
    commitar(repo)
    r = varrer(repo)
    assert r.returncode == 0 and "ok" in r.stdout


def test_varredura_acha_segredos_sem_imprimi_los(repo):
    (repo / "segredos.txt").write_text("\n".join([
        "aws " + CHAVE_AWS, "gh " + TOKEN_GH, "ant " + CHAVE_ANT, SENHA, PEM, ""]))
    commitar(repo)
    r = varrer(repo)
    assert r.returncode == 1
    for tipo in ("chave AWS", "token GitHub", "chave Anthropic", "senha/token com valor",
                 "chave privada PEM"):
        assert tipo in r.stdout
    assert "segredos.txt:1:" in r.stdout and "segredos.txt:5:" in r.stdout
    for segredo in (CHAVE_AWS, TOKEN_GH, CHAVE_ANT, SENHA.split("=")[1]):
        assert segredo not in r.stdout + r.stderr


def test_varredura_emails(repo):
    (repo / "e.txt").write_text("\n".join([
        "noreply@anthropic.com", "12345+x@users.noreply.github.com", "nome@exemplo.com",
        EMAIL_REAL, ""]))
    commitar(repo)
    r = varrer(repo)
    assert r.returncode == 1
    assert r.stdout.count("e-mail") == 1 and "e.txt:4:" in r.stdout
    assert EMAIL_REAL not in r.stdout


def test_varredura_caminhos_de_home(repo):
    (repo / "c.txt").write_text("/home/<usuario>/x\n/home/usuario/x\n" + CAMINHO_REAL
                                + "/p\n/Users/" + "joao" + "/p\n")
    commitar(repo)
    r = varrer(repo)
    assert r.stdout.count("caminho de home") == 2
    assert "c.txt:1:" not in r.stdout and "c.txt:2:" not in r.stdout
    assert CAMINHO_REAL not in r.stdout


def test_varredura_usuario_da_maquina(repo):
    (repo / "u.txt").write_text("feito por %s\nsem relação: %sx\n" % (USUARIO, USUARIO))
    commitar(repo)
    r = varrer(repo)
    assert r.returncode == 1 and r.stdout.count("usuário da máquina") == 1
    assert "u.txt:1:" in r.stdout and USUARIO not in r.stdout
    assert varrer(repo, usuario="outrapessoa").returncode == 0


def test_varredura_usuario_generico_e_ignorado(repo):
    (repo / "u.txt").write_text("rodando como runner e root\n")
    commitar(repo)
    assert varrer(repo, usuario="runner").returncode == 0


def test_varredura_dono_so_nos_arquivos_do_projeto(repo):
    (repo / "projeto.env").write_text("NOME=x\nDONO=" + USUARIO + "\n")
    (repo / "outro.md").write_text("autor: " + USUARIO + "\n")
    commitar(repo)
    r = varrer(repo)
    assert "outro.md:1:" in r.stdout and "projeto.env" not in r.stdout


def test_varredura_aceita_o_dono_como_usuario_publico_do_github(repo):
    (repo / "projeto.env").write_text("NOME=x\nDONO=" + USUARIO + "\n")
    (repo / "LEIAME.md").write_text(
        "https://github.com/" + USUARIO + "/x\n/plugin marketplace add " + USUARIO + "/x\n"
        "Copyright (c) 2026 " + USUARIO + "\n")
    (repo / "ruim.md").write_text("cd /home/" + USUARIO + "/x\nfeito por " + USUARIO + "\n")
    commitar(repo)
    r = varrer(repo)
    assert "LEIAME.md" not in r.stdout
    assert "ruim.md:1:" in r.stdout and "ruim.md:2:" in r.stdout


def test_varredura_so_arquivos_rastreados(repo):
    (repo / "ok.txt").write_text("limpo\n")
    commitar(repo)
    (repo / "solto.txt").write_text(CHAVE_AWS + "\n")
    assert varrer(repo).returncode == 0


def test_varredura_marca_de_liberacao_e_arquivo_de_permitidos(repo):
    (repo / "tools").mkdir()
    (repo / "tools" / "varredura-permitidos.txt").write_text("# fixtures\nfixture.py\n")
    (repo / "fixture.py").write_text("CHAVE = '" + CHAVE_AWS + "'\nE = '" + EMAIL_REAL + "'\n")
    (repo / "liberado.txt").write_text(CHAVE_AWS + "  varredura" + ": ok\n")
    commitar(repo)
    r = varrer(repo)
    assert r.returncode == 1
    assert "fixture.py:1:" not in r.stdout and "liberado.txt" not in r.stdout
    assert "fixture.py:2: e-mail" in r.stdout          # o arquivo só silencia segredos


def test_varredura_historico(repo):
    (repo / "a.txt").write_text("limpo\n")
    commitar(repo, "mensagem com " + CHAVE_AWS, GIT_AUTHOR_EMAIL=EMAIL_REAL,
             GIT_AUTHOR_NAME="Fulano " + USUARIO)
    assert varrer(repo).returncode == 0              # sem --historico, só os arquivos
    r = varrer(repo, "--historico")
    assert r.returncode == 1
    assert "e-mail do autor" in r.stdout and "mensagem: chave AWS" in r.stdout
    assert "nome do autor com o usuário da máquina" in r.stdout
    assert EMAIL_REAL not in r.stdout and CHAVE_AWS not in r.stdout


def test_varredura_fora_de_um_repositorio(tmp_path):
    r = rodar("varredura.py", "--raiz", str(tmp_path))
    assert r.returncode == 2 and "erro" in r.stderr


def test_mascarar_nunca_mostra_o_segredo_inteiro():
    varredura = carregar("varredura")
    assert "XYZW1234567890" not in varredura.mascarar("XYZW1234567890")
    assert varredura.mascarar("abc") == "***"
