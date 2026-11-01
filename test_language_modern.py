import contextlib
import io
import unittest

from interpreter import run
from lexer import Lexer, TokenType
from parser import Parser


class ModernExpressionTests(unittest.TestCase):
    def run_source(self, source):
        program = Parser(Lexer(source).tokenize()).parse()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            run(program)
        return output.getvalue()

    def test_null_coalescing_uses_fallback_only_for_null(self):
        output = self.run_source(
            'print(null ?? "fallback");\n'
            'print("value" ?? (1 / 0));\n'
        )

        self.assertEqual(output, "fallback\nvalue\n")

    def test_conditional_expression_evaluates_only_selected_branch(self):
        output = self.run_source(
            'print(true ? "yes" : (1 / 0));\n'
            'print(false ? (1 / 0) : "no");\n'
        )

        self.assertEqual(output, "yes\nno\n")

    def test_null_coalescing_is_right_associative(self):
        output = self.run_source(
            'print(null ?? null ?? "fallback");\n'
        )

        self.assertEqual(output, "fallback\n")

    def test_lexer_recognizes_null_coalescing_operator(self):
        tokens = Lexer("value ?? fallback").tokenize()

        self.assertEqual(tokens[1].type, TokenType.NULL_COALESCING)


if __name__ == "__main__":
    unittest.main()
