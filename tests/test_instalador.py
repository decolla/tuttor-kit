"""Testes do install.sh: tudo em diretórios temporários, com HOME falsa e `claude` falso."""
import os
import shutil
import subprocess

import pytest

import kit

RAIZ = kit.raiz_do_kit()
INSTALADOR = os.path.join(RAIZ, "install.sh")
COMANDO = kit.COMANDO
BASH = shutil.which("bash")
NOMES = [COMANDO, COMANDO + "-vigia", COMANDO + "-estado"]
FERRAMENTAS = ("python3", "git", "dirname", "basename", "readlink", "mkdir", "rm", "mv", "ln",
               "rmdir", "cat")


class Ambiente:
    def __init__(self, tmp_path):
        self.casa = tmp_path / "casa"
        self.bin = tmp_path / "pasta com espaço" / "bin"
        self.dados = tmp_path / "dados"
        self.falsos = tmp_path / "falsos"
        for pasta in (self.casa, self.falsos):
            pasta.mkdir()
        self.path_extra = [str(self.falsos)]
        self.so_ferramentas = False
        self.base_path = os.environ["PATH"]

    def claude(self, versao):
        falso = self.falsos / "claude"
        falso.write_text('#!/bin/sh\necho "%s (Claude Code)"\n' % versao)
        falso.chmod(0o755)

    def env(self, **extra):
        env = {k: v for k, v in os.environ.items() if not k.startswith(("TUTTOR_", "XDG_"))}
        env["HOME"] = str(self.casa)
        env["TUTTOR_BIN_DIR"] = str(self.bin)
        env["XDG_DATA_HOME"] = str(self.dados)
        env["PATH"] = os.pathsep.join(self.path_extra + [self.base_path])
        env.update(extra)
        return env

    def rodar(self, *args, instalador=INSTALADOR, **extra):
        return subprocess.run([BASH, instalador, *args], env=self.env(**extra),
                              capture_output=True, text=True)

    @property
    def manifesto(self):
        return self.dados / kit.NOME / "instalado"


@pytest.fixture
def amb(tmp_path):
    return Ambiente(tmp_path)


def arvore(pasta):
    return sorted(str(p.relative_to(pasta)) for p in pasta.rglob("*")) if pasta.exists() else []


def test_instala_so_links_e_manifesto(amb):
    r = amb.rodar()
    assert r.returncode == 0, r.stderr
    for nome in NOMES:
        link = amb.bin / nome
        assert link.is_symlink()
        assert os.readlink(link) == os.path.join(RAIZ, "bin", nome)
    linhas = amb.manifesto.read_text(encoding="utf-8").splitlines()
    assert "versao=" + kit.VERSAO in linhas and "kit=" + RAIZ in linhas
    assert [x for x in linhas if x.startswith("link=")] == ["link=%s" % (amb.bin / n)
                                                          for n in NOMES]
    assert not (amb.casa / ".claude").exists()      # não toca em ~/.claude
    assert not (amb.casa / ".tutor").exists()


def test_idempotente_sem_bak(amb):
    amb.rodar()
    antes = (arvore(amb.bin), amb.manifesto.read_bytes())
    r = amb.rodar()
    assert r.returncode == 0 and "já instalado" in r.stdout
    assert (arvore(amb.bin), amb.manifesto.read_bytes()) == antes
    assert not [p for p in arvore(amb.bin) + arvore(amb.dados) if ".bak" in p or ".novo" in p]


def test_nao_sobrescreve_o_que_nao_e_do_kit(amb):
    amb.bin.mkdir(parents=True)
    (amb.bin / COMANDO).write_text("meu script\n")
    r = amb.rodar()
    assert r.returncode == 1 and "--forcar" in r.stderr
    assert (amb.bin / COMANDO).read_text() == "meu script\n"
    assert not (amb.bin / (COMANDO + "-vigia")).exists()    # nada foi instalado pela metade
    assert not amb.manifesto.exists()


def test_nao_sobrescreve_link_de_outro_lugar(amb, tmp_path):
    amb.bin.mkdir(parents=True)
    (amb.bin / COMANDO).symlink_to(tmp_path / "outro")
    assert amb.rodar().returncode == 1
    assert os.readlink(amb.bin / COMANDO) == str(tmp_path / "outro")


def test_forcar_substitui(amb):
    amb.bin.mkdir(parents=True)
    (amb.bin / COMANDO).write_text("meu script\n")
    r = amb.rodar("--forcar")
    assert r.returncode == 0, r.stderr
    assert (amb.bin / COMANDO).is_symlink()
    assert not [p for p in arvore(amb.bin) if ".bak" in p]


def test_dry_run_nao_grava(amb):
    r = amb.rodar("--dry-run")
    assert r.returncode == 0 and "[dry-run]" in r.stdout
    assert not amb.bin.exists() and not amb.dados.exists()
    amb.rodar()
    antes = arvore(amb.bin)
    r = amb.rodar("--uninstall", "--dry-run")
    assert "[dry-run]" in r.stdout and arvore(amb.bin) == antes and amb.manifesto.exists()


def test_uninstall_remove_so_o_do_manifesto_e_preserva_tutor(amb, tmp_path):
    amb.rodar()
    (amb.casa / ".tutor").mkdir()
    (amb.casa / ".tutor" / "perfil.md").write_text("meu perfil")
    (amb.bin / "outro-programa").write_text("x")
    r = amb.rodar("--uninstall")
    assert r.returncode == 0, r.stderr
    assert arvore(amb.bin) == ["outro-programa"]
    assert not amb.manifesto.exists()
    assert (amb.casa / ".tutor" / "perfil.md").read_text() == "meu perfil"
    assert "~/.tutor" in r.stdout and "intocados" in r.stdout


def test_uninstall_mantem_link_que_nao_e_mais_do_kit(amb, tmp_path):
    amb.rodar()
    (amb.bin / NOMES[1]).unlink()
    (amb.bin / NOMES[1]).symlink_to(tmp_path / "outro")
    r = amb.rodar("--uninstall")
    assert r.returncode == 0 and "mantido" in r.stdout
    assert arvore(amb.bin) == [NOMES[1]]


def test_uninstall_sem_manifesto(amb):
    r = amb.rodar("--uninstall")
    assert r.returncode == 0 and "nada a remover" in r.stdout


def test_ajuda_e_opcao_invalida(amb):
    assert "--verificar" in amb.rodar("--ajuda").stdout
    r = amb.rodar("--xis")
    assert r.returncode == 2 and "desconhecida" in r.stderr


# ---------------------------------------------------------------- --verificar

def test_verificar_tudo_certo(amb):
    amb.claude("2.1.322")
    amb.path_extra.append(str(amb.bin))
    amb.rodar()
    r = amb.rodar("--verificar")
    assert r.returncode == 0, r.stdout
    assert "claude 2.1.322" in r.stdout and "0 falha(s), 0 aviso(s)" in r.stdout


def test_verificar_claude_antigo_avisa_que_nao_ha_falha_fechada(amb):
    amb.claude("2.1.294")
    r = amb.rodar("--verificar")
    assert r.returncode == 1
    assert "FALHA" in r.stdout and "falha fechada" in r.stdout


def test_verificar_aceita_a_versao_minima(amb):
    amb.claude("2.1.295")
    assert "ok:    claude 2.1.295" in amb.rodar("--verificar").stdout


def ambiente_enxuto(amb, tmp_path, com_claude):
    """PATH só com as ferramentas necessárias (sem o claude real) e, se pedido, o falso."""
    enxuto = tmp_path / "enxuto"
    enxuto.mkdir()
    for nome in FERRAMENTAS:
        caminho = shutil.which(nome)
        (enxuto / nome).symlink_to(caminho)
    amb.path_extra = [str(enxuto)]
    amb.base_path = ""
    if com_claude:
        amb.path_extra.insert(0, str(amb.falsos))


def test_verificar_sem_claude(amb, tmp_path):
    ambiente_enxuto(amb, tmp_path, com_claude=False)
    r = amb.rodar("--verificar")
    assert r.returncode == 1 and "claude não encontrado" in r.stdout


def test_verificar_sem_git_so_avisa(amb, tmp_path):
    amb.claude("2.1.322")
    ambiente_enxuto(amb, tmp_path, com_claude=True)
    (tmp_path / "enxuto" / "git").unlink()
    r = amb.rodar("--verificar")
    assert "aviso: git não encontrado" in r.stdout and r.returncode == 0, r.stdout


def test_verificar_path_e_versao_instalada(amb):
    amb.claude("2.1.322")
    amb.rodar()
    texto = amb.manifesto.read_text(encoding="utf-8").replace(
        "versao=" + kit.VERSAO, "versao=0.0.1")
    amb.manifesto.write_text(texto, encoding="utf-8")
    r = amb.rodar("--verificar")
    assert r.returncode == 0
    assert "não está no PATH" in r.stdout and "difere de projeto.env" in r.stdout


def test_verificar_sem_instalar_avisa(amb):
    amb.claude("2.1.322")
    r = amb.rodar("--verificar")
    assert r.returncode == 0 and "kit não instalado" in r.stdout


def test_verificar_python_antigo(amb):
    amb.claude("2.1.322")
    (amb.falsos / "python3").write_text("#!/bin/sh\nexit 1\n")
    (amb.falsos / "python3").chmod(0o755)
    r = amb.rodar("--verificar")
    assert r.returncode == 1 and "FALHA: python3 abaixo de 3.9" in r.stdout


def test_verificar_gerados_desatualizados(amb, tmp_path):
    copia = tmp_path / "copia"
    shutil.copytree(RAIZ, copia, ignore=shutil.ignore_patterns(".git", "__pycache__",
                                                                ".pytest_cache", ".ruff_cache"))
    amb.claude("2.1.322")
    ok = amb.rodar("--verificar", instalador=str(copia / "install.sh"))
    assert "arquivos gerados em dia" in ok.stdout
    env = copia / "projeto.env"
    env.write_text(env.read_text(encoding="utf-8").replace("VERSAO=" + kit.VERSAO,
                                                           "VERSAO=9.9.9"), encoding="utf-8")
    r = amb.rodar("--verificar", instalador=str(copia / "install.sh"))
    assert r.returncode == 1 and "arquivos gerados desatualizados" in r.stdout
