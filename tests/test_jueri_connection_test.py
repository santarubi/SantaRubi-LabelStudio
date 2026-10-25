import email.message
import io
import json
import unittest
import urllib.error
from unittest.mock import patch

from app.api.auth import JueriCredentials
from app.api.connection_test import CONNECTION_TEST_PATH, JUERI_BASE_URL, test_connection


def build_credentials(**overrides) -> JueriCredentials:
    fields = {"enabled": True, "cliente_sistema": "SANTARUBI", "token": "abc123"}
    fields.update(overrides)
    return JueriCredentials(**fields)


def http_error(status: int, reason: str, body: bytes = b"", headers: email.message.Message | None = None):
    return urllib.error.HTTPError(JUERI_BASE_URL, status, reason, headers or email.message.Message(), io.BytesIO(body))


class JueriConnectionTestTests(unittest.TestCase):
    def setUp(self) -> None:
        # O log de diagnóstico é desabilitado por padrão (JUERI_DEBUG_LOG) —
        # mockado aqui só para isolar a suíte de qualquer configuração de
        # ambiente da máquina que roda os testes.
        patcher = patch("app.api.connection_test.log_jueri_api_error")
        self.addCleanup(patcher.stop)
        self.mock_log_jueri_api_error = patcher.start()

    def test_disabled_integration_is_reported_without_a_request(self):
        result = test_connection(build_credentials(enabled=False))
        self.assertFalse(result.success)
        self.assertEqual(result.message, "Habilite a integração antes de testar a conexão.")

    def test_missing_credentials_are_reported_without_a_request(self):
        result = test_connection(build_credentials(cliente_sistema="", token=""))
        self.assertFalse(result.success)
        self.assertEqual(result.message, "Preencha Cliente Sistema e Token antes de testar.")

    @patch("app.api.client.urllib.request.urlopen")
    def test_successful_response_reports_success(self, mock_urlopen):
        mock_response = mock_urlopen.return_value.__enter__.return_value
        mock_response.read.return_value = json.dumps([]).encode("utf-8")

        result = test_connection(build_credentials())

        self.assertTrue(result.success)
        self.assertEqual(result.message, "Conectado com sucesso.")

        request = mock_urlopen.call_args[0][0]
        expected_path = CONNECTION_TEST_PATH.format(cliente_sistema="SANTARUBI")
        self.assertEqual(request.full_url, f"{JUERI_BASE_URL}{expected_path}")

    @patch("app.api.client.urllib.request.urlopen")
    def test_http_error_without_body_uses_generic_message_with_status_code(self, mock_urlopen):
        mock_urlopen.side_effect = http_error(401, "Unauthorized")

        result = test_connection(build_credentials())

        self.assertFalse(result.success)
        self.assertEqual(result.message, "Erro de comunicação com a API Jueri (HTTP 401).")

    @patch("app.api.client.urllib.request.urlopen")
    def test_no_longer_assumes_403_means_invalid_cliente_sistema(self, mock_urlopen):
        # Regressão: 403 já foi erroneamente mapeado para "Cliente Sistema
        # inválido" — na prática era bloqueio do Cloudflare (ver teste
        # abaixo). Sem corpo reconhecível, a mensagem deve ser genérica.
        mock_urlopen.side_effect = http_error(403, "Forbidden")

        result = test_connection(build_credentials())

        self.assertFalse(result.success)
        self.assertNotIn("Cliente Sistema inválido", result.message)
        self.assertEqual(result.message, "Erro de comunicação com a API Jueri (HTTP 403).")

    @patch("app.api.client.urllib.request.urlopen")
    def test_cloudflare_block_is_reported_with_specific_message(self, mock_urlopen):
        mock_urlopen.side_effect = http_error(403, "Forbidden", body=b"error code: 1010")

        result = test_connection(build_credentials())

        self.assertFalse(result.success)
        self.assertIn("Cloudflare", result.message)
        self.assertIn("1010", result.message)

    @patch("app.api.client.urllib.request.urlopen")
    def test_api_json_message_is_used_when_present(self, mock_urlopen):
        body = json.dumps({"message": "Token informado nao e valido"}).encode("utf-8")
        mock_urlopen.side_effect = http_error(401, "Unauthorized", body=body)

        result = test_connection(build_credentials())

        self.assertFalse(result.success)
        self.assertEqual(result.message, "Token informado nao e valido")

    @patch("app.api.client.urllib.request.urlopen")
    def test_http_500_uses_generic_message_with_status_code(self, mock_urlopen):
        mock_urlopen.side_effect = http_error(500, "Internal Server Error")

        result = test_connection(build_credentials())

        self.assertFalse(result.success)
        self.assertEqual(result.message, "Erro de comunicação com a API Jueri (HTTP 500).")

    @patch("app.api.client.urllib.request.urlopen")
    def test_api_error_is_passed_to_debug_logger(self, mock_urlopen):
        headers = email.message.Message()
        headers["Content-Type"] = "application/json"
        mock_urlopen.side_effect = http_error(404, "Not Found", body=b"error code: 1010", headers=headers)

        test_connection(build_credentials())

        self.mock_log_jueri_api_error.assert_called_once()
        args, _kwargs = self.mock_log_jueri_api_error.call_args
        method, url, exc = args
        self.assertEqual(method, "GET")
        self.assertEqual(url, f"{JUERI_BASE_URL}{CONNECTION_TEST_PATH.format(cliente_sistema='SANTARUBI')}")
        self.assertEqual(exc.status_code, 404)
        self.assertEqual(exc.response_body, "error code: 1010")

    @patch("app.api.client.urllib.request.urlopen")
    def test_timeout_is_reported(self, mock_urlopen):
        mock_urlopen.side_effect = TimeoutError()

        result = test_connection(build_credentials())

        self.assertFalse(result.success)
        self.assertEqual(result.message, "Tempo de resposta excedido.")

    @patch("app.api.client.urllib.request.urlopen")
    def test_connection_failure_is_reported_as_no_internet(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("nome não resolvido")

        result = test_connection(build_credentials())

        self.assertFalse(result.success)
        self.assertEqual(result.message, "Sem conexão com a internet.")


if __name__ == "__main__":
    unittest.main()
