#!/usr/bin/env python3
"""Lançador do kit: abre o Claude Code em modo tutor (ou prepara outra CLI de IA).

Uso (pelo wrapper `bin/<comando>`):
    tuttor [opções] [argumentos repassados ao claude]
    tuttor preparar --cli <codex|gemini|opencode|ollama> [--remover] [--dry-run]
    tuttor vigia [...]      repassa ao vigia
    tuttor estado [...]     repassa ao estado

O que faz ao abrir o Claude Code: mostra o banner do mascote (só em terminal), prepara o projeto
(`.tutor/`, exclusão no git, `~/.tutor/perfil.md`) e substitui o processo por
`claude --plugin-dir <raiz do kit> --settings <JSON em linha> --setting-sources project,local`.
Só biblioteca padrão. Compatível com Python 3.9+.
"""
import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys

import configuracoes
import kit
import mascote

ISOLAMENTO_FONTES = "project,local"
DOCS_CLI = "docs/cli"
SUBCOMANDOS_REPASSADOS = {"vigia": "vigia.py", "estado": "estado.py"}
OPCOES_SEM_VALOR = ("--sem-mascote", "--ascii", "--com-meus-plugins", "--tmux", "--onde",
                    "--versao", "--ajuda", "-h", "--help")
OPCOES_COM_VALOR = ("--cli",)
FALA_DO_BANNER = "Modo tutor: eu ilumino, você pilota."
TRAVAS = {
    "sandbox": "sandbox somente leitura da própria CLI (o guard.py do kit não existe lá)",
    "permissoes": "permissões e modo de plano da própria CLI (o guard.py do kit não existe lá)",
    "instrucoes": "nenhuma trava técnica: só as instruções, que o modelo pode desobedecer",
}
AJUDA = """Uso:
  {c} [opções] [argumentos para o claude]    abre o Claude Code em modo tutor
  {c} preparar --cli CLI [--remover] [--dry-run]
  {c} vigia [...]    {c} estado [...]        repassam a {c}-vigia e {c}-estado

Opções (só valem antes dos argumentos do claude; `--` encerra a lista):
  --sem-mascote        sem banner e sem o mascote na linha de status
  --ascii              banner só em ASCII (NO_COLOR tira a cor)
  --com-meus-plugins   não isola: carrega também seus outros plugins, hooks e ajustes de usuário
  --tmux               abre o tmux com dois painéis: o tutor e o {c}-vigia
  --cli CLI            usa outra CLI (codex, gemini, opencode, ollama): experimental, não testado
  --onde               mostra a raiz do kit
  --versao             mostra a versão
  --ajuda              mostra esta ajuda

Isolamento (padrão): o claude abre com `--setting-sources {fontes}`, ou seja, sem as
configurações de USUÁRIO (~/.claude/settings.json). Isso tira os plugins instalados em escopo
de usuário e também os hooks, as permissões, o tema e o modelo padrão definidos lá; as
configurações do projeto (.claude/settings.json e .local) continuam valendo. Use
--com-meus-plugins para desligar o isolamento.
"""


class ErroLancador(Exception):
    """Falha esperada: a mensagem vai para o stderr e o programa sai com o código."""

    def __init__(self, mensagem, codigo=1):
        super().__init__(mensagem)
        self.codigo = codigo


# ---------------------------------------------------------------- caminhos e dados

def raiz():
    return kit.raiz_do_kit()


def pasta_da_skill():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def casa():
    return os.path.expanduser("~")


def carregar_clis():
    caminho = os.path.join(raiz(), "modelos", "cli.json")
    try:
        with open(caminho, encoding="utf-8") as f:
            dados = json.load(f)
    except (OSError, ValueError) as e:
        raise ErroLancador("não consegui ler %s: %s" % (caminho, e))
    if not isinstance(dados, dict):
        raise ErroLancador("%s não é um objeto JSON" % caminho)
    return dados


def clis_de_fora(clis):
    return sorted(nome for nome in clis if nome != "claude")


def ler_persona():
    """Corpo de references/persona.md, sem o frontmatter."""
    caminho = os.path.join(pasta_da_skill(), "references", "persona.md")
    try:
        with open(caminho, encoding="utf-8") as f:
            texto = f.read()
    except OSError as e:
        raise ErroLancador("não consegui ler a persona: %s" % e)
    m = re.match(r"^---\n.*?\n---\n?(.*)$", texto, re.S)
    return (m.group(1) if m else texto).strip("\n")


# ---------------------------------------------------------------- preparo do projeto

def _escrever_novo(caminho, conteudo):
    """Cria o arquivo só se não existir (nunca segue link nem sobrescreve)."""
    try:
        with open(caminho, "x", encoding="utf-8") as f:
            f.write(conteudo)
    except FileExistsError:
        return False
    return True


def _excluir_do_git(projeto):
    """Acrescenta `.tutor/` em .git/info/exclude (se for repositório git). Sem git: nada."""
    if shutil.which("git") is None:
        return
    try:
        r = subprocess.run(["git", "rev-parse", "--git-path", "info/exclude"], cwd=projeto,
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                           text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return
    saida = r.stdout.strip()
    if r.returncode != 0 or not saida:
        return
    exclude = saida if os.path.isabs(saida) else os.path.join(projeto, saida)
    if os.path.islink(exclude):
        return
    atual = ""
    try:
        with open(exclude, encoding="utf-8", errors="replace") as f:
            atual = f.read()
    except OSError:
        pass
    if ".tutor/" in [linha.strip() for linha in atual.splitlines()]:
        return
    try:
        os.makedirs(os.path.dirname(exclude), exist_ok=True)
        with open(exclude, "a", encoding="utf-8") as f:
            if atual and not atual.endswith("\n"):
                f.write("\n")
            f.write(".tutor/\n")
    except OSError:
        pass


def preparar_projeto(projeto=None):
    """Cria .tutor/ (recusa link simbólico), exclui do git e cria ~/.tutor/perfil.md."""
    projeto = projeto or os.getcwd()
    pasta = os.path.join(projeto, ".tutor")
    if os.path.islink(pasta):
        raise ErroLancador("recuso: %s é um link simbólico (apague-o ou troque por uma pasta)"
                           % pasta)
    if os.path.exists(pasta) and not os.path.isdir(pasta):
        raise ErroLancador("%s existe e não é uma pasta" % pasta)
    try:
        os.makedirs(pasta, exist_ok=True)
    except OSError as e:
        raise ErroLancador("não consegui criar %s: %s" % (pasta, e))
    _excluir_do_git(projeto)
    pasta_casa = os.path.join(casa(), ".tutor")
    try:
        os.makedirs(pasta_casa, exist_ok=True)
        perfil = os.path.join(pasta_casa, "perfil.md")
        if not os.path.lexists(perfil):
            modelo = os.path.join(pasta_da_skill(), "assets", "perfil-modelo.md")
            with open(modelo, encoding="utf-8") as f:
                if _escrever_novo(perfil, f.read()):
                    print("perfil inicial criado em ~/.tutor/perfil.md (complete com /perfil)",
                          file=sys.stderr)
    except OSError as e:
        print("aviso: não consegui preparar ~/.tutor: %s" % e, file=sys.stderr)


# ---------------------------------------------------------------- banner

def mostrar_banner(usar_ascii):
    if not sys.stdout.isatty():
        return
    arte = mascote.desenhar("atento", ascii=True if usar_ascii else None, fala=FALA_DO_BANNER)
    try:
        arte.encode(getattr(sys.stdout, "encoding", None) or "utf-8")
    except (UnicodeEncodeError, LookupError):
        arte = mascote.desenhar("atento", ascii=True, fala=FALA_DO_BANNER)
    print(arte)
    print()


# ---------------------------------------------------------------- execução

def _executar(programa, argv):
    """Substitui o processo (os testes trocam esta função)."""
    os.execvp(programa, argv)


def montar_comando_claude(sem_mascote, com_meus_plugins, extras):
    json_em_linha = json.dumps(configuracoes.configuracoes(sem_mascote), ensure_ascii=True)
    comando = ["claude", "--plugin-dir", raiz(), "--settings", json_em_linha]
    tem_fontes = any(a == "--setting-sources" or a.startswith("--setting-sources=")
                     for a in extras)
    if not com_meus_plugins and not tem_fontes:
        comando += ["--setting-sources", ISOLAMENTO_FONTES]
    return comando + list(extras)


def abrir_claude(opcoes, extras):
    if shutil.which("claude") is None:
        raise ErroLancador("não encontrei o comando 'claude' no PATH. Instale o Claude Code "
                           "(https://code.claude.com/docs) e tente de novo.", 127)
    preparar_projeto()
    if not opcoes["sem_mascote"]:
        mostrar_banner(opcoes["ascii"])
    _executar("claude", montar_comando_claude(
        opcoes["sem_mascote"], opcoes["com_meus_plugins"], extras))


def nome_da_sessao(projeto):
    base = re.sub(r"[^A-Za-z0-9_-]+", "-", os.path.basename(projeto.rstrip("/")) or "projeto")
    return "%s-%s" % (kit.COMANDO, base.strip("-") or "projeto")


def abrir_tmux(opcoes, extras):
    """Sessão tmux com dois painéis: o tutor (este lançador, sem --tmux) e o vigia."""
    tmux = shutil.which("tmux")
    if tmux is None:
        raise ErroLancador(
            "o tmux não está instalado. Instale-o (por exemplo, `sudo apt install tmux`) ou "
            "use dois terminais: em um, `%s`; no outro, `%s-vigia`." % (kit.COMANDO,
                                                                         kit.COMANDO), 127)
    projeto = os.getcwd()
    sessao = nome_da_sessao(projeto)
    bin_dir = os.path.join(raiz(), "bin")
    flags = [f for f, ligado in (("--sem-mascote", opcoes["sem_mascote"]),
                                 ("--ascii", opcoes["ascii"]),
                                 ("--com-meus-plugins", opcoes["com_meus_plugins"])) if ligado]
    partes_tutor = [os.path.join(bin_dir, kit.COMANDO)] + flags
    if extras:
        partes_tutor += ["--"] + list(extras)
    cmd_tutor = shlex.join(partes_tutor)
    cmd_vigia = shlex.join([os.path.join(bin_dir, kit.COMANDO + "-vigia"), projeto])
    existe = subprocess.run([tmux, "has-session", "-t", "=" + sessao],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    if not existe:
        preparar_projeto(projeto)
        passos = [
            [tmux, "new-session", "-d", "-s", sessao, "-c", projeto, cmd_tutor],
            [tmux, "split-window", "-h", "-d", "-t", sessao, "-c", projeto, cmd_vigia],
        ]
        for passo in passos:
            if subprocess.run(passo).returncode != 0:
                raise ErroLancador("o tmux falhou em: " + " ".join(passo[:2]))
    verbo = "switch-client" if os.environ.get("TMUX") else "attach-session"
    _executar(tmux, [tmux, verbo, "-t", sessao])


def abrir_outra_cli(nome, opcoes, extras):
    clis = carregar_clis()
    info = clis.get(nome)
    if nome not in clis_de_fora(clis) or not isinstance(info, dict):
        raise ErroLancador("CLI desconhecida: %s (opções: %s)"
                           % (nome, ", ".join(clis_de_fora(clis))), 2)
    rotulo = TRAVAS.get(info.get("trava"), "campo trava = %s" % info.get("trava"))
    print("aviso: %s é experimental (não testado). Proteção de escrita: %s."
          % (info.get("nome", nome), rotulo), file=sys.stderr)
    binario = info.get("binario") or nome
    if shutil.which(binario) is None:
        raise ErroLancador("não encontrei '%s' no PATH. Veja %s/%s/%s.md para instalar e "
                           "configurar." % (binario, raiz(), DOCS_CLI, nome), 127)
    comando = info.get("interativo")
    if not isinstance(comando, list) or not comando:
        raise ErroLancador("modelos/cli.json sem o comando interativo de %s" % nome)
    preparar_projeto()
    if not opcoes["sem_mascote"]:
        mostrar_banner(opcoes["ascii"])
    print("dica: `%s preparar --cli %s` grava as instruções do tutor para essa CLI."
          % (kit.COMANDO, nome), file=sys.stderr)
    _executar(comando[0], [str(c) for c in comando] + list(extras))


# ---------------------------------------------------------------- preparar --cli

def marca():
    return "%s: arquivo gerado por '%s preparar'; não edite à mão" % (kit.NOME, kit.COMANDO)


def _tem_marca(caminho):
    try:
        with open(caminho, encoding="utf-8", errors="replace") as f:
            return marca() in "".join(f.readline() for _ in range(5))
    except OSError:
        return False


def _sem_cabecalho(texto):
    """Tira do modelo o comentário de cabeçalho (`<!-- ... -->` ou linhas `#` no começo)."""
    if texto.lstrip().startswith("<!--"):
        texto = re.sub(r"\A\s*<!--.*?-->\s*", "", texto, count=1, flags=re.S)
    else:
        linhas = texto.split("\n")
        while linhas and linhas[0].startswith("#"):
            linhas.pop(0)
        texto = "\n".join(linhas)
    return texto.lstrip("\n")


def renderizar_modelo(cli, info):
    """Devolve (texto pronto, nome do arquivo) do modelo de `modelos/<cli>/`."""
    if cli == "ollama":
        arquivo = "Modelfile"
    else:
        arquivo = (info.get("instrucoes") or {}).get("arquivo") or ""
    caminho = os.path.join(raiz(), "modelos", cli, arquivo)
    if not arquivo or not os.path.isfile(caminho):
        raise ErroLancador("não achei o modelo de %s em modelos/%s/" % (cli, cli))
    with open(caminho, encoding="utf-8") as f:
        modelo = _sem_cabecalho(f.read())
    persona = ler_persona()
    if cli == "ollama" and '"""' in persona:
        raise ErroLancador("a persona contém três aspas duplas, que quebram o Modelfile")
    corpo = modelo.replace("{{PERSONA}}", persona)
    cabecalho = "# %s" % marca() if cli == "ollama" else "<!-- %s -->" % marca()
    return cabecalho + "\n" + corpo.rstrip("\n") + "\n", arquivo


def preparar_cli(cli, remover=False, simulacao=False, projeto=None):
    clis = carregar_clis()
    if cli not in clis_de_fora(clis):
        raise ErroLancador("CLI desconhecida: %s (opções: %s)"
                           % (cli, ", ".join(clis_de_fora(clis))), 2)
    info = clis[cli]
    texto, arquivo = renderizar_modelo(cli, info)
    if cli == "ollama":
        destino = os.path.join(casa(), ".tutor", "ollama", "Modelfile")
        onde = "~/.tutor/ollama/Modelfile"
    else:
        destino = os.path.join(projeto or os.getcwd(), arquivo)
        onde = arquivo
    existe = os.path.lexists(destino)
    if existe and (os.path.islink(destino) or not _tem_marca(destino)):
        raise ErroLancador("%s já existe e não foi gerado pelo kit (sem a marca '%s'): não vou "
                           "sobrescrever nem apagar. Mova-o ou junte o conteúdo à mão."
                           % (onde, marca()))
    modelo_ollama = (info.get("interativo") or ["ollama", "run", kit.COMANDO])[-1]
    if remover:
        if not existe:
            print("nada a remover: %s não existe" % onde)
        elif simulacao:
            print("[dry-run] removeria %s" % onde)
        else:
            os.remove(destino)
            print("removido: %s" % onde)
        if cli == "ollama":
            print("Para apagar o modelo do Ollama, rode você mesmo: ollama rm %s" % modelo_ollama)
        return 0
    if existe and _ler(destino) == texto:
        print("já em dia: %s" % onde)
    elif simulacao:
        print("[dry-run] gravaria %s (%d linhas)" % (onde, texto.count("\n")))
    else:
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        with open(destino, "w", encoding="utf-8") as f:
            f.write(texto)
        print("gravado: %s" % onde)
    if cli == "ollama":
        print("Agora rode você mesmo (o kit não executa o ollama):")
        print("  ollama create %s -f %s" % (modelo_ollama, shlex.quote(destino)))
        print("  ollama run %s" % modelo_ollama)
        print("Se não quiser o modelo base do exemplo, troque a linha FROM do Modelfile antes.")
    return 0


def _ler(caminho):
    try:
        with open(caminho, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


# ---------------------------------------------------------------- linha de comando

def separar_opcoes(args):
    """Separa as opções do lançador (só no começo) do que vai para o claude."""
    opcoes = {"sem_mascote": False, "ascii": False, "com_meus_plugins": False, "tmux": False,
              "onde": False, "versao": False, "ajuda": False, "cli": None}
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            i += 1
            break
        if a in OPCOES_COM_VALOR or any(a.startswith(o + "=") for o in OPCOES_COM_VALOR):
            if "=" in a:
                nome, valor = a.split("=", 1)
            elif i + 1 < len(args):
                nome, valor = a, args[i + 1]
                i += 1
            else:
                raise ErroLancador("%s precisa de um valor" % a, 2)
            opcoes[nome[2:]] = valor
        elif a in OPCOES_SEM_VALOR:
            chave = {"-h": "ajuda", "--help": "ajuda"}.get(a, a[2:].replace("-", "_"))
            opcoes[chave] = True
        else:
            break
        i += 1
    return opcoes, args[i:]


def _parser_preparar():
    p = argparse.ArgumentParser(prog="%s preparar" % kit.COMANDO,
                                description="Grava as instruções do tutor para outra CLI.")
    p.add_argument("--cli", required=True, help="codex, gemini, opencode ou ollama")
    p.add_argument("--remover", action="store_true",
                   help="apaga o arquivo, só se tiver a marca do kit")
    p.add_argument("--dry-run", action="store_true", help="só mostra o que faria")
    return p


def principal(args):
    if args and args[0] == "preparar":
        ns = _parser_preparar().parse_args(args[1:])
        return preparar_cli(ns.cli, ns.remover, ns.dry_run)
    if args and args[0] in SUBCOMANDOS_REPASSADOS:
        script = os.path.join(pasta_da_skill(), "scripts", SUBCOMANDOS_REPASSADOS[args[0]])
        _executar(sys.executable, [sys.executable, script] + args[1:])
        return 0
    opcoes, extras = separar_opcoes(args)
    if opcoes["ajuda"]:
        print(AJUDA.format(c=kit.COMANDO, fontes=ISOLAMENTO_FONTES), end="")
        return 0
    if opcoes["versao"]:
        print("%s %s" % (kit.COMANDO, kit.VERSAO))
        return 0
    if opcoes["onde"]:
        print(raiz())
        return 0
    if opcoes["cli"]:
        if opcoes["tmux"]:
            raise ErroLancador("--tmux só funciona com o Claude Code", 2)
        abrir_outra_cli(opcoes["cli"], opcoes, extras)
    elif opcoes["tmux"]:
        abrir_tmux(opcoes, extras)
    else:
        abrir_claude(opcoes, extras)
    return 0


def main(argv=None):
    try:
        return principal(list(sys.argv[1:] if argv is None else argv))
    except ErroLancador as e:
        print("%s: %s" % (kit.COMANDO, e), file=sys.stderr)
        return e.codigo


if __name__ == "__main__":
    sys.exit(main())
