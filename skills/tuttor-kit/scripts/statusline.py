#!/usr/bin/env python3
"""Status line do kit para o Claude Code: uma linha com o Lume e o que importa ao aluno.

Lê o JSON de sessão do Claude Code no stdin (statusline.md, seção "Available data") e imprime
uma linha: mini-mascote, nome do kit, trilha em andamento, tema de erro mais recorrente nos
últimos 14 dias (vigia) e quantos temas vencem para revisão. Nunca falha: em qualquer erro
imprime só o nome do kit e sai com 0. Sem rede. Não segue links simbólicos em .tutor/.

Largura: usa a variável COLUMNS, que o Claude Code define antes de rodar o script
(statusline.md, "Size output to the terminal"); sem ela, usa o teto fixo de 100 colunas.

Uso: statusline.py [--sem-mascote]      (o JSON vem no stdin)
"""
import json
import os
import re
import stat
import sys
import time

try:
    import estado
except Exception:  # noqa: BLE001 - a linha funciona sem o módulo
    estado = None
try:
    import mascote
except Exception:  # noqa: BLE001
    mascote = None

DIAS_PADROES = 14
LIMITE_STDIN = 1 << 20
LIMITE_ARQUIVO = 65536
LIMITE_VIGIA = 262144
TETO_SEM_COLUMNS = 100
MIN_ERROS = 2
_CONTROLE = re.compile(r"[\x00-\x1f\x7f-\x9f]")


def _limpo(texto, limite=40):
    """Texto de uma linha, sem caracteres de controle (dados do projeto não são confiáveis)."""
    return re.sub(r"\s+", " ", _CONTROLE.sub(" ", str(texto))).strip()[:limite]


def _raiz_do_kit():
    """Raiz do repositório: scripts/ -> <skill>/ -> skills/ -> raiz."""
    pasta = os.path.abspath(__file__)
    for _ in range(4):
        pasta = os.path.dirname(pasta)
    return pasta


def nome_do_kit():
    """NOME de projeto.env na raiz do repositório, se existir; senão a pasta da skill."""
    pasta_skill = os.path.basename(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    try:
        texto = _ler(os.path.join(_raiz_do_kit(), "projeto.env"), 4096)
        for linha in texto.splitlines():
            m = re.match(r"\s*NOME\s*=\s*([A-Za-z0-9._-]+)\s*(?:#.*)?$", linha)
            if m:
                return m.group(1)
    except Exception:  # noqa: BLE001
        pass
    return pasta_skill


# ---------------------------------------------------------------- leitura segura

def _ler(caminho, limite, do_fim=False):
    """Lê até `limite` bytes de um arquivo comum; recusa links simbólicos e não-arquivos."""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    fd = os.open(caminho, flags)
    try:
        info = os.fstat(fd)
        if not _eh_arquivo(info):
            return ""
        if do_fim and info.st_size > limite:
            os.lseek(fd, info.st_size - limite, os.SEEK_SET)
        dados = os.read(fd, limite)
    finally:
        os.close(fd)
    return dados.decode("utf-8", "replace")


def _eh_arquivo(info):
    return stat.S_ISREG(info.st_mode)


def _pasta_real(caminho):
    return os.path.isdir(caminho) and not os.path.islink(caminho)


def _pasta_do_projeto(dados):
    candidatos = []
    ws = dados.get("workspace") if isinstance(dados, dict) else None
    if isinstance(ws, dict):
        candidatos += [ws.get("project_dir"), ws.get("current_dir")]
    if isinstance(dados, dict):
        candidatos.append(dados.get("cwd"))
    for c in candidatos:
        if isinstance(c, str) and c and os.path.isabs(c):
            return c
    return os.getcwd()


# ---------------------------------------------------------------- peças

def trilha_atual(tutor):
    """'Título 2/4' da trilha .md mais recente em .tutor/trilhas/ (sem seguir links)."""
    pasta = os.path.join(tutor, "trilhas")
    if not _pasta_real(pasta):
        return ""
    melhor = None
    with os.scandir(pasta) as it:
        for e in it:
            if e.name.endswith(".md") and not e.is_symlink() and e.is_file(follow_symlinks=False):
                m = e.stat(follow_symlinks=False).st_mtime
                if melhor is None or m > melhor[0]:
                    melhor = (m, e.path)
    if not melhor:
        return ""
    texto = _ler(melhor[1], LIMITE_ARQUIVO)
    titulo = re.search(r"^#\s*(?:Trilha:\s*)?(.+)$", texto, re.M)
    if not titulo:
        return ""
    saida = _limpo(titulo.group(1), 28)
    prog = re.search(r"^Progresso:\s*(.+)$", texto, re.M)
    if prog:
        etapas = re.findall(r"\[([ xX])\]", prog.group(1))
        if etapas:
            saida += f" {sum(1 for m in etapas if m in 'xX')}/{len(etapas)}"
    return saida


def erro_recorrente(tutor, agora=None):
    """(tema, vezes) do erro que mais se repete em .tutor/vigia.jsonl nos últimos 14 dias."""
    arq = os.path.join(tutor, "vigia.jsonl")
    if not os.path.lexists(arq):
        return None
    corte = (agora or time.time()) - DIAS_PADROES * 86400
    cont = {}
    for linha in _ler(arq, LIMITE_VIGIA, do_fim=True).splitlines():
        try:
            it = json.loads(linha)
        except ValueError:
            continue
        if not isinstance(it, dict) or it.get("sev") not in ("erro", "melhoria"):
            continue
        tag, ts = it.get("tag"), it.get("ts")
        if not isinstance(tag, str) or tag in ("", "outro"):
            continue
        if isinstance(ts, bool) or not isinstance(ts, (int, float)) or ts < corte:
            continue
        cont[tag] = cont.get(tag, 0) + 1
    if not cont:
        return None
    tema, n = max(cont.items(), key=lambda kv: (kv[1], kv[0]))
    return (_limpo(tema, 24), n) if n >= MIN_ERROS else None


def revisoes_vencidas():
    if estado is None:
        return 0
    return len(estado.vencidos(estado.carregar(), limite=999))


def _largura_disponivel():
    try:
        n = int(os.environ.get("COLUMNS", ""))
        if n > 0:
            return n
    except ValueError:
        pass
    return TETO_SEM_COLUMNS


def _cortar(texto, limite, ascii_):
    if limite <= 0:
        return ""
    if len(texto) <= limite:
        return texto
    reticencias = "..." if ascii_ else "…"
    return texto[:max(limite - len(reticencias), 0)].rstrip() + reticencias[:limite]


def _usa_cor():
    return not os.environ.get("NO_COLOR") and os.environ.get("TERM") != "dumb"


def _ascii():
    return mascote.so_ascii() if mascote is not None else True


# ---------------------------------------------------------------- montagem

def montar(dados, com_mascote=True):
    nome = nome_do_kit()
    usar_ascii = _ascii()
    sep = " | " if usar_ascii else " · "
    tutor = os.path.join(_pasta_do_projeto(dados), ".tutor")
    partes = [nome]
    erro = None
    try:
        if _pasta_real(tutor):
            trilha = trilha_atual(tutor)
            if trilha:
                partes.append("trilha " + trilha)
            erro = erro_recorrente(tutor)
            if erro:
                partes.append(f"erro: {erro[0]} {erro[1]}x")
    except Exception:  # noqa: BLE001 - uma peça com defeito não derruba as outras
        pass
    try:
        venc = revisoes_vencidas()
        if venc:
            partes.append(f"revisar {venc}")
    except Exception:  # noqa: BLE001
        pass
    texto = sep.join(partes)
    prefixo, larg_prefixo = "", 0
    if com_mascote and mascote is not None:
        try:
            forma = "alerta" if erro and erro[1] >= 3 else "atento"
            prefixo = mascote.mini(forma, ascii=usar_ascii, cor=_usa_cor())
            larg_prefixo = mascote.colunas(mascote.mini(forma, ascii=usar_ascii, cor=False)) + 1
        except Exception:  # noqa: BLE001
            prefixo, larg_prefixo = "", 0
    texto = _cortar(texto, _largura_disponivel() - 1 - larg_prefixo, usar_ascii)
    return f"{prefixo} {texto}" if prefixo else texto


def _ler_entrada():
    try:
        bruto = sys.stdin.read(LIMITE_STDIN)
        dados = json.loads(bruto) if bruto.strip() else {}
        return dados if isinstance(dados, dict) else {}
    except Exception:  # noqa: BLE001 - JSON inválido, stdin fechado etc.
        return {}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    try:
        linha = montar(_ler_entrada(), com_mascote="--sem-mascote" not in argv)
    except Exception:  # noqa: BLE001 - nunca falha
        try:
            linha = nome_do_kit()
        except Exception:  # noqa: BLE001
            linha = "tutor"
    try:
        print(_limpo_final(linha))
    except Exception:  # noqa: BLE001
        pass
    return 0


def _limpo_final(linha):
    """Garante uma linha só (sem quebras), preservando as sequências de cor do próprio kit."""
    return linha.replace("\r", " ").replace("\n", " ")


if __name__ == "__main__":
    sys.exit(main())
