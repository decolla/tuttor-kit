"""Testes do mascote Lume: dimensões, ASCII, estados distintos, cor, largura e CLI."""
import re
import subprocess
import sys

import pytest

import mascote

ANSI = re.compile(r"\x1b\[")
ESTADOS = mascote.ESTADOS
MODOS = [False, True]   # ascii=


@pytest.fixture(autouse=True)
def ambiente_limpo(monkeypatch):
    for var in ("NO_COLOR", "TERM", "COLUMNS", "LC_ALL", "LC_CTYPE", "LANG"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("LANG", "pt_BR.UTF-8")


def sem_ansi(texto):
    return re.sub(r"\x1b\[[0-9;]*m", "", texto)


def test_identidade():
    assert mascote.NOME == "Lume"
    assert ESTADOS == ("atento", "pensando", "comemorando", "alerta")


@pytest.mark.parametrize("estado", ESTADOS)
@pytest.mark.parametrize("modo_ascii", MODOS)
@pytest.mark.parametrize("cor", [False, True])
def test_dimensoes_em_colunas(estado, modo_ascii, cor):
    saida = mascote.desenhar(estado, ascii=modo_ascii, cor=cor, largura=80)
    linhas = sem_ansi(saida).split("\n")
    assert 1 <= len(linhas) <= 6
    assert max(mascote.colunas(linha) for linha in linhas) <= 14


@pytest.mark.parametrize("estado", ESTADOS)
def test_ascii_e_ascii_puro(estado):
    saida = mascote.desenhar(estado, ascii=True, cor=False, largura=80, fala="olá")
    assert saida.replace("á", "a").isascii()
    assert mascote.mini(estado, ascii=True, cor=False).isascii()
    assert mascote.desenhar(estado, ascii=True, cor=False, largura=80).isascii()


@pytest.mark.parametrize("estado", ESTADOS)
def test_unicode_sem_emoji_nem_largura_dupla(estado):
    saida = mascote.desenhar(estado, ascii=False, cor=False, largura=80)
    for c in saida:
        assert mascote.colunas(c) == 1 or c == "\n"
        assert not (0x1F000 <= ord(c) <= 0x1FFFF)


@pytest.mark.parametrize("modo_ascii", MODOS)
def test_quatro_estados_sao_diferentes(modo_ascii):
    artes = {e: mascote.desenhar(e, ascii=modo_ascii, cor=False, largura=80) for e in ESTADOS}
    assert len(set(artes.values())) == 4
    minis = {e: mascote.mini(e, ascii=modo_ascii, cor=False) for e in ESTADOS}
    assert len(set(minis.values())) == 4


@pytest.mark.parametrize("estado", ESTADOS)
@pytest.mark.parametrize("modo_ascii", MODOS)
def test_mini_uma_linha_ate_6_colunas(estado, modo_ascii):
    for cor in (False, True):
        m = mascote.mini(estado, ascii=modo_ascii, cor=cor)
        assert "\n" not in m
        assert mascote.colunas(sem_ansi(m)) <= 6


def test_cor_e_so_reforco_a_forma_ja_distingue():
    # sem nenhuma cor os quatro continuam diferentes; com cor o texto visível é o mesmo
    for modo in MODOS:
        for e in ESTADOS:
            com = mascote.desenhar(e, ascii=modo, cor=True, largura=80)
            sem = mascote.desenhar(e, ascii=modo, cor=False, largura=80)
            assert ANSI.search(com) and not ANSI.search(sem)
            assert sem_ansi(com) == sem


def test_no_color_vale_qualquer_valor_nao_vazio(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    assert mascote.sem_cor() is True
    monkeypatch.setenv("NO_COLOR", "0")
    assert mascote.sem_cor() is True
    # padrão da detecção: sem ANSI
    for e in ESTADOS:
        assert not ANSI.search(mascote.desenhar(e, largura=80, fala="oi"))
        assert not ANSI.search(mascote.mini(e))


def test_no_color_vazio_nao_conta(monkeypatch):
    class Terminal:
        def isatty(self):
            return True
    monkeypatch.setattr(sys, "stdout", Terminal())
    monkeypatch.setenv("NO_COLOR", "")
    assert mascote.sem_cor() is False


def test_term_dumb_sem_cor_e_ascii(monkeypatch):
    class Terminal:
        def isatty(self):
            return True
    monkeypatch.setattr(sys, "stdout", Terminal())
    monkeypatch.setenv("TERM", "dumb")
    assert mascote.sem_cor() is True
    assert mascote.so_ascii() is True
    assert not ANSI.search(mascote.desenhar("alerta", largura=80))


def test_saida_que_nao_e_terminal_sem_cor(monkeypatch):
    class Arquivo:
        def isatty(self):
            return False
    monkeypatch.setattr(sys, "stdout", Arquivo())
    assert mascote.sem_cor() is True


def test_terminal_com_cor_quando_nada_impede(monkeypatch):
    class Terminal:
        def isatty(self):
            return True
    monkeypatch.setattr(sys, "stdout", Terminal())
    monkeypatch.setenv("TERM", "xterm-256color")
    assert mascote.sem_cor() is False
    assert ANSI.search(mascote.desenhar("atento", largura=80, ascii=False))


def test_parametro_explicito_vence_a_deteccao(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("LANG", "C")
    assert ANSI.search(mascote.desenhar("alerta", cor=True, ascii=False, largura=80))
    assert not mascote.desenhar("alerta", cor=True, ascii=False, largura=80).isascii()


@pytest.mark.parametrize("locale,esperado", [
    ("pt_BR.UTF-8", False), ("C.UTF-8", False), ("en_US.utf8", False),
    ("C", True), ("POSIX", True), ("pt_BR.ISO-8859-1", True), ("ja_JP.UTF-8", True),
])
def test_locale_decide_ascii(monkeypatch, locale, esperado):
    monkeypatch.delenv("LANG", raising=False)
    monkeypatch.setenv("LC_ALL", locale)
    assert mascote.so_ascii() is esperado


def test_locale_sem_utf8_cai_para_ascii(monkeypatch):
    monkeypatch.setenv("LANG", "C")
    assert mascote.desenhar("atento", largura=80, cor=False).isascii()


def test_fala_a_direita_quando_cabe():
    saida = mascote.desenhar("atento", ascii=True, cor=False, largura=80, fala="Oi, vamos?")
    linhas = saida.split("\n")
    assert len(linhas) == 6
    assert any("Oi, vamos?" in linha for linha in linhas)
    assert mascote.desenhar("atento", ascii=True, cor=False, largura=80).count("\n") == 5


def test_largura_estreita_manda_fala_para_baixo():
    fala = "Qual é o próximo passo que você acha que falta nesta função?"
    saida = mascote.desenhar("atento", ascii=False, cor=False, largura=30, fala=fala)
    linhas = saida.split("\n")
    assert len(linhas) > 6
    assert all(mascote.colunas(linha) <= 30 for linha in linhas)
    assert " ".join(linha.strip() for linha in linhas[6:]) == fala


def test_largura_menor_que_arte_cai_para_mini():
    saida = mascote.desenhar("alerta", ascii=False, cor=False, largura=10)
    assert saida == mascote.mini("alerta", ascii=False, cor=False)
    com_fala = mascote.desenhar("alerta", ascii=True, cor=False, largura=10, fala="cuidado")
    assert "\n" not in com_fala and "cuidado" in com_fala


def test_largura_exata_da_arte_sem_fala_nao_vira_mini():
    saida = mascote.desenhar("atento", ascii=True, cor=False, largura=14)
    assert saida.count("\n") == 5


def test_fala_nao_carrega_controle_nem_escape():
    saida = mascote.desenhar("atento", ascii=True, cor=False, largura=80,
                             fala="oi\x1b[31mvermelho\x07\n\nfim")
    assert "\x1b" not in saida and "\x07" not in saida
    assert saida.count("\n") == 5


@pytest.mark.parametrize("estado", ["", "xyz", None, 42, "ATENTO ", "Alerta"])
def test_estado_desconhecido_nao_estoura(estado):
    esperado = "alerta" if estado == "Alerta" else "atento"
    assert (mascote.desenhar(estado, ascii=True, cor=False, largura=80)
            == mascote.desenhar(esperado, ascii=True, cor=False, largura=80))
    assert mascote.mini(estado, ascii=True, cor=False) == mascote.mini(
        esperado, ascii=True, cor=False)


def test_largura_invalida_do_ambiente_nao_estoura(monkeypatch):
    monkeypatch.setenv("COLUMNS", "abc")
    assert mascote.desenhar("atento", cor=False)


# ---------------------------------------------------------------- CLI

def cli(*args, env=None):
    import os
    ambiente = {k: v for k, v in os.environ.items()
                if k not in ("NO_COLOR", "TERM", "COLUMNS", "LC_ALL", "LC_CTYPE", "LANG")}
    ambiente["LANG"] = "pt_BR.UTF-8"
    ambiente["PYTHONIOENCODING"] = "utf-8"
    ambiente.update(env or {})
    return subprocess.run([sys.executable, mascote.__file__, *args], capture_output=True,
                          text=True, encoding="utf-8", env=ambiente, timeout=20)


def test_cli_padrao_sem_cor_porque_nao_e_terminal():
    r = cli()
    assert r.returncode == 0 and not ANSI.search(r.stdout)
    assert r.stdout.count("\n") == 6


def test_cli_ascii_e_estado():
    r = cli("alerta", "--ascii")
    assert r.returncode == 0 and r.stdout.isascii()
    assert r.stdout.strip("\n") == mascote.desenhar("alerta", ascii=True, cor=False, largura=80)


def test_cli_mini_e_fala():
    r = cli("comemorando", "--mini", "--ascii", "--fala", "trilha concluída")
    esperado = mascote.mini("comemorando", ascii=True, cor=False) + " trilha concluída"
    assert r.stdout.strip() == esperado


def test_cli_fala_larga_vai_para_baixo():
    r = cli("atento", "--ascii", "--largura", "20", "--fala", "uma fala bem comprida aqui")
    assert len(r.stdout.strip("\n").split("\n")) > 6


@pytest.mark.parametrize("extra", [[], ["--ascii"]])
def test_cli_todos_mostra_nomes_e_quatro_estados(extra):
    r = cli("--todos", *extra, "--largura", "100")
    assert r.returncode == 0
    for e in ESTADOS:
        assert e in r.stdout
    assert not ANSI.search(r.stdout)


def test_cli_todos_em_sequencia_quando_estreito():
    r = cli("--todos", "--ascii", "--largura", "40")
    assert r.returncode == 0
    nomes = [linha for linha in r.stdout.split("\n") if linha in ESTADOS]
    assert nomes == list(ESTADOS)


def test_cli_todos_mini():
    r = cli("--todos", "--mini", "--ascii")
    assert len(r.stdout.strip().split("\n")) == 4


def test_cli_no_color_e_term_dumb():
    r = cli("alerta", env={"NO_COLOR": "1"})
    assert not ANSI.search(r.stdout)
    r = cli("alerta", env={"TERM": "dumb"})
    assert not ANSI.search(r.stdout) and r.stdout.isascii()


def test_cli_locale_c_cai_para_ascii():
    r = cli("atento", env={"LANG": "C"})
    assert r.returncode == 0 and r.stdout.isascii()


def test_cli_estado_desconhecido_nao_estoura():
    r = cli("nao-existe", "--ascii")
    assert r.returncode == 0
    assert r.stdout == cli("atento", "--ascii").stdout
