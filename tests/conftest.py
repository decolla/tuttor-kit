"""Configuração comum dos testes: caminhos do kit e uma HOME isolada por teste."""
import os
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent


def _pasta_da_skill():
    skills = [p for p in (RAIZ / "skills").iterdir() if (p / "scripts" / "guard.py").is_file()]
    assert len(skills) == 1, f"esperava exatamente uma skill principal, achei {skills}"
    return skills[0]


SKILL = _pasta_da_skill()
SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(SCRIPTS))


@pytest.fixture
def raiz():
    return RAIZ


@pytest.fixture
def skill():
    return SKILL


@pytest.fixture
def scripts():
    return SCRIPTS


@pytest.fixture
def projeto(tmp_path, monkeypatch):
    """Projeto de aluno vazio, com HOME isolada (nada toca a HOME real)."""
    casa = tmp_path / "home"
    proj = tmp_path / "proj"
    casa.mkdir()
    proj.mkdir()
    monkeypatch.setenv("HOME", str(casa))
    monkeypatch.setenv("USERPROFILE", str(casa))
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    for var in list(os.environ):
        if var.startswith(("TUTTOR_", "TUTOR_")) or var.endswith("_API_KEY"):
            monkeypatch.delenv(var, raising=False)
    monkeypatch.chdir(proj)
    return proj
