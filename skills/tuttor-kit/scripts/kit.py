"""Nomes do kit: NOME, COMANDO, VERSAO, MASCOTE, DONO, DESCRICAO (com reserva segura).

Ordem de leitura, do mais para o menos específico:
  1. `projeto.env` na raiz do repositório (linhas CHAVE=valor; fonte única do projeto);
  2. `assets/kit.json` da skill (gerado por tools/gerar.py; vale quando a skill é instalada
     sozinha, sem `projeto.env`; chaves nome, comando, versao, mascote);
  3. o nome da pasta da skill (`tuttor-kit`); o comando é o primeiro trecho do nome.
Nunca levanta exceção.
"""
import json
import os

_AQUI = os.path.dirname(os.path.abspath(__file__))
_PASTA_SKILL = os.path.dirname(_AQUI)
_RAIZ = os.path.dirname(os.path.dirname(_PASTA_SKILL))


def raiz_do_kit():
    """Raiz do repositório (a pasta que contém `skills/` e, se existir, `projeto.env`)."""
    return _RAIZ


def _ler_env(caminho):
    dados = {}
    try:
        with open(caminho, encoding="utf-8", errors="replace") as f:
            for linha in f:
                linha = linha.split("#", 1)[0].strip()
                if "=" in linha:
                    chave, valor = linha.split("=", 1)
                    dados[chave.strip()] = valor.strip().strip("\"'")
    except OSError:
        pass
    return dados


def _ler_kit_json(caminho):
    """kit.json -> dicionário com as mesmas chaves de projeto.env (NOME, COMANDO, ...)."""
    try:
        with open(caminho, encoding="utf-8", errors="replace") as f:
            bruto = json.load(f)
    except (OSError, ValueError):
        return {}
    if not isinstance(bruto, dict):
        return {}
    return {chave.upper(): valor for chave, valor in bruto.items()
            if isinstance(chave, str) and isinstance(valor, str)}


_ENV = _ler_env(os.path.join(_RAIZ, "projeto.env"))
_JSON = _ler_kit_json(os.path.join(_PASTA_SKILL, "assets", "kit.json"))
_NOME_PASTA = os.path.basename(_PASTA_SKILL) or "tuttor-kit"


def _valor(chave, padrao=""):
    return _ENV.get(chave) or _JSON.get(chave) or padrao


NOME = _valor("NOME", _NOME_PASTA)
COMANDO = _valor("COMANDO") or NOME.split("-")[0]
VERSAO = _valor("VERSAO", "desconhecida")
MASCOTE = _valor("MASCOTE")
DONO = _valor("DONO")  # só em projeto.env; kit.json não o carrega
DESCRICAO = _valor("DESCRICAO")  # só em projeto.env
PREFIXO_ENV = "".join(c for c in COMANDO.upper() if c.isalnum()) or "TUTTOR"
