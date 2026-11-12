#!/usr/bin/env bash
# Instalador do kit: cria links simbólicos de bin/{COMANDO,COMANDO-vigia,COMANDO-estado} (nomes
# vindos de projeto.env) em TUTTOR_BIN_DIR (padrão ~/.local/bin) apontando para este clone, e
# registra o que instalou num manifesto em ${XDG_DATA_HOME:-~/.local/share}/<NOME>/instalado.
# Não toca em ~/.claude (o plugin é carregado pelo lançador) e não apaga ~/.tutor.
set -euo pipefail

VERSAO_MINIMA_CLAUDE="2.1.295"   # abaixo disso a trava (guard.py) não tem falha fechada
PYTHON_MINIMO="3.9"

KIT="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

uso() {
  cat <<'FIM'
Uso: bash install.sh [opção]

  (sem opção)    instala os links simbólicos (idempotente)
  --dry-run      só mostra o que faria; não grava nada
  --forcar       sobrescreve no destino o que não é link deste kit
  --uninstall    remove só o que está no manifesto e ainda aponta para este kit
  --verificar    confere versão e ambiente (python, claude, git, PATH, manifesto, gerados)
  --ajuda        mostra esta ajuda

Variáveis: TUTTOR_BIN_DIR (padrão ~/.local/bin), XDG_DATA_HOME (padrão ~/.local/share).
FIM
}

# ---------------------------------------------------------------- projeto.env

NOME=""; COMANDO=""; VERSAO=""
ler_projeto_env() {
  local arquivo="$KIT/projeto.env" chave valor
  [ -f "$arquivo" ] || { echo "erro: não achei $arquivo" >&2; exit 2; }
  while IFS='=' read -r chave valor || [ -n "$chave" ]; do
    case "$chave" in
      NOME) NOME="${valor//[\"\']/}" ;;
      COMANDO) COMANDO="${valor//[\"\']/}" ;;
      VERSAO) VERSAO="${valor//[\"\']/}" ;;
      *) ;;
    esac
  done < "$arquivo"
  if [ -z "$NOME" ] || [ -z "$COMANDO" ] || [ -z "$VERSAO" ]; then
    echo "erro: projeto.env sem NOME, COMANDO ou VERSAO" >&2
    exit 2
  fi
}

# ---------------------------------------------------------------- utilidades

DRY=0; FORCAR=0; MODO="instalar"

aponta_para() {  # aponta_para <link> <alvo>: o link existe e aponta para o alvo
  local destino resolvido
  [ -L "$1" ] || return 1
  destino="$(readlink "$1")"
  [ "$destino" = "$2" ] && return 0
  resolvido="$(readlink -f "$1" 2>/dev/null || true)"
  [ -n "$resolvido" ] && [ "$resolvido" = "$2" ]
}

versao_ge() {  # versao_ge A B: A >= B (números separados por ponto)
  local -a a b
  local i x y
  IFS=. read -r -a a <<< "$1"
  IFS=. read -r -a b <<< "$2"
  for i in 0 1 2; do
    x="${a[$i]:-0}"; y="${b[$i]:-0}"
    [ "$x" -gt "$y" ] && return 0
    [ "$x" -lt "$y" ] && return 1
  done
  return 0
}

pasta_dos_dados() { printf '%s' "${XDG_DATA_HOME:-$HOME/.local/share}/$NOME"; }
pasta_dos_binarios() { printf '%s' "${TUTTOR_BIN_DIR:-$HOME/.local/bin}"; }

nomes_dos_binarios() { printf '%s\n' "$COMANDO" "$COMANDO-vigia" "$COMANDO-estado"; }

# ---------------------------------------------------------------- instalar

instalar() {
  local bin_dir data manifesto nome alvo destino conflitos=0
  bin_dir="$(pasta_dos_binarios)"
  data="$(pasta_dos_dados)"
  manifesto="$data/instalado"

  for nome in $(nomes_dos_binarios); do
    alvo="$KIT/bin/$nome"
    destino="$bin_dir/$nome"
    if [ ! -f "$alvo" ]; then
      echo "erro: não achei $alvo" >&2
      exit 2
    fi
    if [ -e "$destino" ] || [ -L "$destino" ]; then
      if aponta_para "$destino" "$alvo"; then
        continue
      fi
      if [ -d "$destino" ] && [ ! -L "$destino" ]; then
        echo "erro: $destino é um diretório; não mexo nele" >&2
        conflitos=1
      elif [ "$FORCAR" -eq 0 ]; then
        echo "erro: $destino já existe e não é link para este kit (use --forcar para substituir)" >&2
        conflitos=1
      fi
    fi
  done
  [ "$conflitos" -eq 0 ] || exit 1

  if [ "$DRY" -eq 0 ]; then
    mkdir -p "$bin_dir" "$data"
  fi
  for nome in $(nomes_dos_binarios); do
    alvo="$KIT/bin/$nome"
    destino="$bin_dir/$nome"
    if aponta_para "$destino" "$alvo"; then
      echo "já instalado: $destino"
      continue
    fi
    [ -x "$alvo" ] || echo "aviso: $alvo não tem permissão de execução (chmod +x)" >&2
    if [ "$DRY" -eq 1 ]; then
      echo "[dry-run] ln -s $alvo $destino"
      continue
    fi
    if [ -e "$destino" ] || [ -L "$destino" ]; then
      rm -f -- "$destino"
    fi
    ln -s "$alvo" "$destino"
    echo "instalado: $destino -> $alvo"
  done

  if [ "$DRY" -eq 1 ]; then
    echo "[dry-run] gravaria o manifesto $manifesto"
    return 0
  fi
  local temporario="$manifesto.novo.$$"
  {
    echo "# $NOME: links instalados por install.sh (não edite)"
    echo "versao=$VERSAO"
    echo "kit=$KIT"
    for nome in $(nomes_dos_binarios); do
      echo "link=$bin_dir/$nome"
    done
  } > "$temporario"
  mv -f -- "$temporario" "$manifesto"
  echo "manifesto: $manifesto"
  case ":$PATH:" in
    *":$bin_dir:"*) ;;
    *) echo "aviso: $bin_dir não está no PATH; acrescente ao seu shell:"
       echo "  export PATH=\"$bin_dir:\$PATH\"" ;;
  esac
  echo "Pronto. Rode '$COMANDO' dentro da pasta do seu projeto."
}

# ---------------------------------------------------------------- desinstalar

desinstalar() {
  local data manifesto linha link removidos=0
  data="$(pasta_dos_dados)"
  manifesto="$data/instalado"
  if [ ! -f "$manifesto" ]; then
    echo "nada a remover: não achei o manifesto $manifesto"
  else
    while IFS= read -r linha || [ -n "$linha" ]; do
      case "$linha" in
        link=*) ;;
        *) continue ;;
      esac
      link="${linha#link=}"
      if aponta_para "$link" "$KIT/bin/$(basename "$link")"; then
        if [ "$DRY" -eq 1 ]; then
          echo "[dry-run] removeria $link"
        else
          rm -f -- "$link"
          echo "removido: $link"
        fi
        removidos=$((removidos + 1))
      else
        echo "mantido: $link (não aponta mais para este kit)"
      fi
    done < "$manifesto"
    if [ "$DRY" -eq 1 ]; then
      echo "[dry-run] removeria o manifesto $manifesto"
    else
      rm -f -- "$manifesto"
      rmdir "$data" 2>/dev/null || true
    fi
  fi
  echo "Seu perfil e seu diário em ~/.tutor ficaram intocados (apague à mão, se quiser)."
}

# ---------------------------------------------------------------- verificar

PROBLEMAS=0; AVISOS=0
ok() { echo "ok:    $*"; }
aviso() { echo "aviso: $*"; AVISOS=$((AVISOS + 1)); }
falha() { echo "FALHA: $*"; PROBLEMAS=$((PROBLEMAS + 1)); }

verificar() {
  local saida versao bin_dir data manifesto instalada
  echo "$NOME $VERSAO (clone em $KIT)"

  if command -v python3 >/dev/null 2>&1; then
    if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)"; then
      ok "python3 $(python3 -c 'import platform; print(platform.python_version())') (mínimo $PYTHON_MINIMO)"
    else
      falha "python3 abaixo de $PYTHON_MINIMO"
    fi
  else
    falha "python3 não encontrado"
  fi

  if command -v claude >/dev/null 2>&1; then
    saida="$(claude --version 2>&1 || true)"
    if [[ "$saida" =~ ([0-9]+\.[0-9]+\.[0-9]+) ]]; then
      versao="${BASH_REMATCH[1]}"
      if versao_ge "$versao" "$VERSAO_MINIMA_CLAUDE"; then
        ok "claude $versao (mínimo $VERSAO_MINIMA_CLAUDE)"
      else
        falha "claude $versao é anterior a $VERSAO_MINIMA_CLAUDE: nessa versão a trava de escrita NÃO tem falha fechada (se o guard.py falhar, a ação passa). Atualize o Claude Code"
      fi
    else
      falha "não consegui ler a versão do claude (saída: $saida)"
    fi
  else
    falha "claude não encontrado no PATH (instale o Claude Code)"
  fi

  if command -v git >/dev/null 2>&1; then
    ok "git presente"
  else
    aviso "git não encontrado: o lançador não poderá esconder .tutor/ do repositório"
  fi

  bin_dir="$(pasta_dos_binarios)"
  case ":$PATH:" in
    *":$bin_dir:"*) ok "$bin_dir está no PATH" ;;
    *) aviso "$bin_dir não está no PATH" ;;
  esac

  data="$(pasta_dos_dados)"
  manifesto="$data/instalado"
  if [ -f "$manifesto" ]; then
    instalada=""
    while IFS= read -r linha || [ -n "$linha" ]; do
      case "$linha" in
        versao=*) instalada="${linha#versao=}" ;;
        *) ;;
      esac
    done < "$manifesto"
    if [ "$instalada" = "$VERSAO" ]; then
      ok "versão instalada $instalada = projeto.env"
    else
      aviso "versão instalada (${instalada:-?}) difere de projeto.env ($VERSAO): rode install.sh de novo"
    fi
    local nome
    for nome in $(nomes_dos_binarios); do
      if aponta_para "$bin_dir/$nome" "$KIT/bin/$nome"; then
        ok "link $bin_dir/$nome"
      else
        aviso "link $bin_dir/$nome ausente ou aponta para outro lugar"
      fi
    done
  else
    aviso "kit não instalado (sem manifesto em $manifesto): rode install.sh"
  fi

  if command -v python3 >/dev/null 2>&1; then
    if python3 "$KIT/tools/gerar.py" --conferir >/dev/null 2>&1; then
      ok "arquivos gerados em dia (tools/gerar.py --conferir)"
    else
      falha "arquivos gerados desatualizados: rode python3 tools/gerar.py"
    fi
  fi

  echo "resumo: $PROBLEMAS falha(s), $AVISOS aviso(s)"
  [ "$PROBLEMAS" -eq 0 ]
}

# ---------------------------------------------------------------- principal

while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run) DRY=1 ;;
    --forcar) FORCAR=1 ;;
    --uninstall) MODO="desinstalar" ;;
    --verificar) MODO="verificar" ;;
    --ajuda|-h|--help) uso; exit 0 ;;
    *) echo "opção desconhecida: $1" >&2; uso >&2; exit 2 ;;
  esac
  shift
done

ler_projeto_env
case "$MODO" in
  instalar) instalar ;;
  desinstalar) desinstalar ;;
  verificar) verificar ;;
  *) echo "modo inválido: $MODO" >&2; exit 2 ;;
esac
