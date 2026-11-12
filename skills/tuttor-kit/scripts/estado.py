#!/usr/bin/env python3
"""Estado do aluno por tema: domínio, revisão espaçada e pedidos de dica.

Isto é uma heurística simples, inspirada em P2 (prática espaçada), P5 e P6 (apoio que
diminui com o domínio) e P9 (abuso de dica); ver docs/pesquisa/principios-e-recursos.md.
NÃO é rastreamento bayesiano de conhecimento (Bayesian Knowledge Tracing), nem um modelo
validado: o domínio de 0 a 4 é uma contagem de acertos e erros, a escada de intervalos
(1, 3, 7, 14, 30, 60 dias) é uma escolha de engenharia e a regra de "dicas em sequência"
é um limiar simples. Serve para o tutor escolher o formato do exercício e o que revisar.

Arquivo: ~/.tutor/estado.json (a variável TUTTOR_ESTADO troca o caminho, para testes).

Uso:
    estado.py registrar --tema <slug> --resultado acerto|parcial|erro [--dicas N]
                        [--origem quiz|checkpoint|tarefa|pratica|vigia] [--nota TEXTO]
    estado.py dica --tema <slug> --nivel 1..4
    estado.py apoio --tema <slug>
    estado.py revisar [--limite N]
    estado.py resumo
    estado.py caminho
Todo subcomando aceita --json.
"""
import argparse
import json
import os
import re
import sys
import tempfile
from datetime import date, datetime, timedelta

ESCADA = [1, 3, 7, 14, 30, 60]
RESULTADOS = ("acerto", "parcial", "erro")
ORIGENS = ("quiz", "checkpoint", "tarefa", "pratica", "vigia")
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,59}$")
MAX_TEMAS = 200
MAX_HISTORICO = 20
MAX_NOTA = 200
MAX_DICAS = 99
JANELA_DICAS = 600      # segundos: janela do gatilho "3 pedidos"
INTERVALO_CURTO = 60    # segundos: gatilho "dois pedidos colados"
PEDIDOS_SEQUENCIA = 3
MAX_PEDIDOS = 10
NIVEIS_DE_APOIO = {
    "alto": ("Apoio alto: mostre antes um exemplo resolvido de OUTRO problema análogo e "
             "proponha prever a saída ou completar lacunas; a dica vem em degraus curtos."),
    "medio": ("Apoio médio: exercícios de ordenar linhas (Parsons, com distratores) ou "
              "completar; dica só sob demanda, depois de uma tentativa do aluno."),
    "baixo": ("Apoio baixo: problema aberto (modificar ou criar); só perguntas, sem "
              "exemplo pronto; dica só depois de uma tentativa concreta."),
}


class ErroDeEstado(Exception):
    """Erro esperado, com mensagem curta em português para o aluno."""


# ---------------------------------------------------------------- caminho e disco

def caminho():
    """Caminho do arquivo de estado (TUTTOR_ESTADO ou ~/.tutor/estado.json)."""
    return os.environ.get("TUTTOR_ESTADO") or os.path.join(
        os.path.expanduser("~"), ".tutor", "estado.json")


def _pasta_segura(arq, criar):
    pasta = os.path.dirname(os.path.abspath(arq))
    if os.path.islink(pasta):
        raise ErroDeEstado("a pasta do estado é um link simbólico; recusei por segurança")
    if not os.path.isdir(pasta):
        if not criar:
            return False
        os.makedirs(pasta, mode=0o700, exist_ok=True)
        if os.path.islink(pasta) or not os.path.isdir(pasta):
            raise ErroDeEstado("a pasta do estado não é uma pasta comum")
    return True


def _vazio():
    return {"versao": 1, "temas": {}, "pedidos": {}}


def _texto(valor, limite):
    s = re.sub(r"\s+", " ", re.sub(r"[\x00-\x1f\x7f]", " ", str(valor))).strip()
    return s[:limite]


def _inteiro(valor, minimo, maximo, padrao):
    if isinstance(valor, bool) or not isinstance(valor, int):
        return padrao
    return max(minimo, min(maximo, valor))


def _data(valor):
    try:
        return date.fromisoformat(str(valor))
    except ValueError:
        return None


def _tema_limpo(bruto, hoje):
    """Valida um tema lido do disco; devolve None se não tiver conserto."""
    if not isinstance(bruto, dict):
        return None
    intervalo = _inteiro(bruto.get("intervalo_dias"), 0, ESCADA[-1], 0)
    proxima = _data(bruto.get("proxima_revisao")) or hoje + timedelta(days=max(intervalo, 1))
    historico = []
    brutos = bruto.get("historico")
    for ev in (brutos if isinstance(brutos, list) else [])[-MAX_HISTORICO:]:
        if isinstance(ev, dict):
            historico.append({k: _texto(ev.get(k, ""), MAX_NOTA)
                              for k in ("em", "resultado", "dicas", "origem", "nota")})
    return {
        "dominio": _inteiro(bruto.get("dominio"), 0, 4, 0),
        "intervalo_dias": intervalo,
        "proxima_revisao": proxima.isoformat(),
        "acertos_seguidos": _inteiro(bruto.get("acertos_seguidos"), 0, 10**6, 0),
        "tentativas": _inteiro(bruto.get("tentativas"), 0, 10**6, 0),
        "dicas_total": _inteiro(bruto.get("dicas_total"), 0, 10**6, 0),
        "ultima": (_data(bruto.get("ultima")) or hoje).isoformat(),
        "historico": historico,
    }


def _normalizar(bruto, hoje):
    estado = _vazio()
    if not isinstance(bruto, dict):
        return estado
    temas = bruto.get("temas")
    for slug, dados in (temas.items() if isinstance(temas, dict) else []):
        if isinstance(slug, str) and SLUG.match(slug) and len(estado["temas"]) < MAX_TEMAS:
            limpo = _tema_limpo(dados, hoje)
            if limpo:
                estado["temas"][slug] = limpo
    pedidos = bruto.get("pedidos")
    for slug, lista in (pedidos.items() if isinstance(pedidos, dict) else []):
        if not (isinstance(slug, str) and SLUG.match(slug) and isinstance(lista, list)):
            continue
        itens = [{"t": float(p["t"]), "n": _inteiro(p.get("n"), 1, 4, 1)}
                 for p in lista if isinstance(p, dict)
                 and isinstance(p.get("t"), (int, float)) and not isinstance(p.get("t"), bool)]
        if itens and len(estado["pedidos"]) < MAX_TEMAS:
            estado["pedidos"][slug] = itens[-MAX_PEDIDOS:]
    return estado


def carregar(caminho_arq=None):
    """Lê o estado. Arquivo ausente: estado vazio. JSON corrompido: renomeia e recomeça."""
    arq = caminho_arq or caminho()
    if not _pasta_segura(arq, criar=False) and not os.path.lexists(arq):
        return _vazio()
    if os.path.islink(arq):
        raise ErroDeEstado("o arquivo de estado é um link simbólico; recusei por segurança")
    if not os.path.exists(arq):
        return _vazio()
    try:
        with open(arq, encoding="utf-8") as f:
            bruto = json.load(f)
        if not isinstance(bruto, dict):
            raise ValueError("raiz não é objeto")
    except (ValueError, UnicodeDecodeError):
        try:
            os.replace(arq, arq + ".corrompido")
        except OSError:
            pass
        return _vazio()
    except OSError as e:
        raise ErroDeEstado(f"não consegui ler o estado ({e.strerror})") from e
    return _normalizar(bruto, date.today())


def salvar(estado, caminho_arq=None):
    """Grava de forma atômica (arquivo temporário + os.replace), sem seguir link."""
    arq = os.path.abspath(caminho_arq or caminho())
    _pasta_segura(arq, criar=True)
    if os.path.islink(arq):
        raise ErroDeEstado("o arquivo de estado é um link simbólico; recusei por segurança")
    dados = json.dumps(estado, ensure_ascii=False, indent=1, sort_keys=True)
    fd, tmp = tempfile.mkstemp(prefix=".estado-", suffix=".tmp", dir=os.path.dirname(arq))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(dados)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, arq)
    except OSError as e:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise ErroDeEstado(f"não consegui gravar o estado ({e.strerror})") from e


# ---------------------------------------------------------------- regras

def validar_slug(tema):
    if not isinstance(tema, str) or not SLUG.match(tema):
        raise ErroDeEstado("tema inválido: use minúsculas, números e hífen "
                           "(ex.: async-await, laco-for), até 60 caracteres")
    return tema


def nivel_de_apoio(dominio):
    """Domínio 0-1 alto; 2 médio; 3-4 baixo."""
    return "alto" if dominio <= 1 else ("medio" if dominio == 2 else "baixo")


def _novo_tema(hoje):
    return {"dominio": 0, "intervalo_dias": 0, "proxima_revisao": hoje.isoformat(),
            "acertos_seguidos": 0, "tentativas": 0, "dicas_total": 0,
            "ultima": hoje.isoformat(), "historico": []}


def _proximo_intervalo(atual):
    for passo in ESCADA:
        if passo > atual:
            return passo
    return ESCADA[-1]


def _agora(agora):
    return agora if agora is not None else datetime.now()


def registrar(estado, tema, resultado, dicas=0, origem=None, nota=None, agora=None):
    """Aplica uma tentativa ao tema e devolve um resumo do que mudou."""
    validar_slug(tema)
    if resultado not in RESULTADOS:
        raise ErroDeEstado("resultado deve ser acerto, parcial ou erro")
    if origem is not None and origem not in ORIGENS:
        raise ErroDeEstado("origem deve ser " + ", ".join(ORIGENS))
    if isinstance(dicas, bool) or not isinstance(dicas, int) or dicas < 0:
        raise ErroDeEstado("dicas deve ser um número inteiro, 0 ou mais")
    dicas = min(dicas, MAX_DICAS)
    agora = _agora(agora)
    hoje = agora.date()
    temas = estado["temas"]
    if tema not in temas and len(temas) >= MAX_TEMAS:
        antigo = min(temas, key=lambda s: temas[s]["ultima"])
        del temas[antigo]
    t = temas.setdefault(tema, _novo_tema(hoje))
    antes = (t["dominio"], t["intervalo_dias"])
    efetivo = "parcial" if resultado == "acerto" and dicas >= 2 else resultado
    if efetivo == "acerto" and dicas == 0:
        t["dominio"] = min(4, t["dominio"] + 1)
        t["intervalo_dias"] = _proximo_intervalo(t["intervalo_dias"])
    elif efetivo == "acerto":
        t["intervalo_dias"] = max(t["intervalo_dias"], 1)
    elif efetivo == "parcial":
        t["intervalo_dias"] = 1
    else:
        t["dominio"] = max(0, t["dominio"] - 1)
        t["intervalo_dias"] = 1
    t["acertos_seguidos"] = t["acertos_seguidos"] + 1 if efetivo == "acerto" else 0
    t["tentativas"] += 1
    t["dicas_total"] += dicas
    t["ultima"] = hoje.isoformat()
    t["proxima_revisao"] = (hoje + timedelta(days=t["intervalo_dias"])).isoformat()
    t["historico"].append({"em": agora.isoformat(timespec="seconds"), "resultado": resultado,
                           "dicas": str(dicas), "origem": origem or "",
                           "nota": _texto(nota or "", MAX_NOTA)})
    del t["historico"][:-MAX_HISTORICO]
    estado["pedidos"].pop(tema, None)  # tentativa registrada zera a contagem de pedidos
    return {"tema": tema, "resultado": resultado, "resultado_efetivo": efetivo,
            "dominio_antes": antes[0], "dominio": t["dominio"],
            "intervalo_dias": t["intervalo_dias"], "proxima_revisao": t["proxima_revisao"],
            "nivel_de_apoio": nivel_de_apoio(t["dominio"])}


def dica(estado, tema, nivel, agora=None):
    """Registra um pedido de dica e avisa se parece uma sequência sem tentativa."""
    validar_slug(tema)
    if isinstance(nivel, bool) or not isinstance(nivel, int) or not 1 <= nivel <= 4:
        raise ErroDeEstado("nivel deve ser de 1 a 4")
    agora_ts = _agora(agora).timestamp()
    pedidos = estado["pedidos"]
    for slug in list(pedidos):  # esquece o que saiu da janela
        pedidos[slug] = [p for p in pedidos[slug] if agora_ts - p["t"] <= JANELA_DICAS]
        if not pedidos[slug]:
            del pedidos[slug]
    lista = pedidos.setdefault(tema, [])
    colado = any(0 <= agora_ts - p["t"] < INTERVALO_CURTO for p in lista)
    lista.append({"t": agora_ts, "n": nivel})
    del lista[:-MAX_PEDIDOS]
    muitos = len(lista) >= PEDIDOS_SEQUENCIA
    motivo = None
    if colado:
        motivo = "dois pedidos com menos de 60 segundos entre si"
    elif muitos:
        motivo = "3 ou mais pedidos neste tema em 10 minutos sem registrar uma tentativa"
    while len(pedidos) > MAX_TEMAS:
        del pedidos[next(iter(pedidos))]
    return {"tema": tema, "nivel": nivel, "dicas_em_sequencia": motivo is not None,
            "motivo": motivo, "pedidos_recentes": len(lista)}


def apoio(estado, tema):
    validar_slug(tema)
    t = estado["temas"].get(tema)
    dominio = t["dominio"] if t else 0
    nivel = nivel_de_apoio(dominio)
    return {"tema": tema, "dominio": dominio, "nivel": nivel, "visto": t is not None,
            "significado": NIVEIS_DE_APOIO[nivel]}


def _resumo_tema(slug, t):
    return {"tema": slug, "dominio": t["dominio"], "nivel_de_apoio": nivel_de_apoio(t["dominio"]),
            "proxima_revisao": t["proxima_revisao"], "intervalo_dias": t["intervalo_dias"],
            "tentativas": t["tentativas"], "dicas_total": t["dicas_total"]}


def vencidos(estado, hoje=None, limite=5):
    """Temas com revisão para hoje ou atrasada, os mais atrasados primeiro."""
    hoje = hoje or date.today()
    lista = [(t["proxima_revisao"], slug) for slug, t in estado["temas"].items()
             if t["tentativas"] > 0 and t["proxima_revisao"] <= hoje.isoformat()]
    return [_resumo_tema(slug, estado["temas"][slug]) for _, slug in sorted(lista)[:limite]]


def fracos(estado, limite=3):
    """Temas de domínio baixo (0 a 2) já tentados, do mais fraco para o menos fraco."""
    lista = [(t["dominio"], t["acertos_seguidos"], slug) for slug, t in estado["temas"].items()
             if t["tentativas"] > 0 and t["dominio"] <= 2]
    return [_resumo_tema(slug, estado["temas"][slug]) for _, _, slug in sorted(lista)[:limite]]


def revisar(estado, limite=5, hoje=None):
    """Vencidos primeiro; se sobrar vaga, completa com os mais fracos."""
    itens = [dict(i, motivo="vencido") for i in vencidos(estado, hoje, limite)]
    usados = {i["tema"] for i in itens}
    for i in fracos(estado, limite):
        if len(itens) < limite and i["tema"] not in usados:
            itens.append(dict(i, motivo="fraco"))
    return itens


def resumo(estado):
    return [_resumo_tema(s, t) for s, t in sorted(estado["temas"].items())]


# ---------------------------------------------------------------- linha de comando

class _Analisador(argparse.ArgumentParser):
    def error(self, message):
        raise ErroDeEstado("uso inválido (" + message + "); veja o cabeçalho de estado.py")


def _parser():
    p = _Analisador(prog="tuttor-estado", add_help=False)
    sub = p.add_subparsers(dest="cmd", parser_class=_Analisador)
    for nome in ("registrar", "dica", "apoio", "revisar", "resumo", "caminho"):
        s = sub.add_parser(nome, add_help=False)
        s.add_argument("--json", action="store_true")
        if nome in ("registrar", "dica", "apoio"):
            s.add_argument("--tema", required=True)
        if nome == "registrar":
            s.add_argument("--resultado", required=True)
            s.add_argument("--dicas", type=int, default=0)
            s.add_argument("--origem")
            s.add_argument("--nota")
        if nome == "dica":
            s.add_argument("--nivel", type=int, required=True)
        if nome == "revisar":
            s.add_argument("--limite", type=int, default=5)
    return p


def _linha_tema(i):
    return (f"- {i['tema']}: domínio {i['dominio']}/4, apoio {i['nivel_de_apoio']}, "
            f"próxima revisão {i['proxima_revisao']}")


def _texto_saida(cmd, r):
    if cmd == "registrar":
        s = (f"Registrado: {r['tema']} ({r['resultado']}"
             + (", contado como parcial por 2+ dicas" if r["resultado_efetivo"] != r["resultado"]
                else "") + f"). Domínio {r['dominio_antes']} -> {r['dominio']} de 4; "
             f"próxima revisão em {r['intervalo_dias']} dia(s), {r['proxima_revisao']}; "
             f"apoio {r['nivel_de_apoio']}.")
        return s
    if cmd == "dica":
        if r["dicas_em_sequencia"]:
            return (f"AVISO dicas_em_sequencia ({r['motivo']}). Não desça o degrau: peça uma "
                    f"tentativa concreta do aluno antes da próxima dica de {r['tema']}.")
        return f"Dica nível {r['nivel']} registrada para {r['tema']}. Sem aviso de sequência."
    if cmd == "apoio":
        visto = "" if r["visto"] else " (tema ainda não visto)"
        return (f"{r['tema']}{visto}: domínio {r['dominio']}/4, apoio {r['nivel']}.\n"
                + r["significado"])
    if cmd == "revisar":
        if not r:
            return "Nada para revisar agora."
        return "Para revisar:\n" + "\n".join(f"{_linha_tema(i)} [{i['motivo']}]" for i in r)
    if cmd == "resumo":
        if not r:
            return "Nenhum tema registrado ainda."
        linhas = [_linha_tema(i) for i in r[:50]]
        if len(r) > 50:
            linhas.append(f"... e mais {len(r) - 50} tema(s)")
        return "Temas:\n" + "\n".join(linhas)
    return r["caminho"]


def main(argv=None):
    try:
        args = _parser().parse_args(argv)
        if not args.cmd:
            raise ErroDeEstado("faltou o subcomando: registrar, dica, apoio, revisar, "
                               "resumo ou caminho")
        if args.cmd == "caminho":
            res = {"caminho": caminho()}
        else:
            estado = carregar()
            if args.cmd == "registrar":
                res = registrar(estado, args.tema, args.resultado, args.dicas, args.origem,
                                args.nota)
                salvar(estado)
            elif args.cmd == "dica":
                res = dica(estado, args.tema, args.nivel)
                salvar(estado)
            elif args.cmd == "apoio":
                res = apoio(estado, args.tema)
            elif args.cmd == "revisar":
                res = revisar(estado, max(1, min(args.limite, 50)))
            else:
                res = resumo(estado)
        if args.json:
            print(json.dumps(res, ensure_ascii=False))
        else:
            print(_texto_saida(args.cmd, res))
        return 0
    except ErroDeEstado as e:
        print(f"tuttor-estado: {e}", file=sys.stderr)
    except Exception:  # nunca vaza traceback para o aluno
        print("tuttor-estado: erro inesperado; o estado não foi alterado", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
