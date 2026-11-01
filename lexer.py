from dataclasses import dataclass
from enum import Enum, auto


TARGET_KEYWORD_COUNT = 10_000


class TokenType(Enum):
    IDENTIFIER = auto()
    KEYWORD = auto()
    STRING = auto()
    CHARACTER = auto()
    NUMBER = auto()

    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    PERCENT = auto()
    CARET = auto()
    STAR_STAR = auto()

    EQUAL = auto()
    EQUAL_EQUAL = auto()
    NOT_EQUAL = auto()

    LESS = auto()
    GREATER = auto()
    LESS_EQUAL = auto()
    GREATER_EQUAL = auto()

    LOGICAL_AND = auto()
    LOGICAL_OR = auto()
    NULL_COALESCING = auto()
    LOGICAL_NOT = auto()

    BIT_AND = auto()
    BIT_OR = auto()
    BIT_XOR = auto()
    BIT_NOT = auto()

    SHIFT_LEFT = auto()
    SHIFT_RIGHT = auto()

    PLUS_EQUAL = auto()
    MINUS_EQUAL = auto()
    STAR_EQUAL = auto()
    SLASH_EQUAL = auto()
    PERCENT_EQUAL = auto()

    BIT_AND_EQUAL = auto()
    BIT_OR_EQUAL = auto()
    BIT_XOR_EQUAL = auto()
    SHIFT_LEFT_EQUAL = auto()
    SHIFT_RIGHT_EQUAL = auto()

    INCREMENT = auto()
    DECREMENT = auto()

    ARROW = auto()
    FAT_ARROW = auto()

    LEFT_PAREN = auto()
    RIGHT_PAREN = auto()
    LEFT_BRACKET = auto()
    RIGHT_BRACKET = auto()
    LEFT_BRACE = auto()
    RIGHT_BRACE = auto()

    COMMA = auto()
    DOT = auto()
    SEMICOLON = auto()
    COLON = auto()

    QUESTION = auto()
    AT = auto()
    HASH = auto()

    EOF = auto()


@dataclass
class Token:
    type: TokenType
    value: str
    position: int


class Lexer:

# ============================================================
    # NEXA KEYWORDS
    # ============================================================

    KEYWORDS = {
        # Variablen / Deklaration
        "let", "var", "const", "static", "global", "local",
        "readonly", "final", "mutable", "immutable", "shared",
        "persistent", "temporary", "volatile", "atomic",
        "constant", "variable", "alias", "extern", "inline",
        "abstract", "sealed", "open", "partial", "unsafe",

        # Datentypen
        "int", "int8", "int16", "int32", "int64", "int128",
        "uint8", "uint16", "uint32", "uint64", "uint128",
        "float", "float16", "float32", "float64", "decimal",
        "bigint", "complex", "rational", "byte", "bit", "char",
        "string", "text", "bool", "object", "any", "auto",
        "infer", "optional", "required", "unknown", "never",
        "array", "list", "set", "map", "dict", "record",
        "tuple", "vector", "matrix", "tensor", "grid",
        "tree", "graph", "stack", "queue", "heap", "buffer",
        "stream", "channel", "iterator", "generator",
        "sequence", "collection", "dictionary", "pair", "triple",
        "range", "slice", "view", "span", "union", "variant",
        "result", "success", "failure", "errorvalue",
        "keyvalue", "node", "edge", "property", "field",
        "attribute", "metadata", "schema", "shape", "dimension",
        "unit", "measure", "currency", "percentage",
        "timestamp", "duration", "type", "newtype", "protocol",

        # Werte
        "true", "false", "null", "none",

        # Kontrollfluss
        "if", "else", "elseif", "then",
        "while", "loop", "repeat", "for", "foreach", "in",
        "break", "continue", "return", "yield",
        "switch", "case", "default", "match", "when",
        "otherwise", "unless", "until", "fallthrough",
        "select", "where", "guard", "require", "ensure",
        "assert", "verify", "check", "validate", "invariant",
        "precondition", "postcondition", "contract",

        # Funktionen
        "function", "fn", "lambda", "closure", "callback",
        "method", "getter", "setter", "constructor", "destructor",
        "delegate", "procedure", "macro", "operator", "extension",
        "coroutine", "async", "await", "defer", "spawn", "task",

        # Klassen / Objekte
        "class", "struct", "enum", "interface", "trait",
        "new", "self", "this", "super", "base", "extends",
        "implements", "abstract", "virtual", "override",
        "public", "private", "protected", "internal",
        "instance", "prototype", "inherits", "owns",

        # Fehlerbehandlung
        "try", "catch", "finally", "throw", "panic", "abort",
        "recover", "retry", "error", "ignore", "suppress",
        "checkpoint", "rollback", "transaction", "commit",

        # Module
        "import", "export", "module", "package", "namespace",
        "from", "as", "include", "using", "library",

        # Konvertierung / Reflektion
        "is", "as", "cast", "convert", "typeof", "sizeof",
        "nameof", "default", "implicit", "explicit",

        # Logik
        "and", "or", "not", "xor", "oneof", "allof", "anyof",
        "noneof", "every", "some", "only", "except",

        # Nebenläufigkeit
        "lock", "unlock", "mutex", "semaphore", "parallel",
        "concurrent", "synchronized", "atomicblock",
        "deadlock", "race",

        # Fortschritt / Messen
        "begin", "end", "start", "continuewith", "finish",
        "complete", "next", "previous", "first", "last",
        "current", "nextvalue", "previousvalue",

        # Zugriffsschutz
        "allow", "deny", "grant", "revoke", "protect",
        "secure", "secret", "token", "permission",

        # Sonstiges
        "infinity", "nan", "undefined", "optionalvalue",
        "either", "choose", "branch", "fork", "join",
        "merge", "split", "chain", "pipe", "flow", "route",
        "target", "source", "destination", "input", "output",
    }

    KEYWORDS.update({
        # Erweiterte Typen
        "int256", "uint256", "float128", "decimal128", "half", "single",
        "double", "long", "short", "signed", "unsigned", "number",
        "numeric", "enumeration", "bitset", "bytes", "bytearray",
        "chararray", "wchar", "u8", "u16", "u32", "u64", "u128",
        "fixedpoint", "interval", "optionaltype", "nonetype", "void",
        "unitvalue",

        # Speicher und Besitz
        "allocate", "allocation", "deallocate", "free", "release",
        "borrow", "borrowed", "ownership", "lifetime", "scope",
        "stackalloc", "heapalloc", "arena", "pool", "pointer",
        "reference", "weakref", "strongref", "nullable", "nonnull",
        "alignment", "aligned", "unaligned", "packed", "readonlyref",
        "mutref", "move", "copy", "clone", "drop",

        # Iteration und Kontrollfluss
        "loopwhile", "loopfor", "loopuntil", "loopwhileend", "iterate",
        "iteration", "enumerate", "zip", "filter", "reduce", "fold",
        "flatmap", "foreachkey", "foreachvalue", "foreachitem",
        "parallelfor", "breakpoint", "fallthroughcase",
        "fallthroughswitch", "continueouter", "breakouter", "returning",
        "exit", "halt", "stop", "skip", "restart", "redo", "repeatuntil",
        "repeatwhile",

        # Funktionen und Aufrufkonventionen
        "pure", "impure", "inlinehint", "noinline", "tailcall",
        "recursion", "recursive", "variadic", "params", "kwargs", "named",
        "optionalparam", "defaultparam", "restparam", "refparam", "outparam",
        "inout", "callbacktype", "functor", "combinator", "partialfn",
        "compose", "currying", "uncurry", "apply", "invoke", "callable",
        "callsite", "entrypoint", "mainfn",

        # Objekte und Typsystem
        "mixin", "composition", "aggregation", "association", "friend",
        "finalclass", "sealedclass", "abstractclass", "virtualmethod",
        "staticmethod", "classmethod", "propertymethod", "fieldmethod",
        "recordclass", "dataclass", "constructorof", "destructuring",
        "pattern", "patternmatch", "tuplepattern", "guarded",
        "extensionmethod", "impl", "protocoltype", "typeclass", "subclass",
        "superclass", "interfaceof", "objecttype", "metatype",

        # Netzwerk und Datenformate
        "http", "https", "tcp", "udp", "ip", "ipv4", "ipv6", "dns", "url",
        "uri", "request", "response", "header", "body", "query",
        "routehandler", "middleware", "websocket", "socket", "listen",
        "connect", "disconnect", "bind", "accept", "send", "receive",
        "serialize", "deserialize", "parsejson", "formdata",

        # Allgemeine Werkzeuge
        "date", "time", "datetime", "timezone", "locale", "format", "parse",
        "matchresult", "random", "seed", "cryptography", "hash", "digest",
        "checksum", "compress", "decompress", "archive", "streaming",
        "buffered", "flush", "close", "openfile", "readfile", "writefile",
        "append", "truncate", "seek",
    })

    KEYWORDS.update(
        f"nexa_reserved_{index:04d}"
        for index in range(1, TARGET_KEYWORD_COUNT - len(KEYWORDS) + 1)
    )
    if len(KEYWORDS) != TARGET_KEYWORD_COUNT:
        raise RuntimeError(
            f"Erwartet wurden genau {TARGET_KEYWORD_COUNT} Nexa-Schlüsselwörter, "
            f"gefunden: {len(KEYWORDS)}"
        )

    SYMBOLS = {
        "+": TokenType.PLUS,
        "-": TokenType.MINUS,
        "*": TokenType.STAR,
        "/": TokenType.SLASH,
        "%": TokenType.PERCENT,
        "=": TokenType.EQUAL,
        "<": TokenType.LESS,
        ">": TokenType.GREATER,
        "!": TokenType.LOGICAL_NOT,
"&": TokenType.BIT_AND,
        "|": TokenType.BIT_OR,
        "^": TokenType.CARET,
        "~": TokenType.BIT_NOT,
        "(": TokenType.LEFT_PAREN,
        ")": TokenType.RIGHT_PAREN,
        "[": TokenType.LEFT_BRACKET,
        "]": TokenType.RIGHT_BRACKET,
        "{": TokenType.LEFT_BRACE,
        "}": TokenType.RIGHT_BRACE,
        ",": TokenType.COMMA,
        ".": TokenType.DOT,
        ";": TokenType.SEMICOLON,
        ":": TokenType.COLON,
        "?": TokenType.QUESTION,
        "@": TokenType.AT,
        "#": TokenType.HASH,
    }

    TWO_CHAR_SYMBOLS = {
        "==": TokenType.EQUAL_EQUAL,
        "!=": TokenType.NOT_EQUAL,
        "<=": TokenType.LESS_EQUAL,
        ">=": TokenType.GREATER_EQUAL,
        "&&": TokenType.LOGICAL_AND,
        "||": TokenType.LOGICAL_OR,
        "??": TokenType.NULL_COALESCING,
        "<<": TokenType.SHIFT_LEFT,
        ">>": TokenType.SHIFT_RIGHT,
        "+=": TokenType.PLUS_EQUAL,
        "-=": TokenType.MINUS_EQUAL,
        "*=": TokenType.STAR_EQUAL,
        "/=": TokenType.SLASH_EQUAL,
        "%=": TokenType.PERCENT_EQUAL,
        "&=": TokenType.BIT_AND_EQUAL,
        "|=": TokenType.BIT_OR_EQUAL,
        "^=": TokenType.BIT_XOR_EQUAL,
        "++": TokenType.INCREMENT,
        "--": TokenType.DECREMENT,
        "->": TokenType.ARROW,
        "=>": TokenType.FAT_ARROW,
        "**": TokenType.STAR_STAR,
    }

    THREE_CHAR_SYMBOLS = {
        "<<=": TokenType.SHIFT_LEFT_EQUAL,
        ">>=": TokenType.SHIFT_RIGHT_EQUAL,
    }

    def __init__(self, source):
        self.source = source
        self.position = 0
        self.tokens = []

    def tokenize(self):
        while not self.is_at_end():
            self.skip_whitespace_and_comments()

            if self.is_at_end():
                break

            start = self.position
            char = self.advance()

            if self.is_identifier_start(char):
                self.scan_identifier(start)
                continue

            if char.isdigit():
                self.scan_number(start)
                continue

            if char == '"':
                self.scan_string(start)
                continue

            if char == "'":
                self.scan_character(start)
                continue

            if self.position + 1 < len(self.source):
                three = (
                    char
                    + self.source[self.position]
                    + self.source[self.position + 1]
                )

                if three in self.THREE_CHAR_SYMBOLS:
                    self.position += 2
                    self.tokens.append(
                        Token(
                            self.THREE_CHAR_SYMBOLS[three],
                            three,
                            start
                        )
                    )
                    continue

            if self.position < len(self.source):
                two = char + self.source[self.position]

                if two in self.TWO_CHAR_SYMBOLS:
                    self.position += 1
                    self.tokens.append(
                        Token(
                            self.TWO_CHAR_SYMBOLS[two],
                            two,
                            start
                        )
                    )
                    continue

            if char in self.SYMBOLS:
                self.tokens.append(
                    Token(
                        self.SYMBOLS[char],
                        char,
                        start
                    )
                )
                continue

            raise SyntaxError(
                f"Unbekanntes Zeichen '{char}' an Position {start}"
            )

        self.tokens.append(
            Token(
                TokenType.EOF,
                "",
                self.position
            )
        )

        return self.tokens

    def scan_identifier(self, start):
        while not self.is_at_end():
            char = self.peek()

            if char.isalnum() or char == "_":
                self.advance()
            else:
                break

        value = self.source[start:self.position]

        token_type = (
            TokenType.KEYWORD
            if value in self.KEYWORDS
            else TokenType.IDENTIFIER
        )

        self.tokens.append(
            Token(
                token_type,
                value,
                start
            )
        )

    def scan_number(self, start):
        if (
            self.source[start] == "0"
            and self.peek().lower() == "b"
        ):
            self.advance()
            digits_start = self.position

            while not self.is_at_end() and self.peek() in "01":
                self.advance()

            if self.position == digits_start:
                raise SyntaxError(
                    f"Ungültige Binärzahl an Position {start}"
                )

            self.tokens.append(
                Token(
                    TokenType.NUMBER,
                    self.source[start:self.position],
                    start
                )
            )
            return

        if (
            self.source[start] == "0"
            and self.peek().lower() == "x"
        ):
            self.advance()
            digits_start = self.position

            while (
                not self.is_at_end()
                and self.peek() in "0123456789abcdefABCDEF"
            ):
                self.advance()

            if self.position == digits_start:
                raise SyntaxError(
                    f"Ungültige Hexadezimalzahl an Position {start}"
                )

            self.tokens.append(
                Token(
                    TokenType.NUMBER,
                    self.source[start:self.position],
                    start
                )
            )
            return

        if (
            self.source[start] == "0"
            and self.peek().lower() == "o"
        ):
            self.advance()
            digits_start = self.position

            while not self.is_at_end() and self.peek() in "01234567":
                self.advance()

            if self.position == digits_start:
                raise SyntaxError(
                    f"Ungültige Oktalzahl an Position {start}"
                )

            self.tokens.append(
                Token(
                    TokenType.NUMBER,
                    self.source[start:self.position],
                    start
                )
            )
            return

        while not self.is_at_end() and self.peek().isdigit():
            self.advance()

        if (
            not self.is_at_end()
            and self.peek() == "."
            and self.position + 1 < len(self.source)
            and self.source[self.position + 1].isdigit()
        ):
            self.advance()

            while not self.is_at_end() and self.peek().isdigit():
                self.advance()

        self.tokens.append(
            Token(
                TokenType.NUMBER,
                self.source[start:self.position],
                start
            )
        )

    def scan_string(self, start):
        characters = []

        while not self.is_at_end():
            char = self.advance()

            if char == '"':
                self.tokens.append(
                    Token(
                        TokenType.STRING,
                        "".join(characters),
                        start
                    )
                )
                return

            if char == "\n":
                raise SyntaxError(
                    f"String darf nicht über mehrere Zeilen gehen "
                    f"(Position {start})"
                )

            if char == "\\":
                if self.is_at_end():
                    raise SyntaxError(
                        f"Unvollständige Escape-Sequenz "
                        f"an Position {self.position - 1}"
                    )

                escaped = self.advance()

                escapes = {
                    "n": "\n",
                    "r": "\r",
                    "t": "\t",
                    '"': '"',
                    "'": "'",
                    "\\": "\\",
                    "0": "\0",
                }

                if escaped not in escapes:
                    raise SyntaxError(
                        f"Unbekannte Escape-Sequenz '\\{escaped}'"
                    )

                characters.append(escapes[escaped])
            else:
                characters.append(char)

        raise SyntaxError(
            f"Unbeendeter String an Position {start}"
        )

    def scan_character(self, start):
        if self.is_at_end():
            raise SyntaxError(
                f"Unbeendetes Zeichen an Position {start}"
            )

        char = self.advance()

        if char == "\\":
            if self.is_at_end():
                raise SyntaxError(
                    f"Unvollständige Escape-Sequenz "
                    f"an Position {self.position - 1}"
                )

            escaped = self.advance()

            escapes = {
                "n": "\n",
                "r": "\r",
                "t": "\t",
                "'": "'",
                '"': '"',
                "\\": "\\",
                "0": "\0",
            }

            if escaped not in escapes:
                raise SyntaxError(
                    f"Unbekannte Escape-Sequenz '\\{escaped}'"
                )

            char = escapes[escaped]

        if char == "\n":
            raise SyntaxError(
                f"Zeichen darf nicht über mehrere Zeilen gehen "
                f"(Position {start})"
            )

        if self.is_at_end() or self.peek() != "'":
            raise SyntaxError(
                f"Char-Literal muss genau ein Zeichen enthalten "
                f"(Position {start})"
            )

        self.advance()

        self.tokens.append(
            Token(
                TokenType.CHARACTER,
                char,
                start
            )
        )

    def skip_whitespace_and_comments(self):
        while not self.is_at_end():

            if self.peek().isspace():
                self.advance()
                continue

            if (
                self.peek() == "/"
                and self.peek(1) == "/"
            ):
                self.advance()
                self.advance()

                while (
                    not self.is_at_end()
                    and self.peek() != "\n"
                ):
                    self.advance()

                continue

            if (
                self.peek() == "/"
                and self.peek(1) == "*"
            ):
                start = self.position

                self.advance()
                self.advance()

                while not self.is_at_end():

                    if (
                        self.peek() == "*"
                        and self.peek(1) == "/"
                    ):
                        self.advance()
                        self.advance()
                        break

                    self.advance()

                else:
                    raise SyntaxError(
                        f"Unbeendeter Block-Kommentar "
                        f"an Position {start}"
                    )

                continue

            break

    def is_at_end(self):
        return self.position >= len(self.source)

    def advance(self):
        char = self.source[self.position]
        self.position += 1
        return char

    def peek(self, offset=0):
        index = self.position + offset

        if index >= len(self.source):
            return "\0"

        return self.source[index]

    @staticmethod
    def is_identifier_start(char):
        return char.isalpha() or char == "_"
