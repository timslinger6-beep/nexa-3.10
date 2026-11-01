import contextlib
import io
import tempfile
import unittest
from pathlib import Path

import extended_cli
import legacy_cli
import main


class ExtendedCliTests(unittest.TestCase):
    def test_registers_exactly_19354_unique_extra_commands(self):
        keyword_commands = extended_cli.keyword_commands()
        all_extra_commands = {
            **extended_cli.EXTRA_COMMANDS,
            **keyword_commands,
        }
        self.assertEqual(len(all_extra_commands), 19354)
        self.assertEqual(
            len({id(handler) for handler, _ in all_extra_commands.values()}),
            19354,
        )
        self.assertEqual(len(extended_cli.GENERATED_COMMANDS), 9000)
        self.assertEqual(len(extended_cli.AST_COMMANDS), 41)
        self.assertEqual(len(extended_cli.TOKEN_COMMANDS), 40)
        self.assertEqual(len(extended_cli.PROJECT_QUERIES), 40)
        self.assertEqual(len(extended_cli.QUALITY_COMMANDS), 40)
        self.assertEqual(len(extended_cli.JSON_COMMANDS), 40)
        self.assertEqual(len(keyword_commands), 10_000)
        self.assertEqual(len(extended_cli.TEXT_COMMANDS), 153)
        self.assertFalse(
            set(all_extra_commands)
            & (set(legacy_cli.COMMANDS) | set(main.CURRENT_COMMANDS))
        )
        self.assertEqual(len(main.all_commands()), 19_501)

    def test_generated_keyword_is_reserved_by_the_lexer(self):
        from lexer import Lexer, TARGET_KEYWORD_COUNT, TokenType

        tokens = Lexer("nexa_reserved_0001").tokenize()
        self.assertEqual(len(Lexer.KEYWORDS), TARGET_KEYWORD_COUNT)
        self.assertEqual(tokens[0].type, TokenType.KEYWORD)

    def test_generated_command_forwards_to_its_target(self):
        target_name = "text-uppercase-argument"
        target_index = sorted(extended_cli.BASE_EXTRA_COMMANDS).index(target_name)
        alias_name = f"generated-{target_index + 1:04d}-{target_name}"
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = main.main([alias_name, "hello", "nexa"])

        self.assertEqual(result, 0)
        self.assertEqual(output.getvalue(), "HELLO NEXA\n")

    def test_keyword_commands_count_keyword_tokens(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "sample.nexa"
            source.write_text("if true { print(1); } // if\n", encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = extended_cli.keyword_commands()["keyword-count-if"][0](
                    [str(source)]
                )

        self.assertEqual(result, 0)
        self.assertIn(": 1", output.getvalue())

    def test_text_command_transforms_argument(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = extended_cli.EXTRA_COMMANDS["text-uppercase-argument"][0](
                ["hello", "nexa"]
            )

        self.assertEqual(result, 0)
        self.assertEqual(output.getvalue(), "HELLO NEXA\n")

    def test_ast_command_counts_specific_node_type(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "sample.nexa"
            source.write_text("print(1);", encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = extended_cli.EXTRA_COMMANDS[
                    "ast-count-print-statement"
                ][0]([str(source)])

        self.assertEqual(result, 0)
        self.assertIn(": 1", output.getvalue())

    def test_token_command_lexes_without_parsing(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "sample.nexa"
            source.write_text("print(1 + 2);", encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = extended_cli.EXTRA_COMMANDS["token-count-plus"][0](
                    [str(source)]
                )

        self.assertEqual(result, 0)
        self.assertIn(": 1", output.getvalue())

    def test_quality_command_reports_matching_line(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "sample.py"
            source.write_text("value = 1  \n", encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = extended_cli.EXTRA_COMMANDS[
                    "quality-trailing-whitespace"
                ][0]([str(source)])

        self.assertEqual(result, 0)
        self.assertIn("sample.py:1", output.getvalue())
        self.assertIn("1 Treffer", output.getvalue())

    def test_json_command_detects_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "sample.json"
            source.write_text('{"name": 1, "name": 2}', encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = extended_cli.EXTRA_COMMANDS[
                    "json-duplicate-keys"
                ][0]([str(source)])

        self.assertEqual(result, 0)
        self.assertEqual(output.getvalue().strip(), "name")

    def test_project_command_uses_requested_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            (project / "empty.txt").write_text("", encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = extended_cli.EXTRA_COMMANDS["project-empty-files"][0](
                    [str(project)]
                )

        self.assertEqual(result, 0)
        self.assertEqual(output.getvalue().strip(), "empty.txt")


if __name__ == "__main__":
    unittest.main()
