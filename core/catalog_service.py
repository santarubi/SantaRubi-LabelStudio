"""Serviço de regras de negócio do Catálogo Integrado.

Concentra toda a pesquisa, filtro, ordenação e estatísticas sobre os
CatalogProduct[] já carregados em memória pelo CatalogRepository. Nunca
toca a DataSource diretamente — só `repository.products` (cache) e
`repository.reload()` (a única operação que efetivamente relê a origem).

Fluxo: DataSource -> Repository -> CatalogService -> CatalogTab (interface).
A interface só lê controles e chama métodos daqui; nenhuma lógica de
pesquisa/filtro/ordenação deve existir na camada de interface.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from core.catalog_product import CatalogProduct
from core.catalog_repository import CatalogRepository
from core.catalog_settings import CatalogSettings
from core.print_item import PrintItem
from core.text_normalize import normalize_search_text

SUPPLIER_ALL = "Todos"
CATEGORY_ALL = "Todos"


def _text_key(getter: Callable[[CatalogProduct], Any]) -> Callable[[CatalogProduct], str]:
    return lambda product: normalize_search_text(getter(product))


# Registro de critérios de ordenação disponíveis. Adicionar um novo
# critério é só acrescentar uma entrada aqui — nenhum outro código precisa
# mudar (nem CatalogService.sort_by(), nem a interface).
SORT_KEY_FUNCTIONS: dict[str, Callable[[CatalogProduct], Any]] = {
    "codigo": _text_key(lambda product: product.codigo),
    "descricao": _text_key(lambda product: product.descricao),
    "fornecedor": _text_key(lambda product: product.fornecedor),
    "categoria": _text_key(lambda product: product.display_category),
    "numeracao": _text_key(lambda product: product.numeracao),
    "preco": lambda product: product.preco if product.preco is not None else float("-inf"),
}


@dataclass
class CatalogStatistics:
    """Estatísticas do catálogo carregado, independentes da interface."""

    total_products: int
    supplier_count: int
    category_count: int
    last_reload: str | None


class CatalogService:
    """Toda a manipulação (pesquisa, filtro, ordenação, estatísticas) dos
    produtos do catálogo — sempre sobre a lista já carregada em memória
    pelo Repository. A interface nunca deve filtrar/ordenar por conta
    própria; só chamar os métodos deste serviço."""

    def __init__(self, repository: CatalogRepository, settings: CatalogSettings):
        self.repository = repository
        self.settings = settings
        self._search_text: str = ""
        self._supplier_filter: str = SUPPLIER_ALL
        self._category_filter: str = CATEGORY_ALL
        self._sort_field: str | None = None
        self._sort_reverse: bool = False

    # ------------------------------------------------------------------
    # Estado de pesquisa / filtro / ordenação
    # ------------------------------------------------------------------

    def search(self, text: str) -> None:
        self._search_text = text or ""

    def filter_supplier(self, name: str | None) -> None:
        self._supplier_filter = name or SUPPLIER_ALL

    def filter_category(self, name: str | None) -> None:
        self._category_filter = name or CATEGORY_ALL

    def sort_by(self, field: str | None, reverse: bool = False) -> None:
        self._sort_field = field
        self._sort_reverse = reverse

    def clear_filters(self) -> None:
        self._search_text = ""
        self._supplier_filter = SUPPLIER_ALL
        self._category_filter = CATEGORY_ALL
        self._sort_field = None
        self._sort_reverse = False

    # ------------------------------------------------------------------
    # Leitura — sempre sobre o cache em memória do Repository
    # ------------------------------------------------------------------

    def apply_filters(self) -> list[CatalogProduct]:
        """Aplica pesquisa + filtro de fornecedor + filtro de categoria +
        ordenação atuais sobre o cache em memória. Nunca lê a DataSource."""
        if not self.repository.is_loaded:
            return []

        products = self.repository.products

        if self._supplier_filter and self._supplier_filter != SUPPLIER_ALL:
            products = [product for product in products if product.fornecedor == self._supplier_filter]

        if self._category_filter and self._category_filter != CATEGORY_ALL:
            products = [product for product in products if product.display_category == self._category_filter]

        query = normalize_search_text(self._search_text)
        if query:
            products = [product for product in products if query in product.search_blob]

        sort_key = SORT_KEY_FUNCTIONS.get(self._sort_field) if self._sort_field else None
        if sort_key is not None:
            products = sorted(products, key=sort_key, reverse=self._sort_reverse)

        return list(products)

    def get_suppliers(self) -> list[str]:
        """Fornecedores disponíveis (das abas realmente carregadas), com
        "Todos" sempre como primeira opção."""
        if not self.repository.is_loaded:
            return [SUPPLIER_ALL]
        suppliers = sorted(
            {product.fornecedor for product in self.repository.products if product.fornecedor}, key=str.lower
        )
        return [SUPPLIER_ALL] + suppliers

    def get_categories(self) -> list[str]:
        """Categorias disponíveis (via `display_category`), com "Todos"
        sempre como primeira opção."""
        if not self.repository.is_loaded:
            return [CATEGORY_ALL]
        categories = sorted(
            {product.display_category for product in self.repository.products if product.display_category},
            key=str.lower,
        )
        return [CATEGORY_ALL] + categories

    def get_statistics(self) -> CatalogStatistics:
        """Estatísticas do catálogo carregado — independentes de qualquer
        pesquisa/filtro/ordenação em vigor (sempre sobre o total real)."""
        if not self.repository.is_loaded:
            return CatalogStatistics(
                total_products=0, supplier_count=0, category_count=0, last_reload=self.settings.last_reload
            )

        products = self.repository.products
        suppliers = {product.fornecedor for product in products if product.fornecedor}
        categories = {product.display_category for product in products if product.display_category}
        return CatalogStatistics(
            total_products=len(products),
            supplier_count=len(suppliers),
            category_count=len(categories),
            last_reload=self.settings.last_reload,
        )

    # ------------------------------------------------------------------
    # Recarregamento — única operação que efetivamente toca a DataSource
    # ------------------------------------------------------------------

    def reload(self) -> list[CatalogProduct]:
        """Relê a DataSource através do Repository e atualiza o timestamp
        do último carregamento bem-sucedido."""
        products = self.repository.reload(self.settings)
        self.settings.last_reload = datetime.now().strftime("%Y-%m-%d %H:%M")
        return products

    # ------------------------------------------------------------------
    # Ponte com o domínio de impressão (PrintItem/PrintQueue)
    # ------------------------------------------------------------------

    def create_print_item(self, product: CatalogProduct) -> PrintItem:
        """Cria uma solicitação de impressão para o produto, usando a
        quantidade padrão configurada originalmente na coluna QTD da
        planilha (guardada em `product.attributes["default_quantity"]`
        pelo Repository). Se a planilha não tiver quantidade configurada
        para esse produto, PrintItem usa 1 por padrão."""
        default_quantity = product.attributes.get("default_quantity")
        return PrintItem(product=product, quantity=default_quantity)
