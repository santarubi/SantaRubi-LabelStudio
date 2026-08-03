import json
import unittest
import urllib.error
from unittest.mock import patch

from app.api.auth import JueriCredentials
from app.api.client import JueriClient
from app.api.exceptions import (
    JueriAPIError,
    JueriAuthenticationError,
    JueriConnectionError,
    JueriDisabledError,
    JueriTimeoutError,
)


def build_client(**credential_kwargs) -> JueriClient:
    credentials = JueriCredentials(enabled=True, cliente_sistema="SANTARUBI", token="abc123", **credential_kwargs)
    return JueriClient("https://api.jueri.exemplo/", credentials, timeout=5)


class JueriClientTests(unittest.TestCase):
    def test_raises_when_integration_disabled(self):
        credentials = JueriCredentials(enabled=False)
        client = JueriClient("https://api.jueri.exemplo", credentials)

        with self.assertRaises(JueriDisabledError):
            client.get("/produtos")

    def test_raises_when_credentials_missing(self):
        credentials = JueriCredentials(enabled=True)
        client = JueriClient("https://api.jueri.exemplo", credentials)

        with self.assertRaises(JueriAuthenticationError):
            client.get("/produtos")

    def test_base_url_trailing_slash_is_normalized(self):
        client = build_client()
        self.assertEqual(client.base_url, "https://api.jueri.exemplo")

    @patch("app.api.client.urllib.request.urlopen")
    def test_get_returns_parsed_json(self, mock_urlopen):
        mock_response = mock_urlopen.return_value.__enter__.return_value
        mock_response.read.return_value = json.dumps({"ok": True}).encode("utf-8")

        client = build_client()
        result = client.get("/produtos")

        self.assertEqual(result, {"ok": True})
        request = mock_urlopen.call_args[0][0]
        self.assertEqual(request.full_url, "https://api.jueri.exemplo/produtos")
        self.assertEqual(request.get_header("Authorization"), "Bearer abc123")
        self.assertEqual(request.get_header("Cliente-sistema"), "SANTARUBI")
        self.assertEqual(request.get_header("Content-type"), "application/json")

    @patch("app.api.client.urllib.request.urlopen")
    def test_sends_browser_like_user_agent_and_accept_header(self, mock_urlopen):
        mock_response = mock_urlopen.return_value.__enter__.return_value
        mock_response.read.return_value = json.dumps({"ok": True}).encode("utf-8")

        client = build_client()
        client.get("/produtos")

        request = mock_urlopen.call_args[0][0]
        self.assertEqual(request.get_header("User-agent"), "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        self.assertEqual(request.get_header("Accept"), "application/json")

    @patch("app.api.client.urllib.request.urlopen")
    def test_http_error_is_mapped_to_jueri_api_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "https://api.jueri.exemplo/produtos", 401, "Unauthorized", {}, None
        )

        client = build_client()
        with self.assertRaises(JueriAPIError) as ctx:
            client.get("/produtos")

        self.assertEqual(ctx.exception.status_code, 401)

    @patch("app.api.client.urllib.request.urlopen")
    def test_http_error_carries_raw_response_body_and_headers(self, mock_urlopen):
        import email.message
        import io

        headers = email.message.Message()
        headers["Content-Type"] = "application/json"
        body = b'{"message": "Cliente do sistema invalido"}'
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "https://api.jueri.exemplo/produtos", 404, "Not Found", headers, io.BytesIO(body)
        )

        client = build_client()
        with self.assertRaises(JueriAPIError) as ctx:
            client.get("/produtos")

        self.assertEqual(ctx.exception.response_body, body.decode("utf-8"))
        self.assertIn("application/json", ctx.exception.response_headers)

    @patch("app.api.client.urllib.request.urlopen")
    def test_timeout_is_mapped_to_jueri_timeout_error(self, mock_urlopen):
        mock_urlopen.side_effect = TimeoutError()

        client = build_client()
        with self.assertRaises(JueriTimeoutError):
            client.get("/produtos")

    @patch("app.api.client.urllib.request.urlopen")
    def test_connection_failure_is_mapped_to_jueri_connection_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("nome não resolvido")

        client = build_client()
        with self.assertRaises(JueriConnectionError):
            client.get("/produtos")


if __name__ == "__main__":
    unittest.main()
