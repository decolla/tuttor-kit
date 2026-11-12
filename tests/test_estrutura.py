"""Estrutura de plugin e Agent Skill: gerador em dia, manifestos, atalhos, hooks, nomes."""
import json
import re
import shutil
import subprocess
import sys

import pytest

COMANDOS = ("trilha", "praticar", "dica", "duvida", "revisar", "quiz", "material", "fontes",
            "fechar", "perfil", "calibrar")
CAMPOS_DO_ENV = ("NOME", "COMANDO", "VERSAO", "MASCOTE", "DONO", "DESCRICAO")


def ler_env(raiz):
    dados = {}
    for linha in (raiz / "projeto.env").read_text(encoding="utf-8").splitlines():
        if "=" in linha and not linha.lstrip().startswith("#"):
            k, v = linha.split("=", 1)
            dados[k.strip()] = v.strip()
    return dados


def rodar_gerador(raiz, *args):
    return subprocess.run([sys.executable, str(raiz / "tools" / "gerar.py"), "--raiz", str(raiz),
                           *args], capture_output=True, text=True)


def frontmatter(texto):
    m = re.match(r"^---\n(.*?)\n---\n", texto, re.S)
    assert m, "sem frontmatter"
    campos = {}
    for linha in m.group(1).splitlines():
        k, _, v = linha.partition(":")
        v = v.strip()
        campos[k.strip()] = json.loads(v) if v.startswith('"') else v
    return campos


def test_projeto_env_tem_todos_os_campos(raiz):
    env = ler_env(raiz)
    for campo in CAMPOS_DO_ENV:
        assert env.get(campo), campo


def test_gerador_confere_no_repositorio(raiz):
    r = rodar_gerador(raiz, "--conferir")
    assert r.returncode == 0, r.stderr


def test_gerador_conferir_nao_escreve_e_aponta_o_atrasado(raiz, tmp_path):
    copia = copiar_kit(raiz, tmp_path)
    alvo = copia / ".claude-plugin" / "plugin.json"
    alvo.write_text("{}\n", encoding="utf-8")
    r = rodar_gerador(copia, "--conferir")
    assert r.returncode == 1
    assert "plugin.json" in r.stderr
    assert alvo.read_text(encoding="utf-8") == "{}\n"


def test_manifestos_sao_json_valido_com_campos_e_versao(raiz):
    env = ler_env(raiz)
    plugin = json.loads((raiz / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert plugin["name"] == env["NOME"]
    assert plugin["version"] == env["VERSAO"]
    assert plugin["author"] == {"name": env["DONO"]}
    mercado = json.loads((raiz / ".claude-plugin" / "marketplace.json").read_text("utf-8"))
    assert mercado["name"] and mercado["owner"] == {"name": env["DONO"]}
    assert mercado["plugins"] and all(p["name"] and p["source"] for p in mercado["plugins"])
    assert mercado["plugins"][0]["name"] == plugin["name"]
    kit = json.loads((raiz / "skills" / env["NOME"] / "assets" / "kit.json").read_text("utf-8"))
    assert kit == {"nome": env["NOME"], "comando": env["COMANDO"], "versao": env["VERSAO"],
                   "mascote": env["MASCOTE"]}


@pytest.mark.parametrize("cmd", COMANDOS)
def test_atalho_aponta_para_referencia_existente(raiz, skill, cmd):
    texto = (raiz / "skills" / cmd / "SKILL.md").read_text(encoding="utf-8")
    campos = frontmatter(texto)
    ref = skill / "references" / (cmd + ".md")
    assert ref.is_file()
    origem = frontmatter(ref.read_text(encoding="utf-8"))
    assert campos["name"] == cmd
    for campo in ("description", "argument-hint"):
        assert campos[campo] == origem[campo]
    assert "gerado por tools/gerar.py; não edite à mão" in texto
    assert "${CLAUDE_PLUGIN_ROOT}/skills/%s/references/%s.md" % (skill.name, cmd) in texto
    assert "$ARGUMENTS" in texto


def test_so_existem_os_atalhos_esperados(raiz, skill):
    atalhos = {p.parent.name for p in (raiz / "skills").glob("*/SKILL.md")}
    assert atalhos == set(COMANDOS) | {skill.name}


def test_skill_principal_respeita_a_especificacao(skill):
    texto = (skill / "SKILL.md").read_text(encoding="utf-8")
    campos = frontmatter(texto)
    nome = campos["name"]
    assert nome == skill.name
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", nome) and len(nome) <= 64
    assert 1 <= len(campos["description"]) <= 1024
    assert len(texto.splitlines()) <= 500
    for ref in re.findall(r"`(references/[\w.-]+\.md)`", texto):
        assert (skill / ref).is_file(), ref


def test_hooks_referenciam_scripts_que_existem(raiz, skill):
    hooks = json.loads((raiz / "hooks" / "hooks.json").read_text(encoding="utf-8"))["hooks"]
    comandos = [h["command"] for grupos in hooks.values() for g in grupos for h in g["hooks"]]
    assert len(comandos) == 2
    for cmd in comandos:
        m = re.fullmatch(r'python3 "\$\{CLAUDE_PLUGIN_ROOT\}/([^"]+)"', cmd)
        assert m, cmd
        assert (raiz / m.group(1)).is_file(), cmd
    guard = hooks["PreToolUse"][0]
    assert guard["hooks"][0]["onFailure"] == "block"
    for ferramenta in ("Edit", "Write", "NotebookEdit", "Bash"):
        assert ferramenta in guard["matcher"].split("|")


def test_estilo_de_saida_vem_da_persona(raiz, skill):
    estilo = (raiz / "output-styles" / "tutor.md").read_text(encoding="utf-8")
    persona = (skill / "references" / "persona.md").read_text(encoding="utf-8")
    assert frontmatter(estilo)["force-for-plugin"] == "true"
    assert persona.split("---\n", 2)[2].strip() in estilo


def test_nome_do_kit_nao_esta_espalhado_nos_scripts(raiz, skill):
    """O nome vem de projeto.env: o gerador não pode conter o literal, e os scripts não podem
    atribuir ou comparar com ele (kit.py, statusline.py e configuracoes.py têm reserva)."""
    env = ler_env(raiz)
    permitidos = {"kit.py", "statusline.py", "configuracoes.py"}
    for arq in sorted((skill / "scripts").glob("*.py")):
        if arq.name in permitidos:
            continue
        linhas = arq.read_text(encoding="utf-8").splitlines()
        # menção em texto é tolerada; atribuição ou comparação com o nome literal, não
        suspeitas = [l for l in linhas
                     if re.search(r"[=!]=?\s*[\"']%s[\"']" % env["NOME"], l)]
        assert not suspeitas, (arq.name, suspeitas)
    assert env["NOME"] not in (raiz / "tools" / "gerar.py").read_text(encoding="utf-8")


def copiar_kit(raiz, destino):
    """Cópia mínima do repositório: projeto.env, gerador e a pasta da skill (referências)."""
    env = ler_env(raiz)
    copia = destino / "copia"
    (copia / "tools").mkdir(parents=True)
    shutil.copy(raiz / "projeto.env", copia / "projeto.env")
    shutil.copy(raiz / "tools" / "gerar.py", copia / "tools" / "gerar.py")
    shutil.copytree(raiz / "skills" / env["NOME"] / "references",
                    copia / "skills" / env["NOME"] / "references")
    assert rodar_gerador(copia).returncode == 0
    return copia


def test_gerador_idempotente(raiz, tmp_path):
    copia = copiar_kit(raiz, tmp_path)
    r = rodar_gerador(copia)
    assert r.returncode == 0 and "escrito" not in r.stdout
    assert rodar_gerador(copia, "--conferir").returncode == 0


def test_trocar_nome_e_comando_muda_manifestos_e_atalhos(raiz, tmp_path):
    env = ler_env(raiz)
    copia = copiar_kit(raiz, tmp_path)
    novo = "outro-kit"
    texto = (copia / "projeto.env").read_text(encoding="utf-8")
    texto = re.sub(r"^NOME=.*$", "NOME=" + novo, texto, flags=re.M)
    texto = re.sub(r"^COMANDO=.*$", "COMANDO=outro", texto, flags=re.M)
    (copia / "projeto.env").write_text(texto, encoding="utf-8")
    # a pasta da skill acompanha o nome, como no repositório
    shutil.move(str(copia / "skills" / env["NOME"]), str(copia / "skills" / novo))
    r = rodar_gerador(copia)
    assert r.returncode == 0, r.stderr
    plugin = json.loads((copia / ".claude-plugin" / "plugin.json").read_text("utf-8"))
    mercado = json.loads((copia / ".claude-plugin" / "marketplace.json").read_text("utf-8"))
    assert plugin["name"] == novo and mercado["plugins"][0]["name"] == novo
    kit = json.loads((copia / "skills" / novo / "assets" / "kit.json").read_text("utf-8"))
    assert kit["nome"] == novo and kit["comando"] == "outro"
    atalho = (copia / "skills" / "dica" / "SKILL.md").read_text(encoding="utf-8")
    assert "skills/%s/references/dica.md" % novo in atalho and env["NOME"] not in atalho
    hooks = (copia / "hooks" / "hooks.json").read_text(encoding="utf-8")
    assert "skills/%s/scripts/guard.py" % novo in hooks and env["NOME"] not in hooks
    for arq in (".claude-plugin/plugin.json", ".claude-plugin/marketplace.json"):
        assert env["NOME"] not in (copia / arq).read_text(encoding="utf-8")
