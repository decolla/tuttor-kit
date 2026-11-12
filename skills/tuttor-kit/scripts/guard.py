#!/usr/bin/env python3
"""Trava de escrita do modo tutor (hook PreToolUse).

Garante mecanicamente que o tutor não escreva o código do aluno.

Decisões possíveis para cada chamada de ferramenta:

- ``allow``  escrita dentro da pasta ``.tutor/`` do projeto ou de ``~/.tutor/``
             (materiais, trilhas e notas);
- ``deny``   escrita fora dessas pastas ou comando que altera arquivos ou o ambiente;
- ``ask``    não dá para provar que o comando só lê: quem decide é o aluno;
- (nada)     comando reconhecido como leitura ou como build/teste/execução do projeto
             na forma simples: segue o fluxo normal de permissão do CLI.

Princípios:

1. Lista de permissão, não de bloqueio: o que a trava não reconhece vira pergunta.
2. Comandos que executam código (testes, compiladores, gerenciadores) só passam na
   forma simples; qualquer opção fora da lista conhecida vira pergunta.
3. ``bash -c``, ``eval``, ``$(...)``, crases, ``xargs`` e ``find -exec`` são analisados
   recursivamente.
4. Nada escrito pelo tutor em ``.tutor/`` é executado sem o aluno confirmar.
5. Falha fechada: erro interno vira ``ask``, nunca ``allow``.

O que a trava NÃO cobre está em docs/seguranca.md (por exemplo: rodar o programa do
aluno executa código arbitrário, por definição). Só usa a biblioteca padrão.
"""
import json
import os
import re
import shutil
import sys

PASS, ASK, DENY = 0, 1, 2
PASTA = ".tutor"

FERRAMENTAS_DE_ESCRITA = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
FERRAMENTAS_DE_COMANDO = {"Bash", "Monitor"}

MSG_ESCRITA = (
    "Modo tutor: você não escreve nem edita o código do aluno. Só é permitido criar "
    "arquivos dentro da pasta .tutor/ do projeto ou em ~/.tutor/ (materiais, exercícios, "
    "notas). Em vez de editar, explique o que o aluno deve mudar e por quê, usando a "
    "escada de dicas, e deixe que ele mesmo digite."
)
MSG_NEGADO = (
    "Modo tutor: este comando altera arquivos ou o ambiente ({motivo}) e foi bloqueado. "
    "Explique ao aluno o que fazer e deixe que ele execute. Leitura (ls, cat, grep, "
    "git diff/log/status) e build/testes/execução do projeto continuam liberados."
)
MSG_PERGUNTA = (
    "Modo tutor: a trava não conseguiu confirmar que este comando só lê ({motivo}). "
    "Aluno: aprove apenas se você entende o que ele faz e ele não altera seu código."
)

# ------------------------------------------------------------------ tabelas

PALAVRAS_RESERVADAS = {"if", "then", "else", "elif", "fi", "while", "until", "do", "done",
                       "{", "}", "!", "esac", "in"}
CABECALHOS = {"for", "select", "case", "function"}  # o resto do comando não é executável

# Variáveis que podem ser definidas sem mudar *o que* é executado.
ENV_SEGURO = {
    "ASPNETCORE_ENVIRONMENT", "DOTNET_ENVIRONMENT", "DOTNET_CLI_TELEMETRY_OPTOUT",
    "DOTNET_NOLOGO", "NODE_ENV", "DEBUG", "LANG", "LC_ALL", "LANGUAGE", "TZ", "CI",
    "NO_COLOR", "FORCE_COLOR", "CLICOLOR", "COLUMNS", "LINES", "PYTHONUNBUFFERED",
    "PYTHONDONTWRITEBYTECODE", "PYTHONIOENCODING", "RUST_BACKTRACE",
}

# Comandos que nunca executam seus argumentos. Valor: opções que gravam ou executam.
_SEM_RISCO = (
    "ls ll la dir cat head tail grep egrep fgrep wc cut tr nl tac rev fold column paste "
    "join comm diff cmp stat which whereis type pwd cd pushd popd dirs echo printf true "
    "false test [ [[ ]] : date cal whoami id groups hostname uname uptime ps pgrep free "
    "df du lsof ss netstat ping dig nslookup host basename dirname realpath readlink jq "
    "od hexdump strings md5sum sha1sum sha256sum sha512sum cksum base64 seq expr bc "
    "sleep wait tput clear tty locale help nproc lscpu lsblk getconf zcat zgrep bzcat "
    "xzcat read shift return exit break continue set unset shopt ulimit printenv more"
).split()
LEITORES = {nome: () for nome in _SEM_RISCO}
LEITORES.update({
    "sort": ("-o", "--output", "--compress-program"),
    "uniq": (), "xxd": ("-r",),
    "less": ("-o", "-O", "--log-file", "--LOG-FILE", "-k", "--lesskey-file"),
    "zless": ("-o", "-O", "--log-file", "--LOG-FILE", "-k", "--lesskey-file"),
    "bat": ("--pager",), "batcat": ("--pager",),
    "rg": ("--pre", "--pre-glob", "--hostname-bin"),
    "ag": ("--pager",), "ack": ("--pager",),
    "man": ("-P", "--pager", "-H", "--html"),
    "tree": ("-o",), "file": ("-C", "--compile"), "sdiff": ("-o", "--output"),
    "yq": ("-i", "--inplace", "--in-place"),
})

SEMPRE_NEGADO = {
    "rm", "rmdir", "unlink", "shred", "mv", "cp", "touch", "truncate", "dd", "tee",
    "install", "ln", "chmod", "chown", "chgrp", "patch", "ed", "ex", "vi", "vim", "nvim",
    "nano", "emacs", "pico", "sponge", "mkfifo", "mknod", "rsync", "scp", "sftp", "ftp",
    "zip", "gzip", "gunzip", "bzip2", "bunzip2", "xz", "unxz", "7z", "crontab", "at",
    "mkdir", "nuget", "prettier", "black", "autopep8", "isort", "gofmt", "rustfmt",
    "clang-format", "csharpier", "dos2unix", "unix2dos", "iconv", "split", "csplit",
    "mktemp", "chattr", "setfacl", "mount", "umount",
}
# Tolerados quando todos os caminhos de destino estão dentro de .tutor/.
SOMENTE_EM_TUTOR = {"mkdir", "touch", "tee", "rm", "rmdir", "cp", "mv"}

ENVOLTORIOS = {"command", "builtin", "time", "nohup", "nice", "ionice", "stdbuf",
               "timeout", "setsid", "chronic", "unbuffer", "watch", "caffeinate"}
OPCOES_COM_VALOR = {"-n", "-k", "-s", "-c", "-o", "-e", "-i", "--signal", "--kill-after",
                    "--interval"}
SHELLS = {"bash", "sh", "zsh", "dash", "ksh", "fish", "ash"}
INTERPRETADORES = ("python", "node", "nodejs", "ruby", "perl", "php", "lua", "Rscript",
                   "pwsh", "powershell", "osascript", "tclsh", "julia", "groovy", "scala",
                   "elixir", "ghci", "irb", "jshell")
INDICIOS_DE_ESCRITA = ("write", "open(", "remove", "unlink", "rename", "shutil", "fs.",
                       "rmtree", "mkdir", "copyfile", "system(", "subprocess", "exec(",
                       "popen", "file.", "path(", "savefile", "tofile", "dump(", "spawn",
                       "child_process", "os.", "io.", "fopen", "file_put_contents")
PYTHON_LETRAS_INOFENSIVAS = set("BbdEIOqsSuvxV")
PYTHON_M_SEGURO = {"doctest", "json.tool", "timeit", "py_compile", "compileall",
                   "tokenize", "ast", "dis", "platform", "site", "sysconfig", "calendar"}

# Executores: (opções sem valor, opções com valor, padrões aceitos). Fora disso, pergunta.
_VERBOSO = {"-q", "-v", "-vv", "-vvv", "--quiet", "--verbose", "-h", "--help", "--version"}
EXECUTORES = {
    "pytest": (_VERBOSO | {"-x", "-s", "-l", "--lf", "--ff", "--co", "--collect-only",
                           "--no-header", "--disable-warnings", "--no-cov", "-rA", "-ra",
                           "-rs", "-rf", "--strict-markers", "--exitfirst", "--showlocals",
                           "--last-failed", "--failed-first", "--sw", "--stepwise"},
               {"-k", "-m", "--maxfail", "--tb", "--durations", "-W", "-n", "--cov",
                "--timeout"}, ()),
    "unittest": (_VERBOSO | {"-f", "-b", "--failfast", "--buffer"},
                 {"-s", "-p", "-t", "-k"}, ()),
    "jest": (_VERBOSO | {"--runInBand", "-i", "--ci", "--coverage", "--silent", "--bail",
                         "-b", "--passWithNoTests", "--run", "--no-cache"},
             {"-t", "--testNamePattern", "--testPathPattern", "-g", "--grep", "--filter",
              "-R", "-e", "--watchAll", "--watch"}, ()),
    "lint": (_VERBOSO | {"--strict", "--noEmit", "--pretty", "--ignore-missing-imports",
                         "--show-error-codes"},
             {"--max-warnings", "--ext", "--format", "-f", "--max-line-length", "--select",
              "--ignore", "--disable", "--enable", "-p", "--project", "--python-version"}, ()),
    "cc": ({"-c", "-g", "-pthread", "-pedantic", "-shared", "-static", "-v", "--version",
            "-E", "-S", "-fPIC", "-fpic"},
           {"-o", "-I", "-L", "-l", "-D", "-include"},
           (r"-W[\w=,-]*", r"-O[0-3sgz]?", r"-g\w*", r"-std=[\w+]+", r"-[ILlD].+",
            r"-fsanitize=[\w,]+", r"-m(32|64)", r"-fno-[\w-]+", r"-f(lto|openmp|stack-protector)")),
    "rustc": ({"-O", "-g", "--test", "-v", "--version"},
              {"-o", "--edition", "--crate-name", "--crate-type", "-A", "-W", "-D"}, ()),
    "javac": ({"-g", "-verbose", "-nowarn", "-version", "--version"},
              {"-d", "-cp", "-classpath", "--class-path", "-sourcepath", "--release",
               "-source", "-target", "-encoding"}, (r"-Xlint(:[\w,-]+)?",)),
    "java": ({"-ea", "-esa", "-version", "--version", "--enable-preview", "-server"},
             {"-cp", "-classpath", "--class-path", "-jar"},
             (r"-Xm[sx]\d+[kmgKMG]?", r"-Xss\d+[kmgKMG]?", r"-D[\w.]+=[\w./:-]*")),
    "simples": (_VERBOSO, set(), ()),  # compiladores e ferramentas sem opções conhecidas
    "make": ({"-k", "-s", "-B", "-n", "--dry-run", "--no-print-directory", "--keep-going",
              "--silent", "--always-make", "-h", "--help", "--version"},
             {"-j", "--jobs"}, (r"-j\d+",)),
    "dotnet": ({"--no-build", "--no-restore", "--nologo", "--no-incremental",
                "--list-tests", "--blame", "--no-launch-profile", "--self-contained",
                "--no-self-contained", "--tl", "-h", "--help", "--version", "--info",
                "--list-sdks", "--list-runtimes", "--outdated", "--include-transitive",
                "--vulnerable", "--deprecated", "--no-dependencies", "--force",
                "--disable-build-servers"},
               {"-c", "--configuration", "--project", "--filter", "-v", "--verbosity",
                "-f", "--framework", "-r", "--runtime", "--launch-profile", "--urls",
                "--collect", "--logger", "-l", "--arch", "-a", "--os", "--environment",
                "-e"}, ()),
    "cargo": ({"--release", "-r", "--workspace", "--all", "--all-targets",
               "--all-features", "--no-default-features", "--lib", "--bins", "--tests",
               "--examples", "-q", "-v", "--offline", "--locked", "--frozen", "--no-run",
               "-h", "--help", "--version"},
              {"-p", "--package", "--features", "--bin", "--test", "--example", "-j",
               "--jobs", "--color"}, ()),
    "go": ({"-v", "-race", "-short", "-cover", "-failfast", "-json", "-x", "-a", "-h"},
           {"-run", "-count", "-bench", "-timeout", "-tags", "-parallel", "-cpu",
            "-benchtime"}, ()),
    "npm": ({"--silent", "-s", "--if-present", "--workspaces", "-ws", "--json", "--long",
             "-l", "--all", "-a", "--production", "--omit", "-h", "--help", "--version",
             "-g", "--global", "-v"},
            {"--workspace", "-w", "--depth", "--prefix", "--loglevel"}, ()),
}
PARA_EXECUTOR = {
    "pytest": "pytest", "py.test": "pytest", "jest": "jest", "vitest": "jest",
    "mocha": "jest", "phpunit": "jest", "rspec": "jest", "ctest": "jest",
    "mypy": "lint", "pyflakes": "lint", "pylint": "lint", "flake8": "lint",
    "eslint": "lint", "tsc": "lint", "ruff": "lint",
    "gcc": "cc", "g++": "cc", "cc": "cc", "c++": "cc", "clang": "cc", "clang++": "cc",
    "rustc": "rustc", "javac": "javac", "kotlinc": "javac", "java": "java",
    "ghc": "simples", "swiftc": "simples", "csc": "simples", "msbuild": "simples",
    "make": "make", "gmake": "make", "just": "make", "task": "make", "ninja": "make",
}
EXTENSOES_DE_SAIDA = {"", ".o", ".obj", ".out", ".exe", ".so", ".dylib", ".a", ".lib",
                      ".class", ".dll", ".bin", ".wasm", ".jar", ".rlib"}
ARGS_QUE_REESCREVEM = re.compile(
    r"^--?(fix|write|update\w*|u|o|out\w*|output\w*|init|save\w*|force|in-?place|i|"
    r"updateSnapshot|ci-update)(=|$)", re.I)
SCRIPTS_QUE_REESCREVEM = re.compile(
    r"(format|fmt|fix|prettier|codegen|generate|migrat|scaffold|install|clean|release|"
    r"publish|deploy)", re.I)
LOGGER_SEGURO = re.compile(r"^(console|trx|html)(;verbosity=\w+)?$", re.I)

GIT_LEITURA = {"status", "diff", "log", "show", "blame", "rev-parse", "ls-files",
               "ls-tree", "ls-remote", "describe", "shortlog", "grep", "cat-file",
               "reflog", "rev-list", "merge-base", "name-rev", "whatchanged",
               "count-objects", "check-ignore", "check-attr", "diff-tree", "diff-index",
               "diff-files", "for-each-ref", "show-ref", "show-branch", "var", "version",
               "help", "annotate", "range-diff", "cherry", "verify-commit", "verify-tag"}
GIT_ALTERA = {"add", "commit", "apply", "am", "checkout", "restore", "reset", "clean",
              "merge", "rebase", "cherry-pick", "revert", "rm", "mv", "switch", "push",
              "pull", "init", "clone", "fetch", "gc", "prune", "filter-branch", "bisect",
              "update-index", "update-ref", "write-tree", "commit-tree", "hash-object",
              "notes", "replace", "sparse-checkout", "lfs", "format-patch", "bundle",
              "archive", "mergetool", "difftool", "gui", "citool", "send-email"}
GIT_OPCOES_QUE_EXECUTAM = ("--output", "--textconv", "--ext-diff", "--open-files-in-pager",
                           "--upload-pack", "--receive-pack", "--exec", "-O", "-u")

_NPM = ({"test", "t", "run", "run-script", "start", "ls", "list", "ll", "la", "view",
         "info", "show", "outdated", "audit", "why", "explain", "version", "help",
         "root", "prefix", "bin", "ping", "doctor", "search", "fund"},
        {"install", "i", "add", "ci", "remove", "rm", "uninstall", "un", "update", "up",
         "upgrade", "dedupe", "prune", "link", "unlink", "publish", "pack", "init",
         "create", "rebuild", "set", "pkg", "exec", "x", "dlx", "cache", "login",
         "adduser", "logout", "shrinkwrap", "config"})
_PIP = ({"list", "show", "freeze", "check", "help", "index", "inspect", "debug", "search",
         "info", "outdated", "tree", "why"},
        {"install", "uninstall", "download", "wheel", "cache", "config", "add", "remove",
         "update", "upgrade", "sync", "lock", "init", "new", "build", "publish", "venv",
         "create", "env", "tap", "untap", "link", "unlink", "autoremove", "purge",
         "reinstall", "pin", "unpin", "tool", "python", "self", "run"})
GERENCIADORES = {
    # nome: (subcomandos liberados, subcomandos negados, executor); o resto vira pergunta
    "npm": _NPM + ("npm",), "yarn": _NPM + ("npm",), "pnpm": _NPM + ("npm",),
    "cargo": ({"build", "b", "test", "t", "run", "r", "check", "c", "clippy", "bench",
               "doc", "tree", "metadata", "search", "version", "help", "verify-project"},
              {"install", "uninstall", "add", "remove", "rm", "update", "fmt", "fix",
               "new", "init", "publish", "generate-lockfile", "vendor", "clean", "login"},
              "cargo"),
    "go": ({"build", "test", "run", "vet", "version", "env", "list", "doc", "help"},
           {"get", "install", "fmt", "fix", "generate", "mod", "work", "clean"}, "go"),
    "mvn": ({"test", "compile", "verify", "validate", "package", "dependency:tree"},
            {"install", "deploy", "clean", "archetype:generate"}, "simples"),
    "gradle": ({"test", "build", "check", "tasks", "dependencies", "projects", "run",
                "assemble", "compileJava", "compileKotlin"},
               {"clean", "init", "wrapper", "publish"}, "simples"),
}
for _nome in ("pip", "pip3", "pipx", "uv", "poetry", "conda", "gem", "composer", "brew",
              "apt", "apt-get", "dnf", "yum", "pacman", "snap", "choco", "winget", "scoop"):
    GERENCIADORES[_nome] = _PIP + ("simples",)
GERENCIADORES["mvnw"] = GERENCIADORES["mvn"]
GERENCIADORES["gradlew"] = GERENCIADORES["gradle"]

DOTNET_LIBERADO = {"build", "test", "run", "restore", "publish", "pack", "watch", "list",
                   "msbuild", "vstest", "help", "sdk", "clean"}
DOTNET_NEGADO = {"add", "new", "remove", "format", "sln", "nuget", "workload", "store",
                 "migrate", "build-server", "dev-certs"}
DOTNET_EF_NEGADO = {"migrations add", "migrations remove", "migrations script",
                    "migrations bundle", "database update", "database drop",
                    "dbcontext scaffold", "dbcontext optimize", "dbcontext script"}
DOTNET_EF_LIBERADO = {"migrations list", "migrations has-pending-model-changes",
                      "dbcontext info", "dbcontext list"}

DOCKER_LIBERADO = {"ps", "images", "logs", "inspect", "version", "info", "stats", "top",
                   "port", "diff", "history", "events", "search", "context"}
DOCKER_NEGADO = {"cp", "rm", "rmi", "push", "commit", "prune", "save", "load", "import",
                 "export", "login", "logout"}
COMPOSE_LIBERADO = {"ps", "logs", "config", "top", "images", "version", "ls", "port",
                    "events"}
KUBECTL_LIBERADO = {"get", "describe", "logs", "top", "version", "api-resources",
                    "api-versions", "explain", "cluster-info", "auth", "diff"}
KUBECTL_NEGADO = {"apply", "delete", "create", "replace", "patch", "edit", "scale",
                  "rollout", "cp", "exec", "run", "drain", "cordon", "taint", "label",
                  "annotate", "set", "expose", "autoscale"}
MAKE_LIBERADO = {"", "all", "build", "test", "tests", "check", "run", "lint", "compile",
                 "help", "bench", "unit", "integration"}

MCP_ALTERA = re.compile(r"(write|edit|creat|delet|remov|updat|move|renam|push|commit|"
                        r"insert|drop|exec|run_|upload|apply|patch|put_|post_|set_|"
                        r"mkdir|save|append|replace|merge|deploy)", re.I)
DESTINOS_INOFENSIVOS = {"/dev/null", "/dev/stdout", "/dev/stderr", "/dev/tty",
                        "/dev/fd/1", "/dev/fd/2"}
CURINGAS = "*?["


# ------------------------------------------------------------------ caminhos

def raizes_permitidas(cwd):
    """Pastas .tutor/ reconhecidas: a do diretório atual, a do projeto e a global."""
    bases = [cwd or os.getcwd(), os.environ.get("CLAUDE_PROJECT_DIR", ""),
             os.path.expanduser("~")]
    raizes = []
    for base in bases:
        if not base or not os.path.isabs(base):
            continue
        if os.path.islink(os.path.join(base, PASTA)):
            continue  # .tutor não pode ser um atalho para outro lugar
        raiz = os.path.join(os.path.realpath(base), PASTA)
        if raiz not in raizes:
            raizes.append(raiz)
    return raizes


def dentro_de_tutor(caminho, cwd, a_propria_pasta=False):
    """True se o caminho real fica dentro de <projeto>/.tutor/ ou de ~/.tutor/.

    `..` e links simbólicos são resolvidos antes da comparação; arquivos com link
    físico para outro lugar são recusados. Chaves (expansão do shell) nunca valem, e
    curingas só valem depois da pasta .tutor/ e sem `..` no caminho. A própria pasta
    só conta com `a_propria_pasta` (usado por `mkdir -p .tutor`).
    """
    if not isinstance(caminho, str) or not caminho:
        return False
    if any(ch in caminho for ch in "$`\n\x00{}"):
        return False
    tem_curinga = any(ch in caminho for ch in CURINGAS)
    if tem_curinga and ".." in caminho.replace("\\", "/").split("/"):
        return False
    caminho = os.path.expanduser(caminho)
    if caminho.startswith("~"):
        return False  # ~usuario que não foi expandido
    cwd = cwd or os.getcwd()
    if not os.path.isabs(caminho):
        caminho = os.path.join(cwd, caminho)
    normal = os.path.normpath(caminho)
    if tem_curinga:  # avalia só a parte fixa, antes do primeiro curinga
        corte = min(normal.find(ch) for ch in CURINGAS if ch in normal)
        normal = os.path.dirname(normal[:corte]) or os.sep
        a_propria_pasta = True  # ".tutor/*" expande para dentro da pasta
    real = os.path.realpath(normal)
    try:
        info = os.lstat(real)
        if not os.path.isdir(real) and info.st_nlink > 1:
            return False  # link físico: escrever aqui alteraria outro arquivo
    except OSError:
        pass  # ainda não existe
    for raiz in raizes_permitidas(cwd):
        if real.startswith(raiz + os.sep) or (a_propria_pasta and real == raiz):
            return True
    return False


def _pedacos(arg):
    """Partes de um argumento que podem ser caminhos (--opcao=caminho, a:b, a,b)."""
    return [p for p in re.split(r"[=:,;]", arg) if p and not p.startswith("-")]


# ------------------------------------------------------------------ análise léxica

class ErroDeSintaxe(ValueError):
    """Comando que a trava não conseguiu interpretar (vira pergunta ao aluno)."""


class Palavra:
    __slots__ = ("texto", "dinamica", "substituicoes")

    def __init__(self, texto=""):
        self.texto = texto
        self.dinamica = False     # tem $VAR, ${...} ou $((...)): valor desconhecido
        self.substituicoes = []   # comandos dentro de $(...), `...`, <(...), >(...)

    def __repr__(self):
        return f"Palavra({self.texto!r})"


def _fecha_parenteses(s, i):
    """`i` aponta para logo depois de '('. Retorna o índice do ')' correspondente."""
    nivel, n = 1, len(s)
    while i < n:
        ch = s[i]
        if ch == "\\":
            i += 2
            continue
        if ch == "'":
            j = s.find("'", i + 1)
            if j < 0:
                raise ErroDeSintaxe("aspas simples sem fechar")
            i = j + 1
            continue
        if ch == '"':
            i += 1
            while i < n and s[i] != '"':
                i += 2 if s[i] == "\\" else 1
            if i >= n:
                raise ErroDeSintaxe("aspas duplas sem fechar")
            i += 1
            continue
        if ch == "(":
            nivel += 1
        elif ch == ")":
            nivel -= 1
            if nivel == 0:
                return i
        i += 1
    raise ErroDeSintaxe("parênteses sem fechar")


def _cifrao(s, i, palavra):
    """Trata o que vem depois de '$' em s[i]. Retorna o novo índice."""
    n = len(s)
    prox = s[i + 1] if i + 1 < n else ""
    if prox == "(":
        if s.startswith("$((", i):
            fim = s.find("))", i + 3)
            if fim < 0:
                raise ErroDeSintaxe("$(( sem fechar")
            interno = s[i + 3:fim]
            if "$(" in interno or "`" in interno:
                palavra.substituicoes.append(interno)
            palavra.dinamica = True
            return fim + 2
        fim = _fecha_parenteses(s, i + 2)
        palavra.substituicoes.append(s[i + 2:fim])
        palavra.dinamica = True
        return fim + 1
    if prox == "{":
        fim = s.find("}", i + 2)
        if fim < 0:
            raise ErroDeSintaxe("${ sem fechar")
        interno = s[i + 2:fim]
        if "$(" in interno or "`" in interno:
            palavra.substituicoes.append(interno)
        palavra.dinamica = True
        return fim + 1
    if prox.isalnum() or (prox and prox in "_@*#?!$-"):
        palavra.dinamica = True
        j = i + 2
        if prox.isalpha() or prox == "_":
            while j < n and (s[j].isalnum() or s[j] == "_"):
                j += 1
        return j
    palavra.texto += "$"
    return i + 1


def _crase(s, i, palavra):
    j = i + 1
    while j < len(s) and s[j] != "`":
        j += 2 if s[j] == "\\" else 1
    if j >= len(s):
        raise ErroDeSintaxe("crase sem fechar")
    palavra.substituicoes.append(s[i + 1:j])
    palavra.dinamica = True
    return j + 1


OPERADORES = ("&&", "||", ";;", "|&", ";", "|", "&", "(", ")")
REDIRECIONADORES = ("&>>", "<<<", "<<-", "&>", ">>", ">|", ">&", "<<", "<&", "<>", ">", "<")


def tokenizar(s):
    """Divide um comando de shell em tokens.

    Retorna (tokens, heredocs), com tokens em ("p", Palavra) | ("op", str) |
    ("r", operador, fd). Os corpos de heredoc são retirados da sequência de tokens.
    """
    tokens, heredocs = [], []
    pendentes = []  # (delimitador, remove_tabs)
    palavra = None
    i, n = 0, len(s)

    def fecha():
        nonlocal palavra
        if palavra is not None:
            tokens.append(("p", palavra))
            palavra = None

    def abre():
        nonlocal palavra
        if palavra is None:
            palavra = Palavra()
        return palavra

    while i < n:
        ch = s[i]
        if ch == "\n":
            fecha()
            tokens.append(("op", ";"))
            i += 1
            while pendentes:  # consome os corpos de heredoc
                delim, tira_tabs = pendentes.pop(0)
                corpo = []
                while i < n:
                    fim = s.find("\n", i)
                    linha = s[i:] if fim < 0 else s[i:fim]
                    i = n if fim < 0 else fim + 1
                    if (linha.lstrip("\t") if tira_tabs else linha) == delim:
                        break
                    corpo.append(linha)
                heredocs.append("\n".join(corpo))
            continue
        if ch in " \t\r":
            fecha()
            i += 1
            continue
        if ch == "#" and palavra is None:
            fim = s.find("\n", i)
            i = n if fim < 0 else fim
            continue
        if ch == "\\":
            if i + 1 < n and s[i + 1] == "\n":
                i += 2
                continue
            abre().texto += s[i + 1] if i + 1 < n else ""
            i += 2
            continue
        if ch == "'":
            j = s.find("'", i + 1)
            if j < 0:
                raise ErroDeSintaxe("aspas simples sem fechar")
            abre().texto += s[i + 1:j]
            i = j + 1
            continue
        if ch == '"':
            p = abre()
            i += 1
            while True:
                if i >= n:
                    raise ErroDeSintaxe("aspas duplas sem fechar")
                c2 = s[i]
                if c2 == '"':
                    i += 1
                    break
                if c2 == "\\" and i + 1 < n:
                    p.texto += s[i + 1]
                    i += 2
                elif c2 == "$":
                    i = _cifrao(s, i, p)
                elif c2 == "`":
                    i = _crase(s, i, p)
                else:
                    p.texto += c2
                    i += 1
            continue
        if ch == "$":
            i = _cifrao(s, i, abre())
            continue
        if ch == "`":
            i = _crase(s, i, abre())
            continue
        if ch in "<>" and i + 1 < n and s[i + 1] == "(":  # substituição de processo
            fim = _fecha_parenteses(s, i + 2)
            p = abre()
            p.substituicoes.append(s[i + 2:fim])
            p.dinamica = True
            i = fim + 1
            continue
        redir = next((r for r in REDIRECIONADORES if s.startswith(r, i)), None)
        if redir:
            fd = ""
            if palavra is not None and palavra.texto.isdigit() and not palavra.dinamica:
                fd, palavra = palavra.texto, None
            fecha()
            tokens.append(("r", redir, fd))
            i += len(redir)
            if redir in ("<<", "<<-"):
                j = i
                while j < n and s[j] in " \t":
                    j += 1
                k = j
                while k < n and s[k] not in " \t\n;&|<>()":
                    k += 1
                delim = s[j:k].replace("'", "").replace('"', "").replace("\\", "")
                if not delim:
                    raise ErroDeSintaxe("heredoc sem delimitador")
                pendentes.append((delim, redir == "<<-"))
                tokens.append(("p", Palavra(delim)))
                i = k
            continue
        op = next((o for o in OPERADORES if s.startswith(o, i)), None)
        if op:
            fecha()
            tokens.append(("op", op))
            i += len(op)
            continue
        abre().texto += ch
        i += 1
    fecha()
    return tokens, heredocs


def comandos_simples(tokens):
    """Agrupa os tokens em comandos simples: (palavras, redirecionamentos, vem_de_pipe)."""
    saida, palavras, redirs = [], [], []
    vem_de_pipe = False
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok[0] == "op":
            if palavras or redirs:
                saida.append((palavras, redirs, vem_de_pipe))
            palavras, redirs = [], []
            vem_de_pipe = tok[1] in ("|", "|&")
        elif tok[0] == "r":
            if i + 1 >= len(tokens) or tokens[i + 1][0] != "p":
                raise ErroDeSintaxe("redirecionamento sem destino")
            redirs.append((tok[1], tok[2], tokens[i + 1][1]))
            i += 1
        else:
            palavras.append(tok[1])
        i += 1
    if palavras or redirs:
        saida.append((palavras, redirs, vem_de_pipe))
    return saida


# ------------------------------------------------------------------ avaliação

class Veredito:
    """Acumula o pior resultado encontrado e o motivo."""

    def __init__(self):
        self.nivel, self.motivo = PASS, ""

    def soma(self, nivel, motivo=""):
        if nivel > self.nivel:
            self.nivel, self.motivo = nivel, motivo
        return self

    @property
    def par(self):
        return self.nivel, self.motivo


class Contexto:
    """Estado que muda ao longo de uma linha de comando."""

    def __init__(self, cwd, profundidade=0, em_tutor=None, cwd_incerto=False):
        self.cwd = cwd or os.getcwd()
        self.profundidade = profundidade
        # o diretório de trabalho está (ou pode estar) dentro de .tutor/
        self.em_tutor = dentro_de_tutor(os.path.join(self.cwd, "x"), self.cwd) \
            if em_tutor is None else em_tutor
        self.cwd_incerto = cwd_incerto  # houve `cd`: caminhos relativos não são confiáveis

    def filho(self):
        return Contexto(self.cwd, self.profundidade + 1, self.em_tutor, self.cwd_incerto)

    def destino(self, caminho, a_propria_pasta=False):
        """Nível para gravar em `caminho`: PASS dentro de .tutor/, ASK se incerto, DENY fora."""
        if not dentro_de_tutor(caminho, self.cwd, a_propria_pasta):
            return DENY
        if self.cwd_incerto and not os.path.isabs(os.path.expanduser(caminho)):
            return ASK
        return PASS


def _nao_flags(args):
    return [a for a in args if not a.startswith("-")]


ESTADO_SUBCOMANDOS = {"registrar", "dica", "apoio", "revisar", "resumo", "caminho"}
ESTADO_OPCOES = {"--tema", "--resultado", "--dicas", "--origem", "--nota", "--nivel", "--limite"}


def _comando_do_kit(nome):
    """True se `nome` é um executável da pasta bin/ deste kit (e é ele que o PATH acha)."""
    raiz = os.path.dirname(os.path.dirname(os.path.dirname(_scripts_do_kit())))
    do_kit = os.path.join(raiz, "bin", nome)
    if not os.path.isfile(do_kit):
        return False
    achado = shutil.which(nome)
    return achado is None or os.path.realpath(achado) == os.path.realpath(do_kit)


def _scripts_do_kit():
    return os.path.realpath(os.path.dirname(os.path.abspath(__file__)))


def _toca_tutor(args, cwd):
    """True se algum argumento PODE apontar para dentro de .tutor/.

    Usado para decidir se uma execução vira pergunta, então erra para o lado do
    "sim": o que `dentro_de_tutor` recusa por cautela (chaves, variáveis, curingas,
    links físicos) aqui conta como "pode tocar".
    """
    cwd = cwd or os.getcwd()
    raizes = raizes_permitidas(cwd) + [os.path.join(os.path.realpath(b), PASTA)
                                       for b in (cwd, os.path.expanduser("~"))]
    for a in args:
        if PASTA in a or any(ch in a for ch in "{$`"):
            return True
        for p in [a] + _pedacos(a):
            for parte in p.replace("\\", "/").split("/"):
                if parte.startswith(".") and any(ch in parte for ch in CURINGAS):
                    return True  # .tu*, .[t]utor
            cam = os.path.expanduser(p)
            real = os.path.realpath(cam if os.path.isabs(cam) else os.path.join(cwd, cam))
            if any(real == r or real.startswith(r + os.sep) for r in raizes):
                return True
    return False


def _abrevia(base, opcao):
    """True se `base` é uma abreviação aceita de uma opção longa (--out de --output)."""
    return (base.startswith("--") and len(base) > 2 and opcao.startswith("--")
            and opcao.startswith(base))


def _tem_opcao(args, proibidas):
    """Detecta opções proibidas, inclusive coladas (-oARQ) e agrupadas (-no)."""
    for a in args:
        if not a.startswith("-") or a == "-":
            continue
        base = a.split("=", 1)[0]
        for op in proibidas:
            if base == op or _abrevia(base, op):
                return a
            if len(op) == 2 and not a.startswith("--") and op[1] in a[1:]:
                return a
    return None


def _analisa_opcoes(args, regras):
    """Confere as opções contra uma lista de permissão.

    Retorna (posicionais, depois_de_traco_duplo, opcao_desconhecida_ou_None).
    """
    sem_valor, com_valor, padroes = regras
    pos, j = [], 0
    while j < len(args):
        a = args[j]
        if a == "--":
            return pos, args[j + 1:], None
        if not a.startswith("-") or a == "-":
            pos.append(a)
            j += 1
            continue
        base = a.split("=", 1)[0]
        if "=" not in a and base in sem_valor:
            j += 1
        elif base in com_valor:
            j += 1 if "=" in a else 2
        elif not a.startswith("--") and len(a) > 2 and a[:2] in com_valor:
            j += 1  # valor colado: -j8, -kexpr
        elif not a.startswith("--") and len(a) > 2 and all("-" + c in sem_valor for c in a[1:]):
            j += 1  # agrupadas: -qx
        elif any(re.fullmatch(p, a) for p in padroes):
            j += 1
        else:
            return pos, [], a
    return pos, [], None


def _valor_de(args, nomes):
    """Valores das opções `nomes` (separados, com '=' ou colados)."""
    valores = []
    for j, a in enumerate(args):
        for nome in nomes:
            if a == nome and j + 1 < len(args):
                valores.append(args[j + 1])
            elif a.startswith(nome + "="):
                valores.append(a[len(nome) + 1:])
            elif len(nome) == 2 and a.startswith(nome) and len(a) > 2 and not a.startswith("--"):
                valores.append(a[2:])
    return valores


def avaliar(comando, cwd, profundidade=0, contexto=None):
    """Avalia uma linha de comando de shell. Retorna (nivel, motivo)."""
    ctx = contexto or Contexto(cwd, profundidade)
    v = Veredito()
    if ctx.profundidade > 4:
        return ASK, "comandos aninhados demais"
    try:
        tokens, _heredocs = tokenizar(comando)
        simples = comandos_simples(tokens)
    except ErroDeSintaxe as e:
        return ASK, f"sintaxe que a trava não interpreta: {e}"
    for palavras, redirs, vem_de_pipe in simples:
        for op, _fd, alvo in redirs:
            for interno in alvo.substituicoes:
                v.soma(*avaliar(interno, ctx.cwd, contexto=ctx.filho()))
            if ">" not in op:
                continue
            if op in (">&", "<&") and (alvo.texto.isdigit() or alvo.texto == "-"):
                continue
            if alvo.dinamica:
                v.soma(ASK, f"redirecionamento '{op}' para destino variável")
            elif alvo.texto in DESTINOS_INOFENSIVOS:
                continue
            else:
                nivel = ctx.destino(alvo.texto)
                v.soma(nivel, f"redirecionamento '{op} {alvo.texto}'"
                       + (" depois de mudar de pasta" if nivel == ASK else ""))
        for p in palavras:
            for interno in p.substituicoes:
                v.soma(*avaliar(interno, ctx.cwd, contexto=ctx.filho()))
        if palavras:
            tem_heredoc = any(op in ("<<", "<<-", "<<<") for op, _f, _a in redirs)
            v.soma(*avaliar_palavras(palavras, ctx, entrada_externa=vem_de_pipe or tem_heredoc))
    return v.par


def avaliar_palavras(palavras, ctx, entrada_externa=False, via_xargs=False):
    """Avalia um comando simples já dividido em palavras. Retorna (nivel, motivo)."""
    v = Veredito()
    cwd = ctx.cwd
    palavras = list(palavras)
    while palavras and not palavras[0].dinamica and palavras[0].texto in PALAVRAS_RESERVADAS:
        palavras.pop(0)
    if not palavras:
        return PASS, ""
    if not palavras[0].dinamica and palavras[0].texto in CABECALHOS:
        return (ASK, "estrutura 'case'") if palavras[0].texto == "case" else (PASS, "")

    # Atribuições de variável antes do comando (VAR=valor cmd ...).
    while palavras:
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\+?=", palavras[0].texto)
        if not m:
            break
        if m.group(1) not in ENV_SEGURO:
            v.soma(ASK, f"define a variável {m.group(1)}")
        palavras.pop(0)
    if not palavras:
        return v.par

    cabeca = palavras[0]
    if cabeca.dinamica:
        return v.soma(ASK, "o nome do comando vem de variável ou substituição").par
    nome = os.path.basename(cabeca.texto)
    resto = palavras[1:]
    args = [p.texto for p in resto]
    if "/" in cabeca.texto and _toca_tutor([cabeca.texto], cwd):
        return v.soma(ASK, "executa um programa de dentro de .tutor/").par

    def recursivo(novas, **kw):
        return v.soma(*avaliar_palavras(novas, ctx.filho(), **kw)).par

    # --- envoltórios -----------------------------------------------------------
    if nome in ("sudo", "doas", "su", "pkexec"):
        return DENY, f"'{nome}' (privilégios de administrador)"
    if nome == "env":
        while resto:
            t = resto[0].texto
            if t in ("-S", "--split-string"):
                return ASK, "'env -S'"
            if t in ("-u", "--unset", "-C", "--chdir"):
                resto = resto[2:]
            elif t.startswith("-"):
                resto = resto[1:]
            elif re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", t):
                if t.split("=", 1)[0] not in ENV_SEGURO:
                    v.soma(ASK, f"define a variável {t.split('=', 1)[0]}")
                resto = resto[1:]
            else:
                break
        return recursivo(resto) if resto else v.par
    if nome in ENVOLTORIOS:
        while resto:
            t = resto[0].texto
            if t.startswith("-"):
                resto = resto[2:] if t in OPCOES_COM_VALOR else resto[1:]
            elif nome in ("timeout", "watch") and re.match(r"^\d+(\.\d+)?[smhd]?$", t):
                resto = resto[1:]
            else:
                break
        return recursivo(resto) if resto else v.par
    if nome == "xargs":
        com_valor = {"-n", "-I", "-P", "-d", "-L", "-s", "-E", "-a", "--max-args",
                     "--replace", "--max-procs", "--delimiter", "--max-lines",
                     "--arg-file", "-J", "-R"}
        while resto and resto[0].texto.startswith("-"):
            resto = resto[2:] if resto[0].texto in com_valor else resto[1:]
        return recursivo(resto, via_xargs=True) if resto else v.par
    if nome in SHELLS:
        for j, p in enumerate(resto):
            a = p.texto
            if a.startswith("-") and not a.startswith("--") and "c" in a[1:]:
                if j + 1 >= len(resto):
                    return ASK, f"'{nome} -c' sem comando"
                if resto[j + 1].dinamica:
                    v.soma(ASK, f"'{nome} -c' com conteúdo variável")
                return v.soma(*avaliar(resto[j + 1].texto, cwd, contexto=ctx.filho())).par
        scripts = _nao_flags(args)
        if not scripts:
            return v.soma(ASK, f"'{nome}' lendo comandos da entrada").par
        if _toca_tutor(args, cwd) or ctx.em_tutor:
            v.soma(ASK, "executa um script de dentro de .tutor/")
        return v.par
    if nome == "eval":
        if any(p.dinamica for p in resto):
            v.soma(ASK, "'eval' com conteúdo variável")
        return v.soma(*avaliar(" ".join(args), cwd, contexto=ctx.filho())).par
    if nome in ("source", ".", "alias", "trap", "enable", "bind", "complete", "exec",
                "coproc", "hash"):
        return v.soma(ASK, f"'{nome}'").par
    if nome in ("export", "declare", "local", "readonly", "typeset"):
        for a in _nao_flags(args):
            if "=" in a and a.split("=", 1)[0] not in ENV_SEGURO:
                v.soma(ASK, f"define a variável {a.split('=', 1)[0]}")
        return v.par
    if nome in ("cd", "pushd"):
        alvo = next(iter(_nao_flags(args)), "")
        if alvo:
            ctx.cwd_incerto = True
        if any(p.dinamica for p in resto) or (alvo and dentro_de_tutor(alvo, cwd, True)):
            ctx.em_tutor = True
        return v.par

    # --- comandos do próprio kit ----------------------------------------------
    if re.match(r"^[a-z][a-z0-9]*-(estado|vigia)$", nome):
        # Só vale o executável da pasta bin/ do kit, chamado pelo nome, com os
        # argumentos escritos à vista (nada vindo de xargs/find) e fora de .tutor/.
        if "/" in cabeca.texto or not _comando_do_kit(nome):
            return v.soma(ASK, f"'{nome}' não é o comando deste kit").par
        if via_xargs:
            return v.soma(ASK, f"'{nome}' recebendo argumentos de outro comando").par
        if ctx.em_tutor or ctx.cwd_incerto:
            return v.soma(ASK, f"'{nome}' chamado de dentro de .tutor/ ou de pasta incerta").par
        if any(p.dinamica for p in resto):
            return v.soma(ASK, f"'{nome}' com argumentos calculados").par
    if re.match(r"^[a-z][a-z0-9]*-estado$", nome):
        if any(p.dinamica for p in resto) or not args or args[0] not in ESTADO_SUBCOMANDOS:
            return v.soma(ASK, f"'{nome}' com argumentos fora do esperado").par
        j = 1
        while j < len(args):
            if args[j] == "--json":
                j += 1
            elif args[j] in ESTADO_OPCOES and j + 1 < len(args):
                j += 2
            else:
                return v.soma(ASK, f"argumento '{args[j]}' de '{nome}'").par
        return v.par  # só grava o registro de domínio em ~/.tutor/
    if re.match(r"^[a-z][a-z0-9]*-vigia$", nome):
        consulta = {"--resumo", "--leituras", "--estado", "--help", "-h", "--version"}
        if args and all(a in consulta or a.isdigit() for a in args):
            return v.par
        return v.soma(ASK, f"'{nome}' fora dos modos de consulta").par

    # --- arquivos: tolerados só dentro de .tutor/ -----------------------------
    if nome in SOMENTE_EM_TUTOR:
        if any(p.dinamica for p in resto):
            return DENY, f"'{nome}' com caminho variável"
        if any(a == "-t" or a.startswith(("--target-directory", "--backup", "--suffix",
                                          "--link", "--symbolic-link", "--reflink"))
               or a == "-S" for a in args):
            return DENY, f"'{nome}' com opção de destino ou de link"
        if nome == "cp" and any(not a.startswith("--") and a.startswith("-")
                                and set(a[1:]) & set("ls") for a in args):
            return DENY, "'cp' criando link em vez de cópia"
        caminhos = _nao_flags(args)
        if nome == "cp":
            caminhos = caminhos[-1:]  # copiar PARA .tutor/ só grava em .tutor/
        niveis = [ctx.destino(c, a_propria_pasta=(nome == "mkdir")) for c in caminhos]
        if not caminhos or via_xargs or DENY in niveis:
            return DENY, f"'{nome}' fora de .tutor/"
        if ASK in niveis:
            v.soma(ASK, f"'{nome}' com caminho relativo depois de mudar de pasta")
        if nome in ("rm", "rmdir", "mv"):  # as notas do aluno também são dele
            v.soma(ASK, f"'{nome}' apaga ou move arquivos das suas notas")
        return v.par
    if nome in SEMPRE_NEGADO:
        return DENY, f"'{nome}'"

    # --- leitura pura ----------------------------------------------------------
    if nome in LEITORES:
        ruim = _tem_opcao(args, LEITORES[nome])
        if ruim:
            return DENY, f"'{nome} {ruim}' (grava arquivo ou executa comando)"
        if nome in ("uniq", "xxd") and len(_nao_flags(args)) >= 2:
            return DENY, f"'{nome}' com arquivo de saída"
        return v.par
    if nome == "find":
        j = 0
        while j < len(resto):
            t = resto[j].texto
            if t in ("-delete", "-fprint", "-fprintf", "-fls", "-fprint0"):
                return DENY, f"'find {t}'"
            if t in ("-exec", "-execdir", "-ok", "-okdir"):
                fim = j + 1
                while fim < len(resto) and resto[fim].texto not in (";", "+"):
                    fim += 1
                nivel, motivo = avaliar_palavras(resto[j + 1:fim], ctx.filho(), via_xargs=True)
                v.soma(nivel, f"find {t}: {motivo}" if motivo else "")
                j = fim
            j += 1
        return v.par
    if nome == "sed":
        return v.soma(*_sed(args)).par
    if nome in ("awk", "gawk", "mawk", "nawk"):
        return v.soma(*_awk(nome, args)).par
    if nome == "tar":
        modo = args[0] if args else ""
        letras = "" if modo.startswith("--") else modo.lstrip("-")
        longas = [a for a in args if a.startswith("--")
                  and a.split("=", 1)[0] not in ("--list", "--file", "--verbose", "--gzip",
                                                 "--bzip2", "--xz", "--zstd")]
        if longas:
            return DENY, f"'tar {longas[0]}'"
        for a in args[1:]:
            if a.startswith("-") and not a.startswith("--"):
                letras += a[1:]
        if set(letras) - set("tvfzjJ"):
            return DENY, "'tar' com opção que extrai, cria ou executa"
        if "--list" in args or "t" in letras:
            return v.par
        return DENY, "'tar' (extrai ou cria arquivo)"
    if nome == "unzip":
        return v.par if args[:1] in (["-l"], ["-Z"], ["-t"], ["-v"], ["-lv"]) \
            else (DENY, "'unzip' (extrai arquivos)")
    if nome == "wget":
        return v.par if "--spider" in args else (DENY, "'wget' (baixa arquivo)")
    if nome == "curl":
        return v.soma(*_curl(args)).par

    # --- daqui em diante: comandos que executam código -------------------------
    if ctx.em_tutor:
        v.soma(ASK, "executa um comando com a pasta atual dentro de .tutor/")
    if _toca_tutor(args, cwd):
        v.soma(ASK, "usa arquivos de dentro de .tutor/ para compilar ou executar")

    if nome == "git":
        return v.soma(*_git(args)).par
    if nome in ("kill", "pkill", "killall", "systemctl", "service", "launchctl"):
        return v.soma(ASK, f"'{nome}' (processos ou serviços)").par
    if nome in ("docker", "podman", "nerdctl"):
        return v.soma(*_docker(nome, args)).par
    if nome in ("docker-compose", "podman-compose"):
        sub = next(iter(_nao_flags(args)), "")
        return v.par if sub in COMPOSE_LIBERADO else v.soma(ASK, f"'{nome} {sub}'").par
    if nome == "kubectl":
        pos = _nao_flags(args)
        sub = pos[0] if pos else ""
        if sub in KUBECTL_NEGADO:
            return DENY, f"'kubectl {sub}'"
        if sub == "config":
            leitura = {"view", "current-context", "get-contexts", "get-clusters", "get-users"}
            return v.par if set(pos[1:2]) & leitura else (DENY, "'kubectl config' que altera")
        return v.par if sub in KUBECTL_LIBERADO else v.soma(ASK, f"'kubectl {sub}'").par
    if nome in ("npx", "bunx", "pnpx", "uvx", "deno", "bun"):
        return v.soma(ASK, f"'{nome}' (baixa ou executa pacotes)").par
    if nome == "dotnet":
        return v.soma(*_dotnet(args)).par
    if nome in GERENCIADORES:
        return v.soma(*_gerenciador(nome, args)).par
    if nome.startswith(INTERPRETADORES) or nome == "py":
        return v.soma(*_interpretador(nome, resto, cwd, entrada_externa)).par
    if nome in PARA_EXECUTOR:
        return v.soma(*_executor(nome, args, cwd, ctx.cwd_incerto or ctx.em_tutor)).par

    # --- executar um arquivo do projeto (./programa, bin/Debug/app) -----------
    if "/" in cabeca.texto:
        if dentro_de_tutor(cabeca.texto, cwd):
            return v.soma(ASK, "executa um arquivo de dentro de .tutor/").par
        if via_xargs:
            return v.soma(ASK, f"'{cabeca.texto}' recebendo argumentos de outro comando").par
        return v.par  # rodar o programa do aluno é permitido por definição

    return v.soma(ASK, f"comando '{nome}' não reconhecido como somente leitura").par


def _sed(args):
    v = Veredito()
    scripts, j, achou_e = [], 0, False
    while j < len(args):
        a = args[j]
        if a == "--in-place" or a.startswith("--in-place=") \
                or (not a.startswith("--") and re.match(r"^-[a-zA-Z]*i", a)):
            return DENY, "'sed -i'"
        if a in ("-f", "--file") or a.startswith(("--file=", "-f")) and not a.startswith("--"):
            return ASK, "'sed -f' (script em arquivo)"
        if a in ("-e", "--expression") and j + 1 < len(args):
            scripts.append(args[j + 1])
            achou_e = True
            j += 2
            continue
        if a.startswith("--expression="):
            scripts.append(a.split("=", 1)[1])
            achou_e = True
        elif not a.startswith("-") and not achou_e and not scripts:
            scripts.append(a)
        j += 1
    for s in scripts:
        if re.search(r"(^|[;{}\s])w\s+\S", s) or re.search(r"/[gIpm0-9]*w\s", s) \
                or re.search(r"/[gIpm0-9]*e\b", s) or re.search(r"(^|[;{}])\s*e(\s|$)", s):
            v.soma(ASK, "'sed' com comando de escrita ou execução")
    return v.par


def _awk(nome, args):
    programa, j = None, 0
    while j < len(args):
        a = args[j]
        if a in ("-i", "--include") or a.startswith("-i"):
            return DENY, f"'{nome} -i inplace'"
        if a in ("-f", "--file", "-E", "--exec") or a.startswith(("--file=", "--exec=")) \
                or (a.startswith("-f") and not a.startswith("--")):
            return ASK, f"'{nome} -f' (programa em arquivo)"
        if a in ("-v", "--assign", "-F", "--field-separator", "-e", "--source"):
            if a in ("-e", "--source") and j + 1 < len(args):
                programa = (programa or "") + " " + args[j + 1]
            j += 2
            continue
        if not a.startswith("-") and programa is None:
            programa = a
        j += 1
    if programa and any(x in programa for x in (">", "system", "|", "close(", "getline")):
        return ASK, f"programa '{nome}' que pode gravar ou executar"
    return PASS, ""


def _curl(args):
    v = Veredito()
    grava = {"-o", "-O", "--output", "--remote-name", "--remote-name-all", "-T",
             "--upload-file", "-K", "--config", "--create-dirs", "-c", "--cookie-jar",
             "-D", "--dump-header", "--trace", "--trace-ascii", "--stderr", "--libcurl",
             "--hsts", "--etag-save", "--alt-svc", "-J", "--remote-header-name",
             "--output-dir"}
    for j, a in enumerate(args):
        if a in grava or a.split("=", 1)[0] in grava \
                or (not a.startswith("--") and re.match(r"^-[a-zA-Z]*[oOTJKcD]", a)):
            return DENY, f"'curl {a}' (grava ou envia arquivo)"
        if "%output" in a or "%{stderr}" in a:
            return DENY, "'curl -w' gravando arquivo"
        if a in ("-X", "--request") and j + 1 < len(args) \
                and args[j + 1].upper() not in ("GET", "HEAD", "OPTIONS"):
            v.soma(ASK, f"requisição {args[j + 1].upper()} (pode alterar dados)")
        if a in ("-d", "-F") or a.startswith(("--data", "--form", "--json")):
            v.soma(ASK, "requisição com corpo (pode alterar dados)")
    return v.par


def _git(args):
    sub, resto, pula = "", [], False
    for a in args:
        if pula:
            pula = False
        elif not sub and a == "-c":
            return ASK, "'git -c' (configuração temporária pode executar comandos)"
        elif not sub and a in ("-C", "--git-dir", "--work-tree", "--namespace",
                               "--exec-path", "--super-prefix"):
            pula = True
        elif not sub and a.startswith("-"):
            if a.startswith(("--exec-path=", "--config-env")):
                return ASK, f"'git {a}'"
        elif not sub:
            sub = a
        else:
            resto.append(a)
    if not sub:
        return PASS, ""
    pos = _nao_flags(resto)
    for a in resto:
        base = a.split("=", 1)[0]
        if (base in GIT_OPCOES_QUE_EXECUTAM
                or any(_abrevia(base, op) for op in GIT_OPCOES_QUE_EXECUTAM)
                or (sub == "grep" and a.startswith("-O"))):
            return DENY, f"'git {sub} {base}' (grava arquivo ou executa comando)"
    if sub in GIT_ALTERA:
        return DENY, f"'git {sub}'"
    if sub in GIT_LEITURA:
        return PASS, ""
    if sub == "branch":
        altera = {"-d", "-D", "-m", "-M", "-c", "-C", "--delete", "--move", "--copy",
                  "--set-upstream-to", "--unset-upstream", "--edit-description", "-f",
                  "--force", "--track", "--no-track"}
        filtros = {"--list", "-l", "--contains", "--merged", "--no-merged", "--points-at"}
        flags = {a.split("=", 1)[0] for a in resto if a.startswith("-")}
        if flags & altera or (pos and not flags & filtros):
            return DENY, "'git branch' que cria, renomeia ou apaga"
        return PASS, ""
    if sub == "tag":
        flags = {a.split("=", 1)[0] for a in resto if a.startswith("-")}
        if not resto or flags & {"-l", "--list", "-n", "--contains", "--points-at",
                                 "--merged", "--sort"}:
            return PASS, ""
        return DENY, "'git tag' que cria ou apaga"
    if sub == "stash":
        return (PASS, "") if pos[:1] in (["list"], ["show"]) else (DENY, "'git stash'")
    if sub == "remote":
        return (PASS, "") if pos[:1] in ([], ["show"], ["get-url"]) \
            else (DENY, f"'git remote {pos[0]}'")
    if sub == "worktree":
        return (PASS, "") if pos[:1] == ["list"] else (DENY, "'git worktree'")
    if sub == "submodule":
        return (PASS, "") if pos[:1] in ([], ["status"], ["summary"]) \
            else (DENY, "'git submodule'")
    if sub == "config":
        escreve = {"--add", "--unset", "--unset-all", "--replace-all", "--rename-section",
                   "--remove-section", "-e", "--edit", "set", "unset", "edit",
                   "rename-section", "remove-section"}
        le = {"--get", "--get-all", "--get-regexp", "--list", "-l", "--get-urlmatch",
              "get", "list"}
        if set(resto) & escreve:
            return DENY, "'git config' que altera"
        if set(resto) & le or len(pos) <= 1:
            return PASS, ""
        return DENY, "'git config' que altera"
    return ASK, f"'git {sub}'"


def _docker(nome, args):
    pos = _nao_flags(args)
    sub = pos[0] if pos else ""
    if sub and args[0].startswith("-"):
        if any(a in DOCKER_NEGADO for a in pos):
            return DENY, f"'{nome} {' '.join(pos[:2])}'"
        return ASK, f"opção '{args[0]}' antes do subcomando de '{nome}'"
    if sub == "compose":
        s2 = pos[1] if len(pos) > 1 else ""
        return (PASS, "") if s2 in COMPOSE_LIBERADO else (ASK, f"'{nome} compose {s2}'")
    if sub in DOCKER_NEGADO or "prune" in pos:
        return DENY, f"'{nome} {sub}'"
    if sub in ("network", "volume", "image", "container", "system"):
        s2 = pos[1] if len(pos) > 1 else ""
        if s2 in ("ls", "list", "inspect", "df", "info", "logs", "top", "stats", "port",
                  "history", "diff"):
            return PASS, ""
        if s2 in ("rm", "prune", "create", "cp", "commit", "export", "import", "save", "load"):
            return DENY, f"'{nome} {sub} {s2}'"
        return ASK, f"'{nome} {sub} {s2}'"
    if sub in DOCKER_LIBERADO:
        return PASS, ""
    return ASK, f"'{nome} {sub}' (altera contêineres ou imagens)"


def _dotnet(args):
    if not args:
        return PASS, ""
    pos = _nao_flags(args)
    sub = pos[0] if pos else ""
    if not sub:  # só opções: dotnet --version, --info
        _p, _e, ruim = _analisa_opcoes(args, EXECUTORES["dotnet"])
        return (ASK, f"opção '{ruim}' de 'dotnet'") if ruim else (PASS, "")
    if args[0].startswith("-"):
        if any(a in DOTNET_NEGADO for a in pos):
            return DENY, f"'dotnet {' '.join(pos[:2])}'"
        return ASK, f"opção '{args[0]}' antes do subcomando de 'dotnet'"
    if sub in DOTNET_NEGADO:
        if sub == "sln" and "list" in pos[1:]:
            return PASS, ""
        if sub in ("nuget", "workload") and pos[1:2] in (["list"], ["why"], ["verify"],
                                                         ["search"]):
            return PASS, ""
        return DENY, f"'dotnet {sub}'"
    if sub == "tool":
        s2 = pos[1] if len(pos) > 1 else ""
        if s2 in ("list", "search"):
            return PASS, ""
        if s2 in ("install", "update", "uninstall", "restore"):
            return DENY, f"'dotnet tool {s2}'"
        return ASK, f"'dotnet tool {s2}'"
    if sub == "user-secrets":
        s2 = pos[1] if len(pos) > 1 else ""
        return (PASS, "") if s2 == "list" else (DENY, f"'dotnet user-secrets {s2}'")
    if sub == "ef":
        par = " ".join(pos[1:3])
        if par in DOTNET_EF_NEGADO:
            return DENY, f"'dotnet ef {par}'"
        return (PASS, "") if par in DOTNET_EF_LIBERADO else (ASK, f"'dotnet ef {par}'")
    if sub in DOTNET_LIBERADO or sub.endswith((".dll", ".csproj", ".sln", ".slnx", ".fsproj")):
        _p, _depois, ruim = _analisa_opcoes(args, EXECUTORES["dotnet"])
        if ruim:
            return ASK, f"opção '{ruim}' de 'dotnet {sub}'"
        for valor in _valor_de(args, ("--logger", "-l")):
            if not LOGGER_SEGURO.match(valor):
                return ASK, "'--logger' que grava arquivo"
        return PASS, ""
    return ASK, f"'dotnet {sub}'"


def _gerenciador(nome, args):
    liberado, negado, executor = GERENCIADORES[nome]
    pos, depois, ruim = _analisa_opcoes(args, EXECUTORES[executor])
    if ruim:  # opção desconhecida: não dá para saber qual é o subcomando
        crus = _nao_flags(args)
        if any(a in negado for a in crus) or ruim.split("=", 1)[0] == "--fix":
            return DENY, f"'{nome} {' '.join(crus[:2])} {ruim}'"
        return ASK, f"opção '{ruim}' de '{nome}'"
    sub = pos[0] if pos else ""
    if not sub:
        if nome in ("yarn", "pnpm") and not args:
            return DENY, f"'{nome}' (instala dependências)"
        return PASS, ""
    if sub in negado:
        if sub in ("config", "cache") and pos[1:2] in (["get"], ["list"], ["ls"], ["dir"]):
            return PASS, ""
        if nome == "go" and sub == "mod" and pos[1:2] in (["graph"], ["why"], ["verify"]):
            return PASS, ""
        return DENY, f"'{nome} {sub}'"
    if "--fix" in args:
        return DENY, f"'{nome} {sub} --fix'"
    if sub not in liberado:
        if executor == "npm" and SCRIPTS_QUE_REESCREVEM.search(sub):
            return ASK, f"o script '{sub}' pode reescrever arquivos"
        return ASK, f"'{nome} {sub}'"
    if sub == "audit" and "fix" in pos:
        return DENY, f"'{nome} audit fix'"
    if executor == "npm":
        if sub in ("run", "run-script") and len(pos) > 1 and SCRIPTS_QUE_REESCREVEM.search(pos[1]):
            return ASK, f"o script '{pos[1]}' pode reescrever arquivos"
        for a in depois:
            if ARGS_QUE_REESCREVEM.match(a):
                return ASK, f"o argumento '{a}' pode fazer o script reescrever arquivos"
    return PASS, ""


def _saida_segura(alvo, cwd):
    """Saída de compilador: dentro do projeto e sem sobrescrever arquivo de texto."""
    cwd = os.path.realpath(cwd or os.getcwd())
    if any(ch in alvo for ch in "$`{}*?[~") or os.path.basename(alvo).startswith("."):
        return False
    if os.path.splitext(alvo)[1].lower() not in EXTENSOES_DE_SAIDA:
        return False
    real = os.path.realpath(os.path.join(cwd, alvo))
    if not real.startswith(cwd + os.sep):
        return False
    if any(parte.startswith(".") for parte in os.path.relpath(real, cwd).split(os.sep)):
        return False  # .git/, .vscode/, .tutor/, arquivos ocultos
    if os.path.islink(os.path.join(cwd, alvo)):
        return False
    if os.path.isfile(real):
        try:
            with open(real, "rb") as f:
                if b"\0" not in f.read(4096):
                    return False  # existe e parece texto (Makefile, script, fonte)
        except OSError:
            return False
    return True


def _executor(nome, args, cwd=None, cwd_incerto=False):
    tipo = PARA_EXECUTOR[nome]
    pos, _depois, ruim = _analisa_opcoes(args, EXECUTORES[tipo])
    if ruim:
        if ruim.split("=", 1)[0] in ("--fix", "--fix-dry-run", "--init", "--write"):
            return DENY, f"'{nome} {ruim}' (reescreve arquivos)"
        return ASK, f"opção '{ruim}' de '{nome}'"
    if any(a.startswith("@") for a in args):
        return ASK, f"'{nome}' com arquivo de argumentos"
    if tipo in ("cc", "rustc", "javac"):
        for alvo in _valor_de(args, ("-o", "-d")):
            if cwd_incerto:
                return ASK, f"saída '{alvo}' depois de mudar de pasta"
            if not _saida_segura(alvo, cwd):
                return ASK, f"saída '{alvo}' pode sobrescrever um arquivo que não é binário"
    if tipo == "make":
        alvos = [a for a in pos if "=" not in a] or [""]
        if any("=" in a for a in pos):
            return ASK, f"'{nome}' redefinindo variáveis"
        if any(a in ("install", "uninstall", "dist", "distclean") for a in alvos):
            return DENY, f"'{nome} {' '.join(alvos)}'"
        if not all(a in MAKE_LIBERADO for a in alvos):
            return ASK, f"alvo '{nome} {' '.join(alvos)}'"
    return PASS, ""


def _inline(nome, codigo):
    if any(h in codigo.lower() for h in INDICIOS_DE_ESCRITA):
        return DENY, f"código inline em '{nome}' que grava, apaga ou executa"
    return ASK, f"código inline em '{nome}'"


def _interpretador(nome, palavras, cwd, entrada_externa):
    args = [p.texto for p in palavras]
    python = nome.startswith(("python", "py"))
    if args and all(a in ("--version", "-V", "-v", "--help", "-h") for a in args):
        return PASS, ""
    j = 0
    while j < len(args):
        a = args[j]
        seguinte = args[j + 1] if j + 1 < len(args) else ""
        if a == "-":
            return ASK, f"'{nome}' lendo código da entrada"
        if a.startswith("--"):
            if a.split("=", 1)[0] in ("--eval", "--print", "--command", "--execute"):
                return _inline(nome, a.split("=", 1)[1] if "=" in a else seguinte)
            return ASK, f"opção '{a}' de '{nome}'"
        if a.startswith("-") and python:
            letras = a[1:]
            for k, letra in enumerate(letras):
                cola = letras[k + 1:]
                if letra == "c":
                    return _inline(nome, cola or seguinte)
                if letra == "m":
                    modulo = cola or seguinte
                    resto = args[j + (1 if cola else 2):]
                    return _python_m(modulo, resto)
                if letra in "WX":
                    if not cola:
                        j += 1
                    break
                if letra not in PYTHON_LETRAS_INOFENSIVAS:
                    return ASK, f"opção '{a}' de '{nome}'"
            j += 1
            continue
        if a.startswith("-"):
            if re.match(r"^-[a-zA-Z0-9.]*i", a) and nome.startswith(("perl", "ruby")):
                return DENY, f"'{nome} -i' (edita arquivo no lugar)"
            if re.match(r"^-[a-zA-Z0-9]*[eEprc]", a):
                return _inline(nome, seguinte)
            if a in ("-w",):
                j += 1
                continue
            return ASK, f"opção '{a}' de '{nome}'"
        # primeiro argumento que não é opção: o script
        if palavras[j].dinamica:
            return ASK, f"'{nome}' com script variável"
        real = os.path.realpath(os.path.join(cwd or os.getcwd(), os.path.expanduser(a)))
        if real.startswith(_scripts_do_kit() + os.sep):
            return PASS, ""  # scripts do próprio kit (estado, vigia --resumo...)
        return PASS, ""  # rodar o programa do aluno é permitido por definição
    return ASK, f"'{nome}' interativo ou lendo código da entrada"


def _python_m(modulo, resto):
    if modulo == "pip":
        return _gerenciador("pip", resto)
    if modulo in ("ensurepip", "venv", "virtualenv"):
        return DENY, f"'python -m {modulo}'"
    if modulo in ("pytest", "unittest"):
        _p, _d, ruim = _analisa_opcoes(resto, EXECUTORES[modulo])
        return (ASK, f"opção '{ruim}' de '{modulo}'") if ruim else (PASS, "")
    if modulo in ("mypy", "pyflakes", "pylint", "flake8", "ruff"):
        return _executor(modulo, resto)
    return (PASS, "") if modulo in PYTHON_M_SEGURO else (ASK, f"'python -m {modulo}'")


# ------------------------------------------------------------------ decisão

def decidir(ferramenta, entrada, cwd):
    """Decide o que fazer com uma chamada de ferramenta.

    Retorna (decisao, motivo), com decisao em {"allow", "deny", "ask", None}.
    """
    entrada = entrada if isinstance(entrada, dict) else {}
    if ferramenta in FERRAMENTAS_DE_ESCRITA:
        caminho = (entrada.get("file_path") or entrada.get("notebook_path")
                   or entrada.get("path") or "")
        if dentro_de_tutor(caminho, cwd):
            return "allow", "Modo tutor: escrita em .tutor/ é permitida (materiais e notas)."
        return "deny", MSG_ESCRITA
    if ferramenta in FERRAMENTAS_DE_COMANDO:
        comando = entrada.get("command")
        if not isinstance(comando, str) or not comando.strip():
            return None, ""
        nivel, motivo = avaliar(comando, cwd)
        if nivel == DENY:
            return "deny", MSG_NEGADO.format(motivo=motivo)
        if nivel == ASK:
            return "ask", MSG_PERGUNTA.format(motivo=motivo)
        return None, ""
    if ferramenta == "PowerShell":
        return "ask", MSG_PERGUNTA.format(motivo="comandos PowerShell não são analisados")
    if ferramenta.startswith("mcp__") and MCP_ALTERA.search(ferramenta.split("__")[-1]):
        return "ask", MSG_PERGUNTA.format(
            motivo=f"a ferramenta externa '{ferramenta}' pode alterar arquivos ou dados")
    return None, ""


def responder(decisao, motivo, saida=None):
    if decisao:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decisao,
            "permissionDecisionReason": motivo}}, ensure_ascii=False), file=saida or sys.stdout)


def main():
    try:
        dados = json.load(sys.stdin)
        if not isinstance(dados, dict):
            raise ValueError("a entrada não é um objeto JSON")
        decisao, motivo = decidir(str(dados.get("tool_name", "")), dados.get("tool_input"),
                                  str(dados.get("cwd") or ""))
    except Exception as e:  # falha fechada: na dúvida, o aluno decide
        decisao, motivo = "ask", MSG_PERGUNTA.format(
            motivo=f"erro interno da trava ({type(e).__name__})")
    responder(decisao, motivo)
    sys.exit(0)


if __name__ == "__main__":
    main()
