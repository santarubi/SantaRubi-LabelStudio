"""Contrato abstrato de fonte de dados do Catálogo Integrado.

Qualquer origem de dados do catálogo (Excel hoje; SQLite, API ou outra
fonte no futuro) implementa esta interface. O Repository e a interface só
conhecem este contrato — nunca uma implementação concreta — para que trocar
a origem dos dados não exija alterar Repository nem UI.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class DataSource(ABC):
    """Contrato mínimo que uma fonte de dados do catálogo deve implementar."""

    @abstractmethod
    def list_sheets(self) -> list[str]:
        """Retorna os nomes de todas as abas/coleções disponíveis na origem."""

    @abstractmethod
    def get_headers(self, sheet_names: list[str]) -> dict[str, list[str]]:
        """Retorna, para cada aba informada, os cabeçalhos encontrados."""

    @abstractmethod
    def count_rows(self, sheet_names: list[str]) -> dict[str, int]:
        """Retorna, para cada aba informada, a quantidade de linhas de dados
        (sem contar o cabeçalho)."""

    @abstractmethod
    def read_rows(self, sheet_names: list[str]) -> list[dict[str, Any]]:
        """Retorna todas as linhas de dados das abas informadas, cada uma
        como um dicionário {cabeçalho original: valor}."""
