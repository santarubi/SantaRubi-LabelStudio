import tkinter as tk
import unittest
from typing import Any
from unittest.mock import patch

from app.api.connection_test import ConnectionTestResult
from ui.settings_dialog import SettingsDialog


class FakeConfigManager:
    def __init__(self) -> None:
        self.saved: dict[str, Any] | None = None

    def save(self, config: dict[str, Any]) -> None:
        self.saved = dict(config)


class SettingsDialogTests(unittest.TestCase):
    def setUp(self) -> None:
        try:
            self.root = tk.Tk()
            self.root.withdraw()
        except tk.TclError as exc:
            self.skipTest(f"Sem display disponível para testes de Tkinter: {exc}")

        self.config_manager = FakeConfigManager()
        self.config: dict[str, Any] = {"last_printer": "ELGIN L42PRO FULL - Produtos"}
        self.dialog = SettingsDialog(self.root, self.config_manager, self.config)

    def tearDown(self) -> None:
        self.dialog.destroy()
        self.root.destroy()

    def test_loads_defaults_when_jueri_not_configured(self):
        self.assertFalse(self.dialog.jueri_enabled_var.get())
        self.assertEqual(self.dialog.jueri_cliente_var.get(), "")
        self.assertEqual(self.dialog.jueri_token_var.get(), "")

    def test_saving_persists_through_jueri_credentials_only(self):
        self.dialog.jueri_enabled_var.set(True)
        self.dialog.jueri_cliente_var.set("SANTARUBI")
        self.dialog.jueri_token_var.set("abc123")

        self.dialog._save_jueri_settings()

        self.assertEqual(
            self.config["jueri"],
            {"enabled": True, "cliente_sistema": "SANTARUBI", "token": "abc123"},
        )
        self.assertEqual(self.config["last_printer"], "ELGIN L42PRO FULL - Produtos")
        self.assertEqual(self.config_manager.saved, self.config)

    @patch("ui.settings_dialog.test_connection")
    def test_test_connection_button_shows_success_message(self, mock_test_connection):
        mock_test_connection.return_value = ConnectionTestResult(True, "Conectado com sucesso.")

        self.dialog.jueri_enabled_var.set(True)
        self.dialog.jueri_cliente_var.set("SANTARUBI")
        self.dialog.jueri_token_var.set("abc123")
        self.dialog._on_test_connection()

        self.assertEqual(self.dialog.jueri_result_var.get(), "✓ Conectado com sucesso.")
        self.assertEqual(str(self.dialog.test_button["state"]), "normal")

    @patch("ui.settings_dialog.test_connection")
    def test_test_connection_button_shows_failure_message(self, mock_test_connection):
        mock_test_connection.return_value = ConnectionTestResult(False, "Token inválido.")

        self.dialog._on_test_connection()

        self.assertEqual(self.dialog.jueri_result_var.get(), "✗ Token inválido.")


if __name__ == "__main__":
    unittest.main()
