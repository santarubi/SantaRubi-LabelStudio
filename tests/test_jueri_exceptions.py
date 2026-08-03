import unittest

from app.api.exceptions import (
    JueriAPIError,
    JueriConnectionError,
    JueriError,
)


class JueriErrorDescribeTests(unittest.TestCase):
    def test_base_error_describe_defaults_to_str(self):
        exc = JueriError("algo deu errado")
        self.assertEqual(exc.describe(), str(exc))

    def test_connection_error_describe_defaults_to_str(self):
        exc = JueriConnectionError("Falha de conexão com a API Jueri: sem rede")
        self.assertEqual(exc.describe(), str(exc))


class JueriAPIErrorDescribeTests(unittest.TestCase):
    def test_no_body_uses_generic_message_with_status_code(self):
        exc = JueriAPIError(500, "Internal Server Error")
        self.assertEqual(exc.describe(), "Erro de comunicação com a API Jueri (HTTP 500).")

    def test_does_not_assume_403_means_invalid_cliente_sistema(self):
        exc = JueriAPIError(403, "Forbidden")
        self.assertNotIn("Cliente Sistema", exc.describe())

    def test_does_not_assume_401_means_invalid_token(self):
        exc = JueriAPIError(401, "Unauthorized")
        self.assertNotIn("Token", exc.describe())

    def test_cloudflare_1010_is_detected_from_body(self):
        exc = JueriAPIError(403, "Forbidden", response_body="error code: 1010")
        message = exc.describe()
        self.assertIn("Cloudflare", message)
        self.assertIn("1010", message)

    def test_cloudflare_detection_is_case_insensitive(self):
        exc = JueriAPIError(403, "Forbidden", response_body="Error Code: 1010")
        self.assertIn("Cloudflare", exc.describe())

    def test_json_message_field_is_used_verbatim(self):
        exc = JueriAPIError(422, "Unprocessable", response_body='{"message": "Campo obrigatorio ausente"}')
        self.assertEqual(exc.describe(), "Campo obrigatorio ausente")

    def test_json_error_field_is_used_when_message_absent(self):
        exc = JueriAPIError(400, "Bad Request", response_body='{"error": "parametro invalido"}')
        self.assertEqual(exc.describe(), "parametro invalido")

    def test_json_without_recognizable_key_falls_back_to_raw_body(self):
        exc = JueriAPIError(400, "Bad Request", response_body='{"codigo": 42}')
        message = exc.describe()
        self.assertIn("HTTP 400", message)
        self.assertIn('{"codigo": 42}', message)

    def test_non_json_body_falls_back_to_raw_body(self):
        exc = JueriAPIError(502, "Bad Gateway", response_body="<html>Bad Gateway</html>")
        message = exc.describe()
        self.assertIn("HTTP 502", message)
        self.assertIn("<html>Bad Gateway</html>", message)

    def test_very_long_body_is_truncated(self):
        long_body = "x" * 500
        exc = JueriAPIError(500, "Internal Server Error", response_body=long_body)
        message = exc.describe()
        self.assertLess(len(message), 300)
        self.assertIn("…", message)

    def test_blank_body_is_treated_as_no_body(self):
        exc = JueriAPIError(500, "Internal Server Error", response_body="   ")
        self.assertEqual(exc.describe(), "Erro de comunicação com a API Jueri (HTTP 500).")

    def test_empty_message_field_falls_back_to_raw_body(self):
        exc = JueriAPIError(400, "Bad Request", response_body='{"message": ""}')
        message = exc.describe()
        self.assertIn("HTTP 400", message)


if __name__ == "__main__":
    unittest.main()
