
from dataclasses import dataclass
from pathlib import Path
import random as _random
import sys

from lexer import Lexer, TokenType
from parser import (
    Parser,
    Program,
    NumberExpression,
    StringExpression,
    CharacterExpression,
    BooleanExpression,
    NullExpression,
    ArrayExpression,
    VariableExpression,
    IndexExpression,
    MemberExpression,
    UnaryExpression,
    BinaryExpression,
    CallExpression,
    NewExpression,
    MethodCallExpression,
    ImportStatement,
    ExpressionStatement,
    PrintStatement,
    VariableDeclaration,
    AssignmentStatement,
    IndexAssignmentStatement,
    MemberAssignmentStatement,
    IfStatement,
    WhileStatement,
    DoWhileStatement,
    SwitchStatement,
    SwitchCase,
    EnumDeclaration,
    ForStatement,
    BreakStatement,
    ContinueStatement,
    ReturnStatement,
    FunctionDeclaration,
    StructDeclaration,
    ClassDeclaration,
    TryStatement,
)


@dataclass(frozen=True)
class NexaChar:
    value: str

    def __post_init__(self):
        if not isinstance(self.value, str) or len(self.value) != 1:
            raise ValueError(
                "Ein NexaChar muss genau ein Zeichen enthalten"
            )

    def __str__(self):
        return self.value


class BreakSignal(Exception):
    pass


class ContinueSignal(Exception):
    pass


@dataclass
class ReturnSignal(Exception):
    value: object


class NexaError(Exception):
    pass


class Environment:

    def __init__(self, parent=None):
        self.values = {}
        self.parent = parent
        self.constants = set()

    def define(self, name, value):
        if name in self.values:
            raise RuntimeError(
                f"Variable '{name}' wurde bereits deklariert"
            )

        self.values[name] = value

    def define_const(self, name, value):
        if name in self.values:
            raise RuntimeError(
                f"Variable '{name}' wurde bereits deklariert"
            )

        self.values[name] = value
        self.constants.add(name)

    def get(self, name):

        if name in self.values:
            return self.values[name]

        if self.parent is not None:
            return self.parent.get(name)

        raise RuntimeError(
            f"Unbekannte Variable '{name}'"
        )

    def assign(self, name, value):

        if name in self.values:

            if name in self.constants:
                raise RuntimeError(
                    f"Konstante '{name}' kann nicht verändert werden"
                )

            self.values[name] = value
            return

        if self.parent is not None:
            self.parent.assign(name, value)
            return

        raise RuntimeError(
            f"Unbekannte Variable '{name}'"
        )


class NexaFunction:

    def __init__(self, declaration, closure, interpreter, instance=None):
        self.declaration = declaration
        self.closure = closure
        self.interpreter = interpreter
        self.instance = instance

    def call(self, arguments):

        if len(arguments) != len(self.declaration.parameters):
            raise RuntimeError(
                f"Funktion '{self.declaration.name}' erwartet "
                f"{len(self.declaration.parameters)} Argument(e), "
                f"aber {len(arguments)} wurden übergeben"
            )

        environment = Environment(self.closure)

        if self.instance is not None:
            environment.define("this", self.instance)
            environment.define("self", self.instance)

        for name, value in zip(
            self.declaration.parameters,
            arguments
        ):
            environment.define(name, value)

        try:

            self.interpreter.execute_block(
                self.declaration.body,
                environment
            )

        except ReturnSignal as signal:
            return signal.value

        return None


class NexaClass:

    def __init__(self, declaration, interpreter):
        self.declaration = declaration
        self.interpreter = interpreter
        self.superclass = None

        if declaration.superclass_name is not None:

            try:
                parent = interpreter.environment.get(
                    declaration.superclass_name
                )
            except RuntimeError:
                parent = None

            if isinstance(parent, NexaClass):
                self.superclass = parent

        self.methods = dict(declaration.methods or {})

        if self.superclass is not None:

            for name, method in self.superclass.methods.items():

                if name not in self.methods:
                    self.methods[name] = method

    def find_method(self, name):

        if name in self.methods:
            return self.methods[name]

        return None

    def instantiate(self, arguments):

        fields = {}

        def collect_fields(cls):

            if cls.superclass is not None:
                collect_fields(cls.superclass)

            for field in (cls.declaration.fields or []):

                value = self.interpreter.evaluate(
                    field.expression
                )

                fields[field.name] = value

        collect_fields(self)

        instance = NexaInstance(self, fields)

        constructor = self.methods.get("constructor")

        if constructor is not None:

            method = NexaFunction(
                constructor,
                self.interpreter.globals,
                self.interpreter,
                instance=instance
            )

            method.call(arguments)

        elif arguments:

            raise RuntimeError(
                f"Klasse '{self.declaration.name}' hat "
                f"keinen Konstruktor"
            )

        return instance


class NexaInstance:

    def __init__(self, cls, fields):
        self.cls = cls
        self.fields = fields

    def get_field(self, name):

        if name in self.fields:
            return self.fields[name]

        raise RuntimeError(
            f"Unbekanntes Member '{name}'"
        )

    def set_field(self, name, value):

        if name not in self.fields:
            raise RuntimeError(
                f"Unbekanntes Member '{name}'"
            )

        self.fields[name] = value


class Interpreter:

    def __init__(self, runtime=None):

        self.globals = Environment()
        self.environment = self.globals
        self.runtime = runtime
        self.imported = set()

        self.register_builtins()

    def register_builtins(self):

        self.globals.define(
            "push",
            self.builtin_push
        )

        self.globals.define(
            "pop",
            self.builtin_pop
        )

        self.globals.define(
            "length",
            self.builtin_length
        )

        self.globals.define(
            "int",
            self.builtin_int
        )

        self.globals.define(
            "float",
            self.builtin_float
        )

        self.globals.define(
            "char",
            self.builtin_char
        )

        self.globals.define(
            "str",
            self.builtin_str
        )

        self.globals.define(
            "throw",
            self.builtin_throw
        )

        self.globals.define(
            "random",
            self.builtin_random
        )

        self.globals.define(
            "substring",
            self.builtin_substring
        )

        self.globals.define(
            "charAt",
            self.builtin_charAt
        )

        self.globals.define(
            "indexOf",
            self.builtin_indexOf
        )

        self.globals.define(
            "replace",
            self.builtin_replace
        )

        self.globals.define(
            "uppercase",
            self.builtin_uppercase
        )

        self.globals.define(
            "lowercase",
            self.builtin_lowercase
        )

        self.globals.define(
            "trim",
            self.builtin_trim
        )

        if self.runtime is not None:

            self.globals.define(
                "window",
                self.runtime.window
            )

            self.globals.define(
                "clear",
                self.runtime.clear
            )

            self.globals.define(
                "rect",
                self.runtime.rect
            )

            self.globals.define(
                "circle",
                self.runtime.circle
            )

            self.globals.define(
                "text",
                self.runtime.text
            )

            self.globals.define(
                "present",
                self.runtime.present
            )

            self.globals.define(
                "wait",
                self.runtime.wait
            )

            self.globals.define(
                "key_down",
                self.runtime.key_down
            )

            self.globals.define(
                "sleep",
                self.runtime.sleep
            )

            self.globals.define(
                "close",
                self.runtime.close
            )

    # ========================================================
    # PROGRAMM
    # ========================================================

    def interpret(self, program):

        if not isinstance(program, Program):
            raise RuntimeError(
                "Ungültiges Programm"
            )

        for statement in program.statements:
            self.execute(statement)

    # ========================================================
    # STATEMENTS
    # ========================================================

    def execute(self, statement):

        if isinstance(statement, ExpressionStatement):

            self.evaluate(
                statement.expression
            )

            return

        if isinstance(statement, PrintStatement):

            value = self.evaluate(
                statement.expression
            )

            reconfigure_stdout = getattr(sys.stdout, "reconfigure", None)
            if callable(reconfigure_stdout):
                reconfigure_stdout(encoding="utf-8", errors="replace")

            print(self.format_value(value))

            return

        # ====================================================
        # VARIABLE DECLARATION
        # ====================================================

        if isinstance(statement, VariableDeclaration):

            value = self.evaluate(
                statement.expression
            )

            # ------------------------------------------------
            # AUTO / LET
            # ------------------------------------------------
            #
            # let zahl = 10;
            #
            # Der Typ wird automatisch aus dem Wert bestimmt.
            # Der konkrete Wert wird gespeichert und spätere
            # Zuweisungen werden über assignment_types_compatible()
            # geprüft.
            #
            # Dadurch funktioniert:
            #
            # let zahl = 10;
            # zahl = 20;
            #
            # aber nicht:
            #
            # zahl = "Hallo";
            #
            # ------------------------------------------------

            if statement.variable_type in (
                "auto",
                "infer"
            ):

                self.environment.define(
                    statement.name,
                    value
                )

                return

            if statement.variable_type == "const":

                self.environment.define_const(
                    statement.name,
                    value
                )

                return

            self.check_type(
                statement.variable_type,
                value
            )

            self.environment.define(
                statement.name,
                value
            )

            return

        # ====================================================
        # ASSIGNMENT
        # ====================================================

        if isinstance(statement, AssignmentStatement):

            value = self.evaluate(
                statement.expression
            )

            old_value = self.environment.get(
                statement.name
            )

            if not self.assignment_types_compatible(
                old_value,
                value
            ):

                raise RuntimeError(
                    f"Typfehler bei Variable "
                    f"'{statement.name}': "
                    f"{self.type_name(old_value)} kann nicht "
                    f"mit {self.type_name(value)} überschrieben werden"
                )

            self.environment.assign(
                statement.name,
                value
            )

            return

        # ====================================================
        # INDEX ASSIGNMENT
        # ====================================================

        if isinstance(statement, IndexAssignmentStatement):

            target = self.evaluate(
                statement.target
            )

            index = self.evaluate(
                statement.index
            )

            value = self.evaluate(
                statement.expression
            )

            self.require_integer(
                index,
                "Array-Index"
            )

            if not isinstance(target, list):

                raise RuntimeError(
                    "Nur Arrays können über einen Index verändert werden"
                )

            if index < 0 or index >= len(target):

                raise RuntimeError(
                    f"Array-Index außerhalb des gültigen Bereichs: {index}"
                )

            old_value = target[index]

            if not self.assignment_types_compatible(
                old_value,
                value
            ):

                raise RuntimeError(
                    f"Typfehler im Array: "
                    f"{self.type_name(old_value)} kann nicht "
                    f"mit {self.type_name(value)} überschrieben werden"
                )

            target[index] = value

            return

        # ====================================================
        # MEMBER ASSIGNMENT
        # ====================================================

        if isinstance(statement, MemberAssignmentStatement):

            target = self.evaluate(
                statement.target
            )

            value = self.evaluate(
                statement.expression
            )

            if isinstance(target, NexaInstance):

                target.set_field(
                    statement.member,
                    value
                )

                return

            if not isinstance(target, dict):

                raise RuntimeError(
                    "Nur Structs oder Klassenobjekte "
                    "können Member besitzen"
                )

            if statement.member not in target:

                raise RuntimeError(
                    f"Unbekanntes Struct-Member "
                    f"'{statement.member}'"
                )

            target[statement.member] = value

            return

        # ====================================================
        # IMPORT
        # ====================================================

        if isinstance(statement, ImportStatement):

            self.execute_import(
                statement.path
            )

            return

        # ====================================================
        # STRUCT
        # ====================================================

        if isinstance(statement, StructDeclaration):

            self.environment.define(
                statement.name,
                statement
            )

            return

        # ====================================================
        # CLASS
        # ====================================================

        if isinstance(statement, ClassDeclaration):

            nexaclass = NexaClass(
                statement,
                self
            )

            self.environment.define(
                statement.name,
                nexaclass
            )

            return

        # ====================================================
        # IF
        # ====================================================

        if isinstance(statement, IfStatement):

            condition = self.evaluate(
                statement.condition
            )

            if self.is_truthy(condition):

                self.execute_block(
                    statement.then_branch,
                    Environment(self.environment)
                )

            elif statement.else_branch is not None:

                self.execute_block(
                    statement.else_branch,
                    Environment(self.environment)
                )

            return

        # ====================================================
        # WHILE
        # ====================================================

        if isinstance(statement, WhileStatement):

            while self.is_truthy(
                self.evaluate(statement.condition)
            ):

                try:

                    self.execute_block(
                        statement.body,
                        Environment(self.environment)
                    )

                except ContinueSignal:
                    continue

                except BreakSignal:
                    break

            return

        # ====================================================
        # DO ... WHILE
        # ====================================================

        if isinstance(statement, DoWhileStatement):

            while True:

                try:

                    self.execute_block(
                        statement.body,
                        Environment(self.environment)
                    )

                except ContinueSignal:
                    pass

                except BreakSignal:
                    break

                if not self.is_truthy(
                    self.evaluate(statement.condition)
                ):
                    break

            return

        # ====================================================
        # SWITCH / CASE
        # ====================================================

        if isinstance(statement, SwitchStatement):

            value = self.evaluate(
                statement.expression
            )

            matched = False
            executed = False

            try:

                for case in statement.cases:

                    for case_value in case.values:

                        candidate = self.evaluate(
                            case_value
                        )

                        matching = self.equal_to(
                            value,
                            candidate
                        )

                        if matching:
                            matched = True
                            break

                    if matched and not executed:

                        self.execute_block(
                            case.body,
                            Environment(self.environment)
                        )
                        executed = True
                        break

                if not matched and statement.default_body is not None:

                    self.execute_block(
                        statement.default_body,
                        Environment(self.environment)
                    )
                    executed = True

            except BreakSignal:
                pass

            return

        # ====================================================
        # ENUM
        # ====================================================

        if isinstance(statement, EnumDeclaration):

            for index, member in enumerate(statement.members):

                self.environment.define(
                    member,
                    index
                )

            return

        # ====================================================
        # FOR
        # ====================================================

        if isinstance(statement, ForStatement):

            loop_environment = Environment(
                self.environment
            )

            previous = self.environment
            self.environment = loop_environment

            try:

                if statement.initializer is not None:

                    self.execute(
                        statement.initializer
                    )

                while (
                    statement.condition is None
                    or self.is_truthy(
                        self.evaluate(
                            statement.condition
                        )
                    )
                ):

                    try:

                        self.execute_block(
                            statement.body,
                            self.environment
                        )

                    except ContinueSignal:
                        pass

                    except BreakSignal:
                        break

                    if statement.increment is not None:

                        self.execute(
                            statement.increment
                        )

            finally:

                self.environment = previous

            return

        # ====================================================
        # BREAK
        # ====================================================

        if isinstance(statement, BreakStatement):
            raise BreakSignal()

        # ====================================================
        # CONTINUE
        # ====================================================

        if isinstance(statement, ContinueStatement):
            raise ContinueSignal()

        # ====================================================
        # RETURN
        # ====================================================

        if isinstance(statement, ReturnStatement):

            value = None

            if statement.expression is not None:

                value = self.evaluate(
                    statement.expression
                )

            raise ReturnSignal(value)

        # ====================================================
        # FUNCTION
        # ====================================================

        if isinstance(statement, FunctionDeclaration):

            function = NexaFunction(
                statement,
                self.environment,
                self
            )

            self.environment.define(
                statement.name,
                function
            )

            return

        # ====================================================
        # TRY / CATCH
        # ====================================================

        if isinstance(statement, TryStatement):

            try:

                self.execute_block(
                    statement.try_body,
                    Environment(self.environment)
                )

            except (NexaError, RuntimeError) as signal:

                if statement.catch_body is None:
                    raise

                catch_environment = Environment(self.environment)

                if statement.catch_variable is not None:

                    catch_environment.define(
                        statement.catch_variable,
                        str(signal)
                    )

                self.execute_block(
                    statement.catch_body,
                    catch_environment
                )

            return

        raise RuntimeError(
            f"Unbekannte Anweisung: "
            f"{type(statement).__name__}"
        )

    # ========================================================
    # BLOCK
    # ========================================================

    def execute_block(
        self,
        statements,
        environment
    ):

        previous = self.environment
        self.environment = environment

        try:

            for statement in statements:
                self.execute(statement)

        finally:

            self.environment = previous

    # ========================================================
    # EXPRESSIONS
    # ========================================================

    def evaluate(self, expression):

        if isinstance(expression, NumberExpression):

            return self.parse_number(
                expression.value
            )

        if isinstance(expression, StringExpression):

            return expression.value

        if isinstance(expression, CharacterExpression):

            return NexaChar(
                expression.value
            )

        if isinstance(expression, BooleanExpression):

            return expression.value

        if isinstance(expression, NullExpression):

            return None

        if isinstance(expression, ArrayExpression):

            return [
                self.evaluate(element)
                for element in expression.elements
            ]

        if isinstance(expression, VariableExpression):

            return self.environment.get(
                expression.name
            )

        if isinstance(expression, IndexExpression):

            target = self.evaluate(
                expression.target
            )

            index = self.evaluate(
                expression.index
            )

            self.require_integer(
                index,
                "Array-Index"
            )

            if not isinstance(
                target,
                (list, str)
            ):

                raise RuntimeError(
                    "Nur Arrays oder Strings können "
                    "über einen Index gelesen werden"
                )

            if index < 0 or index >= len(target):

                raise RuntimeError(
                    f"Array-Index außerhalb des "
                    f"gültigen Bereichs: {index}"
                )

            value = target[index]

            if isinstance(target, str):

                return NexaChar(value)

            return value

        if isinstance(expression, MemberExpression):

            target = self.evaluate(
                expression.target
            )

            if isinstance(target, NexaInstance):

                return target.get_field(
                    expression.member
                )

            if not isinstance(target, dict):

                raise RuntimeError(
                    "Nur Structs oder Klassenobjekte "
                    "können Member besitzen"
                )

            if expression.member not in target:

                raise RuntimeError(
                    f"Unbekanntes Struct-Member "
                    f"'{expression.member}'"
                )

            return target[
                expression.member
            ]

        if isinstance(expression, MethodCallExpression):

            target = self.evaluate(
                expression.target
            )

            if not isinstance(target, NexaInstance):

                raise RuntimeError(
                    "Nur Klassenobjekte können Methoden besitzen"
                )

            method_declaration = target.cls.find_method(
                expression.name
            )

            if method_declaration is None:

                raise RuntimeError(
                    f"Unbekannte Methode '{expression.name}'"
                )

            method = NexaFunction(
                method_declaration,
                target.cls.interpreter.globals,
                self,
                instance=target
            )

            arguments = [
                self.evaluate(argument)
                for argument in expression.arguments
            ]

            return method.call(arguments)

        if isinstance(expression, NewExpression):

            class_value = self.environment.get(
                expression.type_name
            )

            arguments = [
                self.evaluate(argument)
                for argument in expression.arguments
            ]

            if isinstance(class_value, NexaClass):

                return class_value.instantiate(
                    arguments
                )

            if isinstance(class_value, StructDeclaration):

                fields = {}

                for index, field in enumerate(
                    class_value.fields
                ):

                    fields[field.name] = (
                        arguments[index]
                        if index < len(arguments)
                        else None
                    )

                return fields

            raise RuntimeError(
                f"'{expression.type_name}' ist keine Klasse "
                f"oder Struktur"
            )

        if isinstance(expression, UnaryExpression):

            operand = self.evaluate(
                expression.operand
            )

            return self.evaluate_unary(
                expression.operator,
                operand
            )

        if isinstance(expression, BinaryExpression):

            left = self.evaluate(
                expression.left
            )

            if expression.operator == TokenType.LOGICAL_AND:

                if not self.is_truthy(left):
                    return False

                right = self.evaluate(
                    expression.right
                )

                return self.is_truthy(right)

            if expression.operator == TokenType.LOGICAL_OR:

                if self.is_truthy(left):
                    return True

                right = self.evaluate(
                    expression.right
                )

                return self.is_truthy(right)

            right = self.evaluate(
                expression.right
            )

            return self.evaluate_binary(
                left,
                expression.operator,
                right
            )

        if isinstance(expression, CallExpression):

            function = self.environment.get(
                expression.name
            )

            arguments = [
                self.evaluate(argument)
                for argument in expression.arguments
            ]

            if isinstance(function, NexaFunction):

                return function.call(
                    arguments
                )

            if not callable(function):

                raise RuntimeError(
                    f"'{expression.name}' ist keine Funktion"
                )

            try:

                return function(
                    *arguments
                )

            except TypeError as error:

                raise RuntimeError(
                    f"Fehler beim Aufruf von "
                    f"'{expression.name}': {error}"
                ) from error

        raise RuntimeError(
            f"Unbekannter Ausdruck: "
            f"{type(expression).__name__}"
        )

    # ========================================================
    # NUMBERS
    # ========================================================

    def parse_number(self, value):

        text = value.replace(
            "_",
            ""
        )

        if text.lower().startswith("0b"):

            return int(
                text[2:],
                2
            )

        if text.lower().startswith("0x"):

            return int(
                text[2:],
                16
            )

        if text.lower().startswith("0o"):

            return int(
                text[2:],
                8
            )

        if "." in text:

            try:

                return float(text)

            except ValueError as error:

                raise RuntimeError(
                    f"Ungültige Fließkommazahl: {value}"
                ) from error

        try:

            return int(text)

        except ValueError as error:

            raise RuntimeError(
                f"Ungültige Zahl: {value}"
            ) from error

    # ========================================================
    # UNARY
    # ========================================================

    def evaluate_unary(
        self,
        operator,
        operand
    ):

        if operator == TokenType.MINUS:

            if not self.is_number(operand):

                raise RuntimeError(
                    "Der Operator '-' benötigt eine Zahl"
                )

            return -operand

        if operator == TokenType.LOGICAL_NOT:

            return not self.is_truthy(
                operand
            )

        if operator == TokenType.BIT_NOT:

            self.require_integer(
                operand,
                "Bitwise NOT"
            )

            return ~operand

        raise RuntimeError(
            f"Unbekannter unärer Operator: {operator}"
        )

    # ========================================================
    # BINARY
    # ========================================================

    def evaluate_binary(
        self,
        left,
        operator,
        right
    ):

        if operator == TokenType.PLUS:

            if (
                self.is_number(left)
                and self.is_number(right)
            ):

                return left + right

            if (
                isinstance(left, str)
                and isinstance(right, str)
            ):

                return left + right

            if (
                isinstance(left, list)
                and isinstance(right, list)
            ):

                return left + right

            if isinstance(left, str):

                return left + self.format_value(
                    right
                )

            if isinstance(right, str):

                return self.format_value(
                    left
                ) + right

            raise RuntimeError(
                f"'+' kann nicht mit "
                f"{self.type_name(left)} und "
                f"{self.type_name(right)} verwendet werden"
            )

        if operator == TokenType.MINUS:

            self.require_numbers(
                left,
                right,
                "-"
            )

            return left - right

        if operator == TokenType.STAR:

            self.require_numbers(
                left,
                right,
                "*"
            )

            return left * right

        if operator == TokenType.SLASH:

            self.require_numbers(
                left,
                right,
                "/"
            )

            if right == 0 or right == 0.0:

                raise RuntimeError(
                    "Division durch 0 ist nicht erlaubt"
                )

            if (
                isinstance(left, float)
                or isinstance(right, float)
            ):

                return left / right

            return left // right

        if operator == TokenType.PERCENT:

            self.require_integer(
                left,
                "Modulo"
            )

            self.require_integer(
                right,
                "Modulo"
            )

            if right == 0:

                raise RuntimeError(
                    "Modulo durch 0 ist nicht erlaubt"
                )

            return left % right

        if operator == TokenType.EQUAL_EQUAL:

            if (
                self.is_number(left)
                and self.is_number(right)
            ):

                return left == right

            return (
                type(left) is type(right)
                and left == right
            )

        if operator == TokenType.NOT_EQUAL:

            if (
                self.is_number(left)
                and self.is_number(right)
            ):

                return left != right

            return not (
                type(left) is type(right)
                and left == right
            )

        if operator == TokenType.LESS:

            self.require_comparable(
                left,
                right
            )

            return left < right

        if operator == TokenType.GREATER:

            self.require_comparable(
                left,
                right
            )

            return left > right

        if operator == TokenType.LESS_EQUAL:

            self.require_comparable(
                left,
                right
            )

            return left <= right

        if operator == TokenType.GREATER_EQUAL:

            self.require_comparable(
                left,
                right
            )

            return left >= right

        if operator == TokenType.BIT_AND:

            self.require_integer(
                left,
                "Bitwise AND"
            )

            self.require_integer(
                right,
                "Bitwise AND"
            )

            return left & right

        if operator == TokenType.BIT_OR:

            self.require_integer(
                left,
                "Bitwise OR"
            )

            self.require_integer(
                right,
                "Bitwise OR"
            )

            return left | right

        if operator == TokenType.BIT_XOR:

            self.require_integer(
                left,
                "Bitwise XOR"
            )

            self.require_integer(
                right,
                "Bitwise XOR"
            )

            return left ^ right

        if operator == TokenType.SHIFT_LEFT:

            self.require_integer(
                left,
                "Shift Left"
            )

            self.require_integer(
                right,
                "Shift Left"
            )

            if right < 0:

                raise RuntimeError(
                    "Shift-Anzahl darf nicht negativ sein"
                )

            return left << right

        if operator == TokenType.SHIFT_RIGHT:

            self.require_integer(
                left,
                "Shift Right"
            )

            self.require_integer(
                right,
                "Shift Right"
            )

            if right < 0:

                raise RuntimeError(
                    "Shift-Anzahl darf nicht negativ sein"
                )

            return left >> right

        if operator in (
            TokenType.STAR_STAR,
            TokenType.CARET
        ):

            if (
                not self.is_number(left)
                or not self.is_number(right)
            ):

                raise RuntimeError(
                    "Power-Operator benötigt "
                    "zwei Zahlen"
                )

            return left ** right

        raise RuntimeError(
            f"Unbekannter binärer Operator: {operator}"
        )

    # ========================================================
    # TYPE HELPERS
    # ========================================================

    def is_number(self, value):

        return (
            isinstance(
                value,
                (int, float)
            )
            and not isinstance(
                value,
                bool
            )
        )

    def require_numbers(
        self,
        left,
        right,
        operator
    ):

        if not self.is_number(left):

            raise RuntimeError(
                f"Operator '{operator}' benötigt "
                f"links eine Zahl, bekam aber "
                f"{self.type_name(left)}"
            )

        if not self.is_number(right):

            raise RuntimeError(
                f"Operator '{operator}' benötigt "
                f"rechts eine Zahl, bekam aber "
                f"{self.type_name(right)}"
            )

    def require_integer(
        self,
        value,
        context
    ):

        if (
            isinstance(value, bool)
            or not isinstance(value, int)
        ):

            raise RuntimeError(
                f"{context} benötigt einen Integer, "
                f"aber bekam {self.type_name(value)}"
            )

    def require_comparable(
        self,
        left,
        right
    ):

        if (
            self.is_number(left)
            and self.is_number(right)
        ):

            return

        if (
            isinstance(left, str)
            and isinstance(right, str)
        ):

            return

        if (
            isinstance(left, NexaChar)
            and isinstance(right, NexaChar)
        ):

            return

        raise RuntimeError(
            f"Werte vom Typ "
            f"{self.type_name(left)} und "
            f"{self.type_name(right)} "
            f"können nicht verglichen werden"
        )

    # ========================================================
    # CHECK TYPE
    # ========================================================

    def check_type(
        self,
        variable_type,
        value
    ):

        # ----------------------------------------------------
        # AUTO / INFER
        # ----------------------------------------------------
        #
        # Wird bereits bei VariableDeclaration behandelt.
        # Hier trotzdem erlaubt, damit auto/infer auch an
        # anderen Stellen sauber verwendet werden können.
        #
        # ----------------------------------------------------

        if variable_type in (
            "auto",
            "infer"
        ):

            return

        if variable_type == "int":

            if (
                isinstance(value, bool)
                or not isinstance(value, int)
            ):

                raise RuntimeError(
                    "Variable vom Typ 'int' benötigt "
                    f"einen Integer, bekam aber "
                    f"{self.type_name(value)}"
                )

            return

        if variable_type == "float":

            if not isinstance(
                value,
                float
            ):

                raise RuntimeError(
                    "Variable vom Typ 'float' benötigt "
                    f"einen Float, bekam aber "
                    f"{self.type_name(value)}"
                )

            return

        if variable_type == "string":

            if not isinstance(
                value,
                str
            ):

                raise RuntimeError(
                    "Variable vom Typ 'string' benötigt "
                    f"Text, bekam aber "
                    f"{self.type_name(value)}"
                )

            return

        if variable_type == "char":

            if not isinstance(
                value,
                NexaChar
            ):

                raise RuntimeError(
                    "Variable vom Typ 'char' benötigt "
                    f"ein einzelnes Zeichen, bekam aber "
                    f"{self.type_name(value)}"
                )

            return

        if variable_type == "bool":

            if not isinstance(
                value,
                bool
            ):

                raise RuntimeError(
                    "Variable vom Typ 'bool' benötigt "
                    f"true oder false, bekam aber "
                    f"{self.type_name(value)}"
                )

            return

        if variable_type.endswith("[]"):

            if not isinstance(
                value,
                list
            ):

                raise RuntimeError(
                    f"Variable vom Typ '{variable_type}' "
                    f"benötigt ein Array, bekam aber "
                    f"{self.type_name(value)}"
                )

            element_type = variable_type[:-2]

            for element in value:

                self.check_type(
                    element_type,
                    element
                )

            return

        raise RuntimeError(
            f"Unbekannter Datentyp '{variable_type}'"
        )

    # ========================================================
    # ASSIGNMENT TYPE COMPATIBILITY
    # ========================================================

    def assignment_types_compatible(
        self,
        old_value,
        new_value
    ):

        # Gleicher Typ ist immer erlaubt.

        if type(old_value) is type(new_value):
            return True

        # Zahlen:
        #
        # int -> float wird hier bewusst NICHT automatisch
        # erlaubt. Nexa bleibt bei Variablen typensicher.
        #

        if (
            isinstance(old_value, float)
            or isinstance(new_value, float)
        ):

            return (
                isinstance(old_value, float)
                and isinstance(new_value, float)
            )

        if (
            isinstance(old_value, bool)
            or isinstance(new_value, bool)
        ):

            return (
                isinstance(old_value, bool)
                and isinstance(new_value, bool)
            )

        if (
            isinstance(old_value, NexaChar)
            or isinstance(new_value, NexaChar)
        ):

            return (
                isinstance(old_value, NexaChar)
                and isinstance(new_value, NexaChar)
            )

        return False

    # ========================================================
    # TYPE NAME
    # ========================================================

    def type_name(self, value):

        if value is None:
            return "null"

        if isinstance(value, bool):
            return "bool"

        if isinstance(value, float):
            return "float"

        if isinstance(value, int):
            return "int"

        if isinstance(value, NexaChar):
            return "char"

        if isinstance(value, str):
            return "string"

        if isinstance(value, list):
            return "array"

        if isinstance(value, dict):
            return "struct"

        if isinstance(value, NexaInstance):
            return value.cls.declaration.name

        if isinstance(value, NexaFunction):
            return "function"

        return type(value).__name__

# ========================================================
# IMPORT
# ========================================================

    def execute_import(self, path):

        import_path = Path(path)

        if not import_path.is_absolute():
            import_path = Path.cwd() / import_path

        import_path = import_path.resolve()

        if str(import_path) in self.imported:
            return

        if not import_path.exists():

            raise RuntimeError(
                f"Modul '{path}' wurde nicht gefunden"
            )

        try:

            source = import_path.read_text(
                encoding="utf-8-sig"
            )

        except OSError as error:

            raise RuntimeError(
                f"Modul '{path}' konnte nicht gelesen werden: {error}"
            ) from error

        lexer = Lexer(source)
        tokens = lexer.tokenize()

        parser = Parser(tokens)
        program = parser.parse()

        self.imported.add(
            str(import_path)
        )

        self.execute_block(
            program.statements,
            self.environment
        )

    # ========================================================
    # TRUTHINESS
    # ========================================================

    def is_truthy(self, value):

        if value is None:
            return False

        if isinstance(value, bool):
            return value

        if isinstance(value, (int, float)):
            return value != 0

        if isinstance(value, NexaChar):
            return True

        if isinstance(value, str):
            return len(value) > 0

        if isinstance(value, list):
            return len(value) > 0

        return True

    # ========================================================
    # EQUAL TO
    # ========================================================

    def equal_to(self, left, right):

        if (
            self.is_number(left)
            and self.is_number(right)
        ):
            return left == right

        if (
            isinstance(left, NexaChar)
            and isinstance(right, str)
            and len(right) == 1
        ):
            return left.value == right

        if (
            isinstance(left, str)
            and isinstance(right, NexaChar)
            and len(left) == 1
        ):
            return left == right.value

        return (
            type(left) is type(right)
            and left == right
        )

    # ========================================================
    # FORMAT VALUE
    # ========================================================

    def format_value(self, value):

        if value is None:
            return "null"

        if isinstance(value, bool):

            return (
                "true"
                if value
                else "false"
            )

        if isinstance(value, NexaChar):

            return value.value

        if isinstance(value, float):

            cleaned = round(
                value,
                12
            )

            if cleaned.is_integer():

                return f"{cleaned:.1f}"

            return (
                f"{cleaned:.12f}"
                .rstrip("0")
                .rstrip(".")
            )

        if isinstance(value, list):

            return "[" + ", ".join(
                self.format_value(element)
                for element in value
            ) + "]"

        if isinstance(value, dict):

            return "{" + ", ".join(
                f"{key}: {self.format_value(val)}"
                for key, val in value.items()
            ) + "}"

        if isinstance(value, NexaInstance):

            fields_str = ", ".join(
                f"{key}: {self.format_value(val)}"
                for key, val in value.fields.items()
            )

            return f"{value.cls.declaration.name}({fields_str})"

        return str(value)

    # ========================================================
    # BUILTIN PUSH
    # ========================================================

    def builtin_push(
        self,
        array,
        value
    ):

        if not isinstance(
            array,
            list
        ):

            raise RuntimeError(
                "push() benötigt ein Array"
            )

        array.append(value)

        return None

    # ========================================================
    # BUILTIN POP
    # ========================================================

    def builtin_pop(self, array):

        if not isinstance(
            array,
            list
        ):

            raise RuntimeError(
                "pop() benötigt ein Array"
            )

        if len(array) == 0:

            raise RuntimeError(
                "pop() kann kein leeres Array verwenden"
            )

        return array.pop()

    # ========================================================
    # BUILTIN LENGTH
    # ========================================================

    def builtin_length(self, value):

        if isinstance(
            value,
            (str, list)
        ):

            return len(value)

        if isinstance(
            value,
            NexaChar
        ):

            return 1

        raise RuntimeError(
            "length() benötigt einen String, "
            "ein Zeichen oder ein Array"
        )

    # ========================================================
    # BUILTIN INT
    # ========================================================

    def builtin_int(self, value):

        if isinstance(
            value,
            bool
        ):

            return int(value)

        if isinstance(
            value,
            int
        ):

            return value

        if isinstance(
            value,
            float
        ):

            return int(value)

        if isinstance(
            value,
            NexaChar
        ):

            try:

                return int(
                    value.value
                )

            except ValueError as error:

                raise RuntimeError(
                    f"int() konnte Zeichen "
                    f"'{value.value}' nicht umwandeln"
                ) from error

        if isinstance(
            value,
            str
        ):

            try:

                return self.parse_number(
                    value
                )

            except (
                ValueError,
                RuntimeError
            ) as error:

                raise RuntimeError(
                    f"int() konnte "
                    f"'{value}' nicht umwandeln"
                ) from error

        raise RuntimeError(
            f"int() kann "
            f"{self.type_name(value)} "
            f"nicht umwandeln"
        )

    # ========================================================
    # BUILTIN FLOAT
    # ========================================================

    def builtin_float(self, value):

        if isinstance(
            value,
            bool
        ):

            return float(value)

        if isinstance(
            value,
            float
        ):

            return value

        if isinstance(
            value,
            int
        ):

            return float(value)

        if isinstance(
            value,
            NexaChar
        ):

            try:

                return float(
                    value.value
                )

            except ValueError as error:

                raise RuntimeError(
                    f"float() konnte Zeichen "
                    f"'{value.value}' nicht umwandeln"
                ) from error

        if isinstance(
            value,
            str
        ):

            text = value.replace(
                "_",
                ""
            )

            try:

                if text.lower().startswith("0b"):

                    return float(
                        int(
                            text[2:],
                            2
                        )
                    )

                if text.lower().startswith("0x"):

                    return float(
                        int(
                            text[2:],
                            16
                        )
                    )

                if text.lower().startswith("0o"):

                    return float(
                        int(
                            text[2:],
                            8
                        )
                    )

                return float(text)

            except ValueError as error:

                raise RuntimeError(
                    f"float() konnte "
                    f"'{value}' nicht umwandeln"
                ) from error

        raise RuntimeError(
            f"float() kann "
            f"{self.type_name(value)} "
            f"nicht umwandeln"
        )

    # ========================================================
    # BUILTIN CHAR
    # ========================================================

    def builtin_char(self, value):

        if isinstance(
            value,
            NexaChar
        ):

            return value

        if isinstance(
            value,
            str
        ):

            if len(value) != 1:

                raise RuntimeError(
                    "char() benötigt einen String "
                    "mit genau einem Zeichen"
                )

            return NexaChar(value)

        raise RuntimeError(
            f"char() kann "
            f"{self.type_name(value)} "
            f"nicht in char umwandeln"
        )

    # ========================================================
    # BUILTIN STR
    # ========================================================

    def builtin_str(self, value):

        return self.format_value(
            value
        )

    # ========================================================
    # BUILTIN THROW
    # ========================================================

    def builtin_throw(self, message="Fehler"):

        raise NexaError(
            self.format_value(message)
        )

    # ========================================================
    # BUILTIN RANDOM
    # ========================================================

    def builtin_random(self, minimum, maximum):

        if not self.is_number(minimum) or not self.is_number(maximum):
            raise RuntimeError(
                "random() benötigt zwei Zahlen (min, max)"
            )

        if maximum < minimum:
            raise RuntimeError(
                "random(): max darf nicht kleiner als min sein"
            )

        return _random.randint(
            int(minimum),
            int(maximum)
        )

    # ========================================================
    # BUILTIN SUBSTRING
    # ========================================================

    def builtin_substring(self, text, start, end=None):

        if not isinstance(text, str):
            raise RuntimeError("substring() erwartet einen String")

        if not self.is_number(start):
            raise RuntimeError("substring() Start muss eine Zahl sein")

        start = int(start)

        if end is None:
            result = text[start:]
        else:
            if not self.is_number(end):
                raise RuntimeError("substring() Ende muss eine Zahl sein")
            result = text[start:int(end)]

        return result

    # ========================================================
    # BUILTIN CHARAT
    # ========================================================

    def builtin_charAt(self, text, index):

        if not isinstance(text, str):
            raise RuntimeError("charAt() erwartet einen String")

        if not self.is_number(index):
            raise RuntimeError("charAt() Index muss eine Zahl sein")

        idx = int(index)

        if idx < 0 or idx >= len(text):
            raise RuntimeError(
                f"charAt() Index {idx} ausserhalb des Strings "
                f"(Laenge {len(text)})"
            )

        return NexaChar(text[idx])

    # ========================================================
    # BUILTIN INDEXOF
    # ========================================================

    def builtin_indexOf(self, text, needle):

        if not isinstance(text, str):
            raise RuntimeError("indexOf() erwartet einen String")

        if not isinstance(needle, str):
            raise RuntimeError("indexOf() zweiter Parameter muss ein String sein")

        pos = text.find(needle)

        return pos

    # ========================================================
    # BUILTIN REPLACE
    # ========================================================

    def builtin_replace(self, text, old, new):

        if not isinstance(text, str):
            raise RuntimeError("replace() erwartet einen String")

        if not isinstance(old, str):
            raise RuntimeError("replace() zweiter Parameter muss ein String sein")

        if not isinstance(new, str):
            raise RuntimeError("replace() dritter Parameter muss ein String sein")

        return text.replace(old, new)

    # ========================================================
    # BUILTIN UPPERCASE
    # ========================================================

    def builtin_uppercase(self, text):

        if not isinstance(text, str):
            raise RuntimeError("uppercase() erwartet einen String")

        return text.upper()

    # ========================================================
    # BUILTIN LOWERCASE
    # ========================================================

    def builtin_lowercase(self, text):

        if not isinstance(text, str):
            raise RuntimeError("lowercase() erwartet einen String")

        return text.lower()

    # ========================================================
    # BUILTIN TRIM
    # ========================================================

    def builtin_trim(self, text):

        if not isinstance(text, str):
            raise RuntimeError("trim() erwartet einen String")

        return text.strip()


# ============================================================
# RUN
# ============================================================

def run(
    program,
    runtime=None
):

    interpreter = Interpreter(
        runtime
    )

    interpreter.interpret(
        program
    )

    return interpreter