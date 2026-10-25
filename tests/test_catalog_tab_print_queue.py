"""Integração entre o Catálogo Integrado e o PrintQueue (v2.3).

Cobre: adicionar produto(s) selecionados à fila (via
CatalogService.create_print_item -> PrintQueue.add/increment), remover,
limpar, atualização automática dos contadores e estado dos botões — tudo
sempre partindo do PrintQueue, nunca de listas manipuladas pela interface.
"""

from __future__ import annotations

import tkinter as tk
import unittest
from typing import Any
from unittest.mock import patch

from core.catalog_datasource import DataSource
from core.catalog_product import CatalogProduct
from core.catalog_repository import CatalogRepository
from core.catalog_service import CatalogService
from core.catalog_settings import CatalogSettings
from ui.catalog_tab import CatalogTab


class FakeConfigManager:
    """Nunca toca o data/config.json real — só precisa expor save()."""

    def save(self, config: dict[str, Any]) -> None:
        pass


class FakeDataSource(DataSource):
    def __init__(self, sheets_data: dict[str, list[dict[str, Any]]]):
        self.sheets_data = sheets_data

    def list_sheets(self) -> list[str]:
        return list(self.sheets_data.keys())

    def get_headers(self, sheet_names: list[str]) -> dict[str, list[str]]:
        headers: dict[str, list[str]] = {}
        for name in sheet_names:
            rows = self.sheets_data.get(name, [])
            headers[name] = list(rows[0].keys()) if rows else []
        return headers

    def count_rows(self, sheet_names: list[str]) -> dict[str, int]:
        return {name: len(self.sheets_data.get(name, [])) for name in sheet_names}

    def read_rows(self, sheet_names: list[str]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for name in sheet_names:
            for row in self.sheets_data.get(name, []):
                row_with_sheet = dict(row)
                row_with_sheet["_sheet"] = name
                rows.append(row_with_sheet)
        return rows


COLUMN_MAP = {
    "codigo": "CODIGO",
    "descricao": "DESCRICAO",
    "preco": "PRECO",
    "categoria": "CATEGORIA",
    "numeracao": "NUMERO",
    "quantidade": "QTD",
}


def _tk_available() -> bool:
    try:
        root = tk.Tk()
        root.destroy()
        return True
    except tk.TclError:
        return False


@unittest.skipUnless(_tk_available(), "ambiente de teste sem display Tk disponível")
class CatalogTabPrintQueueTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = tk.Tk()
        self.root.withdraw()

        self.config: dict[str, Any] = {}
        self.tab = CatalogTab(self.root, FakeConfigManager(), self.config)

        source = FakeDataSource(
            {
                "DIP-15": [
                    {"CODIGO": "1001", "DESCRICAO": "Anel Coração", "PRECO": 59.9,
                     "CATEGORIA": "Aneis", "NUMERO": "16", "QTD": 5},
                    {"CODIGO": "1002", "DESCRICAO": "Brinco Flor", "PRECO": 89.9,
                     "CATEGORIA": "Brincos", "NUMERO": "", "QTD": 2},
                ],
            }
        )
        settings = CatalogSettings(selected_sheets=["DIP-15"], column_map=COLUMN_MAP)
        repository = CatalogRepository(source)
        service = CatalogService(repository, settings)
        service.reload()

        # Substitui o service/produtos diretamente — o carregamento via
        # Excel/config já é coberto por outros testes; aqui o foco é a
        # integração catálogo -> PrintQueue.
        self.tab.service = service
        self.tab.catalog_filtered_products = service.apply_filters()
        self.tab._load_catalog_table()

    def tearDown(self) -> None:
        self.root.destroy()

    def _select_rows(self, *indices: int) -> None:
        self.tab.catalog_tree.selection_set([str(i) for i in indices])

    def test_add_single_selected_item(self):
        self._select_rows(0)
        self.tab._on_add_to_queue()

        self.assertEqual(self.tab.print_queue.count(), 1)
        item = self.tab.print_queue.find(self.tab.catalog_filtered_products[0])
        self.assertIsNotNone(item)
        self.assertEqual(item.quantity, 5)

    def test_add_multiple_selected_items(self):
        self._select_rows(0, 1)
        self.tab._on_add_to_queue()

        self.assertEqual(self.tab.print_queue.count(), 2)
        self.assertEqual(self.tab.print_queue.total_labels(), 7)

    def test_add_existing_item_increments_instead_of_duplicating(self):
        self._select_rows(0)
        self.tab._on_add_to_queue()
        self._select_rows(0)
        self.tab._on_add_to_queue()

        self.assertEqual(self.tab.print_queue.count(), 1, "produto repetido nao deveria duplicar")
        item = self.tab.print_queue.find(self.tab.catalog_filtered_products[0])
        self.assertEqual(item.quantity, 10, "deveria incrementar pela quantidade padrao (5 + 5)")

    def test_remove_selected_queue_item(self):
        self._select_rows(0, 1)
        self.tab._on_add_to_queue()
        product_to_remove = self.tab.catalog_filtered_products[0]

        self.tab._on_select_queue_card(product_to_remove.codigo)
        self.tab._on_remove_from_queue()

        self.assertEqual(self.tab.print_queue.count(), 1)
        self.assertFalse(self.tab.print_queue.contains(product_to_remove))

    def test_remove_without_selection_is_a_no_op(self):
        self._select_rows(0)
        self.tab._on_add_to_queue()
        self.tab._on_remove_from_queue()
        self.assertEqual(self.tab.print_queue.count(), 1, "sem card selecionado, remover nao deve afetar a fila")

    def test_remove_multiple_selected_queue_items(self):
        self._select_rows(0, 1)
        self.tab._on_add_to_queue()
        codes = [product.codigo for product in self.tab.catalog_filtered_products[:2]]
        self.tab._on_select_queue_card(codes[0])
        self.tab._on_select_queue_card(codes[1], additive=True)

        self.tab._on_remove_from_queue()

        self.assertTrue(self.tab.print_queue.is_empty())

    def test_clear_queue_empties_it(self):
        self._select_rows(0, 1)
        self.tab._on_add_to_queue()
        self.tab._on_clear_queue()
        self.assertTrue(self.tab.print_queue.is_empty())

    def test_totals_update_automatically_after_adding(self):
        self._select_rows(0, 1)
        self.tab._on_add_to_queue()

        self.assertEqual(self.tab.queue_count_var.get(), "Produtos na fila: 2")
        self.assertEqual(self.tab.queue_total_var.get(), "Total de etiquetas: 7")

    def test_totals_reset_after_clearing(self):
        self._select_rows(0, 1)
        self.tab._on_add_to_queue()
        self.tab._on_clear_queue()

        self.assertEqual(self.tab.queue_count_var.get(), "Produtos na fila: 0")
        self.assertEqual(self.tab.queue_total_var.get(), "Total de etiquetas: 0")

    def test_buttons_start_disabled_when_queue_is_empty(self):
        self.assertEqual(str(self.tab.remove_from_queue_button["state"]), "disabled")
        self.assertEqual(str(self.tab.clear_queue_button["state"]), "disabled")

    def test_buttons_enable_once_queue_has_items(self):
        self._select_rows(0)
        self.tab._on_add_to_queue()

        self.assertEqual(str(self.tab.remove_from_queue_button["state"]), "normal")
        self.assertEqual(str(self.tab.clear_queue_button["state"]), "normal")

    def test_buttons_disable_again_after_queue_emptied(self):
        self._select_rows(0)
        self.tab._on_add_to_queue()
        self.tab._on_clear_queue()

        self.assertEqual(str(self.tab.remove_from_queue_button["state"]), "disabled")
        self.assertEqual(str(self.tab.clear_queue_button["state"]), "disabled")

    def test_interface_reflects_print_queue_state_without_duplicated_state(self):
        """A interface nao guarda sua propria contagem — ela so' repete o
        que o PrintQueue reporta, entao alterar a fila diretamente e pedir
        um refresh basta para refletir corretamente (prova de sincronizacao)."""
        self._select_rows(0)
        self.tab._on_add_to_queue()

        product = self.tab.catalog_filtered_products[0]
        self.tab.print_queue.increment(product, amount=100)
        self.tab._refresh_queue_view()

        self.assertEqual(self.tab.queue_total_var.get(), "Total de etiquetas: 105")

    def test_adding_with_nothing_selected_does_not_change_queue(self):
        self.tab.catalog_tree.selection_remove(*self.tab.catalog_tree.selection())
        with patch("ui.catalog_tab.messagebox.showinfo") as mock_showinfo:
            self.tab._on_add_to_queue()
            mock_showinfo.assert_called_once()
        self.assertTrue(self.tab.print_queue.is_empty())


class CatalogTabAddProductToQueueTests(unittest.TestCase):
    """add_product_to_queue() é o ponto de entrada usado pela seleção
    múltipla da pesquisa Jueri (ver ui/product_search_dialog.py e
    Product.to_catalog_product()) — prova que produtos de origem externa
    entram na MESMA fila, sem nenhuma tabela/estado paralelo."""

    def setUp(self) -> None:
        if not _tk_available():
            self.skipTest("ambiente de teste sem display Tk disponível")
        self.root = tk.Tk()
        self.root.withdraw()
        self.config: dict[str, Any] = {}
        self.tab = CatalogTab(self.root, FakeConfigManager(), self.config)

    def tearDown(self) -> None:
        self.root.destroy()

    def _jueri_product(self, codigo: str = "181021", quantidade_estoque=3) -> CatalogProduct:
        return CatalogProduct(
            codigo=codigo,
            descricao="ALIANCA",
            preco=75.9,
            categoria="AÇO INOX - DOURADO",
            numeracao="30",
            fornecedor="Jueri",
            attributes={"default_quantity": quantidade_estoque, "quantidade_estoque": quantidade_estoque},
        )

    def test_adds_product_to_the_same_print_queue(self):
        product = self._jueri_product()

        self.tab.add_product_to_queue(product)

        self.assertEqual(self.tab.print_queue.count(), 1)
        self.assertTrue(self.tab.print_queue.contains(product))

    def test_initial_quantity_comes_from_default_quantity_attribute(self):
        """Etapa 4: quantidade para imprimir nasce igual ao estoque atual."""
        product = self._jueri_product(quantidade_estoque=7)

        self.tab.add_product_to_queue(product)

        self.assertEqual(self.tab.print_queue.find(product).quantity, 7)

    def test_missing_default_quantity_falls_back_to_one(self):
        product = self._jueri_product(quantidade_estoque=None)

        self.tab.add_product_to_queue(product)

        self.assertEqual(self.tab.print_queue.find(product).quantity, 1)

    def test_adding_the_same_product_again_sums_instead_of_duplicating(self):
        self.tab.add_product_to_queue(self._jueri_product("181021", quantidade_estoque=3))
        self.tab.add_product_to_queue(self._jueri_product("181021", quantidade_estoque=3))

        self.assertEqual(self.tab.print_queue.count(), 1)
        self.assertEqual(self.tab.print_queue.find(self._jueri_product("181021")).quantity, 6)

    def test_refreshes_the_queue_view_counters(self):
        self.tab.add_product_to_queue(self._jueri_product(quantidade_estoque=4))

        self.assertEqual(self.tab.queue_count_var.get(), "Produtos na fila: 1")
        self.assertEqual(self.tab.queue_total_var.get(), "Total de etiquetas: 4")

    def test_coexists_with_products_added_from_the_catalog_table(self):
        """Compatibilidade: a mesma fila recebe itens do Catálogo
        Integrado (Excel) e da pesquisa Jueri lado a lado, sem conflito."""
        source = FakeDataSource(
            {"DIP-15": [{"CODIGO": "1001", "DESCRICAO": "Anel Coração", "PRECO": 59.9,
                         "CATEGORIA": "Aneis", "NUMERO": "16", "QTD": 5}]}
        )
        settings = CatalogSettings(selected_sheets=["DIP-15"], column_map=COLUMN_MAP)
        repository = CatalogRepository(source)
        service = CatalogService(repository, settings)
        service.reload()
        self.tab.service = service
        self.tab.catalog_filtered_products = service.apply_filters()
        self.tab._load_catalog_table()
        self.tab.catalog_tree.selection_set(["0"])
        self.tab._on_add_to_queue()

        self.tab.add_product_to_queue(self._jueri_product("181021", quantidade_estoque=3))

        self.assertEqual(self.tab.print_queue.count(), 2)
        codigos = {item.product.codigo for item in self.tab.print_queue.items()}
        self.assertEqual(codigos, {"1001", "181021"})
        self.assertEqual(self.tab.queue_count_var.get(), "Produtos na fila: 2")


if __name__ == "__main__":
    unittest.main()
