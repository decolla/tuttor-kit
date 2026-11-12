"""Testes do lançador (lancador.py e bin/<comando>): nada toca a HOME nem o claude reais."""
import json
import os
import subprocess
import sys

import pytest

import configuracoes
import kit
import lancador

COMANDO = kit.COMANDO


class FakeTTY:
    """Substitui sys.stdout: acumula o texto e diz que é um terminal."""

    encoding = "utf-8"

    def __init__(self):
        self.partes = []

    def isatty(self):
        return True

    def write(self, texto):
        self.partes.append(texto)
        return len(texto)

    def flush(self):
        pass

    def texto(self):
        return "".join(self.partes)


@pytest.fixture
def chamadas(monkeypatch):
    """Troca o exec por um registro das chamadas."""
    registro = []
    monkeypatch.setattr(lancador, "_executar", lambda prog, argv: registro.append((prog, argv)))
    return registro


@pytest.fixture
def com_claude(tmp_path, monkeypatch):
    """PATH só com um `claude` falso (e git/python do sistema para o resto)."""
    pasta = tmp_path / "falsos"
    pasta.mkdir()
    falso = pasta / "claude"
    falso.write_text("#!/bin/sh\nexit 0\n")
    falso.chmod(0o755)
    monkeypatch.setenv("PATH", str(pasta) + os.pathsep + os.environ["PATH"])
    return pasta


@pytest.fixture
def sem_binarios(tmp_path, monkeypatch):
    vazio = tmp_path / "vazio"
    vazio.mkdir()
    monkeypatch.setenv("PATH", str(vazio))


def escrever_falso(pasta, nome, corpo):
    caminho = pasta / nome
    caminho.write_text("#!/bin/sh\n" + corpo)
    caminho.chmod(0o755)
    return caminho


# ---------------------------------------------------------------- comando do claude

def test_comando_padrao_e_isolado():
    cmd = lancador.montar_comando_claude(False, False, ["-c", "--model", "opus"])
    assert cmd[0] == "claude"
    assert cmd[cmd.index("--plugin-dir") + 1] == kit.raiz_do_kit()
    assert cmd[cmd.index("--setting-sources") + 1] == "project,local"
    assert cmd[-3:] == ["-c", "--model", "opus"]
    ajustes = json.loads(cmd[cmd.index("--settings") + 1])
    assert set(ajustes) == set(configuracoes.configuracoes())


def test_com_meus_plugins_desliga_o_isolamento():
    cmd = lancador.montar_comando_claude(False, True, [])
    assert "--setting-sources" not in cmd


def test_fontes_do_aluno_nao_duplicam():
    cmd = lancador.montar_comando_claude(False, False, ["--setting-sources", "user"])
    assert cmd.count("--setting-sources") == 1


def test_sem_mascote_vai_para_as_configuracoes():
    cmd = lancador.montar_comando_claude(True, False, [])
    ajustes = json.loads(cmd[cmd.index("--settings") + 1])
    assert "--sem-mascote" in ajustes["statusLine"]["command"]


def test_json_em_linha_e_ascii_puro():
    cmd = lancador.montar_comando_claude(False, False, [])
    cmd[cmd.index("--settings") + 1].encode("ascii")


# ---------------------------------------------------------------- opções

def test_opcoes_so_no_comeco():
    opcoes, extras = lancador.separar_opcoes(["--ascii", "--tmux", "-c", "--ascii"])
    assert opcoes["ascii"] and opcoes["tmux"]
    assert extras == ["-c", "--ascii"]


def test_duplo_traco_encerra_as_opcoes():
    opcoes, extras = lancador.separar_opcoes(["--", "--ascii"])
    assert not opcoes["ascii"]
    assert extras == ["--ascii"]


def test_cli_com_valor():
    assert lancador.separar_opcoes(["--cli", "codex", "x"])[0]["cli"] == "codex"
    assert lancador.separar_opcoes(["--cli=gemini"])[0]["cli"] == "gemini"
    with pytest.raises(lancador.ErroLancador):
        lancador.separar_opcoes(["--cli"])


def test_versao_onde_ajuda(capsys):
    assert lancador.main(["--versao"]) == 0
    assert capsys.readouterr().out.strip() == "%s %s" % (COMANDO, kit.VERSAO)
    assert lancador.main(["--onde"]) == 0
    assert capsys.readouterr().out.strip() == kit.raiz_do_kit()
    assert lancador.main(["--ajuda"]) == 0
    saida = capsys.readouterr().out
    assert "--com-meus-plugins" in saida and "--setting-sources project,local" in saida


# ---------------------------------------------------------------- preparo do projeto

def test_prepara_projeto_e_perfil(projeto):
    lancador.preparar_projeto()
    assert (projeto / ".tutor").is_dir()
    perfil = projeto.parent / "home" / ".tutor" / "perfil.md"
    assert perfil.read_text(encoding="utf-8").startswith("# Perfil do aluno")
    perfil.write_text("meu perfil")
    lancador.preparar_projeto()
    assert perfil.read_text() == "meu perfil"


def test_exclui_do_git_uma_vez(projeto):
    subprocess.run(["git", "init", "-q"], cwd=projeto, check=True)
    lancador.preparar_projeto()
    lancador.preparar_projeto()
    exclude = (projeto / ".git" / "info" / "exclude").read_text()
    assert exclude.splitlines().count(".tutor/") == 1


def test_sem_git_nao_falha(projeto):
    lancador.preparar_projeto()
    assert not (projeto / ".git").exists()


def test_recusa_tutor_como_link(projeto, tmp_path):
    alvo = tmp_path / "alheio"
    alvo.mkdir()
    (projeto / ".tutor").symlink_to(alvo)
    with pytest.raises(lancador.ErroLancador, match="link simbólico"):
        lancador.preparar_projeto()
    assert list(alvo.iterdir()) == []


# ---------------------------------------------------------------- banner

def test_banner_so_em_terminal(projeto, com_claude, chamadas, capsys):
    assert lancador.main([]) == 0
    assert "╔" not in capsys.readouterr().out
    assert chamadas and chamadas[0][0] == "claude"


def test_banner_no_terminal_com_mascote(projeto, com_claude, chamadas, monkeypatch):
    tty = FakeTTY()
    monkeypatch.setattr(sys, "stdout", tty)
    monkeypatch.setenv("TERM", "xterm")
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("LC_ALL", "pt_BR.UTF-8")
    lancador.main([])
    assert "╔" in tty.texto() and "\033[" in tty.texto()
    assert "eu ilumino" in tty.texto()


def test_banner_respeita_ascii_e_no_color(projeto, com_claude, chamadas, monkeypatch):
    tty = FakeTTY()
    monkeypatch.setattr(sys, "stdout", tty)
    monkeypatch.setenv("TERM", "xterm")
    monkeypatch.setenv("NO_COLOR", "1")
    lancador.main(["--ascii"])
    assert "╔" not in tty.texto() and "\033[" not in tty.texto()
    assert "/===\\" in tty.texto()


def test_sem_mascote_nao_mostra_banner(projeto, com_claude, chamadas, monkeypatch):
    tty = FakeTTY()
    monkeypatch.setattr(sys, "stdout", tty)
    lancador.main(["--sem-mascote"])
    assert tty.texto() == ""


# ---------------------------------------------------------------- claude ausente

def test_sem_claude(projeto, sem_binarios, chamadas, capsys):
    assert lancador.main([]) == 127
    assert "não encontrei o comando 'claude'" in capsys.readouterr().err
    assert chamadas == []
    assert not (projeto / ".tutor").exists()


# ---------------------------------------------------------------- repasse

def test_vigia_e_estado_repassam(chamadas):
    lancador.main(["vigia", "--resumo", "7"])
    lancador.main(["estado", "caminho"])
    (_, argv_v), (_, argv_e) = chamadas
    assert argv_v[1].endswith("vigia.py") and argv_v[2:] == ["--resumo", "7"]
    assert argv_e[1].endswith("estado.py") and argv_e[2:] == ["caminho"]


# ---------------------------------------------------------------- ponta a ponta (processo real)

def ambiente_de_teste(projeto, falsos):
    env = {k: v for k, v in os.environ.items() if not k.startswith(("TUTTOR_", "TMUX"))}
    env["HOME"] = str(projeto.parent / "home")
    env["PATH"] = str(falsos) + os.pathsep + env["PATH"]
    return env


def test_wrapper_com_espaco_e_acento_e_link(tmp_path, projeto):
    falsos = tmp_path / "falsos"
    falsos.mkdir()
    registro = tmp_path / "args.txt"
    escrever_falso(falsos, "claude", 'printf "%%s\\n" "$@" > "%s"\nexit 7\n' % registro)
    pasta = tmp_path / "pasta com espaço e ação"
    pasta.mkdir()
    (pasta / COMANDO).symlink_to(os.path.join(kit.raiz_do_kit(), "bin", COMANDO))
    trabalho = tmp_path / "projeto ótimo"
    trabalho.mkdir()
    r = subprocess.run([str(pasta / COMANDO), "-c", "--model", "opus"], cwd=trabalho,
                       env=ambiente_de_teste(projeto, falsos), capture_output=True, text=True)
    assert r.returncode == 7, r.stderr   # o código do claude passa (é exec)
    linhas = registro.read_text(encoding="utf-8").splitlines()
    assert linhas[0] == "--plugin-dir" and linhas[1] == kit.raiz_do_kit()
    assert linhas[-3:] == ["-c", "--model", "opus"]
    assert json.loads(linhas[linhas.index("--settings") + 1])["statusLine"]
    assert (trabalho / ".tutor").is_dir()


def test_tmux_abre_dois_paineis(tmp_path, projeto):
    falsos = tmp_path / "falsos"
    falsos.mkdir()
    registro = tmp_path / "tmux.txt"
    escrever_falso(falsos, "tmux", 'printf "%%s\\n" "$@" >> "%s"\necho --- >> "%s"\n'
                   '[ "$1" = has-session ] && exit 1\nexit 0\n' % (registro, registro))
    trabalho = tmp_path / "meu projeto"
    trabalho.mkdir()
    r = subprocess.run([os.path.join(kit.raiz_do_kit(), "bin", COMANDO), "--tmux", "--ascii",
                        "--", "-c"], cwd=trabalho, env=ambiente_de_teste(projeto, falsos),
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    passos = [p.splitlines() for p in registro.read_text(encoding="utf-8").split("---\n") if p]
    assert [p[0] for p in passos] == ["has-session", "new-session", "split-window",
                                      "attach-session"]
    novo, divide = passos[1], passos[2]
    assert "-d" in novo and novo[novo.index("-c") + 1] == str(trabalho)
    assert "--ascii" in novo[-1] and "-c" in novo[-1] and "--tmux" not in novo[-1]
    assert COMANDO + "-vigia" in divide[-1] and "-h" in divide
    assert "'" + str(trabalho) + "'" in divide[-1]    # caminho com espaço, entre aspas


def test_tmux_ausente(projeto, sem_binarios, chamadas, capsys):
    assert lancador.main(["--tmux"]) == 127
    erro = capsys.readouterr().err
    assert "tmux" in erro and "dois terminais" in erro and COMANDO + "-vigia" in erro


# ---------------------------------------------------------------- --cli

@pytest.mark.parametrize("cli,trava", [("codex", "sandbox"), ("gemini", "permissões"),
                                       ("opencode", "permissões"), ("ollama", "nenhuma trava")])
def test_cli_avisa_e_executa(projeto, tmp_path, monkeypatch, chamadas, capsys, cli, trava):
    falsos = tmp_path / "falsos"
    falsos.mkdir()
    dados = json.loads((open(os.path.join(kit.raiz_do_kit(), "modelos", "cli.json"),
                             encoding="utf-8")).read())
    escrever_falso(falsos, dados[cli]["binario"], "exit 0\n")
    monkeypatch.setenv("PATH", str(falsos) + os.pathsep + os.environ["PATH"])
    assert lancador.main(["--cli", cli, "--sem-mascote", "extra"]) == 0
    erro = capsys.readouterr().err
    assert "experimental (não testado)" in erro and trava in erro
    programa, argv = chamadas[0]
    assert argv == dados[cli]["interativo"] + ["extra"]
    assert (projeto / ".tutor").is_dir()


def test_cli_sem_binario(projeto, sem_binarios, chamadas, capsys):
    assert lancador.main(["--cli", "codex"]) == 127
    erro = capsys.readouterr().err
    assert os.path.join("docs", "cli", "codex.md") in erro and chamadas == []


def test_cli_desconhecida(projeto, chamadas, capsys):
    assert lancador.main(["--cli", "claude"]) == 2
    assert lancador.main(["--cli", "inexistente"]) == 2
    assert chamadas == []


# ---------------------------------------------------------------- preparar --cli

@pytest.mark.parametrize("cli,arquivo", [("codex", "AGENTS.md"), ("gemini", "GEMINI.md"),
                                         ("opencode", "AGENTS.md")])
def test_preparar_grava_instrucoes(projeto, capsys, cli, arquivo):
    assert lancador.main(["preparar", "--cli", cli]) == 0
    texto = (projeto / arquivo).read_text(encoding="utf-8")
    primeira = texto.splitlines()[0]
    assert lancador.marca() in primeira
    assert "{{PERSONA}}" not in texto and "Modelo de " not in texto
    assert "keep-coding-instructions" not in texto
    assert lancador.ler_persona()[:60] in texto
    capsys.readouterr()
    assert lancador.main(["preparar", "--cli", cli]) == 0
    assert "já em dia" in capsys.readouterr().out


def test_preparar_nao_sobrescreve_arquivo_alheio(projeto, capsys):
    (projeto / "AGENTS.md").write_text("minhas regras\n", encoding="utf-8")
    assert lancador.main(["preparar", "--cli", "codex"]) == 1
    assert "não vou sobrescrever" in capsys.readouterr().err
    assert (projeto / "AGENTS.md").read_text(encoding="utf-8") == "minhas regras\n"
    assert lancador.main(["preparar", "--cli", "codex", "--remover"]) == 1
    assert (projeto / "AGENTS.md").exists()


def test_preparar_nao_segue_link(projeto, tmp_path):
    alvo = tmp_path / "alvo.md"
    alvo.write_text("<!-- %s -->\n" % lancador.marca())
    (projeto / "AGENTS.md").symlink_to(alvo)
    assert lancador.main(["preparar", "--cli", "codex"]) == 1
    assert alvo.read_text() == "<!-- %s -->\n" % lancador.marca()


def test_preparar_remover_so_com_marca(projeto, capsys):
    lancador.main(["preparar", "--cli", "gemini"])
    assert lancador.main(["preparar", "--cli", "gemini", "--remover"]) == 0
    assert not (projeto / "GEMINI.md").exists()
    assert lancador.main(["preparar", "--cli", "gemini", "--remover"]) == 0
    assert "nada a remover" in capsys.readouterr().out


def test_preparar_dry_run(projeto, capsys):
    assert lancador.main(["preparar", "--cli", "codex", "--dry-run"]) == 0
    assert "[dry-run]" in capsys.readouterr().out
    assert not (projeto / "AGENTS.md").exists()
    lancador.main(["preparar", "--cli", "codex"])
    assert lancador.main(["preparar", "--cli", "codex", "--remover", "--dry-run"]) == 0
    assert (projeto / "AGENTS.md").exists()


def test_preparar_ollama_mostra_o_comando_e_nao_executa(projeto, tmp_path, monkeypatch, capsys):
    falsos = tmp_path / "falsos"
    falsos.mkdir()
    registro = tmp_path / "ollama.txt"
    escrever_falso(falsos, "ollama", 'echo "$@" >> "%s"\n' % registro)
    monkeypatch.setenv("PATH", str(falsos) + os.pathsep + os.environ["PATH"])
    assert lancador.main(["preparar", "--cli", "ollama"]) == 0
    saida = capsys.readouterr().out
    modelfile = projeto.parent / "home" / ".tutor" / "ollama" / "Modelfile"
    assert "ollama create %s -f %s" % (COMANDO, modelfile) in saida
    assert not registro.exists()
    assert list(projeto.iterdir()) == []              # nada no projeto
    texto = modelfile.read_text(encoding="utf-8")
    assert texto.startswith("# " + lancador.marca())
    assert 'SYSTEM """' in texto and "{{PERSONA}}" not in texto
    assert "Testado:" not in texto                      # cabeçalho do modelo removido
    assert lancador.main(["preparar", "--cli", "ollama", "--remover"]) == 0
    assert not modelfile.exists()
    assert "ollama rm" in capsys.readouterr().out


def test_persona_sem_frontmatter():
    persona = lancador.ler_persona()
    assert not persona.startswith("---") and "Regra de ouro" in persona


def test_preparar_cli_invalida(projeto):
    assert lancador.main(["preparar", "--cli", "claude"]) == 2
