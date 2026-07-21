"""Modelo de configuração do Catálogo Integrado, persistido em config.json.

Mantido separado das configurações da aba de impressão manual (que usa
suas próprias chaves, como last_spreadsheet/last_printer) — tudo do
Catálogo Integrado vive sob uma única chave própria no config.json.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

CATALOG_CONFIG_KEY = "catalog_integrado"

CATALOG_FIELDS = ["codigo", "descricao", "preco", "categoria", "numeracao", "quantidade"]

CATALOG_FIELD_LABELS = {
    "codigo": "Código",
    "descricao": "Descrição",
    "preco": "Preço",
    "categoria": "Categoria",
    "numeracao": "Numeração",
    "quantidade": "Quantidade",
}


@dataclass
class CatalogSettings:
    """Configuração da fonte de dados do Catálogo Integrado: arquivo, abas
    selecionadas, mapeamento de colunas (campo interno -> cabeçalho real) e
    metadados do último carregamento bem-sucedido."""

    file_path: str = ""
    selected_sheets: list[str] = field(default_factory=list)
    column_map: dict[str, str] = field(default_factory=dict)
    version: int = 1
    last_reload: str | None = None
    configuration_expanded: bool = True

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "CatalogSettings":
        raw = config.get(CATALOG_CONFIG_KEY) or {}
        return cls(
            file_path=raw.get("file_path", ""),
            selected_sheets=list(raw.get("selected_sheets", [])),
            column_map=dict(raw.get("column_map", {})),
            version=raw.get("version", 1),
            last_reload=raw.get("last_reload"),
            configuration_expanded=raw.get("configuration_expanded", True),
        )

    def save_to(self, config: dict[str, Any]) -> None:
        """Grava esta configuração dentro do dicionário de config (mutação
        in-place), para ser persistida em seguida via ConfigManager.save()."""
        config[CATALOG_CONFIG_KEY] = {
            "file_path": self.file_path,
            "selected_sheets": list(self.selected_sheets),
            "column_map": dict(self.column_map),
            "version": self.version,
            "last_reload": self.last_reload,
            "configuration_expanded": self.configuration_expanded,
        }
