# ============================================================
# NEXA 3.20.0
# Hauptprogramm / CLI
# ============================================================

from __future__ import annotations

import sys
import os
import json
import shutil
import hashlib
import datetime
import platform as platform_module
import time
from pathlib import Path


# ============================================================
# VERSION / KONFIGURATION
# ============================================================

VERSION = "3.20.0"

SUPPORTED_EXTENSIONS = {
    ".nexa",
    ".my",
}


# ============================================================
# NEXA MODULE
# ============================================================

try:
    from lexer import Lexer
except Exception:
    Lexer = None

try:
    from parser import Parser
except Exception:
    Parser = None

try:
    from interpreter import run
except Exception:
    run = None

try:
    from runtime import GameRuntime
except Exception:
    GameRuntime = None


try:
    from data_service import DataService
except Exception:
    DataService = None

# ============================================================
# PROJEKT
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
# AUSGABE
# ============================================================

def print_header(title):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)
    print()


# ============================================================
# PARSEN
# ============================================================

def parse_source(source):
    if Lexer is None:
        raise RuntimeError("Lexer konnte nicht geladen werden.")

    if Parser is None:
        raise RuntimeError("Parser konnte nicht geladen werden.")

    lexer = Lexer(source)
    tokens = lexer.tokenize()

    parser = Parser(tokens)
    program = parser.parse()

    return tokens, program


def parse_file(path):
    path = Path(path)

    source = path.read_text(
        encoding="utf-8-sig"
    )

    tokens, program = parse_source(source)

    return source, tokens, program


# ============================================================
# AUSFÜHREN
# ============================================================

def run_file(path):
    path = Path(path)

    source, tokens, program = parse_file(path)

    if run is None:
        raise RuntimeError(
            "Interpreter konnte nicht geladen werden."
        )

    runtime = None

    if GameRuntime is not None:
        try:
            runtime = GameRuntime()

            app_name = path.stem

            if hasattr(runtime, "set_program_name"):
                runtime.set_program_name(app_name)
            elif hasattr(runtime, "program_name"):
                runtime.program_name = app_name

        except Exception:
            runtime = None

    if runtime is not None:
        return run(program, runtime=runtime)

    return run(program)


# ============================================================
# GRUNDLEGENDE BEFEHLE
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
    print(f"Python:        {sys.version.split()[0]}")
    print(f"Plattform:     {platform_module.system()}")
    print(f"Architektur:   {platform_module.machine()}")
    print(f"Projekt:       {project_root()}")

    if Lexer is not None:
        print(f"Keywords:      {len(Lexer.KEYWORDS)}")

    return 0


def cmd_about(args):
    print()
    print("Nexa")
    print("Eine eigene moderne Programmiersprache.")
    print()
    print(f"Version {VERSION}")
    print()
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
            print(f"{filename:<20} FEHLER")
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


# ============================================================
# AUSFÜHRUNG
# ============================================================

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
        print(program)

        return 0

    except Exception as error:
        print(f"Fehler: {error}")
        return 1


def cmd_time(args):
    if not args:
        print("Verwendung: nexa time <datei>")
        return 1

    start = time.perf_counter()

    try:
        run_file(args[0])
    except Exception as error:
        print(f"Fehler: {error}")
        return 1

    elapsed = time.perf_counter() - start

    print()
    print(f"Zeit: {elapsed:.6f} Sekunden")

    return 0


def cmd_benchmark(args):
    if not args:
        print("Verwendung: nexa benchmark <datei>")
        return 1

    start = time.perf_counter()

    try:
        run_file(args[0])
    except Exception as error:
        print(f"Fehler: {error}")
        return 1

    elapsed = time.perf_counter() - start

    print(f"Benchmark: {elapsed:.6f}s")

    return 0


def cmd_analyze(args):
    files = find_source_files()

    print_header("NEXA ANALYSE")

    total_statements = 0

    for path in files:
        try:
            source, tokens, program = parse_file(path)

            print(path)
            print(f"  Zeichen: {len(source)}")
            print(f"  Tokens: {len(tokens)}")
            print(f"  Statements: {len(program.statements)}")

            total_statements += len(program.statements)

        except Exception as error:
            print(f"  FEHLER: {error}")

    print()
    print(f"Gesamt-Statements: {total_statements}")

    return 0


def cmd_scan(args):
    files = find_source_files()

    print_header("NEXA SCAN")

    for path in files:
        print(f"[SCAN] {path}")

    print()
    print(f"{len(files)} Datei(en) gefunden.")

    return 0


def cmd_report(args):
    files = find_source_files()

    report = {
        "nexa_version": VERSION,
        "files": [],
    }

    for path in files:
        entry = {
            "file": str(path),
            "size": path.stat().st_size,
        }

        try:
            source, tokens, program = parse_file(path)

            entry["characters"] = len(source)
            entry["tokens"] = len(tokens)
            entry["statements"] = len(program.statements)
            entry["valid"] = True

        except Exception as error:
            entry["valid"] = False
            entry["error"] = str(error)

        report["files"].append(entry)

    print(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False
        )
    )

    return 0


try:
    from data_service import DataService
except Exception:
    DataService = None

# ============================================================
# PROJEKT
# ============================================================

def cmd_init(args):
    root = project_root()

    main = root / "main.nexa"

    if not main.exists():
        main.write_text(
            'print("Hallo aus Nexa 3.0!");\n',
            encoding="utf-8"
        )

    print(f"Nexa-Projekt initialisiert: {root}")

    return 0


def cmd_new(args):
    if not args or args[0] in ["--help", "-h"]:
        print("Verwendung: nexa new <name> [--game] [--template name]")
        print()
        print("Templates:")
        print("  --basic       Standard-Vorlage (Standard)")
        print("  --game        Spiel-Vorlage mit Fenster, Steuerung, Game-Loop")
        print("  --class       Klassen-Beispiel")
        print("  --import      Import-Beispiel")
        print("  --gui         GUI-Vorlage (Fenster + Zeichnen)")
        return 1

    template = "basic"
    name = None

    for arg in args:
        if arg == "--game":
            template = "game"
        elif arg == "--basic":
            template = "basic"
        elif arg == "--class":
            template = "class"
        elif arg == "--import":
            template = "import"
        elif arg == "--gui":
            template = "gui"
        elif not arg.startswith("-") and name is None:
            name = arg

    if name is None:
        print("Fehler: Kein Name angegeben.")
        print("Verwendung: nexa new <name> [--game]")
        return 1

    if not name.endswith(".nexa"):
        name += ".nexa"

    path = project_root() / name

    if template == "game":
        content = '''// ==========================================
// Car Race – Nexa Racing Game
// Steuerung: Pfeiltasten, Leertaste = Start
// R = Neustart, ESC = Ende
// ==========================================

var W = 500;
var H = 700;
var LANES = [125, 225, 325];
var SPEED = 4;
var best = 0;

var playing = 1;

window("Car Race", W, H);

while (playing == 1) {

    // ---------- Reset fuer eine Runde ----------
    var lane = 1;
    var player_y = 600;
    var e1_lane = 0;
    var e1_y = -150;
    var e2_lane = 1;
    var e2_y = -350;
    var e3_lane = 2;
    var e3_y = -550;
    var score = 0;
    var game_over = 0;

    // ---------- Startscreen ----------
    clear("#1a1a1a");
    text(W / 2 - 110, H / 2 - 60, "CAR RACE", 48, "yellow");
    text(W / 2 - 140, H / 2 + 10, "Linke/Rechte Pfeiltaste", 20, "white");
    text(W / 2 - 90, H / 2 + 50, "Start: Leertaste", 20, "#90a4ae");
    present();

    var started = 0;
    while (started == 0) {
        present();
        if (key_down("space")) {
            started = 1;
        }
        if (key_down("escape")) {
            playing = 0;
            started = 1;
        }
        sleep(30);
    }

    if (playing == 0) {
        break;
    }

    // ---------- Hauptschleife ----------
    while (game_over == 0) {

        clear("#1b5e20");

        // Strasse
        rect(75, 0, 300, H, "#424242");
        rect(75, 0, 6, H, "white");
        rect(369, 0, 6, H, "white");

        // Fahrbahn-Markierungen (gestrichelt)
        var y_mark = 0;
        while (y_mark < H) {
            rect(173, y_mark, 6, 30, "#fdd835");
            rect(321, y_mark, 6, 30, "#fdd835");
            y_mark = y_mark + 60;
        }

        // ---------- Steuerung ----------
        if (key_down("left")) {
            lane = lane - 1;
            if (lane < 0) {
                lane = 0;
            }
            sleep(80);
        }
        if (key_down("right")) {
            lane = lane + 1;
            if (lane > 2) {
                lane = 2;
            }
            sleep(80);
        }
        if (key_down("escape")) {
            playing = 0;
            game_over = 1;
        }

        // ---------- Gegner bewegen ----------
        e1_y = e1_y + SPEED;
        e2_y = e2_y + SPEED;
        e3_y = e3_y + SPEED;

        // Respawn + Score
        if (e1_y > H + 60) {
            e1_y = -120;
            e1_lane = random(0, 2);
            score = score + 1;
        }
        if (e2_y > H + 60) {
            e2_y = -120;
            e2_lane = random(0, 2);
            score = score + 1;
        }
        if (e3_y > H + 60) {
            e3_y = -120;
            e3_lane = random(0, 2);
            score = score + 1;
        }

        // ---------- Kollision ----------
        var px = LANES[lane];
        var hit = 0;

        if (e1_lane == lane) {
            if (player_y - 40 < e1_y + 40 && player_y + 40 > e1_y - 40) {
                hit = 1;
            }
        }
        if (e2_lane == lane) {
            if (player_y - 40 < e2_y + 40 && player_y + 40 > e2_y - 40) {
                hit = 1;
            }
        }
        if (e3_lane == lane) {
            if (player_y - 40 < e3_y + 40 && player_y + 40 > e3_y - 40) {
                hit = 1;
            }
        }

        if (hit == 1) {
            game_over = 1;
        }

        // ---------- Gegner zeichnen ----------
        rect(LANES[e1_lane] - 15, e1_y - 25, 30, 50, "#ef5350");
        rect(LANES[e1_lane] - 10, e1_y - 32, 20, 8, "#b71c1c");
        rect(LANES[e1_lane] - 5, e1_y + 25, 10, 8, "#b71c1c");

        rect(LANES[e2_lane] - 15, e2_y - 25, 30, 50, "#ff9800");
        rect(LANES[e2_lane] - 10, e2_y - 32, 20, 8, "#e65100");
        rect(LANES[e2_lane] - 5, e2_y + 25, 10, 8, "#e65100");

        rect(LANES[e3_lane] - 15, e3_y - 25, 30, 50, "#ab47bc");
        rect(LANES[e3_lane] - 10, e3_y - 32, 20, 8, "#6a1b9a");
        rect(LANES[e3_lane] - 5, e3_y + 25, 10, 8, "#6a1b9a");

        // ---------- Spieler zeichnen ----------
        rect(px - 15, player_y - 25, 30, 50, "#1e88e5");
        rect(px - 10, player_y - 32, 20, 8, "#0d47a1");
        rect(px - 5, player_y + 25, 10, 8, "#0d47a1");

        // ---------- HUD ----------
        rect(0, 0, W, 35, "#000000");
        text(10, 7, "SCORE: " + score, 20, "yellow");

        present();
        sleep(16);
    }

    // ---------- Game Over (oder Abbruch) ----------
    if (score > best) {
        best = score;
    }

    if (playing == 1) {

        clear("#1a1a1a");
        rect(W / 2 - 170, H / 2 - 110, 340, 240, "#263238");
        text(W / 2 - 120, H / 2 - 90, "GAME OVER", 42, "#ef5350");
        text(W / 2 - 100, H / 2 - 30, "Score: " + score, 30, "white");
        text(W / 2 - 100, H / 2 + 20, "Best: " + best, 26, "#64b5f6");
        text(W / 2 - 130, H / 2 + 65, "R = Neustart, ESC = Ende", 18, "#90a4ae");
        present();

        var wieder = 0;
        while (wieder == 0) {
            present();
            if (key_down("r")) {
                wieder = 1;
            }
            if (key_down("escape")) {
                playing = 0;
                wieder = 1;
            }
            sleep(30);
        }
    }
}

clear("#1a1a1a");
text(W / 2 - 80, H / 2 - 30, "Tschuess!", 36, "white");
present();
sleep(1000);
'''

    elif template == "class":
        content = '''// Klassen-Beispiel

class Tier {
    string name;

    constructor(name) {
        this.name = name;
    }

    method sprechen() {
        return this.name + " macht Geräusche";
    }
}

class Hund extends Tier {
    constructor(name) {
        this.name = name;
    }

    method bellen() {
        return this.name + " bellt: Wau!";
    }
}

var rex = new Hund("Rex");
print(rex.sprechen());
print(rex.bellen());
'''

    elif template == "import":
        content = '''// Import-Beispiel

// Andere .nexa Dateien importieren:
// import "hilfsfunktionen.nexa";

var a = 10;
var b = 20;

print("Summe: " + (a + b));
print("Produkt: " + (a * b));
'''

    elif template == "gui":
        content = '''// GUI-Vorlage

var W = 600;
var H = 400;

window("Mein Fenster", W, H);

clear("#263238");

// Rechteck zeichnen
rect(50, 50, 100, 60, "#4fc3f7");

// Kreis zeichnen
circle(300, 100, 40, "#ef5350");

// Text zeichnen
text(200, 300, "Hallo Nexa!", 32, "white");

present();

print("Fenster geöffnet. Drücke Enter zum Beenden...");
wait();
'''

    else:
        content = 'print("Hallo aus Nexa!");\n'

    path.write_text(content, encoding="utf-8")

    print(f"Erstellt: {path} (Template: {template})")

    return 0


def cmd_build(args):
    print_header("NEXA BUILD")

    files = find_source_files()

    failed = 0

    for path in files:
        try:
            parse_file(path)
            print(f"[OK] {path}")
        except Exception as error:
            print(f"[FEHLER] {path}: {error}")
            failed += 1

    print()

    if failed:
        print(f"Build fehlgeschlagen: {failed} Fehler.")
        return 1

    print("Build erfolgreich.")
    return 0


def cmd_clean(args):
    cache = project_root() / ".nexa-cache"

    if cache.exists():
        shutil.rmtree(cache)
        print("Nexa-Cache gelöscht.")
    else:
        print("Kein Cache vorhanden.")

    return 0


def cmd_project(args):
    print(project_root())
    return 0


def cmd_project_name(args):
    print(project_root().name)
    return 0


def cmd_project_version(args):
    print(VERSION)
    return 0


def cmd_project_files(args):
    files = find_source_files()

    for path in files:
        print(path)

    return 0


def cmd_project_count(args):
    print(len(find_source_files()))
    return 0


def cmd_project_size(args):
    total = 0

    for path in find_source_files():
        try:
            total += path.stat().st_size
        except OSError:
            pass

    print(total, "Bytes")

    return 0


def cmd_project_tree(args):
    root = project_root()

    print(root)

    for path in sorted(root.rglob("*")):
        if "backup-before-3.0.0" in path.parts:
            continue

        try:
            relative = path.relative_to(root)
        except ValueError:
            continue

        print("  " + str(relative))

    return 0


def cmd_project_dirs(args):
    root = project_root()

    dirs = [
        p for p in root.rglob("*")
        if p.is_dir()
        and "backup-before-3.0.0" not in p.parts
    ]

    for path in sorted(dirs):
        print(path.relative_to(root))

    return 0


def cmd_project_nexa(args):
    files = sorted(project_root().glob("*.nexa"))

    for path in files:
        print(path.name)

    return 0


def cmd_project_my(args):
    files = sorted(project_root().glob("*.my"))

    for path in files:
        print(path.name)

    return 0


def cmd_project_py(args):
    files = sorted(project_root().glob("*.py"))

    for path in files:
        print(path.name)

    return 0


def cmd_project_modules(args):
    modules = [
        "lexer",
        "parser",
        "interpreter",
        "runtime",
        "main",
    ]

    for module in modules:
        path = project_root() / f"{module}.py"
        print(
            f"{module:<16}",
            "OK" if path.exists() else "FEHLT"
        )

    return 0


def cmd_project_health(args):
    modules = [
        "main.py",
        "lexer.py",
        "parser.py",
        "interpreter.py",
        "runtime.py",
    ]

    failed = 0

    for module in modules:
        path = project_root() / module

        if path.exists():
            print(f"{module:<20} OK")
        else:
            print(f"{module:<20} FEHLT")
            failed += 1

    return 1 if failed else 0


# ============================================================
# DATEIEN
# ============================================================

def cmd_files(args):
    for path in sorted(project_root().iterdir()):
        print(path.name)

    return 0


def cmd_files_only(args):
    for path in sorted(project_root().iterdir()):
        if path.is_file():
            print(path.name)

    return 0


def cmd_dirs(args):
    for path in sorted(project_root().iterdir()):
        if path.is_dir():
            print(path.name)

    return 0


def cmd_nexa_files(args):
    for path in sorted(project_root().rglob("*.nexa")):
        if "backup-before-3.0.0" not in path.parts:
            print(path)

    return 0


def cmd_my_files(args):
    for path in sorted(project_root().rglob("*.my")):
        if "backup-before-3.0.0" not in path.parts:
            print(path)

    return 0


def cmd_py_files(args):
    for path in sorted(project_root().rglob("*.py")):
        if "backup-before-3.0.0" not in path.parts:
            print(path)

    return 0


def cmd_empty_dirs(args):
    for path in sorted(project_root().rglob("*")):
        if path.is_dir():
            try:
                if not any(path.iterdir()):
                    print(path)
            except OSError:
                pass

    return 0


def cmd_nexa_count(args):
    print(
        len(
            list(project_root().rglob("*.nexa"))
        )
    )
    return 0


def cmd_my_count(args):
    print(
        len(
            list(project_root().rglob("*.my"))
        )
    )
    return 0


def cmd_py_count(args):
    print(
        len(
            list(project_root().rglob("*.py"))
        )
    )
    return 0


def cmd_dir_count(args):
    print(
        len(
            [
                p for p in project_root().rglob("*")
                if p.is_dir()
            ]
        )
    )
    return 0


def cmd_file_count(args):
    print(
        len(
            [
                p for p in project_root().rglob("*")
                if p.is_file()
            ]
        )
    )
    return 0


def cmd_exists(args):
    if not args:
        print("Verwendung: nexa exists <datei>")
        return 1

    print(
        "JA" if Path(args[0]).exists()
        else "NEIN"
    )

    return 0


def cmd_file_type(args):
    if not args:
        print("Verwendung: nexa file-type <datei>")
        return 1

    path = Path(args[0])

    types = {
        ".nexa": "Nexa Source",
        ".my": "Nexa/My Source",
        ".py": "Python Source",
        ".json": "JSON",
        ".txt": "Text",
        ".md": "Markdown",
    }

    print(
        types.get(
            path.suffix.lower(),
            "Unbekannter Dateityp"
        )
    )

    return 0


def cmd_read(args):
    if not args:
        print("Verwendung: nexa read <datei>")
        return 1

    path = Path(args[0])

    if not path.exists():
        print("Datei nicht gefunden.")
        return 1

    print(
        path.read_text(
            encoding="utf-8-sig"
        )
    )

    return 0


def cmd_head(args):
    if not args:
        print("Verwendung: nexa head <datei>")
        return 1

    count = 10

    if len(args) > 1:
        try:
            count = int(args[1])
        except ValueError:
            pass

    path = Path(args[0])

    if not path.exists():
        print("Datei nicht gefunden.")
        return 1

    lines = path.read_text(
        encoding="utf-8-sig"
    ).splitlines()

    for line in lines[:count]:
        print(line)

    return 0


def cmd_tail(args):
    if not args:
        print("Verwendung: nexa tail <datei>")
        return 1

    count = 10

    if len(args) > 1:
        try:
            count = int(args[1])
        except ValueError:
            pass

    path = Path(args[0])

    if not path.exists():
        print("Datei nicht gefunden.")
        return 1

    lines = path.read_text(
        encoding="utf-8-sig"
    ).splitlines()

    for line in lines[-count:]:
        print(line)

    return 0


def cmd_first_line(args):
    if not args:
        return 1

    path = Path(args[0])

    lines = path.read_text(
        encoding="utf-8-sig"
    ).splitlines()

    if lines:
        print(lines[0])

    return 0


def cmd_last_line(args):
    if not args:
        return 1

    path = Path(args[0])

    lines = path.read_text(
        encoding="utf-8-sig"
    ).splitlines()

    if lines:
        print(lines[-1])

    return 0


def cmd_nonempty_lines(args):
    if not args:
        return 1

    path = Path(args[0])

    lines = path.read_text(
        encoding="utf-8-sig"
    ).splitlines()

    print(
        sum(
            1 for line in lines
            if line.strip()
        )
    )

    return 0


def cmd_empty_lines(args):
    if not args:
        return 1

    path = Path(args[0])

    lines = path.read_text(
        encoding="utf-8-sig"
    ).splitlines()

    print(
        sum(
            1 for line in lines
            if not line.strip()
        )
    )

    return 0


def cmd_comments(args):
    if not args:
        return 1

    path = Path(args[0])

    lines = path.read_text(
        encoding="utf-8-sig"
    ).splitlines()

    count = 0

    for line in lines:
        stripped = line.strip()

        if (
            stripped.startswith("//")
            or stripped.startswith("#")
        ):
            count += 1

    print(count)

    return 0


def cmd_semicolons(args):
    if not args:
        return 1

    text = Path(args[0]).read_text(
        encoding="utf-8-sig"
    )

    print(text.count(";"))

    return 0


def cmd_strings(args):
    if not args:
        return 1

    text = Path(args[0]).read_text(
        encoding="utf-8-sig"
    )

    print(text.count('"'))

    return 0


def cmd_brackets(args):
    if not args:
        return 1

    text = Path(args[0]).read_text(
        encoding="utf-8-sig"
    )

    pairs = {
        "()": (
            text.count("("),
            text.count(")")
        ),
        "[]": (
            text.count("["),
            text.count("]")
        ),
        "{}": (
            text.count("{"),
            text.count("}")
        ),
    }

    for pair, values in pairs.items():
        left, right = values

        print(
            f"{pair}: {left}/{right}",
            "OK" if left == right
            else "FEHLER"
        )

    return 0


def cmd_encoding(args):
    if not args:
        return 1

    raw = Path(args[0]).read_bytes()

    if raw.startswith(b"\xef\xbb\xbf"):
        print("UTF-8 BOM")
    else:
        print("UTF-8 ohne BOM")

    return 0


def cmd_size(args):
    if not args:
        return 1

    path = Path(args[0])

    if not path.exists():
        print("Datei nicht gefunden.")
        return 1

    print(path.stat().st_size)

    return 0


def cmd_modified(args):
    if not args:
        return 1

    path = Path(args[0])

    if not path.exists():
        return 1

    value = datetime.datetime.fromtimestamp(
        path.stat().st_mtime
    )

    print(
        value.strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    return 0


def cmd_created(args):
    if not args:
        return 1

    path = Path(args[0])

    if not path.exists():
        return 1

    value = datetime.datetime.fromtimestamp(
        path.stat().st_ctime
    )

    print(
        value.strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    return 0


# ============================================================
# HASH / INTEGRITÄT
# ============================================================

def file_hash(path, algorithm="sha256"):
    hasher = hashlib.new(algorithm)

    with open(path, "rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b""
        ):
            hasher.update(chunk)

    return hasher.hexdigest()


def cmd_hash(args):
    if not args:
        print("Verwendung: nexa hash <datei>")
        return 1

    path = Path(args[0])

    if not path.exists():
        return 1

    print(file_hash(path))

    return 0


def cmd_hashes(args):
    for path in find_source_files():
        try:
            print(file_hash(path), path)
        except OSError:
            pass

    return 0


def cmd_integrity(args):
    failed = 0

    for path in find_source_files():
        try:
            parse_file(path)
            print(f"[OK] {path}")
        except Exception as error:
            print(f"[FEHLER] {path}: {error}")
            failed += 1

    return 1 if failed else 0


def cmd_validate_all(args):
    return cmd_integrity(args)


# ============================================================
# LEXER / PARSER TESTS
# ============================================================

def cmd_lexer_test(args):
    try:
        from lexer import Lexer

        print("Lexer: OK")
        print("Keywords:", len(Lexer.KEYWORDS))

        return 0

    except Exception as error:
        print("Lexer FEHLER:", error)
        return 1


def cmd_parser_test(args):
    try:
        from parser import Parser

        print("Parser: OK")
        print(Parser)

        return 0

    except Exception as error:
        print("Parser FEHLER:", error)
        return 1


def cmd_interpreter_test(args):
    try:
        import interpreter

        print("Interpreter: OK")
        print(interpreter)

        return 0

    except Exception as error:
        print("Interpreter FEHLER:", error)
        return 1


def cmd_runtime_test(args):
    try:
        import runtime

        print("Runtime: OK")
        print(runtime)

        return 0

    except Exception as error:
        print("Runtime FEHLER:", error)
        return 1


def cmd_import_test(args):
    modules = [
        "lexer",
        "parser",
        "interpreter",
        "runtime",
    ]

    failed = 0

    for name in modules:
        try:
            __import__(name)
            print(f"{name:<16} OK")
        except Exception as error:
            print(
                f"{name:<16} FEHLER: {error}"
            )
            failed += 1

    return 1 if failed else 0


def cmd_count_keywords(args):
    if Lexer is None:
        return 1

    print(len(Lexer.KEYWORDS))

    return 0


def cmd_list_keywords(args):
    if Lexer is None:
        return 1

    for keyword in sorted(Lexer.KEYWORDS):
        print(keyword)

    return 0


def cmd_keyword_exists(args):
    if not args:
        print(
            "Verwendung: "
            "nexa keyword-exists <wort>"
        )
        return 1

    if Lexer is None:
        return 1

    print(
        "JA"
        if args[0] in Lexer.KEYWORDS
        else "NEIN"
    )

    return 0


def cmd_lexer_info(args):
    if Lexer is None:
        return 1

    print("Nexa Lexer")
    print("Keywords:", len(Lexer.KEYWORDS))

    return 0


def cmd_token_count(args):
    if not args:
        return 1

    try:
        _, tokens, _ = parse_file(args[0])
        print(len(tokens))
        return 0
    except Exception as error:
        print(f"Fehler: {error}")
        return 1


def cmd_statement_count(args):
    if not args:
        return 1

    try:
        _, _, program = parse_file(args[0])
        print(len(program.statements))
        return 0
    except Exception as error:
        print(f"Fehler: {error}")
        return 1


def cmd_ast_count(args):
    return cmd_statement_count(args)


# ============================================================
# CACHE
# ============================================================

def cmd_cache_dir(args):
    cache = project_root() / ".nexa-cache"

    cache.mkdir(exist_ok=True)

    print(cache)

    return 0


def cmd_cache_create(args):
    cache = project_root() / ".nexa-cache"

    cache.mkdir(exist_ok=True)

    marker = cache / "cache.info"

    marker.write_text(
        f"Nexa {VERSION}\n",
        encoding="utf-8"
    )

    print(f"Cache erstellt: {cache}")

    return 0


def cmd_cache_clean(args):
    cache = project_root() / ".nexa-cache"

    if cache.exists():
        shutil.rmtree(cache)
        print("Cache gelöscht.")
    else:
        print("Kein Cache vorhanden.")

    return 0


def cmd_cache_status(args):
    cache = project_root() / ".nexa-cache"

    print(
        "Vorhanden:",
        "JA" if cache.exists() else "NEIN"
    )

    if cache.exists():
        print(
            "Dateien:",
            len(list(cache.rglob("*")))
        )

    return 0


# ============================================================
# DOKUMENTATION
# ============================================================

def cmd_docs(args):
    print_header("NEXA DOKUMENTATION")

    print(f"Nexa {VERSION}")
    print()
    print("Beispiele:")
    print("  nexa main.nexa")
    print("  nexa run main.nexa")
    print("  nexa check main.nexa")
    print("  nexa tokens main.nexa")
    print("  nexa ast main.nexa")
    print("  nexa debug main.nexa")
    print("  nexa build")

    return 0


def cmd_examples(args):
    print("Beispiel:")
    print()
    print('print("Hallo Nexa!");')

    return 0


def cmd_template(args):
    name = args[0] if args else "main.nexa"

    Path(name).write_text(
        'print("Neues Nexa-Programm");\n',
        encoding="utf-8"
    )

    print(f"Template erstellt: {name}")

    return 0


def cmd_version_file(args):
    print(VERSION)
    return 0


# ============================================================
# SHELL / CLI
# ============================================================

def cmd_echo(args):
    print(" ".join(args))
    return 0


def cmd_args(args):
    for index, value in enumerate(args):
        print(f"{index}: {value}")

    return 0


def cmd_cli(args):
    print("Nexa CLI")
    print(f"Version: {VERSION}")
    print(f"Befehle: {len(COMMANDS)}")

    return 0


def cmd_status(args):
    print_header("NEXA STATUS")

    print(f"Version:   {VERSION}")
    print(f"Ordner:    {Path.cwd()}")
    print(
        f"Quellcode: {len(find_source_files())}"
    )

    if Lexer is not None:
        print(
            f"Keywords:  {len(Lexer.KEYWORDS)}"
        )

    return 0


def cmd_list(args):
    for command in sorted(COMMANDS):
        print(command)

    return 0


def cmd_commands(args):
    print()
    print(
        f"Nexa CLI Befehle: {len(COMMANDS)}"
    )
    print("=" * 70)

    for command, entry in sorted(
        COMMANDS.items()
    ):
        if isinstance(entry, tuple):
            _, description = entry
        else:
            description = ""

        print(
            f"  nexa {command:<28} "
            f"{description}"
        )

    print()

    return 0


def cmd_help_command(args):
    if not args:
        print_help()
        return 0

    name = args[0]

    if name not in COMMANDS:
        print(
            f"Unbekannter Befehl: {name}"
        )
        return 1

    entry = COMMANDS[name]

    if isinstance(entry, tuple):
        _, description = entry
    else:
        description = ""

    print(f"nexa {name}")
    print(description)

    return 0


def cmd_disk_size(args):
    total, used, free = shutil.disk_usage(
        project_root()
    )

    def gb(value):
        return value / (1024 ** 3)

    print(f"Gesamt: {gb(total):.2f} GB")
    print(f"Belegt: {gb(used):.2f} GB")
    print(f"Frei:   {gb(free):.2f} GB")

    return 0


# ============================================================
# JSON
# ============================================================

def cmd_json_info(args):
    if not args:
        print("Verwendung: nexa json-info <datei>")
        return 1

    path = Path(args[0])

    try:
        data = json.loads(
            path.read_text(
                encoding="utf-8-sig"
            )
        )

        print(
            json.dumps(
                data,
                indent=2,
                ensure_ascii=False
            )
        )

        return 0

    except Exception as error:
        print(f"JSON-Fehler: {error}")
        return 1


def cmd_json_file(args):
    return cmd_json_info(args)


# ============================================================
# ZEILEN / TEXT
# ============================================================

def cmd_lines(args):
    if not args:
        return 1

    path = Path(args[0])

    text = path.read_text(
        encoding="utf-8-sig"
    )

    print(len(text.splitlines()))

    return 0


def cmd_chars(args):
    if not args:
        return 1

    text = Path(args[0]).read_text(
        encoding="utf-8-sig"
    )

    print(len(text))

    return 0


def cmd_search(args):
    if len(args) < 2:
        print(
            "Verwendung: "
            "nexa search <text> <datei>"
        )
        return 1

    needle = args[0]
    path = Path(args[1])

    lines = path.read_text(
        encoding="utf-8-sig"
    ).splitlines()

    for number, line in enumerate(
        lines,
        start=1
    ):
        if needle in line:
            print(f"{number}: {line}")

    return 0


def cmd_stats(args):
    if not args:
        return 1

    path = Path(args[0])

    text = path.read_text(
        encoding="utf-8-sig"
    )

    lines = text.splitlines()

    print("Zeichen:", len(text))
    print("Zeilen:", len(lines))
    print(
        "Nichtleer:",
        sum(1 for x in lines if x.strip())
    )
    print(
        "Leer:",
        sum(1 for x in lines if not x.strip())
    )
    print("Semikolons:", text.count(";"))
    print("Klammern:", text.count("("))
    print("Strings:", text.count('"'))

    return 0


# ============================================================
# EXTRA BEFEHLE
# ============================================================

def cmd_file_count_recursive(args):
    return cmd_file_count(args)


def cmd_dir_count_recursive(args):
    return cmd_dir_count(args)


def cmd_root_exists(args):
    print("JA" if project_root().exists() else "NEIN")
    return 0


def cmd_main_exists(args):
    path = project_root() / "main.nexa"
    print("JA" if path.exists() else "NEIN")
    return 0


def cmd_nexa_version(args):
    print(VERSION)
    return 0


def cmd_source_count(args):
    print(len(find_source_files()))
    return 0


def cmd_source_list(args):
    for path in find_source_files():
        print(path)
    return 0


def cmd_source_size(args):
    total = 0

    for path in find_source_files():
        try:
            total += path.stat().st_size
        except OSError:
            pass

    print(total)

    return 0


def cmd_module_count(args):
    modules = [
        "lexer.py",
        "parser.py",
        "interpreter.py",
        "runtime.py",
        "main.py",
    ]

    print(
        sum(
            (project_root() / x).exists()
            for x in modules
        )
    )

    return 0


def cmd_project_status(args):
    return cmd_project_health(args)


def cmd_version_number(args):
    print(VERSION)
    return 0


def cmd_build_check(args):
    return cmd_build(args)


def cmd_validate_project(args):
    return cmd_integrity(args)


def cmd_python_modules(args):
    return cmd_import_test(args)


def cmd_time_now(args):
    print(
        datetime.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )
    return 0


def cmd_date(args):
    print(
        datetime.date.today().isoformat()
    )
    return 0


def cmd_timestamp(args):
    print(time.time())
    return 0


def cmd_os(args):
    print(platform_module.system())
    return 0


def cmd_arch(args):
    print(platform_module.machine())
    return 0


def cmd_cpu(args):
    print(platform_module.processor())
    return 0


def cmd_home(args):
    print(Path.home())
    return 0


def cmd_temp(args):
    print(
        os.environ.get(
            "TEMP",
            os.environ.get("TMP", "")
        )
    )
    return 0


def cmd_user(args):
    print(
        os.environ.get(
            "USERNAME",
            os.environ.get(
                "USER",
                "unknown"
            )
        )
    )
    return 0


def cmd_cwd(args):
    print(Path.cwd())
    return 0



# ============================================================
# DATA SERVICE
# ============================================================

def get_data_service():
    if DataService is None:
        raise RuntimeError(
            "DataService konnte nicht geladen werden."
        )

    return DataService(project_root())


def cmd_data_status(args):
    service = get_data_service()

    print_header("NEXA DATA SERVICE")

    print("Status:       OK")
    print("Datenordner:  ", service.data_root)
    print("Profile:      ", service.profiles_root)
    print("Profile:      ", len(service.list_profiles()))

    return 0


def cmd_data_path(args):
    service = get_data_service()

    print(service.profiles_root)

    return 0


def cmd_data_profiles(args):
    service = get_data_service()

    profiles = service.list_profiles()

    if not profiles:
        print("Keine Profile vorhanden.")
        return 0

    for profile in profiles:
        print(profile)

    return 0


def cmd_data_create(args):
    if not args:
        print("Verwendung: nexa data-create <profil>")
        return 1

    service = get_data_service()
    profile = args[0]

    if service.exists(profile):
        print(f"Profil existiert bereits: {profile}")
        return 1

    service.open(profile)
    service.save()

    print(f"Profil erstellt: {profile}")

    return 0


def cmd_data_show(args):
    if not args:
        print("Verwendung: nexa data-show <profil>")
        return 1

    service = get_data_service()
    profile = args[0]

    if not service.exists(profile):
        print(f"Profil nicht gefunden: {profile}")
        return 1

    service.open(profile)

    print(
        json.dumps(
            service.all(),
            indent=2,
            ensure_ascii=False
        )
    )

    return 0


def cmd_data_delete(args):
    if not args:
        print("Verwendung: nexa data-delete <profil>")
        return 1

    service = get_data_service()
    profile = args[0]

    if not service.exists(profile):
        print(f"Profil nicht gefunden: {profile}")
        return 1

    service.delete_profile(profile)

    print(f"Profil gelöscht: {profile}")

    return 0

# ============================================================

# ============================================================
# NEW GAME
# ============================================================

def cmd_newgame(args):
    if not args:
        print("Verwendung: nexa newgame <name>")
        return 1

    name = args[0].strip()

    if not name:
        print("Der Spielname darf nicht leer sein.")
        return 1

    if any(char in name for char in '<>:"/\\|?*'):
        print("Ungültiger Spielname.")
        return 1

    game_root = Path.home() / "Desktop" / name

    if game_root.exists():
        print(f"Das Spielprojekt existiert bereits: {game_root}")
        return 1

    directories = [
        game_root / "game",
        game_root / "data",
        game_root / "assets",
        game_root / "assets" / "textures",
        game_root / "assets" / "models",
        game_root / "assets" / "sounds",
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

    main_source = '''print("Nexa Game gestartet!");
'''

    game_source = '''// Nexa Game
// Hier entsteht die Spiellogik.
'''

    player_source = '''// Nexa Player
// Hier entsteht die Spielersystem-Logik.
'''

    world_source = '''// Nexa World
// Hier entsteht die Welt.
'''

    project_source = f'''{{
  "name": "{name}",
  "type": "game",
  "version": "1.0.0",
  "nexa": "3.20.0",
  "entry": "main.nexa"
}}
'''

    (game_root / "main.nexa").write_text(
        main_source,
        encoding="utf-8"
    )

    (game_root / "game.nexa").write_text(
        game_source,
        encoding="utf-8"
    )

    (game_root / "game" / "player.nexa").write_text(
        player_source,
        encoding="utf-8"
    )

    (game_root / "game" / "world.nexa").write_text(
        world_source,
        encoding="utf-8"
    )

    (game_root / "project.nexa").write_text(
        project_source,
        encoding="utf-8"
    )

    print()
    print("=" * 70)
    print("NEXA GAME PROJEKT ERSTELLT")
    print("=" * 70)
    print()
    print(f"Name:     {name}")
    print(f"Pfad:     {game_root}")
    print()
    print("Struktur:")
    print(f"  {name}/")
    print("  ├── main.nexa")
    print("  ├── game.nexa")
    print("  ├── project.nexa")
    print("  ├── game/")
    print("  │   ├── player.nexa")
    print("  │   └── world.nexa")
    print("  ├── data/")
    print("  └── assets/")
    print("      ├── textures/")
    print("      ├── models/")
    print("      └── sounds/")
    print()
    print("Spielprojekt erfolgreich erstellt!")
    print()
    print(f"Start:")
    print(f"  cd {name}")
    print("  nexa run")
    print()

    return 0

# COMMAND REGISTRY
# ============================================================

COMMANDS = {
    "newgame": (cmd_newgame, "Erstellt ein neues Nexa-Spielprojekt"),

    # Grundlagen
    "help": (cmd_help, "Zeigt die Nexa-Hilfe"),
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
    "python-version": (cmd_python_version, "Zeigt nur die Python-Version"),
    "python-path": (cmd_python_path, "Zeigt den Python-Pfad"),
    "platform": (cmd_platform, "Zeigt die Plattform"),
    "env": (cmd_env, "Zeigt Umgebungsvariablen"),

    # Ausführung
    "run": (cmd_run, "Führt ein Nexa-Programm aus"),
    "exec": (cmd_exec, "Führt ein Nexa-Programm aus"),
    "check": (cmd_check, "Prüft ein Nexa-Programm"),
    "validate": (cmd_validate, "Validiert ein Nexa-Programm"),
    "tokens": (cmd_tokens, "Zeigt Lexer-Tokens"),
    "ast": (cmd_ast, "Zeigt den AST"),
    "debug": (cmd_debug, "Startet den Debug-Modus"),
    "time": (cmd_time, "Misst die Ausführungszeit"),
    "benchmark": (cmd_benchmark, "Führt einen Benchmark aus"),
    "analyze": (cmd_analyze, "Analysiert das Projekt"),
    "scan": (cmd_scan, "Scannt Nexa-Dateien"),
    "report": (cmd_report, "Erstellt einen JSON-Bericht"),

    # Projekt
    "init": (cmd_init, "Initialisiert ein Nexa-Projekt"),
    "new": (cmd_new, "Erstellt eine neue Nexa-Datei"),
    "build": (cmd_build, "Prüft alle Nexa-Dateien"),
    "clean": (cmd_clean, "Löscht den Nexa-Cache"),
    "project": (cmd_project, "Zeigt das Projekt"),
    "project-name": (cmd_project_name, "Zeigt den Projektnamen"),
    "project-version": (cmd_project_version, "Zeigt die Projektversion"),
    "project-files": (cmd_project_files, "Listet Projektdateien"),
    "project-count": (cmd_project_count, "Zählt Quelldateien"),
    "project-size": (cmd_project_size, "Zeigt die Projektgröße"),
    "project-tree": (cmd_project_tree, "Zeigt den Projektbaum"),
    "project-dirs": (cmd_project_dirs, "Listet Projektverzeichnisse"),
    "project-nexa": (cmd_project_nexa, "Listet Nexa-Dateien"),
    "project-my": (cmd_project_my, "Listet My-Dateien"),
    "project-py": (cmd_project_py, "Listet Python-Dateien"),
    "project-modules": (cmd_project_modules, "Prüft Nexa-Kernmodule"),
    "project-health": (cmd_project_health, "Prüft die Projektstruktur"),
    "project-status": (cmd_project_status, "Zeigt den Projektstatus"),

    # Dateien
    "files": (cmd_files, "Listet Dateien und Verzeichnisse"),
    "files-only": (cmd_files_only, "Listet nur Dateien"),
    "dirs": (cmd_dirs, "Listet nur Verzeichnisse"),
    "nexa-files": (cmd_nexa_files, "Listet Nexa-Dateien"),
    "my-files": (cmd_my_files, "Listet My-Dateien"),
    "py-files": (cmd_py_files, "Listet Python-Dateien"),
    "empty-dirs": (cmd_empty_dirs, "Findet leere Verzeichnisse"),
    "nexa-count": (cmd_nexa_count, "Zählt Nexa-Dateien"),
    "my-count": (cmd_my_count, "Zählt My-Dateien"),
    "py-count": (cmd_py_count, "Zählt Python-Dateien"),
    "dir-count": (cmd_dir_count, "Zählt Verzeichnisse"),
    "file-count": (cmd_file_count, "Zählt Dateien"),
    "source-count": (cmd_source_count, "Zählt Quelldateien"),
    "source-list": (cmd_source_list, "Listet Quelldateien"),
    "source-size": (cmd_source_size, "Zeigt Quellcodegröße"),
    "file-count-recursive": (cmd_file_count_recursive, "Zählt rekursive Dateien"),
    "dir-count-recursive": (cmd_dir_count_recursive, "Zählt rekursive Verzeichnisse"),
    "exists": (cmd_exists, "Prüft, ob eine Datei existiert"),
    "file-type": (cmd_file_type, "Zeigt den Dateityp"),
    "read": (cmd_read, "Liest eine Datei"),
    "head": (cmd_head, "Zeigt die ersten Zeilen"),
    "tail": (cmd_tail, "Zeigt die letzten Zeilen"),
    "first-line": (cmd_first_line, "Zeigt die erste Zeile"),
    "last-line": (cmd_last_line, "Zeigt die letzte Zeile"),
    "nonempty-lines": (cmd_nonempty_lines, "Zählt nichtleere Zeilen"),
    "empty-lines": (cmd_empty_lines, "Zählt leere Zeilen"),
    "comments": (cmd_comments, "Zählt Kommentare"),
    "semicolons": (cmd_semicolons, "Zählt Semikolons"),
    "strings": (cmd_strings, "Zählt Anführungszeichen"),
    "brackets": (cmd_brackets, "Prüft Klammern"),
    "encoding": (cmd_encoding, "Prüft UTF-8"),
    "size": (cmd_size, "Zeigt die Dateigröße"),
    "modified": (cmd_modified, "Zeigt das Änderungsdatum"),
    "created": (cmd_created, "Zeigt das Erstellungsdatum"),
    "lines": (cmd_lines, "Zählt Zeilen"),
    "chars": (cmd_chars, "Zählt Zeichen"),
    "search": (cmd_search, "Sucht Text in einer Datei"),
    "stats": (cmd_stats, "Zeigt Dateistatistiken"),

    # Hash
    "hash": (cmd_hash, "Berechnet einen SHA-256-Hash"),
    "hashes": (cmd_hashes, "Berechnet Hashes der Quelldateien"),
    "integrity": (cmd_integrity, "Prüft die Integrität"),
    "validate-all": (cmd_validate_all, "Validiert alle Quelldateien"),

    # Lexer / Parser
    "lexer-test": (cmd_lexer_test, "Testet den Lexer"),
    "parser-test": (cmd_parser_test, "Testet den Parser"),
    "interpreter-test": (cmd_interpreter_test, "Testet den Interpreter"),
    "runtime-test": (cmd_runtime_test, "Testet die Runtime"),
    "import-test": (cmd_import_test, "Testet alle Kernmodule"),
    "lexer-info": (cmd_lexer_info, "Zeigt Lexer-Informationen"),
    "token-count": (cmd_token_count, "Zählt Tokens"),
    "statement-count": (cmd_statement_count, "Zählt Statements"),
    "ast-count": (cmd_ast_count, "Zählt AST-Statements"),
    "count-keywords": (cmd_count_keywords, "Zählt Nexa-Schlüsselwörter"),
    "list-keywords": (cmd_list_keywords, "Listet Nexa-Schlüsselwörter"),
    "keyword-exists": (cmd_keyword_exists, "Prüft ein Schlüsselwort"),

    # Cache
    "cache-dir": (cmd_cache_dir, "Zeigt den Cache"),
    "cache-create": (cmd_cache_create, "Erstellt den Cache"),
    "cache-clean": (cmd_cache_clean, "Löscht den Cache"),
    "cache-status": (cmd_cache_status, "Zeigt den Cache-Status"),

    # Dokumentation
    "docs": (cmd_docs, "Zeigt die Dokumentation"),
    "examples": (cmd_examples, "Zeigt Beispiele"),
    "template": (cmd_template, "Erstellt ein Template"),
    "version-file": (cmd_version_file, "Zeigt die Versionsdatei"),

    # JSON
    "json-info": (cmd_json_info, "Liest eine JSON-Datei"),
    "json-file": (cmd_json_file, "Liest eine JSON-Datei"),

    # CLI
    "echo": (cmd_echo, "Gibt Text aus"),
    "args": (cmd_args, "Zeigt CLI-Argumente"),
    "cli": (cmd_cli, "Zeigt CLI-Informationen"),
    "status": (cmd_status, "Zeigt den Nexa-Status"),
    "list": (cmd_list, "Listet Befehle"),
    "commands": (cmd_commands, "Listet alle CLI-Befehle"),
    "help-command": (cmd_help_command, "Zeigt Hilfe zu einem Befehl"),
    "disk-size": (cmd_disk_size, "Zeigt Festplatteninformationen"),

    # System
    "os": (cmd_os, "Zeigt das Betriebssystem"),
    "arch": (cmd_arch, "Zeigt die Architektur"),
    "cpu": (cmd_cpu, "Zeigt den Prozessor"),
    "home": (cmd_home, "Zeigt das Benutzerverzeichnis"),
    "temp": (cmd_temp, "Zeigt das Temp-Verzeichnis"),
    "user": (cmd_user, "Zeigt den aktuellen Benutzer"),
    "cwd": (cmd_cwd, "Zeigt das Arbeitsverzeichnis"),
    "time-now": (cmd_time_now, "Zeigt die aktuelle Uhrzeit"),
    "date": (cmd_date, "Zeigt das aktuelle Datum"),
    "timestamp": (cmd_timestamp, "Zeigt den Unix-Zeitstempel"),

    # DataService
    "data-status": (cmd_data_status, "Zeigt den Nexa DataService-Status"),
    "data-path": (cmd_data_path, "Zeigt den Profil-Speicherort"),
    "data-profiles": (cmd_data_profiles, "Listet alle Datenprofile"),
    "data-create": (cmd_data_create, "Erstellt ein Datenprofil"),
    "data-show": (cmd_data_show, "Zeigt ein Datenprofil"),
    "data-delete": (cmd_data_delete, "Löscht ein Datenprofil"),
    # Weitere
    "root-exists": (cmd_root_exists, "Prüft das Projektverzeichnis"),
    "main-exists": (cmd_main_exists, "Prüft main.nexa"),
    "nexa-version": (cmd_nexa_version, "Zeigt die Nexa-Version"),
    "version-number": (cmd_version_number, "Zeigt die Versionsnummer"),
    "build-check": (cmd_build_check, "Prüft den Build"),
    "validate-project": (cmd_validate_project, "Validiert das Projekt"),
    "python-modules": (cmd_python_modules, "Prüft Python-Module"),
    "module-count": (cmd_module_count, "Zählt Kernmodule"),
}


# ============================================================
# ALIASES
# ============================================================

ALIASES = {
    "--help": "help",
    "-h": "help",

    "--version": "version",
    "-v": "version",

    "--info": "info",

    "--check": "check",
    "--tokens": "tokens",
    "--ast": "ast",
    "--debug": "debug",
    "--time": "time",
    "--run": "run",

    "--build": "build",
    "--clean": "clean",
}


# ============================================================
# HILFE
# ============================================================

def print_help():
    print()
    print(f"Nexa {VERSION}")
    print("=" * 70)
    print("Die Nexa Command Line Interface")
    print()
    print(
        f"Verfügbare Befehle: "
        f"{len(COMMANDS)}"
    )
    print()

    for command, entry in sorted(
        COMMANDS.items()
    ):
        if isinstance(entry, tuple):
            _, description = entry
        else:
            description = ""

        print(
            f"  {command:<28} "
            f"{description}"
        )

    print()
    print("Beispiele:")
    print("  nexa hallo.nexa")
    print("  nexa --check hallo.nexa")
    print("  nexa --tokens hallo.nexa")
    print("  nexa --ast hallo.nexa")
    print("  nexa --debug hallo.nexa")
    print("  nexa --time hallo.nexa")
    print("  nexa init")
    print("  nexa new meinprojekt")
    print("  nexa build")
    print()


# ============================================================
# MAIN
# ============================================================

def main():
    args = sys.argv[1:]

    if not args:
        print_help()
        return 0

    first = args[0]

    # --------------------------------------------------------
    # ALIAS
    # --------------------------------------------------------

    if first in ALIASES:
        command = ALIASES[first]

        entry = COMMANDS.get(command)

        if entry is not None:
            handler = entry[0]

            try:
                return handler(args[1:]) or 0
            except Exception as error:
                print(
                    f"Fehler: {error}",
                    file=sys.stderr
                )
                return 1

    # --------------------------------------------------------
    # DIREKTE NEXA-DATEI
    # --------------------------------------------------------

    path = Path(first)

    if (
        path.is_file()
        and path.suffix.lower()
        in SUPPORTED_EXTENSIONS
    ):
        try:
            run_file(path)
            return 0

        except Exception as error:
            print(
                f"Fehler: {error}",
                file=sys.stderr
            )
            return 1

    # --------------------------------------------------------
    # CLI-BEFEHL
    # --------------------------------------------------------

    if first in COMMANDS:
        entry = COMMANDS[first]

        if isinstance(entry, tuple):
            handler = entry[0]
        else:
            handler = entry

        try:
            result = handler(args[1:])
            return result or 0

        except FileNotFoundError as error:
            print(
                f"Fehler: {error}",
                file=sys.stderr
            )
            return 1

        except (
            SyntaxError,
            RuntimeError,
            ValueError
        ) as error:
            print(
                f"Fehler: {error}",
                file=sys.stderr
            )
            return 1

        except OSError as error:
            print(
                f"Dateifehler: {error}",
                file=sys.stderr
            )
            return 1

        except Exception as error:
            print(
                f"Unerwarteter Fehler: {error}",
                file=sys.stderr
            )
            return 1

    # --------------------------------------------------------
    # UNBEKANNTER BEFEHL
    # --------------------------------------------------------

    print(
        f"Unbekannter Nexa-Befehl: {first}",
        file=sys.stderr
    )

    print()
    print(
        "Nutze 'nexa help' "
        "für alle Befehle."
    )

    return 1


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    raise SystemExit(main())



