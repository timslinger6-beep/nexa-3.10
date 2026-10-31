import contextlib
import io
import tempfile
import unittest
from pathlib import Path

import extended_cli
import legacy_cli
import main


class ExtendedCliTests(unittest.TestCase):
    def test_registers_exactly_200_unique_commands(self):
        self.assertEqual(len(extended_cli.EXTRA_COMMANDS), 200)
        self.assertEqual(
            len({id(handler) for handler, _ in extended_cli.EXTRA_COMMANDS.values()}),
            200,
        )
        self.assertEqual(len(extended_cli.AST_COMMANDS), 40)
        self.assertEqual(len(extended_cli.TOKEN_COMMANDS), 40)
        self.assertEqual(len(extended_cli.PROJECT_QUERIES), 40)
        self.assertEqual(len(extended_cli.QUALITY_COMMANDS), 40)
        self.assertEqual(len(extended_cli.JSON_COMMANDS), 40)
        self.assertFalse(
            set(extended_cli.EXTRA_COMMANDS)
            & (set(legacy_cli.COMMANDS) | set(main.CURRENT_COMMANDS))
        )
        self.assertEqual(len(main.all_commands()), 347)

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
