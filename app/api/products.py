"""Endpoints de produtos da API Jueri.

Reaproveita o JueriClient já existente (autenticação, timeout, tratamento
de erros de rede/HTTP) — nenhuma infraestrutura HTTP nova é criada aqui.

Endpoint: GET /api/v1/{cliente_sistema}/produto — filtros documentados em
https://jueri.com.br/sis/docs/: search, status, categoria_id,
subcategoria_id, data_criacao_inicial/final, data_alteracao_inicial/final,
page, per_page.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .client import JueriClient
from .product import Product

PRODUCTS_PATH = "/api/v1/{cliente_sistema}/produto"


@dataclass
class ProductSearchResult:
    """Página de resultados no formato do paginator documentado.

    `total`/`last_page` não aparecem no exemplo oficial de resposta da
    listagem de produtos — por isso não são expostos aqui.
    """

    products: list[Product] = field(default_factory=list)
    current_page: int | None = None
    per_page: int | None = None
    from_item: int | None = None
    to_item: int | None = None
    first_page_url: str | None = None
    next_page_url: str | None = None
    prev_page_url: str | None = None
    path: str | None = None

    @classmethod
    def from_api(cls, raw: dict[str, Any]) -> "ProductSearchResult":
        return cls(
            products=[Product.from_api(item) for item in raw.get("data") or []],
            current_page=raw.get("current_page"),
            per_page=raw.get("per_page"),
            from_item=raw.get("from"),
            to_item=raw.get("to"),
            first_page_url=raw.get("first_page_url"),
            next_page_url=raw.get("next_page_url"),
            prev_page_url=raw.get("prev_page_url"),
            path=raw.get("path"),
        )


class ProductsAPI:
    def __init__(self, client: JueriClient) -> None:
        self.client = client

    def search_products(
        self,
        search: str | None = None,
        status: int | None = None,
        categoria_id: int | None = None,
        subcategoria_id: int | None = None,
        data_criacao_inicial: str | None = None,
        data_criacao_final: str | None = None,
        data_alteracao_inicial: str | None = None,
        data_alteracao_final: str | None = None,
        page: int | None = None,
        per_page: int | None = None,
    ) -> ProductSearchResult:
        params: dict[str, Any] = {
            "search": search,
            "status": status,
            "categoria_id": categoria_id,
            "subcategoria_id": subcategoria_id,
            "data_criacao_inicial": data_criacao_inicial,
            "data_criacao_final": data_criacao_final,
            "data_alteracao_inicial": data_alteracao_inicial,
            "data_alteracao_final": data_alteracao_final,
            "page": page,
            "per_page": per_page,
        }
        query = {key: value for key, value in params.items() if value is not None}

        path = PRODUCTS_PATH.format(cliente_sistema=self.client.credentials.cliente_sistema)
        raw = self.client.get(path, params=query)
        return ProductSearchResult.from_api(raw)

    def search_multiple_products(self, codes: list[str], **extra_filters: Any) -> list[Product]:
        """Busca vários códigos de uma vez, um por um — reaproveita
        search_products() para cada código em vez de inventar uma
        chamada HTTP nova, então não depende do limite de paginação da
        API (cada busca individual já traz seus próprios resultados).

        `**extra_filters` é repassado para cada busca individual (ex.:
        data_criacao_inicial/final) — permite combinar lista de códigos
        com filtro de data: "só os códigos cadastrados em tal data".

        Códigos sem nenhum resultado são simplesmente ignorados. O
        resultado final é deduplicado por id e ordenado por codigo_barras.
        """
        unique_codes: list[str] = []
        for code in codes:
            if code not in unique_codes:
                unique_codes.append(code)

        products_by_id: dict[Any, Product] = {}
        for code in unique_codes:
            result = self.search_products(search=code, **extra_filters)
            for product in result.products:
                products_by_id[product.id] = product

        return sorted(products_by_id.values(), key=lambda product: product.codigo_barras or "")

    def search_all_pages(self, **filters: Any) -> list[Product]:
        """Busca com paginação automática: chama search_products()
        repetidas vezes (per_page=1000, o máximo confirmado na API),
        seguindo next_page_url até ele vir null — junta tudo numa lista
        só. Usado quando um filtro de data está ativo, para trazer todos
        os produtos do período sem depender do limite de uma página.

        `max_pages` é um limite de segurança (não um parâmetro exposto):
        evita um laço infinito se a API algum dia devolver next_page_url
        de forma inconsistente.
        """
        filters.setdefault("per_page", 1000)
        max_pages = 200

        all_products: list[Product] = []
        page = 1
        while page <= max_pages:
            result = self.search_products(page=page, **filters)
            all_products.extend(result.products)
            if not result.next_page_url:
                break
            page += 1

        return all_products
