## O que muda e por quê / What changes and why

## Lista / Checklist

- [ ] `python3 -m pytest tests -q -p no:cacheprovider` passa / passes
- [ ] `python3 tools/gerar.py --conferir` passa (rodei `tools/gerar.py` se precisou) / passes (ran the generator if needed)
- [ ] `python3 tools/varredura.py` passa; nada pessoal / passes; nothing personal
- [ ] ruff e shellcheck limpos / clean
- [ ] Afirmações pedagógicas têm fonte em `docs/pesquisa/`; flags de CLI têm fonte oficial / Pedagogical claims have a source in `docs/pesquisa/`; CLI flags have an official source
- [ ] A trava de escrita não ficou mais fraca (ou há teste novo em `tests/test_guard.py`) / The write lock was not weakened (or a new test is in `tests/test_guard.py`)

**O que testei de verdade e o que não testei / What I really tested and what I did not**
