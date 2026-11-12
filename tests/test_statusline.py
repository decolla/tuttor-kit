"""Testes da status line: stdin simulado, JSON inválido, sem .tutor/, NO_COLOR, links, largura."""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time

import pytest

import estado
import statusline

ANSI = re.compile(r"\x1b\[[0-9;]*m")


@pytest.fixture(autouse=True)
def ambiente(monkeypatch, projeto):
    for var in ("NO_COLOR", "TERM", "COLUMNS", "LC_ALL", "LC_CTYPE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("LANG", "pt_BR.UTF-8")
    monkeypatch.setenv("TUTTOR_ESTADO", str(projeto.parent / "home" / ".tutor" / "estado.json"))
    return projeto


def entrada(projeto):
    return {"workspace": {"project_dir": str(projeto), "current_dir": str(projeto)},
            "model": {"display_name": "Opus"}}


def rodar(stdin, *args, env=None):
    ambiente = dict(os.environ)
    ambiente.update(env or {})
    return subprocess.run([sys.executable, statusline.__file__, *args], input=stdin,
                          capture_output=True, text=True, encoding="utf-8", env=ambiente,
                          timeout=20)


def tutor_com_trilha(projeto, texto="# Trilha: Listas em C#\nProgresso: Estudar [x], Praticar [x],"
                                    " Checkpoint [ ], Fechar [ ]\n"):
    (projeto / ".tutor" / "trilhas").mkdir(parents=True)
    (projeto / ".tutor" / "trilhas" / "listas.md").write_text(texto, encoding="utf-8")


def grava_vigia(projeto, tags, dias=0):
    (projeto / ".tutor").mkdir(exist_ok=True)
    linhas = [json.dumps({"ts": time.time() - dias * 86400, "sev": "erro", "tag": t})
              for t in tags]
    (projeto / ".tutor" / "vigia.jsonl").write_text("\n".join(linhas) + "\n", encoding="utf-8")


def test_nome_vem_de_projeto_env_ou_da_pasta_da_skill(tmp_path, monkeypatch):
    esperado = os.path.basename(os.path.dirname(os.path.dirname(statusline.__file__)))
    env = os.path.join(statusline._raiz_do_kit(), "projeto.env")
    if os.path.isfile(env):
        valor = re.search(r"^NOME=(\S+)", open(env, encoding="utf-8").read(), re.M).group(1)
        assert statusline.nome_do_kit() == valor
    else:
        assert statusline.nome_do_kit() == esperado


def test_nome_de_projeto_env_tem_prioridade(tmp_path):
    copia = tmp_path / "kit"
    shutil.copytree(os.path.dirname(statusline.__file__),
                    copia / "skills" / "minha-skill" / "scripts")
    (copia / "projeto.env").write_text("NOME=meu-nome\nCOMANDO=x\n", encoding="utf-8")
    script = copia / "skills" / "minha-skill" / "scripts" / "statusline.py"
    r = subprocess.run([sys.executable, str(script)], input="{}", capture_output=True,
                       text=True, encoding="utf-8", env=dict(os.environ, NO_COLOR="1"))
    assert "meu-nome" in r.stdout
    (copia / "projeto.env").unlink()
    r = subprocess.run([sys.executable, str(script)], input="{}", capture_output=True,
                       text=True, encoding="utf-8", env=dict(os.environ, NO_COLOR="1"))
    assert "minha-skill" in r.stdout


def test_sem_tutor_so_o_nome(projeto):
    r = rodar(json.dumps(entrada(projeto)), env={"NO_COLOR": "1"})
    assert r.returncode == 0
    assert r.stdout.count("\n") == 1
    assert statusline.nome_do_kit() in r.stdout
    assert "trilha" not in r.stdout and "revisar" not in r.stdout


@pytest.mark.parametrize("stdin", ["", "   \n", "isto não é json", "{", "[1,2]", "null", "42",
                                   '{"workspace": 5, "cwd": 7}'])
def test_entrada_ruim_nao_falha(stdin):
    r = rodar(stdin, env={"NO_COLOR": "1"})
    assert r.returncode == 0
    assert statusline.nome_do_kit() in r.stdout
    assert r.stdout.count("\n") == 1 and r.stderr == ""


def test_stdin_fechado_nao_falha():
    r = subprocess.run([sys.executable, statusline.__file__], stdin=subprocess.DEVNULL,
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0 and statusline.nome_do_kit() in r.stdout


def test_trilha_e_progresso(projeto):
    tutor_com_trilha(projeto)
    linha = statusline.montar(entrada(projeto))
    assert "trilha Listas em C# 2/4" in linha


def test_erro_recorrente_so_com_dois_ou_mais_e_14_dias(projeto):
    grava_vigia(projeto, ["null-ref", "null-ref", "loop"])
    assert "erro: null-ref 2x" in statusline.montar(entrada(projeto))
    grava_vigia(projeto, ["null-ref"])
    assert "erro:" not in statusline.montar(entrada(projeto))
    grava_vigia(projeto, ["null-ref"] * 3, dias=20)
    assert "erro:" not in statusline.montar(entrada(projeto))


def test_vigia_com_linhas_ruins_e_ignorado(projeto):
    (projeto / ".tutor").mkdir()
    bom = json.dumps({"ts": time.time(), "sev": "erro", "tag": "x"})
    (projeto / ".tutor" / "vigia.jsonl").write_text(
        "lixo\n[]\n" + bom + "\n" + bom + '\n{"ts":"a","sev":"erro","tag":"y"}\n',
        encoding="utf-8")
    assert "erro: x 2x" in statusline.montar(entrada(projeto))


def test_mascote_alerta_com_tres_erros(projeto):
    import mascote
    grava_vigia(projeto, ["a", "a", "a"])
    assert statusline.montar(entrada(projeto)).startswith(
        mascote.mini("alerta", ascii=False, cor=True))
    grava_vigia(projeto, ["a", "a"])
    assert statusline.montar(entrada(projeto)).startswith(
        mascote.mini("atento", ascii=False, cor=True))


def test_revisoes_vencidas(projeto):
    est = estado.carregar()
    estado.registrar(est, "listas", "acerto")
    est["temas"]["listas"]["proxima_revisao"] = "2000-01-01"
    estado.salvar(est)
    assert "revisar 1" in statusline.montar(entrada(projeto))


def test_no_color_sem_ansi(projeto):
    tutor_com_trilha(projeto)
    r = rodar(json.dumps(entrada(projeto)), env={"NO_COLOR": "1"})
    assert not ANSI.search(r.stdout) and "Listas" in r.stdout
    r = rodar(json.dumps(entrada(projeto)), env={"TERM": "dumb"})
    assert not ANSI.search(r.stdout)


def test_com_cor_por_padrao(projeto):
    r = rodar(json.dumps(entrada(projeto)), env={"TERM": "xterm"})
    assert ANSI.search(r.stdout)


def test_sem_mascote(projeto):
    r = rodar(json.dumps(entrada(projeto)), "--sem-mascote", env={"NO_COLOR": "1"})
    assert r.stdout.strip() == statusline.nome_do_kit()


def test_ascii_em_locale_sem_utf8(projeto):
    tutor_com_trilha(projeto)
    r = rodar(json.dumps(entrada(projeto)),
              env={"NO_COLOR": "1", "LC_ALL": "C", "LANG": "C"})
    assert r.stdout.isascii() and " | " in r.stdout


def test_corta_com_reticencias_na_largura(projeto, monkeypatch):
    tutor_com_trilha(projeto)
    monkeypatch.setenv("COLUMNS", "30")
    monkeypatch.setenv("NO_COLOR", "1")
    linha = statusline.montar(entrada(projeto))
    assert len(linha) <= 29 and linha.endswith("…")
    monkeypatch.setenv("COLUMNS", "200")
    assert not statusline.montar(entrada(projeto)).endswith("…")


def test_sem_columns_usa_teto_de_100(projeto, monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    tutor_com_trilha(projeto, "# " + "x" * 500 + "\n")
    assert len(statusline.montar(entrada(projeto))) <= 100
    assert statusline._largura_disponivel() == 100
    monkeypatch.setenv("COLUMNS", "abc")
    assert statusline._largura_disponivel() == 100


def test_largura_minuscula_nao_estoura(projeto, monkeypatch):
    monkeypatch.setenv("COLUMNS", "1")
    assert isinstance(statusline.montar(entrada(projeto)), str)
    monkeypatch.setenv("COLUMNS", "0")
    assert statusline.montar(entrada(projeto))


def test_nao_segue_link_simbolico_em_tutor(projeto, tmp_path):
    fora = tmp_path / "fora"
    fora.mkdir()
    (fora / "t.md").write_text("# Trilha: SEGREDO\n", encoding="utf-8")
    (projeto / ".tutor").mkdir()
    (projeto / ".tutor" / "trilhas").symlink_to(fora)
    assert "SEGREDO" not in statusline.montar(entrada(projeto))
    (projeto / ".tutor" / "trilhas").unlink()
    (projeto / ".tutor" / "trilhas").mkdir()
    (projeto / ".tutor" / "trilhas" / "a.md").symlink_to(fora / "t.md")
    assert "SEGREDO" not in statusline.montar(entrada(projeto))
    (fora / "v.jsonl").write_text(
        (json.dumps({"ts": time.time(), "sev": "erro", "tag": "vazou"}) + "\n") * 3,
        encoding="utf-8")
    (projeto / ".tutor" / "vigia.jsonl").symlink_to(fora / "v.jsonl")
    assert "vazou" not in statusline.montar(entrada(projeto))


def test_tutor_que_e_link_e_ignorado(projeto, tmp_path):
    fora = tmp_path / "fora" / "trilhas"
    fora.mkdir(parents=True)
    (fora / "a.md").write_text("# Trilha: SEGREDO\n", encoding="utf-8")
    (projeto / ".tutor").symlink_to(fora.parent)
    assert "SEGREDO" not in statusline.montar(entrada(projeto))


def test_conteudo_do_projeto_nao_injeta_escape(projeto):
    tutor_com_trilha(projeto, "# Trilha: Ola\x1b]0;titulo\x07\x1b[31mvermelho\nProgresso: A [x]\n")
    r = rodar(json.dumps(entrada(projeto)), env={"NO_COLOR": "1"})
    assert "\x1b" not in r.stdout and "\x07" not in r.stdout


def test_arquivo_enorme_e_lido_com_limite(projeto):
    (projeto / ".tutor").mkdir()
    (projeto / ".tutor" / "vigia.jsonl").write_text("x" * 5_000_000, encoding="utf-8")
    inicio = time.time()
    statusline.montar(entrada(projeto))
    assert time.time() - inicio < 1


def test_pasta_vem_do_cwd_se_nao_ha_workspace(projeto):
    tutor_com_trilha(projeto)
    assert "Listas" in statusline.montar({"cwd": str(projeto)})
    assert "Listas" in statusline.montar({})   # cai no diretório atual (o projeto)


def test_peca_com_defeito_nao_derruba_a_linha(projeto, monkeypatch):
    tutor_com_trilha(projeto)
    monkeypatch.setattr(estado, "carregar", lambda *a, **k: 1 / 0)
    linha = statusline.montar(entrada(projeto))
    assert "Listas" in linha and "revisar" not in linha


def test_main_nunca_falha_mesmo_se_montar_estoura(monkeypatch, capsys):
    monkeypatch.setattr(statusline, "montar", lambda *a, **k: 1 / 0)
    monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))
    assert statusline.main([]) == 0
    assert statusline.nome_do_kit() in capsys.readouterr().out


def test_rapido(projeto):
    tutor_com_trilha(projeto)
    grava_vigia(projeto, ["a"] * 500)
    inicio = time.time()
    r = rodar(json.dumps(entrada(projeto)))
    assert r.returncode == 0
    assert time.time() - inicio < 1.5   # inclui subir o interpretador
