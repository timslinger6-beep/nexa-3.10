import sys
from pathlib import Path

from lexer import Lexer
from parser import Parser
from interpreter import run
from runtime import GameRuntime


def parse_file(path):
    source = Path(path).read_text(encoding="utf-8")

    lexer = Lexer(source)
    tokens = lexer.tokenize()

    parser = Parser(tokens)
    program = parser.parse()

    return program


def main():
    if len(sys.argv) < 2:
        print("Nexa Game Runtime")
        print()
        print("Verwendung:")
        print('  "Nexa Game Runtime.exe" <datei.nexa>')
        return 1

    path = Path(sys.argv[1])

    if not path.exists():
        print(f"FEHLER: Datei nicht gefunden: {path}")
        return 1

    runtime = GameRuntime()

    app_name = path.stem

    if hasattr(runtime, "set_program_name"):
        runtime.set_program_name(app_name)
    elif hasattr(runtime, "program_name"):
        runtime.program_name = app_name

    program = parse_file(path)

    return run(program, runtime=runtime)


if __name__ == "__main__":
    sys.exit(main() or 0)
