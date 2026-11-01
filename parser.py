
from dataclasses import dataclass
from lexer import TokenType, Token


# ============================================================
# AST – AUSDRÜCKE
# ============================================================

@dataclass
class NumberExpression:
    value: str


@dataclass
class StringExpression:
    value: str


@dataclass
class CharacterExpression:
    value: str


@dataclass
class BooleanExpression:
    value: bool


@dataclass
class NullExpression:
    pass


@dataclass
class ArrayExpression:
    elements: list


@dataclass
class VariableExpression:
    name: str


@dataclass
class IndexExpression:
    target: object
    index: object


@dataclass
class MemberExpression:
    target: object
    member: str


@dataclass
class UnaryExpression:
    operator: TokenType
    operand: object


@dataclass
class BinaryExpression:
    left: object
    operator: TokenType
    right: object


@dataclass
class ConditionalExpression:
    condition: object
    true_expression: object
    false_expression: object


@dataclass
class CallExpression:
    name: str
    arguments: list


@dataclass
class NewExpression:
    type_name: str
    arguments: list


# ============================================================
# AST – STATEMENTS
# ============================================================

@dataclass
class ExpressionStatement:
    expression: object


@dataclass
class PrintStatement:
    expression: object


@dataclass
class VariableDeclaration:
    name: str
    variable_type: str
    expression: object


@dataclass
class AssignmentStatement:
    name: str
    expression: object


@dataclass
class IndexAssignmentStatement:
    target: object
    index: object
    expression: object


@dataclass
class MemberAssignmentStatement:
    target: object
    member: str
    expression: object


@dataclass
class IfStatement:
    condition: object
    then_branch: list
    else_branch: object


@dataclass
class WhileStatement:
    condition: object
    body: list


@dataclass
class DoWhileStatement:
    body: list
    condition: object


@dataclass
class SwitchCase:
    values: list
    body: list


@dataclass
class SwitchStatement:
    expression: object
    cases: list
    default_body: object


@dataclass
class EnumDeclaration:
    name: str
    members: list


@dataclass
class ForStatement:
    initializer: object
    condition: object
    increment: object
    body: list


@dataclass
class BreakStatement:
    pass


@dataclass
class ContinueStatement:
    pass


@dataclass
class ReturnStatement:
    expression: object


@dataclass
class FunctionDeclaration:
    name: str
    parameters: list
    body: list


@dataclass
class MethodCallExpression:
    target: object
    name: str
    arguments: list


@dataclass
class ClassDeclaration:
    name: str
    fields: list
    methods: dict
    superclass_name: str = None


@dataclass
class StructField:
    name: str
    variable_type: str


@dataclass
class StructDeclaration:
    name: str
    fields: list


@dataclass
class ImportStatement:
    path: str


@dataclass
class TryStatement:
    try_body: list
    catch_variable: str
    catch_body: list


@dataclass
class Program:
    statements: list


# ============================================================
# PARSER
# ============================================================

class Parser:

    def __init__(self, tokens):
        self.tokens = tokens
        self.position = 0

    # ========================================================
    # PROGRAMM
    # ========================================================

    def parse(self):
        statements = []

        while not self.check(TokenType.EOF):
            statements.append(self.parse_statement())

        return Program(statements)

    # ========================================================
    # STATEMENTS
    # ========================================================

    def parse_statement(self):

        # print(...)
        if self.check_identifier("print"):
            return self.parse_print()

        # let name = expression;
        if self.check_identifier("let"):
            return self.parse_let()

        # var name = expression;
        if self.check_identifier("var"):
            return self.parse_let()

        # const name = expression;
        if self.check_identifier("const"):
            return self.parse_const()

        # Typisierte Variablendeklaration
        # int x = 10;
        # string name = "Tim";
        if self.is_variable_type():
            return self.parse_variable_declaration()

        # import
        if self.check_identifier("import"):
            return self.parse_import()

        # class
        if self.check_identifier("class"):
            return self.parse_class()

        # struct
        if self.check_identifier("struct"):
            return self.parse_struct()

        # if
        if self.check_identifier("if"):
            return self.parse_if()

        # while
        if self.check_identifier("while"):
            return self.parse_while()

        # do ... while
        if self.check_identifier("do"):
            return self.parse_do_while()

        # switch / case
        if self.check_identifier("switch"):
            return self.parse_switch()

        # enum
        if self.check_identifier("enum"):
            return self.parse_enum()

        # loop
        if self.check_identifier("loop"):
            return self.parse_loop()

        # repeat
        if self.check_identifier("repeat"):
            return self.parse_repeat()

        # for
        if self.check_identifier("for"):
            return self.parse_for()

        # foreach
        if self.check_identifier("foreach"):
            return self.parse_foreach()

        # break
        if self.check_identifier("break"):
            self.advance()

            self.consume(
                TokenType.SEMICOLON,
                "Nach 'break' wird ';' erwartet"
            )

            return BreakStatement()

        # continue
        if self.check_identifier("continue"):
            self.advance()

            self.consume(
                TokenType.SEMICOLON,
                "Nach 'continue' wird ';' erwartet"
            )

            return ContinueStatement()

        # return
        if self.check_identifier("return"):
            return self.parse_return()

        # function / fn
        if self.check_identifier("function"):
            return self.parse_function()

        if self.check_identifier("fn"):
            return self.parse_function()

        # try
        if self.check_identifier("try"):
            return self.parse_try()

        # expression / assignment
        return self.parse_expression_or_assignment()

    # ========================================================
    # LET
    # ========================================================

    def parse_let(self):

        # let / var
        self.advance()

        name = self.consume_identifier(
            "Nach 'let' wird ein Variablenname erwartet"
        )

        # let benötigt eine Initialisierung.
        if not self.match(TokenType.EQUAL):

            token = self.peek()

            raise SyntaxError(
                "Nach dem 'let'-Variablennamen wird '=' erwartet "
                f"(Position {token.position})"
            )

        expression = self.parse_expression()

        self.consume(
            TokenType.SEMICOLON,
            "Nach der 'let'-Variablendeklaration wird ';' erwartet"
        )

        return VariableDeclaration(
            name,
            "auto",
            expression
        )

    # ========================================================
    # CONST
    # ========================================================

    def parse_const(self):

        # const
        self.advance()

        name = self.consume_identifier(
            "Nach 'const' wird ein Variablenname erwartet"
        )

        if not self.match(TokenType.EQUAL):

            token = self.peek()

            raise SyntaxError(
                "Nach dem 'const'-Variablennamen wird '=' erwartet "
                f"(Position {token.position})"
            )

        expression = self.parse_expression()

        self.consume(
            TokenType.SEMICOLON,
            "Nach der 'const'-Variablendeklaration wird ';' erwartet"
        )

        return VariableDeclaration(
            name,
            "const",
            expression
        )

    # ========================================================
    # VARIABLE TYPES
    # ========================================================

    def is_variable_type(self):

        if not self.is_name_token():
            return False

        value = self.peek().value

        primitive_types = {
            "int",
            "int8",
            "int16",
            "int32",
            "int64",
            "int128",
            "uint8",
            "uint16",
            "uint32",
            "uint64",
            "uint128",
            "float",
            "float16",
            "float32",
            "float64",
            "decimal",
            "bigint",
            "complex",
            "rational",
            "byte",
            "bit",
            "char",
            "string",
            "text",
            "bool",
            "object",
            "any",
            "auto",
            "infer",
            "optional",
            "required",
            "unknown",
            "array",
            "list",
            "set",
            "map",
            "dict",
            "record",
            "tuple",
            "vector",
            "matrix",
            "tensor",
            "grid",
            "tree",
            "graph",
            "stack",
            "queue",
            "heap",
            "buffer",
            "stream",
            "channel",
            "iterator",
            "generator",
            "sequence",
            "collection",
            "dictionary",
            "pair",
            "triple",
            "range",
            "slice",
            "view",
            "span",
        }

        if value not in primitive_types:
            return False

        # Prüft, dass nach dem Typ wirklich ein Variablenname folgt.
        # text(...) ist ein Funktionsaufruf, keine Deklaration.
        following = self.tokens[self.position + 1]

        if following.type in (
            TokenType.IDENTIFIER,
            TokenType.KEYWORD,
            TokenType.LEFT_BRACKET,
        ):
            return True

        return False

    # ========================================================
    # PRINT
    # ========================================================

    def parse_print(self):

        self.advance()

        self.consume(
            TokenType.LEFT_PAREN,
            "Nach 'print' wird '(' erwartet"
        )

        expression = self.parse_expression()

        self.consume(
            TokenType.RIGHT_PAREN,
            "Nach dem print-Ausdruck wird ')' erwartet"
        )

        self.consume(
            TokenType.SEMICOLON,
            "Nach 'print(...)' wird ';' erwartet"
        )

        return PrintStatement(expression)

    # ========================================================
    # VARIABLE
    # ========================================================

    def parse_variable_declaration(self):

        type_token = self.advance()
        variable_type = type_token.value

        # Typ[]
        if self.match(TokenType.LEFT_BRACKET):

            self.consume(
                TokenType.RIGHT_BRACKET,
                "Nach '[' wird ']' erwartet"
            )

            variable_type += "[]"

        name = self.consume_identifier(
            "Nach dem Datentyp wird ein Variablenname erwartet"
        )

        # optionale Zuweisung
        if self.match(TokenType.EQUAL):

            expression = self.parse_expression()

        else:

            expression = NullExpression()

        self.consume(
            TokenType.SEMICOLON,
            "Nach der Variablendeklaration wird ';' erwartet"
        )

        return VariableDeclaration(
            name,
            variable_type,
            expression
        )

    # ========================================================
    # STRUCT
    # ========================================================

    def parse_struct(self):

        self.advance()

        name = self.consume_identifier(
            "Nach 'struct' wird ein Name erwartet"
        )

        self.consume(
            TokenType.LEFT_BRACE,
            "Nach dem Struct-Namen wird '{' erwartet"
        )

        fields = []

        while (
            not self.check(TokenType.RIGHT_BRACE)
            and not self.check(TokenType.EOF)
        ):

            variable_type = self.consume_identifier(
                "Im Struct wird ein Datentyp erwartet"
            )

            if self.match(TokenType.LEFT_BRACKET):

                self.consume(
                    TokenType.RIGHT_BRACKET,
                    "Nach '[' wird ']' erwartet"
                )

                variable_type += "[]"

            field_name = self.consume_identifier(
                "Nach dem Datentyp wird ein Feldname erwartet"
            )

            self.consume(
                TokenType.SEMICOLON,
                "Nach dem Struct-Feld wird ';' erwartet"
            )

            fields.append(
                StructField(
                    field_name,
                    variable_type
                )
            )

        self.consume(
            TokenType.RIGHT_BRACE,
            "Nach den Struct-Feldern wird '}' erwartet"
        )

        self.match(TokenType.SEMICOLON)

        return StructDeclaration(
            name,
            fields
        )

    # ========================================================
    # IMPORT
    # ========================================================

    def parse_import(self):

        self.advance()

        path_token = self.peek()

        if path_token.type != TokenType.STRING:

            raise SyntaxError(
                "Nach 'import' wird ein "
                f"Dateipfad erwartet (Position {path_token.position})"
            )

        self.advance()

        self.consume(
            TokenType.SEMICOLON,
            "Nach 'import' wird ';' erwartet"
        )

        return ImportStatement(path_token.value)

    # ========================================================
    # CLASS
    # ========================================================

    def parse_class(self):

        self.advance()

        name = self.consume_identifier(
            "Nach 'class' wird ein Name erwartet"
        )

        # optionale Vererbung: class Auto : Fahrzeug {}
        superclass_name = None

        if self.check_identifier("extends"):

            self.advance()

            superclass_name = self.consume_identifier(
                "Nach 'extends' wird ein Basisklassen-Name erwartet"
            )

        if self.match(TokenType.COLON):

            superclass_name = self.consume_identifier(
                "Nach ':' wird ein Basisklassen-Name erwartet"
            )

        self.consume(
            TokenType.LEFT_BRACE,
            "Nach dem Klassen-Namen wird '{' erwartet"
        )

        fields = []
        methods = {}

        while (
            not self.check(TokenType.RIGHT_BRACE)
            and not self.check(TokenType.EOF)
        ):

            if self.check_identifier("function"):
                method = self.parse_function()
                methods[method.name] = method
                continue

            if self.check_identifier("method"):
                method = self.parse_method()
                methods[method.name] = method
                continue

            if self.check_identifier("constructor"):
                method = self.parse_constructor()
                methods["constructor"] = method
                continue

            if self.check_identifier("let"):

                field = self.parse_let()

                fields.append(
                    VariableDeclaration(
                        field.name,
                        field.variable_type,
                        field.expression
                    )
                )

                continue

            if self.check_identifier("var"):

                field = self.parse_let()

                fields.append(
                    VariableDeclaration(
                        field.name,
                        field.variable_type,
                        field.expression
                    )
                )

                continue

            if self.is_variable_type():

                field = self.parse_variable_declaration()

                fields.append(
                    VariableDeclaration(
                        field.name,
                        field.variable_type,
                        field.expression
                    )
                )

                continue

            token = self.peek()

            raise SyntaxError(
                "In einer Klasse werden nur Felder "
                "(let/var) oder Funktionen erwartet "
                f"(Position {token.position})"
            )

        self.consume(
            TokenType.RIGHT_BRACE,
            "Nach den Klassen-Membern wird '}' erwartet"
        )

        self.match(TokenType.SEMICOLON)

        return ClassDeclaration(
            name,
            fields,
            methods,
            superclass_name
        )

    # ========================================================
    # METHOD (nur im Klassen-Block)
    # ========================================================

    def parse_method(self):

        self.advance()

        name = self.consume_identifier(
            "Nach 'method' wird ein Methodenname erwartet"
        )

        self.consume(
            TokenType.LEFT_PAREN,
            "Nach dem Methodennamen wird '(' erwartet"
        )

        parameters = self.parse_parameter_list()

        body = self.parse_block()

        return FunctionDeclaration(
            name,
            parameters,
            body
        )

    # ========================================================
    # CONSTRUCTOR (nur im Klassen-Block)
    # ========================================================

    def parse_constructor(self):

        self.advance()

        self.consume(
            TokenType.LEFT_PAREN,
            "Nach 'constructor' wird '(' erwartet"
        )

        parameters = self.parse_parameter_list()

        body = self.parse_block()

        return FunctionDeclaration(
            "constructor",
            parameters,
            body
        )

    # ========================================================
    # PARAMETER LISTE
    # ========================================================

    def parse_parameter_list(self):

        parameters = []

        if not self.check(TokenType.RIGHT_PAREN):

            while True:

                parameters.append(
                    self.consume_identifier(
                        "Als Parameter wird ein Name erwartet"
                    )
                )

                if not self.match(TokenType.COMMA):
                    break

        self.consume(
            TokenType.RIGHT_PAREN,
            "Nach den Parametern wird ')' erwartet"
        )

        return parameters

    # ========================================================
    # IF
    # ========================================================

    def parse_if(self):

        self.advance()

        self.consume(
            TokenType.LEFT_PAREN,
            "Nach 'if' wird '(' erwartet"
        )

        condition = self.parse_expression()

        self.consume(
            TokenType.RIGHT_PAREN,
            "Nach der if-Bedingung wird ')' erwartet"
        )

        then_branch = self.parse_block()

        else_branch = None

        if self.check_identifier("else"):

            self.advance()

            if self.check_identifier("if"):
                else_branch = [
                    self.parse_if()
                ]

            else:
                else_branch = self.parse_block()

        return IfStatement(
            condition,
            then_branch,
            else_branch
        )

    # ========================================================
    # WHILE
    # ========================================================

    def parse_while(self):

        self.advance()

        self.consume(
            TokenType.LEFT_PAREN,
            "Nach 'while' wird '(' erwartet"
        )

        condition = self.parse_expression()

        self.consume(
            TokenType.RIGHT_PAREN,
            "Nach der while-Bedingung wird ')' erwartet"
        )

        body = self.parse_block()

        return WhileStatement(
            condition,
            body
        )

    # ========================================================
    # DO ... WHILE
    # ========================================================

    def parse_do_while(self):

        self.advance()

        body = self.parse_block()

        self.consume_identifier_exact(
            "while",
            "Nach 'do'-Block wird 'while' erwartet"
        )

        self.consume(
            TokenType.LEFT_PAREN,
            "Nach 'while' wird '(' erwartet"
        )

        condition = self.parse_expression()

        self.consume(
            TokenType.RIGHT_PAREN,
            "Nach der do-while-Bedingung wird ')' erwartet"
        )

        self.consume(
            TokenType.SEMICOLON,
            "Nach der do-while-Bedingung wird ';' erwartet"
        )

        return DoWhileStatement(
            body,
            condition
        )

    # ========================================================
    # SWITCH / CASE
    # ========================================================

    def parse_switch(self):

        self.advance()

        self.consume(
            TokenType.LEFT_PAREN,
            "Nach 'switch' wird '(' erwartet"
        )

        expression = self.parse_expression()

        self.consume(
            TokenType.RIGHT_PAREN,
            "Nach dem switch-Ausdruck wird ')' erwartet"
        )

        self.consume(
            TokenType.LEFT_BRACE,
            "Nach 'switch(...)' wird '{' erwartet"
        )

        cases = []
        default_body = None

        while (
            not self.check(TokenType.RIGHT_BRACE)
            and not self.check(TokenType.EOF)
        ):

            if self.check_identifier("case"):

                self.advance()

                values = [
                    self.parse_expression()
                ]

                while self.match(TokenType.COMMA):
                    values.append(
                        self.parse_expression()
                    )

                self.consume(
                    TokenType.COLON,
                    "Nach 'case'-Wert wird ':' erwartet"
                )

                body = []

                while (
                    not self.check(TokenType.RIGHT_BRACE)
                    and not self.check(TokenType.EOF)
                    and not self.check_identifier("case")
                    and not self.check_identifier("default")
                ):
                    body.append(
                        self.parse_statement()
                    )

                cases.append(
                    SwitchCase(values, body)
                )

            elif self.check_identifier("default"):

                self.advance()

                self.consume(
                    TokenType.COLON,
                    "Nach 'default' wird ':' erwartet"
                )

                default_body = []

                while (
                    not self.check(TokenType.RIGHT_BRACE)
                    and not self.check(TokenType.EOF)
                    and not self.check_identifier("case")
                    and not self.check_identifier("default")
                ):
                    default_body.append(
                        self.parse_statement()
                    )

            else:

                token = self.peek()

                raise SyntaxError(
                    "In 'switch' werden nur 'case' oder "
                    "'default' erwartet "
                    f"(Position {token.position})"
                )

        self.consume(
            TokenType.RIGHT_BRACE,
            "Nach dem switch-Body wird '}' erwartet"
        )

        return SwitchStatement(
            expression,
            cases,
            default_body
        )

    # ========================================================
    # ENUM
    # ========================================================

    def parse_enum(self):

        self.advance()

        name = self.consume_identifier(
            "Nach 'enum' wird ein Name erwartet"
        )

        self.consume(
            TokenType.LEFT_BRACE,
            "Nach dem enum-Namen wird '{' erwartet"
        )

        members = []

        while (
            not self.check(TokenType.RIGHT_BRACE)
            and not self.check(TokenType.EOF)
        ):

            member = self.consume_identifier(
                "Als enum-Member wird ein Name erwartet"
            )

            members.append(member)

            if not self.match(TokenType.COMMA):
                break

        self.consume(
            TokenType.RIGHT_BRACE,
            "Nach den enum-Membern wird '}' erwartet"
        )

        self.match(TokenType.SEMICOLON)

        return EnumDeclaration(
            name,
            members
        )

    # ========================================================
    # LOOP
    # ========================================================

    def parse_loop(self):

        self.advance()

        condition = BooleanExpression(True)

        if self.check(TokenType.LEFT_PAREN):

            self.advance()

            condition = self.parse_expression()

            self.consume(
                TokenType.RIGHT_PAREN,
                "Nach der loop-Bedingung wird ')' erwartet"
            )

        body = self.parse_block()

        return WhileStatement(
            condition,
            body
        )

    # ========================================================
    # REPEAT
    # ========================================================

    def parse_repeat(self):

        self.advance()

        count = self.parse_expression()

        body = self.parse_block()

        initializer = VariableDeclaration(
            "__nexa_repeat_counter",
            "int",
            NumberExpression("0")
        )

        condition = BinaryExpression(
            VariableExpression("__nexa_repeat_counter"),
            TokenType.LESS,
            count
        )

        increment = AssignmentStatement(
            "__nexa_repeat_counter",
            BinaryExpression(
                VariableExpression("__nexa_repeat_counter"),
                TokenType.PLUS,
                NumberExpression("1")
            )
        )

        return ForStatement(
            initializer,
            condition,
            increment,
            body
        )

    # ========================================================
    # FOR
    # ========================================================

    def parse_for(self):

        self.advance()

        self.consume(
            TokenType.LEFT_PAREN,
            "Nach 'for' wird '(' erwartet"
        )

        initializer = None

        if not self.check(TokenType.SEMICOLON):

            if self.is_variable_type():

                initializer = self.parse_variable_declaration()

            elif self.check_identifier("let"):

                initializer = self.parse_let()

            elif self.check_identifier("var"):

                initializer = self.parse_let()

            else:

                initializer = self.parse_assignment_without_semicolon()

        else:

            self.advance()

        condition = None

        if not self.check(TokenType.SEMICOLON):

            condition = self.parse_expression()

        self.consume(
            TokenType.SEMICOLON,
            "Im for-Block wird ';' erwartet"
        )

        increment = None

        if not self.check(TokenType.RIGHT_PAREN):

            increment = self.parse_assignment_without_semicolon()

        self.consume(
            TokenType.RIGHT_PAREN,
            "Nach dem for-Kopf wird ')' erwartet"
        )

        body = self.parse_block()

        return ForStatement(
            initializer,
            condition,
            increment,
            body
        )

    # ========================================================
    # FOREACH
    # ========================================================

    def parse_foreach(self):

        self.advance()

        self.consume(
            TokenType.LEFT_PAREN,
            "Nach 'foreach' wird '(' erwartet"
        )

        variable = self.consume_identifier(
            "Nach 'foreach' wird eine Variable erwartet"
        )

        self.consume_identifier_exact(
            "in",
            "Nach der foreach-Variable wird 'in' erwartet"
        )

        collection = self.parse_expression()

        self.consume(
            TokenType.RIGHT_PAREN,
            "Nach der foreach-Anweisung wird ')' erwartet"
        )

        body = self.parse_block()

        initializer = VariableDeclaration(
            variable,
            "auto",
            NullExpression()
        )

        condition = BinaryExpression(
            VariableExpression("__nexa_foreach_has_next"),
            TokenType.EQUAL_EQUAL,
            BooleanExpression(True)
        )

        increment = ExpressionStatement(
            CallExpression(
                "__nexa_foreach_next",
                []
            )
        )

        return ForStatement(
            initializer,
            condition,
            increment,
            body
        )

    # ========================================================
    # RETURN
    # ========================================================

    def parse_return(self):

        self.advance()

        if self.check(TokenType.SEMICOLON):

            self.advance()

            return ReturnStatement(None)

        expression = self.parse_expression()

        self.consume(
            TokenType.SEMICOLON,
            "Nach 'return' wird ';' erwartet"
        )

        return ReturnStatement(expression)

    # ========================================================
    # FUNCTION
    # ========================================================

    def parse_function(self):

        self.advance()

        name = self.consume_identifier(
            "Nach 'function' wird ein Funktionsname erwartet"
        )

        self.consume(
            TokenType.LEFT_PAREN,
            "Nach dem Funktionsnamen wird '(' erwartet"
        )

        parameters = []

        if not self.check(TokenType.RIGHT_PAREN):

            while True:

                parameters.append(
                    self.consume_identifier(
                        "Als Funktionsparameter wird ein Name erwartet"
                    )
                )

                if not self.match(TokenType.COMMA):
                    break

        self.consume(
            TokenType.RIGHT_PAREN,
            "Nach den Funktionsparametern wird ')' erwartet"
        )

        if self.match(TokenType.ARROW):

            if self.is_name_token():
                self.advance()

        body = self.parse_block()

        return FunctionDeclaration(
            name,
            parameters,
            body
        )

    # ========================================================
    # TRY / CATCH
    # ========================================================

    def parse_try(self):

        self.advance()

        try_body = self.parse_block()

        catch_variable = None
        catch_body = None

        if self.check_identifier("catch"):

            self.advance()

            if self.match(TokenType.LEFT_PAREN):

                if not self.check(TokenType.RIGHT_PAREN):

                    catch_variable = self.consume_identifier(
                        "Nach 'catch(' wird eine Variable erwartet"
                    )

                self.consume(
                    TokenType.RIGHT_PAREN,
                    "Nach 'catch' wird ')' erwartet"
                )

            catch_body = self.parse_block()

        return TryStatement(
            try_body,
            catch_variable,
            catch_body
        )

    # ========================================================
    # BLOCK
    # ========================================================

    def parse_block(self):

        self.consume(
            TokenType.LEFT_BRACE,
            "Ein Block muss mit '{' beginnen"
        )

        statements = []

        while (
            not self.check(TokenType.RIGHT_BRACE)
            and not self.check(TokenType.EOF)
        ):

            statements.append(
                self.parse_statement()
            )

        self.consume(
            TokenType.RIGHT_BRACE,
            "Ein Block muss mit '}' enden"
        )

        return statements

    # ========================================================
    # ASSIGNMENT
    # ========================================================

    def parse_expression_or_assignment(self):

        expression = self.parse_expression()

        if self.match(TokenType.EQUAL):

            value = self.parse_expression()

            self.consume(
                TokenType.SEMICOLON,
                "Nach der Zuweisung wird ';' erwartet"
            )

            if isinstance(expression, VariableExpression):

                return AssignmentStatement(
                    expression.name,
                    value
                )

            if isinstance(expression, IndexExpression):

                return IndexAssignmentStatement(
                    expression.target,
                    expression.index,
                    value
                )

            if isinstance(expression, MemberExpression):

                return MemberAssignmentStatement(
                    expression.target,
                    expression.member,
                    value
                )

            raise SyntaxError(
                "Dieser Ausdruck kann nicht beschrieben werden"
            )

        if self.match(TokenType.PLUS_EQUAL):

            value = self.parse_expression()

            self.consume(
                TokenType.SEMICOLON,
                "Nach '+=' wird ';' erwartet"
            )

            if isinstance(expression, VariableExpression):

                return AssignmentStatement(
                    expression.name,
                    BinaryExpression(
                        expression,
                        TokenType.PLUS,
                        value
                    )
                )

            raise SyntaxError(
                "'+=' kann nur auf Variablen angewendet werden"
            )

        if self.match(TokenType.MINUS_EQUAL):

            value = self.parse_expression()

            self.consume(
                TokenType.SEMICOLON,
                "Nach '-=' wird ';' erwartet"
            )

            if isinstance(expression, VariableExpression):

                return AssignmentStatement(
                    expression.name,
                    BinaryExpression(
                        expression,
                        TokenType.MINUS,
                        value
                    )
                )

            raise SyntaxError(
                "'-=' kann nur auf Variablen angewendet werden"
            )

        if self.match(TokenType.BIT_AND_EQUAL):

            value = self.parse_expression()

            self.consume(
                TokenType.SEMICOLON,
                "Nach '&=' wird ';' erwartet"
            )

            if isinstance(expression, VariableExpression):

                return AssignmentStatement(
                    expression.name,
                    BinaryExpression(
                        expression,
                        TokenType.BIT_AND,
                        value
                    )
                )

            raise SyntaxError(
                "'&=' kann nur auf Variablen angewendet werden"
            )

        if self.match(TokenType.BIT_OR_EQUAL):

            value = self.parse_expression()

            self.consume(
                TokenType.SEMICOLON,
                "Nach '|=' wird ';' erwartet"
            )

            if isinstance(expression, VariableExpression):

                return AssignmentStatement(
                    expression.name,
                    BinaryExpression(
                        expression,
                        TokenType.BIT_OR,
                        value
                    )
                )

            raise SyntaxError(
                "'|=' kann nur auf Variablen angewendet werden"
            )

        if self.match(TokenType.BIT_XOR_EQUAL):

            value = self.parse_expression()

            self.consume(
                TokenType.SEMICOLON,
                "Nach '^=' wird ';' erwartet"
            )

            if isinstance(expression, VariableExpression):

                return AssignmentStatement(
                    expression.name,
                    BinaryExpression(
                        expression,
                        TokenType.BIT_XOR,
                        value
                    )
                )

            raise SyntaxError(
                "'^=' kann nur auf Variablen angewendet werden"
            )

        if self.match(TokenType.SHIFT_LEFT_EQUAL):

            value = self.parse_expression()

            self.consume(
                TokenType.SEMICOLON,
                "Nach '<<=' wird ';' erwartet"
            )

            if isinstance(expression, VariableExpression):

                return AssignmentStatement(
                    expression.name,
                    BinaryExpression(
                        expression,
                        TokenType.SHIFT_LEFT,
                        value
                    )
                )

            raise SyntaxError(
                "'<<=' kann nur auf Variablen angewendet werden"
            )

        if self.match(TokenType.SHIFT_RIGHT_EQUAL):

            value = self.parse_expression()

            self.consume(
                TokenType.SEMICOLON,
                "Nach '>>=' wird ';' erwartet"
            )

            if isinstance(expression, VariableExpression):

                return AssignmentStatement(
                    expression.name,
                    BinaryExpression(
                        expression,
                        TokenType.SHIFT_RIGHT,
                        value
                    )
                )

            raise SyntaxError(
                "'>>=' kann nur auf Variablen angewendet werden"
            )

        if self.match(TokenType.STAR_EQUAL):

            value = self.parse_expression()

            self.consume(
                TokenType.SEMICOLON,
                "Nach '*=' wird ';' erwartet"
            )

            if isinstance(expression, VariableExpression):

                return AssignmentStatement(
                    expression.name,
                    BinaryExpression(
                        expression,
                        TokenType.STAR,
                        value
                    )
                )

            raise SyntaxError(
                "'*=' kann nur auf Variablen angewendet werden"
            )

        if self.match(TokenType.SLASH_EQUAL):

            value = self.parse_expression()

            self.consume(
                TokenType.SEMICOLON,
                "Nach '/=' wird ';' erwartet"
            )

            if isinstance(expression, VariableExpression):

                return AssignmentStatement(
                    expression.name,
                    BinaryExpression(
                        expression,
                        TokenType.SLASH,
                        value
                    )
                )

            raise SyntaxError(
                "'/=' kann nur auf Variablen angewendet werden"
            )

        if self.match(TokenType.PERCENT_EQUAL):

            value = self.parse_expression()

            self.consume(
                TokenType.SEMICOLON,
                "Nach '%=' wird ';' erwartet"
            )

            if isinstance(expression, VariableExpression):

                return AssignmentStatement(
                    expression.name,
                    BinaryExpression(
                        expression,
                        TokenType.PERCENT,
                        value
                    )
                )

            raise SyntaxError(
                "'%=' kann nur auf Variablen angewendet werden"
            )

        if self.match(TokenType.INCREMENT):

            self.consume(
                TokenType.SEMICOLON,
                "Nach '++' wird ';' erwartet"
            )

            if isinstance(expression, VariableExpression):

                return AssignmentStatement(
                    expression.name,
                    BinaryExpression(
                        expression,
                        TokenType.PLUS,
                        NumberExpression("1")
                    )
                )

            raise SyntaxError(
                "'++' kann nur auf Variablen angewendet werden"
            )

        if self.match(TokenType.DECREMENT):

            self.consume(
                TokenType.SEMICOLON,
                "Nach '--' wird ';' erwartet"
            )

            if isinstance(expression, VariableExpression):

                return AssignmentStatement(
                    expression.name,
                    BinaryExpression(
                        expression,
                        TokenType.MINUS,
                        NumberExpression("1")
                    )
                )

            raise SyntaxError(
                "'--' kann nur auf Variablen angewendet werden"
            )

        self.consume(
            TokenType.SEMICOLON,
            "Nach dem Ausdruck wird ';' erwartet"
        )

        return ExpressionStatement(expression)

    # ========================================================
    # ASSIGNMENT OHNE SEMIKOLON
    # ========================================================

    def parse_assignment_without_semicolon(self):

        expression = self.parse_expression()

        if self.match(TokenType.EQUAL):

            value = self.parse_expression()

            if isinstance(expression, VariableExpression):

                return AssignmentStatement(
                    expression.name,
                    value
                )

            if isinstance(expression, IndexExpression):

                return IndexAssignmentStatement(
                    expression.target,
                    expression.index,
                    value
                )

            if isinstance(expression, MemberExpression):

                return MemberAssignmentStatement(
                    expression.target,
                    expression.member,
                    value
                )

            raise SyntaxError(
                "Dieser Ausdruck kann nicht beschrieben werden"
            )

        if self.match(TokenType.PLUS_EQUAL):

            value = self.parse_expression()

            if isinstance(expression, VariableExpression):

                return AssignmentStatement(
                    expression.name,
                    BinaryExpression(
                        expression,
                        TokenType.PLUS,
                        value
                    )
                )

        if self.match(TokenType.MINUS_EQUAL):

            value = self.parse_expression()

            if isinstance(expression, VariableExpression):

                return AssignmentStatement(
                    expression.name,
                    BinaryExpression(
                        expression,
                        TokenType.MINUS,
                        value
                    )
                )

        if self.match(TokenType.BIT_AND_EQUAL):

            value = self.parse_expression()

            if isinstance(expression, VariableExpression):

                return AssignmentStatement(
                    expression.name,
                    BinaryExpression(
                        expression,
                        TokenType.BIT_AND,
                        value
                    )
                )

        if self.match(TokenType.BIT_OR_EQUAL):

            value = self.parse_expression()

            if isinstance(expression, VariableExpression):

                return AssignmentStatement(
                    expression.name,
                    BinaryExpression(
                        expression,
                        TokenType.BIT_OR,
                        value
                    )
                )

        if self.match(TokenType.BIT_XOR_EQUAL):

            value = self.parse_expression()

            if isinstance(expression, VariableExpression):

                return AssignmentStatement(
                    expression.name,
                    BinaryExpression(
                        expression,
                        TokenType.BIT_XOR,
                        value
                    )
                )

        if self.match(TokenType.SHIFT_LEFT_EQUAL):

            value = self.parse_expression()

            if isinstance(expression, VariableExpression):

                return AssignmentStatement(
                    expression.name,
                    BinaryExpression(
                        expression,
                        TokenType.SHIFT_LEFT,
                        value
                    )
                )

        if self.match(TokenType.SHIFT_RIGHT_EQUAL):

            value = self.parse_expression()

            if isinstance(expression, VariableExpression):

                return AssignmentStatement(
                    expression.name,
                    BinaryExpression(
                        expression,
                        TokenType.SHIFT_RIGHT,
                        value
                    )
                )

        if self.match(TokenType.INCREMENT):

            if isinstance(expression, VariableExpression):

                return AssignmentStatement(
                    expression.name,
                    BinaryExpression(
                        expression,
                        TokenType.PLUS,
                        NumberExpression("1")
                    )
                )

        if self.match(TokenType.DECREMENT):

            if isinstance(expression, VariableExpression):

                return AssignmentStatement(
                    expression.name,
                    BinaryExpression(
                        expression,
                        TokenType.MINUS,
                        NumberExpression("1")
                    )
                )

        return ExpressionStatement(expression)

    # ========================================================
    # EXPRESSIONS
    # ========================================================

    def parse_expression(self):
        return self.parse_ternary()

    # ========================================================
    # TERNARY
    # ========================================================

    def parse_ternary(self):

        expression = self.parse_null_coalescing()

        if self.match(TokenType.QUESTION):

            true_expression = self.parse_expression()

            self.consume(
                TokenType.COLON,
                "Nach '?' wird ':' erwartet"
            )

            false_expression = self.parse_expression()

            return ConditionalExpression(
                expression,
                true_expression,
                false_expression,
            )

        return expression

    def parse_null_coalescing(self):
        expression = self.parse_logical_or()

        if self.match(TokenType.NULL_COALESCING):
            return BinaryExpression(
                expression,
                TokenType.NULL_COALESCING,
                self.parse_null_coalescing(),
            )

        return expression

    # ========================================================
    # LOGICAL OR
    # ========================================================

    def parse_logical_or(self):

        expression = self.parse_logical_and()

        while self.match(TokenType.LOGICAL_OR):

            operator = self.previous().type
            right = self.parse_logical_and()

            expression = BinaryExpression(
                expression,
                operator,
                right
            )

        return expression

    # ========================================================
    # LOGICAL AND
    # ========================================================

    def parse_logical_and(self):

        expression = self.parse_comparison()

        while self.match(TokenType.LOGICAL_AND):

            operator = self.previous().type
            right = self.parse_comparison()

            expression = BinaryExpression(
                expression,
                operator,
                right
            )

        return expression

    # ========================================================
    # COMPARISON
    # ========================================================

    def parse_comparison(self):

        expression = self.parse_bit_or()

        while self.match(
            TokenType.EQUAL_EQUAL,
            TokenType.NOT_EQUAL,
            TokenType.LESS,
            TokenType.GREATER,
            TokenType.LESS_EQUAL,
            TokenType.GREATER_EQUAL
        ):

            operator = self.previous().type
            right = self.parse_bit_or()

            expression = BinaryExpression(
                expression,
                operator,
                right
            )

        return expression

    # ========================================================
    # BIT OR
    # ========================================================

    def parse_bit_or(self):

        expression = self.parse_bit_xor()

        while self.match(TokenType.BIT_OR):

            operator = self.previous().type
            right = self.parse_bit_xor()

            expression = BinaryExpression(
                expression,
                operator,
                right
            )

        return expression

    # ========================================================
    # BIT XOR
    # ========================================================

    def parse_bit_xor(self):

        expression = self.parse_bit_and()

        while self.match(TokenType.BIT_XOR):

            operator = self.previous().type
            right = self.parse_bit_and()

            expression = BinaryExpression(
                expression,
                operator,
                right
            )

        return expression

    # ========================================================
    # BIT AND
    # ========================================================

    def parse_bit_and(self):

        expression = self.parse_shift()

        while self.match(TokenType.BIT_AND):

            operator = self.previous().type
            right = self.parse_shift()

            expression = BinaryExpression(
                expression,
                operator,
                right
            )

        return expression

    # ========================================================
    # SHIFT
    # ========================================================

    def parse_shift(self):

        expression = self.parse_addition()

        while self.match(
            TokenType.SHIFT_LEFT,
            TokenType.SHIFT_RIGHT
        ):

            operator = self.previous().type
            right = self.parse_addition()

            expression = BinaryExpression(
                expression,
                operator,
                right
            )

        return expression

    # ========================================================
    # ADDITION
    # ========================================================

    def parse_addition(self):

        expression = self.parse_multiplication()

        while self.match(
            TokenType.PLUS,
            TokenType.MINUS
        ):

            operator = self.previous().type
            right = self.parse_multiplication()

            expression = BinaryExpression(
                expression,
                operator,
                right
            )

        return expression

    # ========================================================
    # MULTIPLIKATION
    # ========================================================

    def parse_multiplication(self):

        expression = self.parse_power()

        while self.match(
            TokenType.STAR,
            TokenType.SLASH,
            TokenType.PERCENT
        ):

            operator = self.previous().type
            right = self.parse_power()

            expression = BinaryExpression(
                expression,
                operator,
                right
            )

        return expression

    # ========================================================
    # POWER
    # ========================================================

    def parse_power(self):

        expression = self.parse_unary()

        while self.match(
            TokenType.STAR_STAR,
            TokenType.CARET
        ):

            operator = self.previous().type
            right = self.parse_unary()

            expression = BinaryExpression(
                expression,
                operator,
                right
            )

        return expression

    # ========================================================
    # UNARY
    # ========================================================

    def parse_unary(self):

        if self.match(
            TokenType.MINUS,
            TokenType.LOGICAL_NOT,
            TokenType.BIT_NOT,
            TokenType.PLUS
        ):

            operator = self.previous().type
            operand = self.parse_unary()

            return UnaryExpression(
                operator,
                operand
            )

        return self.parse_postfix()

    # ========================================================
    # POSTFIX
    # ========================================================

    def parse_postfix(self):

        expression = self.parse_factor()

        while True:

            if self.match(TokenType.LEFT_BRACKET):

                index = self.parse_expression()

                self.consume(
                    TokenType.RIGHT_BRACKET,
                    "Nach dem Array-Index wird ']' erwartet"
                )

                expression = IndexExpression(
                    expression,
                    index
                )

                continue

            if self.match(TokenType.DOT):

                member = self.consume_identifier(
                    "Nach '.' wird ein Member-Name erwartet"
                )

                # Methodenaufruf: object.method(...)
                if self.match(TokenType.LEFT_PAREN):

                    arguments = []

                    if not self.check(TokenType.RIGHT_PAREN):

                        while True:

                            arguments.append(
                                self.parse_expression()
                            )

                            if not self.match(TokenType.COMMA):
                                break

                    self.consume(
                        TokenType.RIGHT_PAREN,
                        "Nach den Methoden-Argumenten wird ')' erwartet"
                    )

                    expression = MethodCallExpression(
                        expression,
                        member,
                        arguments
                    )

                    continue

                expression = MemberExpression(
                    expression,
                    member
                )

                continue

            break

        return expression

    # ========================================================
    # FACTOR
    # ========================================================

    def parse_factor(self):

        # Zahl
        if self.match(TokenType.NUMBER):

            return NumberExpression(
                self.previous().value
            )

        # String
        if self.match(TokenType.STRING):

            return StringExpression(
                self.previous().value
            )

        # Character
        if self.match(TokenType.CHARACTER):

            return CharacterExpression(
                self.previous().value
            )

        # Identifier ODER Keyword
        if self.is_name_token():

            name = self.advance().value

            if name == "new":

                type_name = self.consume_identifier(
                    "Nach 'new' wird ein Klassenname erwartet"
                )

                self.consume(
                    TokenType.LEFT_PAREN,
                    "Nach dem Klassennamen wird '(' erwartet"
                )

                arguments = []

                if not self.check(TokenType.RIGHT_PAREN):

                    while True:

                        arguments.append(
                            self.parse_expression()
                        )

                        if not self.match(TokenType.COMMA):
                            break

                self.consume(
                    TokenType.RIGHT_PAREN,
                    "Nach den Konstruktor-Argumenten wird ')' erwartet"
                )

                return NewExpression(
                    type_name,
                    arguments
                )

            if name == "true":
                return BooleanExpression(True)

            if name == "false":
                return BooleanExpression(False)

            if name == "null":
                return NullExpression()

            if name == "none":
                return NullExpression()

            # Funktionsaufruf
            if self.match(TokenType.LEFT_PAREN):

                arguments = []

                if not self.check(TokenType.RIGHT_PAREN):

                    while True:

                        arguments.append(
                            self.parse_expression()
                        )

                        if not self.match(TokenType.COMMA):
                            break

                self.consume(
                    TokenType.RIGHT_PAREN,
                    "Nach den Funktionsargumenten wird ')' erwartet"
                )

                return CallExpression(
                    name,
                    arguments
                )

            return VariableExpression(name)

        # Array
        if self.match(TokenType.LEFT_BRACKET):

            elements = []

            if not self.check(TokenType.RIGHT_BRACKET):

                while True:

                    elements.append(
                        self.parse_expression()
                    )

                    if not self.match(TokenType.COMMA):
                        break

            self.consume(
                TokenType.RIGHT_BRACKET,
                "Nach dem Array wird ']' erwartet"
            )

            return ArrayExpression(elements)

        # Klammerausdruck
        if self.match(TokenType.LEFT_PAREN):

            expression = self.parse_expression()

            self.consume(
                TokenType.RIGHT_PAREN,
                "Nach dem Ausdruck wird ')' erwartet"
            )

            return expression

        token = self.peek()

        raise SyntaxError(
            f"Unerwarteter Token '{token.value}' "
            f"an Position {token.position}"
        )

    # ========================================================
    # TOKEN HELFER
    # ========================================================

    def peek(self):
        return self.tokens[self.position]

    def previous(self):
        return self.tokens[self.position - 1]

    def advance(self):

        if not self.check(TokenType.EOF):
            self.position += 1

        return self.previous()

    def check(self, token_type):
        return self.peek().type == token_type

    def is_name_token(self):

        return self.peek().type in (
            TokenType.IDENTIFIER,
            TokenType.KEYWORD
        )

    def check_identifier(self, name):

        return (
            self.is_name_token()
            and self.peek().value == name
        )

    def match(self, *token_types):

        for token_type in token_types:

            if self.check(token_type):

                self.advance()
                return True

        return False

    def consume(self, token_type, message):

        if self.check(token_type):
            return self.advance()

        token = self.peek()

        raise SyntaxError(
            f"{message} (Position {token.position})"
        )

    def consume_identifier(self, message):

        if self.is_name_token():
            return self.advance().value

        token = self.peek()

        raise SyntaxError(
            f"{message} (Position {token.position})"
        )

    def consume_identifier_exact(self, name, message):

        if self.check_identifier(name):
            self.advance()
            return

        token = self.peek()

        raise SyntaxError(
            f"{message} (Position {token.position})"
        )