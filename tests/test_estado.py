"""Testes do estado do aluno: domínio, revisão espaçada, dicas em sequência e segurança."""
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta

import pytest

import estado as E

T0 = datetime(2026, 3, 10, 9, 0, 0)


def novo():
    return E._vazio()


def reg(est, resultado, dicas=0, tema="laco-for", quando=T0, **kw):
    return E.registrar(est, tema, resultado, dicas, agora=quando, **kw)


# ---------------------------------------------------------------- domínio e intervalo

def test_acerto_sem_dica_sobe_dominio_e_escada():
    est = novo()
    vistos = []
    for i in range(7):
        r = reg(est, "acerto", quando=T0 + timedelta(days=i))
        vistos.append((r["dominio"], r["intervalo_dias"]))
    assert vistos == [(1, 1), (2, 3), (3, 7), (4, 14), (4, 30), (4, 60), (4, 60)]


def test_proxima_revisao_conta_a_partir_do_dia():
    est = novo()
    r = reg(est, "acerto")
    assert r["proxima_revisao"] == (T0.date() + timedelta(days=1)).isoformat()


def test_acerto_com_uma_dica_mantem_dominio_e_intervalo():
    est = novo()
    reg(est, "acerto")
    reg(est, "acerto")  # domínio 2, intervalo 3
    r = reg(est, "acerto", dicas=1)
    assert (r["dominio"], r["intervalo_dias"], r["resultado_efetivo"]) == (2, 3, "acerto")
    assert est["temas"]["laco-for"]["acertos_seguidos"] == 3


def test_acerto_com_duas_ou_mais_dicas_vira_parcial():
    est = novo()
    reg(est, "acerto")
    reg(est, "acerto")
    r = reg(est, "acerto", dicas=2)
    assert r["resultado_efetivo"] == "parcial"
    assert (r["dominio"], r["intervalo_dias"]) == (2, 1)
    assert est["temas"]["laco-for"]["acertos_seguidos"] == 0


def test_parcial_mantem_dominio_e_volta_intervalo_a_1():
    est = novo()
    for _ in range(3):
        reg(est, "acerto")
    r = reg(est, "parcial")
    assert (r["dominio"], r["intervalo_dias"]) == (3, 1)


def test_erro_desce_dominio_e_nunca_passa_de_zero():
    est = novo()
    reg(est, "acerto")
    reg(est, "acerto")
    assert reg(est, "erro")["dominio"] == 1
    assert reg(est, "erro")["dominio"] == 0
    r = reg(est, "erro")
    assert (r["dominio"], r["intervalo_dias"]) == (0, 1)


def test_tema_novo_com_uma_dica_agenda_revisao():
    est = novo()
    r = reg(est, "acerto", dicas=1)
    assert (r["dominio"], r["intervalo_dias"]) == (0, 1)


def test_contadores_e_historico_limitado():
    est = novo()
    for i in range(30):
        reg(est, "acerto", dicas=1, nota=f"n{i}")
    t = est["temas"]["laco-for"]
    assert t["tentativas"] == 30 and t["dicas_total"] == 30
    assert len(t["historico"]) == E.MAX_HISTORICO
    assert t["historico"][-1]["nota"] == "n29"


def test_nota_limitada_e_sem_quebra_de_linha():
    est = novo()
    reg(est, "erro", nota="linha1\nlinha2\r\n\x00" + "x" * 500)
    nota = est["temas"]["laco-for"]["historico"][-1]["nota"]
    assert "\n" not in nota and "\x00" not in nota and len(nota) <= E.MAX_NOTA


def test_teto_de_temas_descarta_o_mais_antigo():
    est = novo()
    for i in range(E.MAX_TEMAS):
        reg(est, "acerto", tema=f"t{i}", quando=T0 + timedelta(days=i))
    reg(est, "acerto", tema="recente", quando=T0 + timedelta(days=999))
    assert len(est["temas"]) == E.MAX_TEMAS
    assert "t0" not in est["temas"] and "recente" in est["temas"]


@pytest.mark.parametrize(
    "dominio,nivel", [(0, "alto"), (1, "alto"), (2, "medio"), (3, "baixo"), (4, "baixo")])
def test_nivel_de_apoio(dominio, nivel):
    assert E.nivel_de_apoio(dominio) == nivel


def test_apoio_tema_nunca_visto_e_alto():
    r = E.apoio(novo(), "async-await")
    assert (r["dominio"], r["nivel"], r["visto"]) == (0, "alto", False)
    assert "exemplo" in r["significado"]


def test_validacoes():
    est = novo()
    for ruim in ("", "Async", "-x", "a b", "a/b", "x" * 61, "../x", "ação"):
        with pytest.raises(E.ErroDeEstado):
            E.registrar(est, ruim, "acerto")
    with pytest.raises(E.ErroDeEstado):
        E.registrar(est, "ok", "talvez")
    with pytest.raises(E.ErroDeEstado):
        E.registrar(est, "ok", "acerto", origem="outra")
    with pytest.raises(E.ErroDeEstado):
        E.registrar(est, "ok", "acerto", dicas=-1)
    with pytest.raises(E.ErroDeEstado):
        E.dica(est, "ok", 5)
    assert est["temas"] == {}


# ---------------------------------------------------------------- vencidos e fracos

def test_vencidos_e_fracos():
    est = novo()
    reg(est, "acerto", tema="a", quando=T0)                       # dom 1, revisa dia+1
    for i in range(3):
        reg(est, "acerto", tema="b", quando=T0)                   # dom 3
    reg(est, "erro", tema="c", quando=T0 - timedelta(days=5))     # dom 0, venceu
    hoje = T0.date() + timedelta(days=1)
    venc = [v["tema"] for v in E.vencidos(est, hoje)]
    assert venc == ["c", "a"]  # mais atrasado primeiro; b só em 7 dias
    assert [f["tema"] for f in E.fracos(est)] == ["c", "a"]
    assert E.vencidos(est, hoje, limite=1)[0]["tema"] == "c"
    assert E.vencidos(est, T0.date() - timedelta(days=30)) == []


def test_revisar_completa_com_fracos():
    est = novo()
    reg(est, "erro", tema="velho", quando=T0 - timedelta(days=9))
    reg(est, "parcial", tema="fraco", quando=T0)
    itens = E.revisar(est, limite=5, hoje=T0.date())
    assert [(i["tema"], i["motivo"]) for i in itens] == [("velho", "vencido"),
                                                         ("fraco", "fraco")]


# ---------------------------------------------------------------- dicas em sequência

def test_primeiro_pedido_sem_aviso():
    r = E.dica(novo(), "recursao", 1, agora=T0)
    assert r["dicas_em_sequencia"] is False


def test_gatilho_dois_pedidos_em_menos_de_60s():
    est = novo()
    E.dica(est, "recursao", 1, agora=T0)
    r = E.dica(est, "recursao", 2, agora=T0 + timedelta(seconds=30))
    assert r["dicas_em_sequencia"] is True and "60" in r["motivo"]


def test_pedidos_espacados_nao_avisam_ate_o_terceiro():
    est = novo()
    assert not E.dica(est, "recursao", 1, agora=T0)["dicas_em_sequencia"]
    assert not E.dica(est, "recursao", 2, agora=T0 + timedelta(seconds=120))["dicas_em_sequencia"]
    r = E.dica(est, "recursao", 3, agora=T0 + timedelta(seconds=300))
    assert r["dicas_em_sequencia"] is True and "3" in r["motivo"]


def test_tres_pedidos_fora_da_janela_de_10_min_nao_avisam():
    est = novo()
    for k in range(3):
        r = E.dica(est, "recursao", 1, agora=T0 + timedelta(seconds=400 * k))
    assert r["dicas_em_sequencia"] is False


def test_registrar_zera_a_contagem_de_pedidos():
    est = novo()
    E.dica(est, "recursao", 1, agora=T0)
    E.dica(est, "recursao", 2, agora=T0 + timedelta(seconds=120))
    E.registrar(est, "recursao", "parcial", agora=T0 + timedelta(seconds=200))
    r = E.dica(est, "recursao", 2, agora=T0 + timedelta(seconds=250))
    assert r["dicas_em_sequencia"] is False


def test_pedidos_de_outro_tema_nao_se_misturam():
    est = novo()
    E.dica(est, "a", 1, agora=T0)
    assert not E.dica(est, "b", 1, agora=T0 + timedelta(seconds=5))["dicas_em_sequencia"]


# ---------------------------------------------------------------- disco

def test_ida_e_volta_no_disco(tmp_path):
    arq = tmp_path / "e.json"
    est = novo()
    reg(est, "acerto")
    E.salvar(est, str(arq))
    assert E.carregar(str(arq))["temas"]["laco-for"]["dominio"] == 1
    assert not [p for p in tmp_path.iterdir() if p.name.endswith(".tmp")]


def test_arquivo_ausente_da_estado_vazio(tmp_path):
    assert E.carregar(str(tmp_path / "nao-existe" / "e.json")) == novo()


def test_json_corrompido_e_renomeado(tmp_path):
    arq = tmp_path / "e.json"
    arq.write_text("{nao é json", encoding="utf-8")
    assert E.carregar(str(arq)) == novo()
    assert (tmp_path / "e.json.corrompido").read_text(encoding="utf-8") == "{nao é json"
    assert not arq.exists()


def test_raiz_que_nao_e_objeto_conta_como_corrompido(tmp_path):
    arq = tmp_path / "e.json"
    arq.write_text("[1, 2]", encoding="utf-8")
    assert E.carregar(str(arq)) == novo()
    assert (tmp_path / "e.json.corrompido").exists()


def test_dados_malucos_sao_saneados(tmp_path):
    arq = tmp_path / "e.json"
    arq.write_text(json.dumps({"temas": {
        "ok": {"dominio": 99, "intervalo_dias": "x", "historico": "lixo"},
        "Mau Slug": {"dominio": 1}, "lista": [1]}}), encoding="utf-8")
    est = E.carregar(str(arq))
    assert list(est["temas"]) == ["ok"]
    assert est["temas"]["ok"]["dominio"] == 4 and est["temas"]["ok"]["historico"] == []


def test_gravacao_atomica_nao_deixa_lixo_se_falhar(tmp_path, monkeypatch):
    arq = tmp_path / "e.json"
    est = novo()
    reg(est, "acerto")
    E.salvar(est, str(arq))
    antes = arq.read_text(encoding="utf-8")

    def quebra(*a, **k):
        raise OSError(5, "falha simulada")
    monkeypatch.setattr(E.os, "replace", quebra)
    reg(est, "erro")
    with pytest.raises(E.ErroDeEstado):
        E.salvar(est, str(arq))
    assert arq.read_text(encoding="utf-8") == antes
    assert not [p for p in tmp_path.iterdir() if p.name.endswith(".tmp")]


def test_arquivo_de_estado_link_simbolico_e_recusado(tmp_path):
    alvo = tmp_path / "alvo.json"
    alvo.write_text("{}", encoding="utf-8")
    elo = tmp_path / "e.json"
    elo.symlink_to(alvo)
    with pytest.raises(E.ErroDeEstado):
        E.carregar(str(elo))
    with pytest.raises(E.ErroDeEstado):
        E.salvar(novo(), str(elo))
    assert alvo.read_text(encoding="utf-8") == "{}"


def test_pasta_tutor_link_simbolico_e_recusada(projeto, monkeypatch):
    casa = projeto.parent / "home"
    alheia = projeto.parent / "alheia"
    alheia.mkdir()
    (casa / ".tutor").symlink_to(alheia, target_is_directory=True)
    monkeypatch.delenv("TUTTOR_ESTADO", raising=False)
    with pytest.raises(E.ErroDeEstado):
        E.salvar(novo())
    with pytest.raises(E.ErroDeEstado):
        E.carregar()
    assert list(alheia.iterdir()) == []


def test_caminho_padrao_usa_home(projeto, monkeypatch):
    monkeypatch.delenv("TUTTOR_ESTADO", raising=False)
    assert E.caminho() == str(projeto.parent / "home" / ".tutor" / "estado.json")


# ---------------------------------------------------------------- CLI de ponta a ponta

@pytest.fixture
def cli(tmp_path, scripts):
    arq = tmp_path / "pasta" / "estado.json"
    env = dict(os.environ, TUTTOR_ESTADO=str(arq), HOME=str(tmp_path / "home"))

    def rodar(*args):
        p = subprocess.run([sys.executable, str(scripts / "estado.py"), *args],
                           capture_output=True, text=True, env=env, timeout=30)
        return p.returncode, p.stdout, p.stderr
    rodar.arquivo = arq
    return rodar


def test_cli_fluxo_completo(cli):
    cod, out, _ = cli("apoio", "--tema", "laco-for")
    assert cod == 0 and "alto" in out and "ainda não visto" in out
    cod, out, _ = cli("registrar", "--tema", "laco-for", "--resultado", "acerto",
                      "--origem", "quiz", "--nota", "acertou de primeira", "--json")
    assert cod == 0 and json.loads(out)["dominio"] == 1
    cod, out, _ = cli("apoio", "--tema", "laco-for", "--json")
    assert json.loads(out)["nivel"] == "alto"
    cli("registrar", "--tema", "laco-for", "--resultado", "acerto")
    assert json.loads(cli("apoio", "--tema", "laco-for", "--json")[1])["nivel"] == "medio"
    cod, out, _ = cli("resumo", "--json")
    assert [i["tema"] for i in json.loads(out)] == ["laco-for"]
    cod, out, _ = cli("resumo")
    assert cod == 0 and "laco-for" in out
    cod, out, _ = cli("caminho")
    assert out.strip() == str(cli.arquivo)
    assert cli.arquivo.is_file()


def test_cli_dica_em_sequencia(cli):
    cod, out, _ = cli("dica", "--tema", "recursao", "--nivel", "1", "--json")
    assert cod == 0 and json.loads(out)["dicas_em_sequencia"] is False
    cod, out, _ = cli("dica", "--tema", "recursao", "--nivel", "2")
    assert cod == 0 and "dicas_em_sequencia" in out and "tentativa" in out


def test_cli_revisar_vazio_e_com_itens(cli):
    assert "Nada para revisar" in cli("revisar")[1]
    cli("registrar", "--tema", "x", "--resultado", "erro")
    cod, out, _ = cli("revisar", "--limite", "3", "--json")
    assert cod == 0 and json.loads(out)[0]["tema"] == "x"


@pytest.mark.parametrize("args", [
    ["registrar", "--tema", "Ruim", "--resultado", "acerto"],
    ["registrar", "--tema", "ok", "--resultado", "talvez"],
    ["dica", "--tema", "ok", "--nivel", "9"],
    ["dica", "--tema", "ok"],
    ["apoio", "--tema", "ok", "--opcao-estranha", "1"],
    ["--help"],
    [],
])
def test_cli_erros_sao_curtos_e_sem_traceback(cli, args):
    cod, out, err = cli(*args)
    assert cod != 0
    assert "Traceback" not in err and err.startswith("tuttor-estado:")


def test_cli_json_corrompido_recomeca(cli):
    cli.arquivo.parent.mkdir(parents=True)
    cli.arquivo.write_text("lixo", encoding="utf-8")
    cod, out, _ = cli("resumo", "--json")
    assert cod == 0 and json.loads(out) == []
    assert (cli.arquivo.parent / "estado.json.corrompido").exists()
