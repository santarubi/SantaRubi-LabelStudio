from __future__ import annotations

import tkinter as tk
import threading
import time
import unittest
from typing import Any

from app.api.product import Product
from app.api.products import ProductSearchResult
from ui.product_search_dialog import (
    CATEGORY_ALL,
    STOCK_ALL,
    STOCK_AVAILABLE,
    STOCK_EMPTY,
    ProductSearchDialog,
    filter_products,
)


def product(id_: int, stock: int | None, category_id: int | None) -> Product:
    return Product(id=id_, codigo_barras=str(id_), descricao=f"Produto {id_}", quantidade=stock, fk_categoria_id=category_id)


class FakeProductsAPI:
    def __init__(self, products: list[Product]) -> None:
        self.products = products
        self.search_calls: list[dict[str, Any]] = []
        self.all_pages_calls: list[dict[str, Any]] = []

    def search_products(self, **kwargs: Any) -> ProductSearchResult:
        self.search_calls.append(kwargs)
        return ProductSearchResult(products=list(self.products))

    def search_all_pages(self, **kwargs: Any) -> list[Product]:
        self.all_pages_calls.append(kwargs)
        return list(self.products)

    def search_multiple_products(self, _codes: list[str], **_kwargs: Any) -> list[Product]:
        return list(self.products)


class FakeCategoriesAPI:
    categoria_por_id = {10: "Anéis", 20: "Colares"}


class SlowProductsAPI(FakeProductsAPI):
    def __init__(self, products: list[Product], release: threading.Event) -> None:
        super().__init__(products)
        self.release = release

    def search_products(self, **kwargs: Any) -> ProductSearchResult:
        self.release.wait(timeout=2)
        return super().search_products(**kwargs)


class JueriFilterLogicTests(unittest.TestCase):
    def setUp(self) -> None:
        self.products = [
            product(1, 4, 10),
            product(2, 0, 10),
            product(3, 2, 20),
            product(4, None, 20),
        ]

    def test_combines_stock_and_category(self) -> None:
        result = filter_products(self.products, STOCK_AVAILABLE, category_id=10)
        self.assertEqual([item.id for item in result], [1])

    def test_without_stock_excludes_unknown_stock(self) -> None:
        result = filter_products(self.products, STOCK_EMPTY)
        self.assertEqual([item.id for item in result], [2])

    def test_all_preserves_products_with_unavailable_data(self) -> None:
        result = filter_products(self.products, STOCK_ALL)
        self.assertEqual(result, self.products)


def _tk_available() -> bool:
    try:
        root = tk.Tk()
        root.destroy()
        return True
    except tk.TclError:
        return False


@unittest.skipUnless(_tk_available(), "ambiente de teste sem display Tk disponível")
class JueriFilterPersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = tk.Tk()
        self.root.withdraw()
        self.api = FakeProductsAPI([product(1, 4, 10), product(2, 0, 20)])

    def tearDown(self) -> None:
        self.root.destroy()

    def _dialog(self, **kwargs: Any) -> ProductSearchDialog:
        return ProductSearchDialog(self.root, self.api, categories_api=FakeCategoriesAPI(), **kwargs)

    def test_restores_all_supported_filter_fields(self) -> None:
        saved = {
            "supplier": "valor antigo ignorado",
            "stock": STOCK_AVAILABLE,
            "category": "Anéis",
            "query": "anel",
            "data_inicial": "01/10/2026",
            "data_final": "24/10/2026",
            "sort": "Estoque",
            "direction": "Decrescente",
        }
        dialog = self._dialog(initial_filters=saved)

        self.assertEqual(dialog.stock_var.get(), STOCK_AVAILABLE)
        self.assertEqual(dialog.category_var.get(), "Anéis")
        self.assertEqual(dialog.search_var.get(), "anel")
        self.assertEqual(dialog.sort_var.get(), "Estoque")
        self.assertEqual(dialog.direction_var.get(), "Decrescente")

    def test_invalid_old_values_fall_back_safely(self) -> None:
        dialog = self._dialog(initial_filters={"stock": "Removido", "sort": "Antigo", "direction": "X"})
        self.assertEqual(dialog.stock_var.get(), STOCK_ALL)
        self.assertEqual(dialog.category_var.get(), CATEGORY_ALL)
        self.assertEqual(dialog.sort_var.get(), "Código")
        self.assertEqual(dialog.direction_var.get(), "Crescente")

    def test_stock_filter_fetches_all_pages_and_then_filters_locally(self) -> None:
        dialog = self._dialog(initial_filters={"stock": STOCK_EMPTY})
        self.assertEqual(self.api.all_pages_calls, [{"search": None}])
        self.assertEqual([item.id for item in dialog.results], [2])

    def test_category_filter_uses_documented_server_parameter(self) -> None:
        dialog = self._dialog(initial_filters={"category": "Colares"})
        self.assertEqual(self.api.all_pages_calls, [{"search": None, "categoria_id": 20}])
        self.assertEqual([item.id for item in dialog.results], [2])

    def test_changes_are_exposed_for_config_persistence(self) -> None:
        states: list[dict[str, str]] = []
        dialog = self._dialog(on_filters_changed=states.append)
        dialog.stock_var.set(STOCK_AVAILABLE)
        dialog._on_server_filter_changed()
        self.assertEqual(states[-1]["stock"], STOCK_AVAILABLE)
        self.assertIn("query", states[-1])
        self.assertIn("direction", states[-1])

    def test_async_search_keeps_dialog_creation_responsive(self) -> None:
        release = threading.Event()
        self.api = SlowProductsAPI([product(1, 1, 10)], release)
        start = time.perf_counter()
        dialog = self._dialog(async_search=True)
        elapsed = time.perf_counter() - start
        try:
            self.assertLess(elapsed, 0.5)
            self.assertEqual(dialog.status_var.get(), "Carregando produtos...")
        finally:
            release.set()


if __name__ == "__main__":
    unittest.main()
