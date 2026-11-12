"""Confere as referências do tutor: comandos, frontmatter, rótulos proibidos e princípios."""
import re

import pytest

COMANDOS = ("trilha", "praticar", "dica", "duvida", "revisar", "quiz", "material", "fontes",
            "fechar", "perfil", "calibrar")
PROIBIDOS = ("preferências de ensino",
             "estilo de aprendizagem", "estilos de aprendizagem", "visual/auditivo",
             "visual, auditivo", "learning style", "vark")
SECOES_ANTIGAS = ("## Como aprende (observado)", "## Preferências de ensino")


def partir(texto):
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", texto, re.S)
    assert m, "sem frontmatter"
    campos = {}
    for linha in m.group(1).splitlines():
        k, _, v = linha.partition(":")
        campos[k.strip()] = v.strip()
    return campos, m.group(2)


@pytest.fixture
def refs(skill):
    return skill / "references"


@pytest.mark.parametrize("cmd", COMANDOS)
def test_comando_tem_frontmatter_valido_e_sem_arguments(refs, cmd):
    campos, corpo = partir((refs / f"{cmd}.md").read_text(encoding="utf-8"))
    assert set(campos) == {"name", "description", "argument-hint"}
    assert campos["name"] == cmd
    assert 10 <= len(campos["description"]) <= 200
    assert "$ARGUMENTS" not in corpo and "$ARGUMENTS" not in "".join(campos.values())
    if cmd != "perfil":  # o /perfil conversa sem usar o texto do comando
        assert "o pedido do aluno (o texto que veio com o comando)" in corpo


def test_persona_e_perfil_sem_rotulos_de_estilo(refs, skill):
    for arq in (refs / "persona.md", skill / "assets" / "perfil-modelo.md"):
        texto = arq.read_text(encoding="utf-8")
        baixo = texto.lower()
        for termo in PROIBIDOS:
            assert termo not in baixo, f"{arq.name}: {termo}"
        for secao in SECOES_ANTIGAS:
            assert secao not in texto, f"{arq.name}: {secao}"


def test_perfil_modelo_tem_as_secoes_novas(skill):
    texto = (skill / "assets" / "perfil-modelo.md").read_text(encoding="utf-8")
    for secao in ("Contexto", "Objetivos", "Conhecimento prévio por tema",
                  "Padrões de erro recorrentes", "Como pede ajuda (observado)",
                  "Pontos fortes", "A reforçar"):
        assert f"## {secao}" in texto


def test_persona_e_enxuta_e_independe_de_linguagem(refs):
    texto = (refs / "persona.md").read_text(encoding="utf-8")
    assert len(texto.splitlines()) <= 120
    assert "C#" not in texto and ".csproj" not in texto
    assert "dominio-" in texto and "tuttor-estado apoio" in texto


def test_pedagogia_cobre_o_essencial(refs):
    texto = (refs / "pedagogia.md").read_text(encoding="utf-8")
    for trecho in ("Parsons", "PRIMM", "dicas_em_sequencia", "tuttor-estado", "disputad",
                   "docs/pesquisa/principios-e-recursos.md"):
        assert trecho in texto


def test_todo_principio_citado_existe(raiz, refs, skill):
    tabela = (raiz / "docs" / "pesquisa" / "principios-e-recursos.md").read_text(encoding="utf-8")
    existentes = set(re.findall(r"^\| (P\d+) \|", tabela, re.M))
    assert len(existentes) == 17
    arquivos = list(refs.glob("*.md")) + [skill / "assets" / "perfil-modelo.md"]
    citados = set()
    for arq in arquivos:
        citados |= set(re.findall(r"\bP\d+\b", arq.read_text(encoding="utf-8")))
    assert citados, "nenhum princípio citado"
    assert citados <= existentes, citados - existentes
