"""Janela de Configurações do Santa Rubi Label Studio.

Reúne seções de configuração que não pertencem à tela principal de
impressão. Primeira seção: Integração Jueri.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from app.api.auth import JueriCredentials
from app.api.connection_test import test_connection
from core.config import ConfigManager
from ui.branding import AboutDialog, apply_window_icon


class SettingsDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, config_manager: ConfigManager, config: dict[str, Any]) -> None:
        super().__init__(parent)
        self.title("Configurações")
        apply_window_icon(self)
        self.geometry("480x340")
        self.minsize(420, 320)
        self.transient(parent)

        self.config_manager = config_manager
        self.config = config
        self.credentials = JueriCredentials.from_config(config)

        self.jueri_enabled_var = tk.BooleanVar(value=self.credentials.enabled)
        self.jueri_cliente_var = tk.StringVar(value=self.credentials.cliente_sistema)
        self.jueri_token_var = tk.StringVar(value=self.credentials.token)
        self.jueri_result_var = tk.StringVar(value="")

        self._build_widgets()
        self.grab_set()

    def _build_widgets(self) -> None:
        container = ttk.Frame(self, padding=16)
        container.pack(fill="both", expand=True)
        container.grid_columnconfigure(0, weight=1)

        section = ttk.LabelFrame(container, text="Integração Jueri", padding=12)
        section.grid(row=0, column=0, sticky="new")
        section.grid_columnconfigure(0, weight=1)

        ttk.Checkbutton(
            section,
            text="Habilitar integração",
            variable=self.jueri_enabled_var,
            command=self._save_jueri_settings,
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        ttk.Label(section, text="Cliente Sistema").grid(row=1, column=0, sticky="w", pady=(0, 2))
        self.cliente_entry = ttk.Entry(section, textvariable=self.jueri_cliente_var)
        self.cliente_entry.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        self.cliente_entry.bind("<FocusOut>", lambda _event: self._save_jueri_settings())

        ttk.Label(section, text="Token").grid(row=3, column=0, sticky="w", pady=(0, 2))
        self.token_entry = ttk.Entry(section, textvariable=self.jueri_token_var, show="*")
        self.token_entry.grid(row=4, column=0, sticky="ew", pady=(0, 8))
        self.token_entry.bind("<FocusOut>", lambda _event: self._save_jueri_settings())

        self.test_button = ttk.Button(
            section, text="Testar conexão", style="Primary.TButton", command=self._on_test_connection
        )
        self.test_button.grid(row=5, column=0, sticky="w", pady=(4, 0))

        ttk.Label(section, textvariable=self.jueri_result_var, style="Subtitle.TLabel", wraplength=380).grid(
            row=6, column=0, sticky="w", pady=(8, 0)
        )
        ttk.Button(container, text="Sobre", style="App.TButton", command=self._open_about).grid(
            row=1, column=0, sticky="e", pady=(12, 0)
        )

    def _open_about(self) -> None:
        AboutDialog(self)

    def _save_jueri_settings(self) -> None:
        self.credentials.enabled = self.jueri_enabled_var.get()
        self.credentials.cliente_sistema = self.jueri_cliente_var.get().strip()
        self.credentials.token = self.jueri_token_var.get().strip()
        self.credentials.save_to(self.config)
        self.config_manager.save(self.config)

    def _on_test_connection(self) -> None:
        self._save_jueri_settings()
        self.jueri_result_var.set("Testando conexão...")
        self.test_button.configure(state="disabled")
        self.update_idletasks()

        try:
            result = test_connection(self.credentials)
            symbol = "✓" if result.success else "✗"
            self.jueri_result_var.set(f"{symbol} {result.message}")
        finally:
            self.test_button.configure(state="normal")
