from __future__ import annotations
import sys
import os
import platform as platform_module
from pathlib import Path
import legacy_cli
from extended_cli import EXTRA_COMMANDS

try:
    if getattr(sys, "frozen", False):
        sys.path.append(sys._MEIPASS)
except Exception:
    pass

# ============================================================
# VERSION / KONFIGURATION
# ============================================================
VERSION = "3.1.0"
SUPPORTED_EXTENSIONS = {".nexa", ".my"}

# ============================================================
# NEXA KERN-MODULE
# ============================================================
MODULE_ERRORS: dict[str, Exception] = {}

try:
    from lexer import Lexer
except Exception as error:
    Lexer = None
    MODULE_ERRORS["lexer.py"] = error

try:
    from parser import Parser
except Exception as error:
    Parser = None
    MODULE_ERRORS["parser.py"] = error

try:
    from interpreter import run
except Exception as error:
    run = None
    MODULE_ERRORS["interpreter.py"] = error

try:
    from runtime import GameRuntime
except Exception as error:
    GameRuntime = None
    MODULE_ERRORS["runtime.py"] = error

try:
    from data_service import DataService
except Exception as error:
    DataService = None
    MODULE_ERRORS["data_service.py"] = error

# ============================================================
# PROJEKT-PFADE
# ============================================================
def project_root():
    return Path.cwd()

def find_source_files():
    root = project_root()
    files = []
    for extension in SUPPORTED_EXTENSIONS:
        files.extend(root.rglob(f"*{extension}"))
    return sorted(
        p for p in files
        if "backup-before-3.0.0" not in p.parts
        and ".nexa-cache" not in p.parts
    )

# ============================================================
# AUSGABE-HELFER
# ============================================================
def print_header(title):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)
    print()

def print_help():
    print(f"Nexa CLI v{VERSION}")
    print("Verwendung: nexa <befehl> [argumente]")
    print()
    commands = all_commands()
    print(f"Verfügbare Befehle ({len(commands)}):")
    for name, entry in sorted(commands.items()):
        print(f"  {name:<28} {entry[1]}")

    if legacy_cli.ALIASES:
        print()
        print("Aliase:")
        for alias, target in sorted(legacy_cli.ALIASES.items()):
            print(f"  {alias:<28} -> {target}")
    print()

# ============================================================
# COMPILER-LOGIK (LEXER / PARSER / INTERPRETER)
# ============================================================
def parse_source(source):
    if Lexer is None:
        raise RuntimeError(
            f"Lexer konnte nicht geladen werden: "
            f"{MODULE_ERRORS.get('lexer.py', 'unbekannter Importfehler')}"
        ) from MODULE_ERRORS.get("lexer.py")
    if Parser is None:
        raise RuntimeError(
            f"Parser konnte nicht geladen werden: "
            f"{MODULE_ERRORS.get('parser.py', 'unbekannter Importfehler')}"
        ) from MODULE_ERRORS.get("parser.py")

    lexer = Lexer(source)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    program = parser.parse()
    return tokens, program

def parse_file(path):
    path = Path(path)
    source = path.read_text(encoding="utf-8-sig")
    tokens, program = parse_source(source)
    return source, tokens, program

def run_file(path):
    path = Path(path)
    source, tokens, program = parse_file(path)

    if run is None:
        raise RuntimeError(
            f"Interpreter konnte nicht geladen werden: "
            f"{MODULE_ERRORS.get('interpreter.py', 'unbekannter Importfehler')}"
        ) from MODULE_ERRORS.get("interpreter.py")

    runtime = None
    if GameRuntime is not None:
        try:
            runtime = GameRuntime()
            app_name = path.stem
            if hasattr(runtime, "set_program_name"):
                runtime.set_program_name(app_name)
            elif hasattr(runtime, "program_name"):
                runtime.program_name = app_name
        except Exception as error:
            raise RuntimeError(
                f"Grafik-Runtime konnte nicht initialisiert werden: {error}"
            ) from error

    if runtime is not None:
        return run(program, runtime=runtime)
    return run(program)

# ============================================================
# CLI BEFEHLS-FUNKTIONEN
# ============================================================
def cmd_help(args):
    print_help()
    return 0

def cmd_version(args):
    print(f"Nexa {VERSION}")
    return 0

def cmd_info(args):
    print_header("NEXA INFORMATION")
    print(f"Version:       {VERSION}")
    print("Sprache:       Nexa")
    print("CLI:            Nexa Command Line Interface")
    print(f"Python:        {sys.version.split()}")
    print(f"Plattform:     {platform_module.system()}")
    print(f"Architektur:   {platform_module.machine()}")
    print(f"Projekt:       {project_root()}")
    if Lexer is not None and hasattr(Lexer, "KEYWORDS"):
        print(f"Keywords:      {len(Lexer.KEYWORDS)}")
    return 0

def cmd_about(args):
    print(f"\nNexa\nEine eigene moderne Programmiersprache.\n\nVersion {VERSION}\n")
    return 0

def cmd_doctor(args):
    print_header("NEXA DOCTOR")
    modules = [
        ("lexer.py", Lexer),
        ("parser.py", Parser),
        ("interpreter.py", run),
        ("runtime.py", GameRuntime),
    ]
    failed = 0
    for filename, module in modules:
        if module is None:
            print(
                f"{filename:<20} FEHLER: "
                f"{MODULE_ERRORS.get(filename, 'unbekannter Importfehler')}"
            )
            failed += 1
        else:
            print(f"{filename:<20} OK")
    print()
    if failed:
        print(f"{failed} Modul(e) fehlen oder konnten nicht geladen werden.")
        return 1
    print("Nexa-Kern ist OK.")
    return 0

def cmd_system(args):
    print_header("SYSTEM")
    print("System:", platform_module.system())
    print("Release:", platform_module.release())
    print("Version:", platform_module.version())
    print("Architektur:", platform_module.machine())
    print("Python:", platform_module.python_version())
    print("Prozessor:", platform_module.processor())
    return 0

def cmd_pwd(args):
    print(Path.cwd())
    return 0

def cmd_root(args):
    print(project_root())
    return 0

def cmd_name(args):
    print(project_root().name)
    return 0

def cmd_parent(args):
    print(project_root().parent)
    return 0

def cmd_where(args):
    print(Path(__file__).resolve())
    return 0

def cmd_python(args):
    print(sys.version)
    return 0

def cmd_python_version(args):
    print(platform_module.python_version())
    return 0

def cmd_python_path(args):
    print(sys.executable)
    return 0

def cmd_platform(args):
    print(platform_module.platform())
    return 0

def cmd_env(args):
    for key in sorted(os.environ):
        print(f"{key}={os.environ[key]}")
    return 0

def cmd_run(args):
    if not args:
        path = Path("main.nexa")
        if not path.exists():
            path = Path("main.my")
        if not path.exists():
            print("Keine main.nexa oder main.my gefunden.")
            return 1
    else:
        path = Path(args[0])

    try:
        run_file(path)
        return 0
    except Exception as error:
        print(f"Fehler: {error}", file=sys.stderr)
        return 1

def cmd_exec(args):
    return cmd_run(args)

def cmd_check(args):
    if not args:
        print("Verwendung: nexa check <datei>")
        return 1
    try:
        source, tokens, program = parse_file(args[0])
        print("OK")
        print(f"Zeichen: {len(source)}")
        print(f"Tokens: {len(tokens)}")
        print(f"Statements: {len(program.statements)}")
        return 0
    except Exception as error:
        print(f"Fehler: {error}")
        return 1

def cmd_validate(args):
    return cmd_check(args)

def cmd_tokens(args):
    if not args:
        print("Verwendung: nexa tokens <datei>")
        return 1
    try:
        source, tokens, program = parse_file(args[0])
        for token in tokens:
            print(token)
        return 0
    except Exception as error:
        print(f"Fehler: {error}")
        return 1

def cmd_ast(args):
    if not args:
        print("Verwendung: nexa ast <datei>")
        return 1
    try:
        source, tokens, program = parse_file(args[0])
        print(program)
        return 0
    except Exception as error:
        print(f"Fehler: {error}")
        return 1

def cmd_debug(args):
    if not args:
        print("Verwendung: nexa debug <datei>")
        return 1
    try:
        source, tokens, program = parse_file(args[0])
        print_header("NEXA DEBUG")
        print("Datei:", args[0])
        print("Zeichen:", len(source))
        print("Tokens:", len(tokens))
        print("Statements:", len(program.statements))
        print()
        print("--- ABSTRACT SYNTAX TREE ---")
        print(program)
        return 0
    except Exception as error:
        print(f"Fehler beim Debuggen: {error}")
        return 1

def cmd_commands(args):
    for name in sorted(all_commands()):
        print(name)
    for alias, target in sorted(legacy_cli.ALIASES.items()):
        print(f"{alias} -> {target}")
    return 0


def cmd_keywords(args):
    if Lexer is None:
        print(
            f"Schlüsselwortliste nicht verfügbar: "
            f"{MODULE_ERRORS.get('lexer.py', 'unbekannter Importfehler')}",
            file=sys.stderr,
        )
        return 1

    for keyword in sorted(Lexer.KEYWORDS):
        print(keyword)
    return 0


def cmd_keyword(args):
    if not args:
        print("Verwendung: nexa keyword <wort>", file=sys.stderr)
        return 1
    if Lexer is None:
        print(
            f"Schlüsselwortliste nicht verfügbar: "
            f"{MODULE_ERRORS.get('lexer.py', 'unbekannter Importfehler')}",
            file=sys.stderr,
        )
        return 1

    print("JA" if args[0] in Lexer.KEYWORDS else "NEIN")
    return 0


CURRENT_COMMANDS = {
    "help": (cmd_help, "Zeigt alle verfügbaren Nexa-Befehle"),
    "version": (cmd_version, "Zeigt die Nexa-Version"),
    "info": (cmd_info, "Zeigt Nexa-Informationen"),
    "about": (cmd_about, "Informationen über Nexa"),
    "doctor": (cmd_doctor, "Prüft die Nexa-Installation"),
    "system": (cmd_system, "Zeigt Systeminformationen"),
    "pwd": (cmd_pwd, "Zeigt das aktuelle Verzeichnis"),
    "root": (cmd_root, "Zeigt das Projektverzeichnis"),
    "name": (cmd_name, "Zeigt den Projektnamen"),
    "parent": (cmd_parent, "Zeigt das Elternverzeichnis"),
    "where": (cmd_where, "Zeigt den Pfad von main.py"),
    "python": (cmd_python, "Zeigt die Python-Version"),
    "python_version": (cmd_python_version, "Zeigt nur die Python-Version"),
    "python_path": (cmd_python_path, "Zeigt den Python-Pfad"),
    "platform": (cmd_platform, "Zeigt die Plattform"),
    "env": (cmd_env, "Zeigt Umgebungsvariablen"),
    "run": (cmd_run, "Führt ein Nexa-Programm aus"),
    "exec": (cmd_exec, "Führt ein Nexa-Programm aus"),
    "check": (cmd_check, "Prüft ein Nexa-Programm"),
    "validate": (cmd_validate, "Validiert ein Nexa-Programm"),
    "tokens": (cmd_tokens, "Zeigt Lexer-Tokens"),
    "ast": (cmd_ast, "Zeigt den AST"),
    "debug": (cmd_debug, "Zeigt Debug-Informationen"),
    "keywords": (cmd_keywords, "Listet alle Nexa-Schlüsselwörter"),
    "keyword": (cmd_keyword, "Prüft ein Nexa-Schlüsselwort"),
    "commands": (cmd_commands, "Listet alle Befehle und Aliase"),
}

def all_commands():
    commands = dict(legacy_cli.COMMANDS)
    commands.update(CURRENT_COMMANDS)
    collisions = commands.keys() & EXTRA_COMMANDS.keys()
    if collisions:
        names = ", ".join(sorted(collisions))
        raise RuntimeError(f"Doppelte Nexa-Befehle: {names}")
    commands.update(EXTRA_COMMANDS)
    return commands

# ============================================================
# MAIN DISPATCHER
# ============================================================
def main(argv: list[str] | None = None):
    reconfigure_stdout = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure_stdout):
        reconfigure_stdout(encoding="utf-8", errors="replace")

    commands = all_commands()

    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print_help()
        return 0

    first = args[0]
    path = Path(first)
    if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
        try:
            run_file(path)
            return 0
        except Exception as error:
            print(f"Fehler: {error}", file=sys.stderr)
            return 1

    first = legacy_cli.ALIASES.get(first, first)
    entry = commands.get(first)
    if entry is None:
        print(f"Unbekannter Nexa-Befehl: {first}", file=sys.stderr)
        print("Nutze 'nexa help' für alle Befehle.")
        return 1

    handler = entry[0]
    try:
        return handler(args[1:]) or 0
    except Exception as error:
        print(f"Fehler: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())