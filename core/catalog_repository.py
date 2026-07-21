"""Repositório do Catálogo Integrado.

Responsabilidade única: fornecer dados a partir de uma DataSource concreta
e mantê-los em memória depois de carregados. Não valida configuração —
isso é responsabilidade exclusiva de CatalogConfigurationValidator.

Fluxo: DataSource -> load() -> CatalogProduct[] em cache -> toda pesquisa
e filtro subsequente opera sobre essa lista em memória, sem reler a
DataSource. Só load()/reload() voltam a tocar na origem dos dados.

Para trocar Excel por SQLite, API ou outra origem no futuro, basta
implementar uma nova DataSource e passá-la aqui; nada neste módulo muda.
"""

from __future__ import annotations

from typing import Any

from core.catalog_datasource import DataSource
from core.catalog_excel_source import normalize_header
from core.catalog_product import CatalogProduct
from core.catalog_settings import CatalogSettings


class CatalogRepository:
    """Carrega produtos de uma DataSource e os mantém em cache em memória."""

    def __init__(self, data_source: DataSource):
        self.data_source = data_source
        self._products: list[CatalogProduct] | None = None

    @property
    def is_loaded(self) -> bool:
        return self._products is not None

    @property
    def products(self) -> list[CatalogProduct]:
        """Produtos carregados em memória (não relê a DataSource)."""
        if self._products is None:
            raise RuntimeError("O catálogo ainda não foi carregado. Chame load() primeiro.")
        return self._products

    def list_sheets(self) -> list[str]:
        return self.data_source.list_sheets()

    def get_headers_by_sheet(self, sheet_names: list[str]) -> dict[str, list[str]]:
        return self.data_source.get_headers(sheet_names)

    def get_available_headers(self, sheet_names: list[str]) -> list[str]:
        """Cabeçalhos únicos (por texto normalizado) entre as abas
        informadas, preservando a primeira grafia original encontrada."""
        seen: dict[str, str] = {}
        for headers in self.get_headers_by_sheet(sheet_names).values():
            for header in headers:
                key = normalize_header(header)
                if key and key not in seen:
                    seen[key] = header
        return list(seen.values())

    def load(self, settings: CatalogSettings) -> list[CatalogProduct]:
        """Lê as abas selecionadas na DataSource, converte cada linha em
        CatalogProduct usando o mapeamento de colunas e guarda tudo em
        cache. Esta é a única operação que efetivamente toca o Excel para
        obter dados de produtos — chamadas subsequentes a `products` (ou a
        uma nova instância que reutilize este objeto) não releem a fonte."""
        raw_rows = self.data_source.read_rows(settings.selected_sheets)
        self._products = [self._to_product(row, settings.column_map) for row in raw_rows]
        return self._products

    def reload(self, settings: CatalogSettings) -> list[CatalogProduct]:
        """Força uma nova leitura da DataSource, substituindo o cache atual."""
        return self.load(settings)

    def _to_product(self, row: dict[str, Any], column_map: dict[str, str]) -> CatalogProduct:
        return CatalogProduct(
            codigo=self._as_text(self._mapped_value(row, column_map, "codigo")),
            descricao=self._as_text(self._mapped_value(row, column_map, "descricao")),
            preco=self._as_float(self._mapped_value(row, column_map, "preco")),
            categoria=self._as_text(self._mapped_value(row, column_map, "categoria")),
            numeracao=self._as_text(self._mapped_value(row, column_map, "numeracao")),
            fornecedor=self._as_text(row.get("_sheet")),
            # A quantidade da coluna QTD NÃO é um campo do produto — é só a
            # quantidade padrão de impressão, guardada aqui temporariamente
            # (valor bruto, sem normalizar) para CatalogService.create_print_item()
            # usar ao montar um PrintItem. O domínio do produto continua limpo.
            attributes={"default_quantity": self._mapped_value(row, column_map, "quantidade")},
        )

    def _mapped_value(self, row: dict[str, Any], column_map: dict[str, str], internal_field: str) -> Any:
        header = column_map.get(internal_field)
        if not header:
            return None
        target = normalize_header(header)
        for key, value in row.items():
            if key != "_sheet" and normalize_header(key) == target:
                return value
        return None

    @staticmethod
    def _as_text(value: Any) -> str:
        return "" if value is None else str(value)

    @staticmethod
    def _as_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
