import tempfile
import unittest
from pathlib import Path

from core.print_log import log_print_job


class PrintLogTests(unittest.TestCase):
    def test_creates_file_and_writes_one_line(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "print_log.txt"

            log_print_job(3, 12, 1.5, "sucesso", log_file=log_file)

            self.assertTrue(log_file.exists())
            lines = log_file.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1)

    def test_line_contains_all_required_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "print_log.txt"

            log_print_job(3, 12, 1.5, "sucesso", log_file=log_file)

            line = log_file.read_text(encoding="utf-8").splitlines()[0]
            self.assertRegex(line, r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")
            self.assertIn("produtos=3", line)
            self.assertIn("etiquetas=12", line)
            self.assertIn("tempo=1.50s", line)
            self.assertIn("resultado=sucesso", line)

    def test_appends_without_overwriting_previous_entries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "print_log.txt"

            log_print_job(1, 1, 0.5, "sucesso", log_file=log_file)
            log_print_job(2, 5, 0.8, "falha", log_file=log_file)

            lines = log_file.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 2)
            self.assertIn("resultado=sucesso", lines[0])
            self.assertIn("resultado=falha", lines[1])

    def test_creates_parent_directory_if_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "nested" / "print_log.txt"

            log_print_job(1, 1, 0.1, "sucesso", log_file=log_file)

            self.assertTrue(log_file.exists())


if __name__ == "__main__":
    unittest.main()
