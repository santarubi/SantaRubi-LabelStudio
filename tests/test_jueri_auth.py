import unittest

from app.api.auth import JueriCredentials
from app.api.exceptions import JueriAuthenticationError


class JueriCredentialsTests(unittest.TestCase):
    def test_from_config_defaults_when_missing(self):
        credentials = JueriCredentials.from_config({})
        self.assertFalse(credentials.enabled)
        self.assertEqual(credentials.cliente_sistema, "")
        self.assertEqual(credentials.token, "")

    def test_save_and_reload_round_trip(self):
        credentials = JueriCredentials(enabled=True, cliente_sistema="SANTARUBI", token="abc123")

        config: dict = {}
        credentials.save_to(config)

        self.assertEqual(
            config["jueri"],
            {"enabled": True, "cliente_sistema": "SANTARUBI", "token": "abc123"},
        )

        reloaded = JueriCredentials.from_config(config)
        self.assertEqual(reloaded, credentials)

    def test_save_does_not_affect_other_config_keys(self):
        config = {"last_printer": "ELGIN L42 PRO FULL"}
        JueriCredentials(enabled=True, cliente_sistema="SANTARUBI", token="abc123").save_to(config)

        self.assertEqual(config["last_printer"], "ELGIN L42 PRO FULL")
        self.assertIn("jueri", config)

    def test_build_headers_requires_credentials(self):
        credentials = JueriCredentials(enabled=True)
        with self.assertRaises(JueriAuthenticationError):
            credentials.build_headers()

    def test_build_headers_with_valid_credentials(self):
        credentials = JueriCredentials(enabled=True, cliente_sistema="SANTARUBI", token="abc123")
        headers = credentials.build_headers()

        self.assertEqual(headers["Authorization"], "Bearer abc123")
        self.assertEqual(headers["Cliente-Sistema"], "SANTARUBI")


if __name__ == "__main__":
    unittest.main()
