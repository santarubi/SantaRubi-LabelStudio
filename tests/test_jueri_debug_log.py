import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.api.debug_log import is_debug_logging_enabled, log_jueri_api_error
from app.api.exceptions import JueriAPIError


class JueriDebugLoggingEnabledTests(unittest.TestCase):
    @patch.dict("os.environ", {}, clear=True)
    def test_disabled_by_default(self):
        self.assertFalse(is_debug_logging_enabled())

    @patch.dict("os.environ", {"JUERI_DEBUG_LOG": "1"})
    def test_enabled_when_env_var_is_1(self):
        self.assertTrue(is_debug_logging_enabled())

    @patch.dict("os.environ", {"JUERI_DEBUG_LOG": "0"})
    def test_not_enabled_for_other_values(self):
        self.assertFalse(is_debug_logging_enabled())


class JueriDebugLogTests(unittest.TestCase):
    @patch.dict("os.environ", {}, clear=True)
    def test_does_nothing_when_disabled(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "jueri_debug.log"
            exc = JueriAPIError(404, "Not Found", response_body="x", response_headers="y")

            log_jueri_api_error("GET", "https://jueri.com.br/sis/api/v1/1/produto", exc, log_file=log_file)

            self.assertFalse(log_file.exists())

    @patch.dict("os.environ", {"JUERI_DEBUG_LOG": "1"})
    def test_writes_full_diagnostics_when_enabled(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "jueri_debug.log"
            exc = JueriAPIError(
                404,
                "Not Found",
                response_body='{"erro": "x"}',
                response_headers="Content-Type: application/json",
            )

            log_jueri_api_error(
                "GET", "https://jueri.com.br/sis/api/v1/SANTARUBI/revendedor/nivel", exc, log_file=log_file
            )

            content = log_file.read_text(encoding="utf-8")
            self.assertIn("method=GET", content)
            self.assertIn("url=https://jueri.com.br/sis/api/v1/SANTARUBI/revendedor/nivel", content)
            self.assertIn("status_code=404", content)
            self.assertIn('{"erro": "x"}', content)
            self.assertIn("Content-Type: application/json", content)
            self.assertIn("JueriAPIError", content)

    @patch.dict("os.environ", {"JUERI_DEBUG_LOG": "1"})
    def test_appends_without_overwriting_previous_entries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "jueri_debug.log"
            exc = JueriAPIError(500, "Internal Server Error")

            log_jueri_api_error("GET", "https://x", exc, log_file=log_file)
            log_jueri_api_error("GET", "https://x", exc, log_file=log_file)

            content = log_file.read_text(encoding="utf-8")
            self.assertEqual(content.count("====="), 4)

    @patch.dict("os.environ", {"JUERI_DEBUG_LOG": "1"})
    def test_creates_parent_directory_if_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "nested" / "jueri_debug.log"
            exc = JueriAPIError(500, "Internal Server Error")

            log_jueri_api_error("GET", "https://x", exc, log_file=log_file)

            self.assertTrue(log_file.exists())

    @patch.dict("os.environ", {"JUERI_DEBUG_LOG": "1"})
    def test_does_not_leak_token_in_logged_url(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "jueri_debug.log"
            exc = JueriAPIError(404, "Not Found")
            url_without_token = "https://jueri.com.br/sis/api/v1/SANTARUBI/revendedor/nivel"

            log_jueri_api_error("GET", url_without_token, exc, log_file=log_file)

            content = log_file.read_text(encoding="utf-8")
            self.assertNotIn("Bearer", content)
            self.assertNotIn("Authorization", content)


if __name__ == "__main__":
    unittest.main()
