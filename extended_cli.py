"""Additional, read-only Nexa CLI analysis commands."""

from __future__ import annotations

import json
import re
import statistics
import sys
from collections import Counter
from dataclasses import fields, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable


IGNORED_PARTS = {
    ".git",
    ".nexa-cache",
    "__pycache__",
    "backup-before-3.0.0",
    "build",
    "dist",
    "env",
    "venv",
    ".venv",
    ".vscode",
    ".pytest_cache",
    ".mypy_cache",
    "node_modules",
}
SOURCE_SUFFIXES = {".nexa", ".my", ".py"}


def _project_files(root: Path | None = None) -> list[Path]:
    base = root or Path.cwd()
    return sorted(
        path
        for path in base.rglob("*")
        if path.is_file()
        and not any(part in IGNORED_PARTS for part in path.relative_to(base).parts)
    )


def _source_files(root: Path | None = None) -> list[Path]:
    return [
        path for path in _project_files(root)
        if path.suffix.lower() in SOURCE_SUFFIXES
    ]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def _source_paths(args: list[str]) -> list[Path]:
    if args:
        path = Path(args[0])
        if not path.is_file():
            raise FileNotFoundError(f"Datei nicht gefunden: {path}")
        return [path]
    return [
        path for path in _source_files()
        if path.suffix.lower() in {".nexa", ".my"}
    ]


def _parse_nexa(path: Path):
    from parser import Parser

    source, tokens = _lex_nexa(path)
    return source, tokens, Parser(tokens).parse()


def _lex_nexa(path: Path):
    from lexer import Lexer

    source = _read_text(path)
    return source, Lexer(source).tokenize()


def _walk_ast(value):
    if is_dataclass(value) and not isinstance(value, type):
        yield value
        for field in fields(value):
            yield from _walk_ast(getattr(value, field.name))
    elif isinstance(value, dict):
        for child in value.values():
            yield from _walk_ast(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _walk_ast(child)


def _run_ast_query(args: list[str], action: str, target: str) -> int:
    paths = _source_paths(args)
    if not paths:
        print("Keine Nexa-Quelldateien gefunden.")
        return 1

    total = 0
    for path in paths:
        _, _, program = _parse_nexa(path)
        nodes = list(_walk_ast(program))
        if action == "count-node":
            count = sum(type(node).__name__ == target for node in nodes)
            print(f"{path}: {count}")
            total += count
        elif action == "count-group":
            if target == "expression":
                matches = [node for node in nodes if type(node).__name__.endswith("Expression")]
            elif target == "statement":
                matches = [node for node in nodes if type(node).__name__.endswith("Statement")]
            else:
                matches = [
                    node for node in nodes
                    if type(node).__name__.endswith("Declaration")
                ]
            print(f"{path}: {len(matches)}")
            total += len(matches)
        else:
            raise ValueError(f"Unbekannte AST-Abfrage: {action}")

    if len(paths) > 1:
        print(f"Gesamt: {total}")
    return 0


def _run_token_query(args: list[str], token_name: str, show_locations: bool) -> int:
    paths = _source_paths(args)
    if not paths:
        print("Keine Nexa-Quelldateien gefunden.")
        return 1

    from lexer import TokenType

    token_type = TokenType[token_name]
    total = 0
    for path in paths:
        _, tokens = _lex_nexa(path)
        matching = [token for token in tokens if token.type is token_type]
        total += len(matching)
        if show_locations:
            print(f"{path}: {len(matching)}")
            for token in matching:
                print(f"  {token}")
        else:
            print(f"{path}: {len(matching)}")
    if len(paths) > 1:
        print(f"Gesamt: {total}")
    return 0


def _project_query(action: str, args: list[str]) -> int:
    root = Path(args[0]) if args else Path.cwd()
    if not root.is_dir():
        raise NotADirectoryError(f"Kein Verzeichnis: {root}")
    files = _project_files(root)
    sources = [path for path in files if path.suffix.lower() in SOURCE_SUFFIXES]
    relative = lambda path: path.relative_to(root).as_posix()
    sizes = {path: path.stat().st_size for path in files}
    text_files: dict[Path, str] = {}
    for path in sources:
        try:
            text_files[path] = _read_text(path)
        except (OSError, UnicodeError):
            continue

    if action == "largest":
        selected = max(files, key=lambda path: sizes[path], default=None)
        result = f"{relative(selected)} ({sizes[selected]} Bytes)" if selected else "Keine Dateien."
    elif action == "smallest":
        selected = min(files, key=lambda path: sizes[path], default=None)
        result = f"{relative(selected)} ({sizes[selected]} Bytes)" if selected else "Keine Dateien."
    elif action == "newest":
        selected = max(files, key=lambda path: path.stat().st_mtime, default=None)
        result = f"{relative(selected)} ({datetime.fromtimestamp(selected.stat().st_mtime).isoformat(timespec='seconds')})" if selected else "Keine Dateien."
    elif action == "oldest":
        selected = min(files, key=lambda path: path.stat().st_mtime, default=None)
        result = f"{relative(selected)} ({datetime.fromtimestamp(selected.stat().st_mtime).isoformat(timespec='seconds')})" if selected else "Keine Dateien."
    elif action == "median-size":
        result = str(statistics.median(sizes.values())) if sizes else "0"
    elif action == "average-size":
        result = f"{statistics.mean(sizes.values()):.1f}" if sizes else "0"
    elif action == "total-size":
        result = str(sum(sizes.values()))
    elif action == "largest-ten":
        result = "\n".join(
            f"{relative(path)}\t{sizes[path]} Bytes"
            for path in sorted(files, key=lambda item: sizes[item], reverse=True)[:10]
        ) or "Keine Dateien."
    elif action == "extension-count":
        result = str(len({path.suffix.lower() for path in files}))
    elif action == "extension-report":
        counts = Counter(path.suffix.lower() or "[ohne Endung]" for path in files)
        result = "\n".join(f"{ext or '[ohne Endung]'}: {count}" for ext, count in sorted(counts.items()))
    elif action == "empty-files":
        result = "\n".join(relative(path) for path in files if sizes[path] == 0) or "Keine leeren Dateien."
    elif action == "empty-directories":
        dirs = [path for path in root.rglob("*") if path.is_dir()]
        dirs = [path for path in dirs if not any(part in IGNORED_PARTS for part in path.relative_to(root).parts)]
        result = "\n".join(relative(path) for path in dirs if not any(path.iterdir())) or "Keine leeren Verzeichnisse."
    elif action == "deepest-file":
        selected = max(files, key=lambda path: len(path.relative_to(root).parts), default=None)
        result = f"{relative(selected)} (Tiefe {len(selected.relative_to(root).parts)})" if selected else "Keine Dateien."
    elif action == "root-files":
        result = "\n".join(path.name for path in files if path.parent == root) or "Keine Dateien im Projektstamm."
    elif action == "nested-files":
        result = "\n".join(relative(path) for path in files if path.parent != root) or "Keine verschachtelten Dateien."
    elif action == "hidden-files":
        result = "\n".join(relative(path) for path in files if path.name.startswith(".")) or "Keine versteckten Dateien."
    elif action == "extensionless":
        result = "\n".join(relative(path) for path in files if not path.suffix) or "Keine Dateien ohne Endung."
    elif action == "duplicate-names":
        groups: dict[str, list[str]] = {}
        for path in files:
            groups.setdefault(path.name.casefold(), []).append(relative(path))
        result = "\n".join(" | ".join(names) for names in groups.values() if len(names) > 1) or "Keine doppelten Dateinamen."
    elif action == "case-collisions":
        groups: dict[str, list[str]] = {}
        for path in files:
            groups.setdefault(relative(path).casefold(), []).append(relative(path))
        result = "\n".join(" | ".join(names) for names in groups.values() if len(set(names)) > 1) or "Keine Pfad-Kollisionen."
    elif action == "symlinks":
        result = "\n".join(relative(path) for path in files if path.is_symlink()) or "Keine symbolischen Links."
    elif action == "source-line-count":
        result = str(sum(len(text.splitlines()) for text in text_files.values()))
    elif action == "source-character-count":
        result = str(sum(len(text) for text in text_files.values()))
    elif action == "source-average-lines":
        counts = [len(text.splitlines()) for text in text_files.values()]
        result = f"{statistics.mean(counts):.1f}" if counts else "0"
    elif action == "source-average-line-length":
        lines = [line for text in text_files.values() for line in text.splitlines()]
        result = f"{statistics.mean(map(len, lines)):.1f}" if lines else "0"
    elif action == "longest-source-line":
        candidates = [
            (len(line), path, number, line)
            for path, text in text_files.items()
            for number, line in enumerate(text.splitlines(), 1)
        ]
        if candidates:
            length, path, number, line = max(candidates)
            result = f"{relative(path)}:{number}: {length} Zeichen: {line}"
        else:
            result = "Keine Quellzeilen."
    elif action == "blank-lines":
        result = str(sum(
            1 for text in text_files.values()
            for line in text.splitlines() if not line.strip()
        ))
    elif action == "tabbed-files":
        result = "\n".join(relative(path) for path, text in text_files.items() if "\t" in text) or "Keine Quelltexte mit Tabs."
    elif action == "bom-files":
        result = "\n".join(
            relative(path) for path in sources
            if path.read_bytes().startswith(b"\xef\xbb\xbf")
        ) or "Keine UTF-8-BOM-Dateien."
    elif action == "missing-final-newline":
        result = "\n".join(
            relative(path) for path, text in text_files.items()
            if text and not text.endswith(("\n", "\r"))
        ) or "Alle nichtleeren Quelltexte enden mit einem Zeilenumbruch."
    elif action == "newline-report":
        crlf = bare_lf = cr = 0
        for text in text_files.values():
            crlf += text.count("\r\n")
            bare_lf += text.count("\n") - text.count("\r\n")
            cr += text.count("\r") - text.count("\r\n")
        result = f"CRLF: {crlf}\nLF: {bare_lf}\nCR: {cr}"
    elif action == "binary-candidates":
        result = "\n".join(
            relative(path) for path in files
            if b"\0" in path.read_bytes()[:8192]
        ) or "Keine Binärdatei-Kandidaten."
    elif action == "source-by-extension":
        counts = Counter(path.suffix.lower() for path in sources)
        result = "\n".join(f"{ext}: {counts[ext]}" for ext in sorted(counts)) or "Keine Quelltexte."
    elif action == "average-age-days":
        now = datetime.now().timestamp()
        ages = [(now - path.stat().st_mtime) / 86400 for path in files]
        result = f"{statistics.mean(ages):.1f}" if ages else "0"
    elif action == "recent-ten":
        result = "\n".join(
            f"{relative(path)}\t{datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec='seconds')}"
            for path in sorted(files, key=lambda item: item.stat().st_mtime, reverse=True)[:10]
        ) or "Keine Dateien."
    elif action == "oldest-ten":
        result = "\n".join(
            f"{relative(path)}\t{datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec='seconds')}"
            for path in sorted(files, key=lambda item: item.stat().st_mtime)[:10]
        ) or "Keine Dateien."
    elif action == "files-per-directory":
        counts = Counter(relative(path.parent) or "." for path in files)
        result = "\n".join(f"{directory}: {count}" for directory, count in sorted(counts.items())) or "Keine Dateien."
    elif action == "maximum-depth":
        result = str(max((len(path.relative_to(root).parts) for path in files), default=0))
    elif action == "readable-source-count":
        result = str(len(text_files))
    elif action == "unreadable-source-count":
        result = str(len(sources) - len(text_files))
    elif action == "largest-extension":
        totals = Counter()
        for path, size in sizes.items():
            totals[path.suffix.lower() or "[ohne Endung]"] += size
        ext, size = max(totals.items(), key=lambda item: item[1], default=("", 0))
        result = f"{ext}: {size} Bytes" if ext else "Keine Dateien."
    else:
        raise ValueError(f"Unbekannte Projektabfrage: {action}")

    print(result)
    return 0


QUALITY_RULES: dict[str, tuple[str, str]] = {
    "trailing-whitespace": (r"[ \t]+$", "Leerzeichen am Zeilenende"),
    "todo-markers": (r"\bTODO\b", "TODO-Markierung"),
    "fixme-markers": (r"\bFIXME\b", "FIXME-Markierung"),
    "hack-markers": (r"\bHACK\b", "HACK-Markierung"),
    "xxx-markers": (r"\bXXX\b", "XXX-Markierung"),
    "debug-print-calls": (r"\bprint\s*\(", "print-Aufruf"),
    "python-eval-calls": (r"\beval\s*\(", "eval-Aufruf in Python"),
    "python-exec-calls": (r"\bexec\s*\(", "exec-Aufruf in Python"),
    "bare-except": (r"^\s*except\s*:", "Bare except-Klausel"),
    "broad-except": (r"^\s*except\s+Exception\b", "Breite Exception-Klausel"),
    "wildcard-imports": (r"^\s*from\s+\S+\s+import\s+\*", "Wildcard-Import"),
    "mutable-defaults": (r"^\s*def\s+\w+\s*\([^)]*=\s*(?:\[\]|\{\})", "Veränderlicher Funktionsstandardwert"),
    "assert-statements": (r"^\s*assert\b", "assert-Anweisung"),
    "global-statements": (r"^\s*global\b", "global-Anweisung"),
    "python-pass": (r"^\s*pass\s*(?:#.*)?$", "pass-Anweisung"),
    "python-raise": (r"^\s*raise\b", "raise-Anweisung"),
    "nexa-imports": (r"^\s*import\b", "Nexa-import-Anweisung"),
    "nexa-class-declarations": (r"^\s*class\b", "Nexa-Klassendeklaration"),
    "nexa-function-declarations": (r"^\s*(?:function|func)\b", "Nexa-Funktionsdeklaration"),
    "nexa-variable-declarations": (r"^\s*(?:let|var|const)\b", "Nexa-Variablendeklaration"),
    "nexa-loop-keywords": (r"\b(?:while|for|foreach|loop|repeat)\b", "Nexa-Schleifenschlüsselwort"),
    "nexa-branch-keywords": (r"\b(?:if|else|switch|case)\b", "Nexa-Verzweigungsschlüsselwort"),
    "nexa-return-statements": (r"\breturn\b", "Nexa-return-Anweisung"),
    "nexa-break-statements": (r"\bbreak\b", "Nexa-break-Anweisung"),
    "nexa-continue-statements": (r"\bcontinue\b", "Nexa-continue-Anweisung"),
    "nexa-try-statements": (r"\b(?:try|catch)\b", "Nexa-Fehlerbehandlung"),
    "python-async-functions": (r"^\s*async\s+def\b", "Asynchrone Python-Funktion"),
    "python-await-expressions": (r"\bawait\b", "await-Ausdruck"),
    "python-lambda-expressions": (r"\blambda\b", "Lambda-Ausdruck"),
    "python-with-statements": (r"^\s*(?:async\s+)?with\b", "with-Anweisung"),
    "python-yield-expressions": (r"\byield\b", "yield-Ausdruck"),
    "python-type-ignore": (r"#\s*type:\s*ignore\b", "type: ignore-Kommentar"),
    "python-noqa": (r"#\s* noqa\b", "noqa-Kommentar"),
    "python-todo-comments": (r"#.*\b(?:TODO|FIXME|HACK)\b", "Aufgabenmarker im Python-Kommentar"),
    "nexa-semicolon-lines": (r";\s*(?:$|//)", "Nexa-Zeile mit Semikolon"),
    "nexa-line-comments": (r"//", "Nexa-Zeilenkommentar"),
    "nexa-boolean-literals": (r"\b(?:true|false)\b", "Nexa-Boolean-Literal"),
    "nexa-null-literals": (r"\bnull\b", "Nexa-null-Literal"),
    "python-fstring-prefixes": (r"(?i)(?<!\w)f[\"']", "Python-f-String"),
    "python-format-calls": (r"\.format\s*\(", "str.format-Aufruf"),
}


def _run_quality_check(action: str, args: list[str]) -> int:
    pattern, label = QUALITY_RULES[action]
    paths = [Path(args[0])] if args else _source_files()
    if args and not paths[0].is_file():
        raise FileNotFoundError(f"Datei nicht gefunden: {paths[0]}")

    matches = 0
    regex = re.compile(pattern)
    for path in paths:
        if path.suffix.lower() not in SOURCE_SUFFIXES:
            continue
        try:
            lines = _read_text(path).splitlines()
        except (OSError, UnicodeError):
            continue
        for number, line in enumerate(lines, 1):
            if regex.search(line):
                print(f"{path}:{number}: {label}: {line.strip()}")
                matches += 1
    print(f"{label}: {matches} Treffer")
    return 0


def _json_tree(value, path: str = "$"):
    yield path, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _json_tree(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _json_tree(child, f"{path}[{index}]")


def _load_json(path: Path):
    text = _read_text(path)
    duplicate_keys: list[str] = []

    def pairs_hook(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                duplicate_keys.append(key)
            result[key] = value
        return result

    return json.loads(text, object_pairs_hook=pairs_hook), duplicate_keys


def _run_json_query(action: str, args: list[str]) -> int:
    if not args:
        print(f"Verwendung: nexa {action.replace('_', '-')} <json-datei>", file=sys.stderr)
        return 1
    path = Path(args[0])
    value, duplicate_keys = _load_json(path)
    nodes = list(_json_tree(value))
    counts = Counter(type(item).__name__ for _, item in nodes)
    keys = [key for _, item in nodes if isinstance(item, dict) for key in item]
    strings = [item for _, item in nodes if isinstance(item, str)]
    numbers = [item for _, item in nodes if isinstance(item, (int, float)) and not isinstance(item, bool)]
    arrays = [item for _, item in nodes if isinstance(item, list)]
    objects = [item for _, item in nodes if isinstance(item, dict)]
    max_depth = max((path_text.count(".") + path_text.count("[") for path_text, _ in nodes), default=0)

    if action == "root_type":
        result = type(value).__name__
    elif action == "node_count":
        result = str(len(nodes))
    elif action == "max_depth":
        result = str(max_depth)
    elif action == "object_count":
        result = str(len(objects))
    elif action == "array_count":
        result = str(len(arrays))
    elif action == "string_count":
        result = str(len(strings))
    elif action == "number_count":
        result = str(len(numbers))
    elif action == "boolean_count":
        result = str(sum(isinstance(item, bool) for _, item in nodes))
    elif action == "null_count":
        result = str(sum(item is None for _, item in nodes))
    elif action == "unique_key_count":
        result = str(len(set(keys)))
    elif action == "key_occurrences":
        result = str(len(keys))
    elif action == "key_list":
        result = "\n".join(sorted(set(keys))) or "Keine Schlüssel."
    elif action == "duplicate_keys":
        result = "\n".join(duplicate_keys) or "Keine doppelten JSON-Schlüssel."
    elif action == "paths":
        result = "\n".join(node_path for node_path, _ in nodes)
    elif action == "top_level_keys":
        result = "\n".join(value.keys()) if isinstance(value, dict) else "Wurzel ist kein Objekt."
    elif action == "top_level_count":
        result = str(len(value)) if isinstance(value, (dict, list)) else "Wurzel hat keine Elemente."
    elif action == "top_level_type":
        result = "\n".join(f"{key}: {type(child).__name__}" for key, child in value.items()) if isinstance(value, dict) else "Wurzel ist kein Objekt."
    elif action == "empty_objects":
        result = str(sum(not item for item in objects))
    elif action == "empty_arrays":
        result = str(sum(not item for item in arrays))
    elif action == "empty_strings":
        result = str(sum(not item for item in strings))
    elif action == "longest_string":
        result = max(strings, key=len, default="")
    elif action == "shortest_string":
        result = min(strings, key=len, default="")
    elif action == "average_string_length":
        result = f"{statistics.mean(map(len, strings)):.1f}" if strings else "0"
    elif action == "longest_string_path":
        result = max(
            ((len(item), node_path) for node_path, item in nodes if isinstance(item, str)),
            default=(0, ""),
        )[1]
    elif action == "number_min":
        result = str(min(numbers)) if numbers else "Keine Zahlen."
    elif action == "number_max":
        result = str(max(numbers)) if numbers else "Keine Zahlen."
    elif action == "number_sum":
        result = str(sum(numbers))
    elif action == "number_average":
        result = f"{statistics.mean(numbers):.4g}" if numbers else "Keine Zahlen."
    elif action == "array_lengths":
        result = "\n".join(f"{node_path}: {len(item)}" for node_path, item in nodes if isinstance(item, list)) or "Keine Arrays."
    elif action == "largest_array":
        result = max(
            ((len(item), node_path) for node_path, item in nodes if isinstance(item, list)),
            default=(0, "Keine Arrays."),
        )[1]
    elif action == "object_key_counts":
        result = "\n".join(f"{node_path}: {len(item)}" for node_path, item in nodes if isinstance(item, dict)) or "Keine Objekte."
    elif action == "largest_object":
        result = max(
            ((len(item), node_path) for node_path, item in nodes if isinstance(item, dict)),
            default=(0, "Keine Objekte."),
        )[1]
    elif action == "boolean_values":
        result = "\n".join(f"{node_path}: {str(item).lower()}" for node_path, item in nodes if isinstance(item, bool)) or "Keine Boolean-Werte."
    elif action == "null_paths":
        result = "\n".join(node_path for node_path, item in nodes if item is None) or "Keine null-Werte."
    elif action == "value_type_counts":
        result = "\n".join(f"{name}: {count}" for name, count in sorted(counts.items()))
    elif action == "string_duplicates":
        duplicates = [item for item, count in Counter(strings).items() if count > 1]
        result = "\n".join(sorted(duplicates)) or "Keine wiederholten Strings."
    elif action == "empty_value_paths":
        result = "\n".join(
            node_path for node_path, item in nodes
            if item is None or item == "" or item == [] or item == {}
        ) or "Keine leeren Werte."
    elif action == "unicode_strings":
        result = "\n".join(text for text in strings if not text.isascii()) or "Keine Unicode-Strings."
    elif action == "whitespace_strings":
        result = "\n".join(repr(text) for text in strings if text != text.strip()) or "Keine Strings mit Rand-Leerzeichen."
    elif action == "empty_key_count":
        result = str(sum(not key for key in keys))
    else:
        raise ValueError(f"Unbekannte JSON-Abfrage: {action}")

    print(result)
    return 0


def _make_handler(group: str, action: str, target: str = "") -> Callable[[list[str]], int]:
    def handler(args: list[str]) -> int:
        if group == "ast":
            return _run_ast_query(args, action, target)
        if group == "token":
            return _run_token_query(args, target, action == "list")
        if group == "project":
            return _project_query(action, args)
        if group == "quality":
            return _run_quality_check(action, args)
        if group == "json":
            return _run_json_query(action, args)
        raise ValueError(f"Unbekannte Befehlsgruppe: {group}")

    handler.__name__ = f"cmd_{group}_{action}_{target.lower()}"
    return handler


def _command_name(value: str) -> str:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", value)
    return re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()


AST_NODE_NAMES = (
    "NumberExpression", "StringExpression", "CharacterExpression",
    "BooleanExpression", "NullExpression", "ArrayExpression",
    "VariableExpression", "IndexExpression", "MemberExpression",
    "UnaryExpression", "BinaryExpression", "CallExpression",
    "NewExpression", "ExpressionStatement", "PrintStatement",
    "VariableDeclaration", "AssignmentStatement",
    "IndexAssignmentStatement", "MemberAssignmentStatement",
    "IfStatement", "WhileStatement", "DoWhileStatement", "SwitchCase",
    "SwitchStatement", "EnumDeclaration", "ForStatement", "BreakStatement",
    "ContinueStatement", "ReturnStatement", "FunctionDeclaration",
    "MethodCallExpression", "ClassDeclaration", "StructField",
    "StructDeclaration", "ImportStatement", "TryStatement", "Program",
)

AST_COMMANDS: dict[str, tuple[Callable[[list[str]], int], str]] = {}
for _node_name in AST_NODE_NAMES:
    _name = _command_name(_node_name)
    AST_COMMANDS[f"ast-count-{_name}"] = (
        _make_handler("ast", "count-node", _node_name),
        f"Zählt {_node_name}-Knoten im Nexa-AST",
    )

for _group in ("expression", "statement", "declaration"):
    AST_COMMANDS[f"ast-count-{_group}"] = (
        _make_handler("ast", "count-group", _group),
        f"Zählt AST-{_group}-Knoten",
    )

TOKEN_NAMES = (
    "IDENTIFIER", "KEYWORD", "STRING", "CHARACTER", "NUMBER",
    "PLUS", "MINUS", "STAR", "SLASH", "PERCENT", "CARET", "STAR_STAR",
    "EQUAL", "EQUAL_EQUAL", "NOT_EQUAL", "LESS", "GREATER", "LESS_EQUAL",
    "GREATER_EQUAL", "LOGICAL_AND", "LOGICAL_OR", "LOGICAL_NOT",
    "BIT_AND", "BIT_OR", "BIT_XOR", "BIT_NOT", "SHIFT_LEFT",
    "SHIFT_RIGHT", "PLUS_EQUAL", "MINUS_EQUAL", "STAR_EQUAL",
    "SLASH_EQUAL", "PERCENT_EQUAL", "BIT_AND_EQUAL", "BIT_OR_EQUAL",
    "BIT_XOR_EQUAL", "SHIFT_LEFT_EQUAL", "SHIFT_RIGHT_EQUAL",
    "INCREMENT", "DECREMENT",
)

TOKEN_COMMANDS: dict[str, tuple[Callable[[list[str]], int], str]] = {}
for _token_name in TOKEN_NAMES:
    _name = _command_name(_token_name)
    TOKEN_COMMANDS[f"token-count-{_name}"] = (
        _make_handler("token", "count", _token_name),
        f"Zählt {_token_name}-Tokens in Nexa-Quelldateien",
    )


PROJECT_QUERIES = {
    "project-largest-file": ("largest", "Zeigt die größte Projektdatei"),
    "project-smallest-file": ("smallest", "Zeigt die kleinste Projektdatei"),
    "project-newest-file": ("newest", "Zeigt die zuletzt geänderte Projektdatei"),
    "project-oldest-file": ("oldest", "Zeigt die älteste Projektdatei"),
    "project-median-file-size": ("median-size", "Zeigt die mediane Dateigröße"),
    "project-average-file-size": ("average-size", "Zeigt die mittlere Dateigröße"),
    "project-total-bytes": ("total-size", "Summiert die Bytes aller Projektdateien"),
    "project-largest-files": ("largest-ten", "Zeigt die zehn größten Projektdateien"),
    "project-extension-kinds": ("extension-count", "Zählt unterschiedliche Dateiendungen"),
    "project-extension-report": ("extension-report", "Zeigt Dateizahlen je Endung"),
    "project-empty-files": ("empty-files", "Findet leere Dateien"),
    "project-empty-directories": ("empty-directories", "Findet leere Verzeichnisse"),
    "project-deepest-file": ("deepest-file", "Zeigt die am tiefsten verschachtelte Datei"),
    "project-root-files": ("root-files", "Listet Dateien direkt im Projektstamm"),
    "project-nested-files": ("nested-files", "Listet Dateien in Unterverzeichnissen"),
    "project-hidden-files": ("hidden-files", "Listet versteckte Dateien"),
    "project-extensionless-files": ("extensionless", "Listet Dateien ohne Endung"),
    "project-duplicate-names": ("duplicate-names", "Findet gleiche Dateinamen in verschiedenen Ordnern"),
    "project-case-collisions": ("case-collisions", "Findet Pfade mit unterschiedlicher Groß-/Kleinschreibung"),
    "project-symlinks": ("symlinks", "Listet symbolische Links"),
    "project-source-lines": ("source-line-count", "Zählt Quelltextzeilen"),
    "project-source-characters": ("source-character-count", "Zählt Quelltextzeichen"),
    "project-average-source-lines": ("source-average-lines", "Berechnet Quelltextzeilen je Datei im Mittel"),
    "project-average-line-length": ("source-average-line-length", "Berechnet die mittlere Quellzeilenlänge"),
    "project-longest-line": ("longest-source-line", "Findet die längste Quelltextzeile"),
    "project-blank-lines": ("blank-lines", "Zählt Leerzeilen in Quelltexten"),
    "project-tabbed-files": ("tabbed-files", "Findet Quelltexte mit Tabulatoren"),
    "project-bom-files": ("bom-files", "Findet UTF-8-Dateien mit BOM"),
    "project-missing-final-newline": ("missing-final-newline", "Findet Quelltexte ohne abschließenden Zeilenumbruch"),
    "project-newline-report": ("newline-report", "Zählt CRLF-, LF- und CR-Zeilenenden"),
    "project-binary-candidates": ("binary-candidates", "Findet Dateien mit Nullbytes"),
    "project-source-by-extension": ("source-by-extension", "Zählt Quelltexte nach Endung"),
    "project-average-file-age": ("average-age-days", "Berechnet das mittlere Dateialter in Tagen"),
    "project-recent-files": ("recent-ten", "Zeigt die zehn zuletzt geänderten Dateien"),
    "project-oldest-files": ("oldest-ten", "Zeigt die zehn ältesten Dateien"),
    "project-files-per-directory": ("files-per-directory", "Zählt Dateien je Ordner"),
    "project-maximum-depth": ("maximum-depth", "Zeigt die maximale Projekt-Verschachtelung"),
    "project-readable-source-count": ("readable-source-count", "Zählt lesbare Quelltextdateien"),
    "project-unreadable-source-count": ("unreadable-source-count", "Zählt nicht lesbare Quelltextdateien"),
    "project-largest-extension": ("largest-extension", "Zeigt den größten Endungs-Speicherverbrauch"),
}

QUALITY_COMMANDS = {
    f"quality-{name}": (
        _make_handler("quality", name),
        f"Prüft Quelltexte auf {description.lower()}",
    )
    for name, (_, description) in QUALITY_RULES.items()
}

JSON_QUERY_NAMES = {
    "root_type": ("json-root-type", "Zeigt den JSON-Wurzeltyp"),
    "node_count": ("json-node-count", "Zählt alle JSON-Knoten"),
    "max_depth": ("json-max-depth", "Berechnet die maximale JSON-Verschachtelung"),
    "object_count": ("json-object-count", "Zählt JSON-Objekte"),
    "array_count": ("json-array-count", "Zählt JSON-Arrays"),
    "string_count": ("json-string-count", "Zählt JSON-Strings"),
    "number_count": ("json-number-count", "Zählt JSON-Zahlen"),
    "boolean_count": ("json-boolean-count", "Zählt JSON-Boolean-Werte"),
    "null_count": ("json-null-count", "Zählt JSON-null-Werte"),
    "unique_key_count": ("json-unique-key-count", "Zählt unterschiedliche JSON-Schlüssel"),
    "key_occurrences": ("json-key-occurrences", "Zählt alle JSON-Schlüsselvorkommen"),
    "key_list": ("json-key-list", "Listet alle unterschiedlichen JSON-Schlüssel"),
    "duplicate_keys": ("json-duplicate-keys", "Findet doppelte Schlüssel innerhalb eines JSON-Objekts"),
    "paths": ("json-paths", "Listet alle JSON-Pfade"),
    "top_level_keys": ("json-top-level-keys", "Listet Schlüssel des JSON-Wurzelobjekts"),
    "top_level_count": ("json-top-level-count", "Zählt Elemente am JSON-Wurzelknoten"),
    "top_level_type": ("json-top-level-types", "Zeigt Typen der Werte im Wurzelobjekt"),
    "empty_objects": ("json-empty-objects", "Zählt leere JSON-Objekte"),
    "empty_arrays": ("json-empty-arrays", "Zählt leere JSON-Arrays"),
    "empty_strings": ("json-empty-strings", "Zählt leere JSON-Strings"),
    "longest_string": ("json-longest-string", "Zeigt den längsten JSON-String"),
    "shortest_string": ("json-shortest-string", "Zeigt den kürzesten JSON-String"),
    "average_string_length": ("json-average-string-length", "Berechnet die mittlere JSON-Stringlänge"),
    "longest_string_path": ("json-longest-string-path", "Zeigt den Pfad des längsten JSON-Strings"),
    "number_min": ("json-number-min", "Zeigt die kleinste JSON-Zahl"),
    "number_max": ("json-number-max", "Zeigt die größte JSON-Zahl"),
    "number_sum": ("json-number-sum", "Summiert alle JSON-Zahlen"),
    "number_average": ("json-number-average", "Berechnet den Mittelwert der JSON-Zahlen"),
    "array_lengths": ("json-array-lengths", "Zeigt die Länge jedes JSON-Arrays"),
    "largest_array": ("json-largest-array", "Findet das größte JSON-Array"),
    "object_key_counts": ("json-object-key-counts", "Zeigt die Schlüsselanzahl jedes Objekts"),
    "largest_object": ("json-largest-object", "Findet das Objekt mit den meisten Schlüsseln"),
    "boolean_values": ("json-boolean-values", "Listet Pfade und Werte aller Booleans"),
    "null_paths": ("json-null-paths", "Listet Pfade zu allen null-Werten"),
    "value_type_counts": ("json-value-type-counts", "Zählt JSON-Werte nach Typ"),
    "string_duplicates": ("json-duplicate-strings", "Findet wiederholte JSON-Strings"),
    "empty_value_paths": ("json-empty-value-paths", "Findet Pfade zu leeren JSON-Werten"),
    "unicode_strings": ("json-unicode-strings", "Listet JSON-Strings mit Nicht-ASCII-Zeichen"),
    "whitespace_strings": ("json-padded-strings", "Findet JSON-Strings mit Rand-Leerzeichen"),
    "empty_key_count": ("json-empty-key-count", "Zählt leere JSON-Schlüssel"),
}

JSON_COMMANDS = {
    command: (_make_handler("json", action), description)
    for action, (command, description) in JSON_QUERY_NAMES.items()
}

EXTRA_COMMANDS = {
    **AST_COMMANDS,
    **TOKEN_COMMANDS,
    **{
        command: (_make_handler("project", action), description)
        for command, (action, description) in PROJECT_QUERIES.items()
    },
    **QUALITY_COMMANDS,
    **JSON_COMMANDS,
}

if len(EXTRA_COMMANDS) != 200:
    raise RuntimeError(
        f"Erwartet wurden genau 200 neue Befehle, gefunden: {len(EXTRA_COMMANDS)}"
    )
