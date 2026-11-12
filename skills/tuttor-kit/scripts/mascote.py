#!/usr/bin/env python3
"""Lume, o farolzinho do kit: calmo e curioso, "eu ilumino, você pilota".

Ilumina o caminho e nunca pega o leme. Quatro estados que se distinguem pela forma (olhos,
posição do facho, sinais), não pela cor: a cor (ANSI) é só reforço. Só biblioteca padrão.

Uso: mascote.py [estado] [--ascii] [--sem-cor] [--mini] [--fala TEXTO] [--todos]
"""
import argparse
import os
import re
import shutil
import sys
import unicodedata

NOME = "Lume"
ESTADOS = ("atento", "pensando", "comemorando", "alerta")
LARGURA_ARTE = 14
ALTURA_ARTE = 6
COLUNA_LUZ = 9           # da coluna 9 em diante ficam o facho e os sinais (recebem a cor)
LARGURA_PADRAO = 80
ESPACO = 2               # espaço entre a arte e a fala

ARTES = {
    "unicode": {
        "atento": [
            "    ▄█▄",
            "   ╔═══╗",
            "   ║◦ ◦║ ═══╸",
            "   ╚═╤═╝",
            "    ║ ║",
            "   ▄███▄",
        ],
        "pensando": [
            "    ▄█▄  ∙ ∙ ∙",
            "   ╔═══╗ ╌╌╌╌╸",
            "   ║∙ ∙║",
            "   ╚═╤═╝",
            "    ║ ║",
            "   ▄███▄",
        ],
        "comemorando": [
            "    ▄█▄   ✦ ✦",
            "   ╔═══╗ ╲ ╱",
            "   ║◠ ◠║ ═══✦",
            "   ╚═╤═╝ ╱ ╲",
            "    ║ ║   ✦",
            "   ▄███▄",
        ],
        "alerta": [
            "    ▄█▄    ! !",
            "   ╔═══╗   ! !",
            "   ║O O║ ╲",
            "   ╚═╤═╝  ╲═╸",
            "    ║ ║",
            "   ▄███▄    !",
        ],
    },
    "ascii": {
        "atento": [
            "    _^_",
            "   /===\\",
            "   |o o| ===>",
            "   \\_|_/",
            "    | |",
            "   /###\\",
        ],
        "pensando": [
            "    _^_  . . .",
            "   /===\\ ---->",
            "   |. .|",
            "   \\_|_/",
            "    | |",
            "   /###\\",
        ],
        "comemorando": [
            "    _^_   * *",
            "   /===\\ \\ /",
            "   |^ ^| ===*",
            "   \\_|_/ / \\",
            "    | |   *",
            "   /###\\",
        ],
        "alerta": [
            "    _^_    ! !",
            "   /===\\   ! !",
            "   |O O| \\",
            "   \\_|_/  \\=>",
            "    | |",
            "   /###\\    !",
        ],
    },
}

MINIS = {
    "unicode": {"atento": "[◦◦]═", "pensando": "[∙∙]..", "comemorando": "[◠◠]✦",
                "alerta": "[OO]!"},
    "ascii": {"atento": "[oo]=", "pensando": "[..]..", "comemorando": "[^^]*",
              "alerta": "[OO]!"},
}

CORES = {"atento": "33", "pensando": "36", "comemorando": "1;32", "alerta": "1;31"}
RESET = "\033[0m"
_CONTROLE = re.compile(r"[\x00-\x1f\x7f-\x9f]")


# ---------------------------------------------------------------- detecção

def sem_cor():
    """True se não deve colorir: NO_COLOR não vazio, TERM=dumb ou saída que não é terminal."""
    if os.environ.get("NO_COLOR"):
        return True
    if os.environ.get("TERM") == "dumb":
        return True
    try:
        return not sys.stdout.isatty()
    except (AttributeError, ValueError):
        return True


def so_ascii():
    """True se o ambiente não é UTF-8 (ou é locale CJK, onde caixas podem ocupar 2 colunas)."""
    if os.environ.get("TERM") == "dumb":
        return True
    local = ""
    # o Python (PEP 538) troca o locale "C" por C.UTF-8 ao iniciar; isso não é um terminal UTF-8
    if (not os.environ.get("LC_ALL") and os.environ.get("LC_CTYPE", "").lower() == "c.utf-8"
            and os.environ.get("LANG", "C").upper() in ("C", "POSIX")):
        return True
    for var in ("LC_ALL", "LC_CTYPE", "LANG"):
        if os.environ.get(var):
            local = os.environ[var].lower()
            break
    if local:
        if not re.search(r"utf-?8", local):
            return True
        return local.split("_")[0] in ("ja", "zh", "ko")
    codificacao = (getattr(sys.stdout, "encoding", None) or "").lower().replace("_", "-")
    return codificacao not in ("utf-8", "utf8")


def _largura_padrao():
    try:
        colunas = int(os.environ.get("COLUMNS", ""))
        if colunas > 0:
            return colunas
    except ValueError:
        pass
    return shutil.get_terminal_size((LARGURA_PADRAO, 24)).columns


# ---------------------------------------------------------------- medidas e limpeza

def colunas(texto):
    """Largura em colunas de terminal (largura ampla = 2; ambígua = 1; combinante = 0)."""
    total = 0
    for c in texto:
        if unicodedata.combining(c):
            continue
        total += 2 if unicodedata.east_asian_width(c) in ("W", "F") else 1
    return total


def _limpar_fala(fala):
    return re.sub(r"\s+", " ", _CONTROLE.sub(" ", str(fala))).strip()


def _estado(estado):
    nome = str(estado).strip().lower() if isinstance(estado, str) else ""
    return nome if nome in ESTADOS else "atento"


def _resolver(ascii_, cor):
    return (so_ascii() if ascii_ is None else bool(ascii_),
            (not sem_cor()) if cor is None else bool(cor))


def _pintar(texto, estado):
    return f"\033[{CORES[estado]}m{texto}{RESET}" if texto.strip() else texto


def _quebrar(texto, largura):
    """Quebra por palavras em linhas de até `largura` colunas (corta palavras longas)."""
    largura = max(largura, 1)
    linhas, atual = [], ""
    for palavra in texto.split():
        while colunas(palavra) > largura:
            corte = ""
            for c in palavra:
                if colunas(corte + c) > largura:
                    break
                corte += c
            if atual:
                linhas.append(atual)
                atual = ""
            linhas.append(corte)
            palavra = palavra[len(corte):]
        nova = f"{atual} {palavra}".strip()
        if colunas(nova) <= largura:
            atual = nova
        else:
            linhas.append(atual)
            atual = palavra
    if atual:
        linhas.append(atual)
    return linhas


# ---------------------------------------------------------------- desenho

def mini(estado="atento", *, ascii=None, cor=None):
    """Versão de uma linha (≤ 6 colunas), distinta por estado mesmo sem cor."""
    estado = _estado(estado)
    usar_ascii, usar_cor = _resolver(ascii, cor)
    texto = MINIS["ascii" if usar_ascii else "unicode"][estado]
    return _pintar(texto, estado) if usar_cor else texto


def _arte(estado, usar_ascii, usar_cor):
    """Linhas da arte, preenchidas até 14 colunas (a parte do facho recebe a cor)."""
    linhas = []
    for linha in ARTES["ascii" if usar_ascii else "unicode"][estado]:
        corpo, luz = linha[:COLUNA_LUZ], linha[COLUNA_LUZ:]
        if usar_cor:
            luz = _pintar(luz, estado)
        linhas.append((corpo.ljust(COLUNA_LUZ) + luz, colunas(linha)))
    return linhas


def desenhar(estado="atento", *, ascii=None, cor=None, largura=None, fala=None):
    """Arte do Lume (≤ 6 linhas × 14 colunas); `fala` vai à direita ou, se não couber, abaixo.

    Terminal mais estreito que a arte: devolve só o `mini` (com a fala, se houver).
    """
    estado = _estado(estado)
    usar_ascii, usar_cor = _resolver(ascii, cor)
    largura = _largura_padrao() if largura is None else int(largura)
    fala = _limpar_fala(fala) if fala else ""
    if largura < LARGURA_ARTE:
        linha = mini(estado, ascii=usar_ascii, cor=usar_cor)
        return f"{linha} {fala}".rstrip() if fala else linha
    arte = _arte(estado, usar_ascii, usar_cor)
    saida = [t for t, _ in arte]
    if fala:
        cabe = LARGURA_ARTE + ESPACO + colunas(fala) <= largura
        if cabe:
            meio = 2 if len(saida) > 2 else 0
            texto, util = arte[meio]
            saida[meio] = texto + " " * (LARGURA_ARTE + ESPACO - util) + fala
        else:
            saida.extend(_quebrar(fala, largura))
    return "\n".join(s.rstrip() for s in saida)


def _todos(usar_ascii, usar_cor, largura, so_mini):
    if so_mini:
        return "\n".join(f"{e:<12} {mini(e, ascii=usar_ascii, cor=usar_cor)}" for e in ESTADOS)
    folga = 2
    if largura >= len(ESTADOS) * LARGURA_ARTE + (len(ESTADOS) - 1) * folga:
        colunas_arte = [_arte(e, usar_ascii, usar_cor) for e in ESTADOS]
        linhas = []
        for i in range(ALTURA_ARTE):
            partes = []
            for arte in colunas_arte:
                texto, util = arte[i]
                partes.append(texto + " " * (LARGURA_ARTE - util))
            linhas.append((" " * folga).join(partes).rstrip())
        nomes = (" " * folga).join(e.center(LARGURA_ARTE) for e in ESTADOS).rstrip()
        return "\n".join(linhas + [nomes])
    blocos = []
    for e in ESTADOS:
        blocos.append(e + "\n" + desenhar(e, ascii=usar_ascii, cor=usar_cor, largura=largura))
    return "\n\n".join(blocos)


# ---------------------------------------------------------------- CLI

def _parser():
    p = argparse.ArgumentParser(
        prog="mascote.py", description="Lume, o farolzinho do tutor (calmo e curioso).")
    p.add_argument("estado", nargs="?", default="atento",
                   help="um de: " + ", ".join(ESTADOS) + " (desconhecido vira atento)")
    p.add_argument("--ascii", action="store_true", help="só ASCII (sem caracteres de caixa)")
    p.add_argument("--sem-cor", action="store_true", help="não usa cores ANSI")
    p.add_argument("--mini", action="store_true", help="versão de uma linha")
    p.add_argument("--fala", metavar="TEXTO", help="fala ao lado (ou abaixo, se não couber)")
    p.add_argument("--todos", action="store_true", help="mostra os quatro estados, com o nome")
    p.add_argument("--largura", type=int, metavar="N",
                   help="largura do terminal (padrão: detecta)")
    return p


def _imprimir(texto):
    codificacao = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        texto.encode(codificacao)
    except (UnicodeEncodeError, LookupError):
        return False
    print(texto)
    return True


def main(argv=None):
    args = _parser().parse_args(argv)
    usar_ascii = True if args.ascii else None
    usar_cor = False if args.sem_cor else None
    largura = args.largura if args.largura else None

    def montar(forcar_ascii):
        a, c = _resolver(True if forcar_ascii else usar_ascii, usar_cor)
        larg = _largura_padrao() if largura is None else largura
        if args.todos:
            return _todos(a, c, larg, args.mini)
        if args.mini:
            linha = mini(args.estado, ascii=a, cor=c)
            fala = _limpar_fala(args.fala) if args.fala else ""
            return f"{linha} {fala}".rstrip()
        return desenhar(args.estado, ascii=a, cor=c, largura=larg, fala=args.fala)

    if not _imprimir(montar(False)):   # terminal que não codifica a arte: cai para ASCII
        print(montar(True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
