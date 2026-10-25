"""Credenciais e cabeçalhos de autenticação da integração com a API Jueri.

Segue o mesmo padrão de core/catalog_settings.py: um dataclass com
from_config()/save_to() que lê e grava sua própria chave dentro do
dicionário de configuração administrado por core/config.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .exceptions import JueriAuthenticationError

JUERI_CONFIG_KEY = "jueri"


@dataclass
class JueriCredentials:
    enabled: bool = False
    cliente_sistema: str = ""
    token: str = ""

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "JueriCredentials":
        raw = config.get(JUERI_CONFIG_KEY) or {}
        return cls(
            enabled=bool(raw.get("enabled", False)),
            cliente_sistema=raw.get("cliente_sistema", ""),
            token=raw.get("token", ""),
        )

    def save_to(self, config: dict[str, Any]) -> None:
        config[JUERI_CONFIG_KEY] = {
            "enabled": self.enabled,
            "cliente_sistema": self.cliente_sistema,
            "token": self.token,
        }

    def build_headers(self) -> dict[str, str]:
        if not self.cliente_sistema or not self.token:
            raise JueriAuthenticationError(
                "Credenciais da API Jueri não configuradas (cliente_sistema/token)."
            )
        return {
            "Authorization": f"Bearer {self.token}",
            "Cliente-Sistema": self.cliente_sistema,
        }
