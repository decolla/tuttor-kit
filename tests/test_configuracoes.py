"""Testes de configuracoes.py: JSON para --settings, caminhos com espaço e acento, sem escrita."""
import json
import os
import shutil
import subprocess
import sys

import pytest

import configuracoes

SCRIPT = os.path.abspath(configuracoes.__file__)


def saida_json(*args, script=SCRIPT, cwd=None):
    r = subprocess.run([sys.executable, script, *args], capture_output=True, text=True,
                       encoding="utf-8", cwd=cwd, timeout=20)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_json_valido_com_as_chaves_esperadas():
    cfg = saida_json()
    assert set(cfg) == {"statusLine", "spinnerVerbs", "spinnerTipsOverride", "permissions"}


def test_status_line_no_formato_da_doc():
    sl = saida_json()["statusLine"]
    assert sl["type"] == "command"
    assert set(sl) <= {"type", "command", "padding", "refreshInterval", "hideVimModeIndicator"}
    assert "statusline.py" in sl["command"]


def test_spinner_formato_da_doc():
    cfg = saida_json()
    sv = cfg["spinnerVerbs"]
    assert sv["mode"] in ("append", "replace")
    assert sv["verbs"] and all(isinstance(v, str) and v for v in sv["verbs"])
    st = cfg["spinnerTipsOverride"]
    assert set(st) <= {"tips", "tipsFile", "label", "excludeDefault"}
    assert len(st["label"]) <= 40
    assert 0 < len(st["tips"]) <= 200
    for t in st["tips"]:
        assert isinstance(t, str) and "\n" not in t and len(t) <= 500
    assert any("/dica" in t for t in st["tips"])


def test_permissoes_minimas_e_exatas():
    regras = saida_json()["permissions"]["allow"]
    assert set(regras) == set(configuracoes.regras_de_permissao())
    assert "Bash(tuttor-vigia --resumo)" in regras
    assert "Bash(tuttor-vigia --leituras)" in regras
    assert "Bash(tuttor-estado registrar *)" in regras
    for r in regras:
        assert (r.startswith("Bash(tuttor-estado ") or r.startswith("Bash(tuttor-vigia --")
                or (r.startswith("Read(//") and r.endswith("/skills/tuttor-kit/**)")))
        assert r not in ("Bash", "Bash(*)", "Bash(tuttor-estado *)")
        assert "tuttor-vigia *" not in r and "tuttor-vigia --* " not in r
    # o vigia nunca tem curinga: `tuttor-vigia --web`, `--read` etc. continuam pedindo permissão
    assert all("*" not in r for r in regras if "vigia" in r)


def test_sem_mascote_tira_o_que_e_do_mascote():
    com = saida_json()
    sem = saida_json("--sem-mascote")
    assert "--sem-mascote" in sem["statusLine"]["command"]
    assert "--sem-mascote" not in com["statusLine"]["command"]
    assert "Iluminando" in com["spinnerVerbs"]["verbs"]
    assert "Iluminando" not in sem["spinnerVerbs"]["verbs"]
    assert not any("facho" in v.lower() for v in sem["spinnerVerbs"]["verbs"])
    assert sem["permissions"] == com["permissions"]


def test_nao_grava_nada_em_disco(tmp_path):
    antes = set(os.listdir(tmp_path))
    saida_json(cwd=str(tmp_path))
    assert set(os.listdir(tmp_path)) == antes


def test_caminho_absoluto_do_script_real():
    comando = saida_json()["statusLine"]["command"]
    esperado = os.path.join(os.path.dirname(SCRIPT), "statusline.py")
    assert os.path.isfile(esperado)
    assert esperado in comando or esperado.replace("'", "'\"'\"'") in comando


@pytest.mark.parametrize("pasta", ["Meu Código", "pasta com espaço e acento ção", "O'Brien ç"])
def test_comando_funciona_em_pasta_com_espaco_e_acento(tmp_path, pasta):
    copia = tmp_path / pasta / "skills" / "tuttor-kit"
    shutil.copytree(os.path.dirname(SCRIPT), copia / "scripts",
                    ignore=shutil.ignore_patterns("__pycache__"))
    cfg = saida_json(script=str(copia / "scripts" / "configuracoes.py"))
    comando = cfg["statusLine"]["command"]
    assert str(copia / "scripts" / "statusline.py") not in comando.split(" ")[0]
    r = subprocess.run(comando, shell=True, input=json.dumps({"cwd": str(tmp_path)}),
                       capture_output=True, text=True, encoding="utf-8", timeout=20,
                       env=dict(os.environ, NO_COLOR="1"))
    assert r.returncode == 0, r.stderr
    assert r.stderr == ""
    assert "tuttor-kit" in r.stdout    # nome da pasta da skill, achado em tempo de execução


def test_comando_do_kit_vem_de_projeto_env(tmp_path):
    copia = tmp_path / "kit"
    shutil.copytree(os.path.dirname(SCRIPT), copia / "skills" / "x" / "scripts")
    (copia / "projeto.env").write_text("NOME=x\nCOMANDO=lume\n", encoding="utf-8")
    cfg = saida_json(script=str(copia / "skills" / "x" / "scripts" / "configuracoes.py"))
    assert "Bash(lume-vigia --resumo)" in cfg["permissions"]["allow"]
    assert not any("tuttor" in r for r in cfg["permissions"]["allow"])


def test_sem_caminho_pessoal_fixo_no_codigo():
    texto = open(SCRIPT, encoding="utf-8").read()
    assert "/" + "home" + "/" not in texto
