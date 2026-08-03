"""Polimento da Planilha Excel (ver ui/main_window.py para o resto da
rodada): feedback discreto ao adicionar à fila (Melhoria 2), foco do
campo de pesquisa via Ctrl+F (Melhoria 6) e persistência de largura de
colunas/ordenação da tabela (Melhoria 5)."""

from __future__ import annotations

import tkinter as tk
import unittest
from typing import Any

from core.catalog_datasource import DataSource
from core.catalog_product import CatalogProduct
from core.catalog_repository import CatalogRepository
from core.catalog_service import CatalogService
from core.catalog_settings import CatalogSettings
from ui.catalog_tab import CatalogTab


class FakeConfigManager:
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
class CatalogTabPolishTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = tk.Tk()
        self.root.geometry("1000x700+0+0")

        self.config: dict[str, Any] = {}
        self.tab = CatalogTab(self.root, FakeConfigManager(), self.config)

        source = FakeDataSource(
            {
                "DIP-15": [
                    {"CODIGO": "1001", "DESCRICAO": "Anel A", "PRECO": 10.0, "CATEGORIA": "Aneis", "NUMERO": "16", "QTD": 1},
                    {"CODIGO": "1002", "DESCRICAO": "Anel B", "PRECO": 20.0, "CATEGORIA": "Aneis", "NUMERO": "17", "QTD": 2},
                ],
            }
        )
        settings = CatalogSettings(selected_sheets=["DIP-15"], column_map=COLUMN_MAP)
        repository = CatalogRepository(source)
        service = CatalogService(repository, settings)
        service.reload()
        self.tab.service = service
        self.tab.catalog_filtered_products = service.apply_filters()
        self.tab._load_catalog_table()
        self.root.update_idletasks()
        self.root.update()

    def tearDown(self) -> None:
        self.root.destroy()

    # --- Melhoria 2: feedback discreto (nunca messagebox) ---

    def test_adding_new_products_shows_success_toast(self) -> None:
        self.tab.catalog_tree.selection_set(["0", "1"])

        self.tab._on_add_to_queue()

        self.assertEqual(self.tab.catalog_toast_label.cget("text"), "✓ 2 produtos adicionados à fila.")

    def test_adding_an_already_queued_product_shows_updated_toast(self) -> None:
        self.tab.catalog_tree.selection_set(["0"])
        self.tab._on_add_to_queue()

        self.tab.catalog_tree.selection_set(["0"])
        self.tab._on_add_to_queue()

        self.assertEqual(
            self.tab.catalog_toast_label.cget("text"),
            "✓ Produto já existia na fila.\nQuantidade atualizada.",
        )

    # --- Melhoria 6: Ctrl+F foca a pesquisa (ver MainWindow._on_ctrl_f_shortcut) ---

    def test_focus_search_entry_gives_focus_to_the_search_field(self) -> None:
        # focus_get() só reflete o widget focado se a própria janela tiver
        # o foco do SO — força isso aqui para o teste não depender de qual
        # janela está em primeiro plano na máquina que roda a suíte.
        self.root.focus_force()
        self.root.update()

        self.tab.focus_search_entry()
        self.root.update()

        self.assertEqual(str(self.root.focus_get()), str(self.tab.catalog_search_entry))

    # --- Melhoria 5: persistência de largura de colunas e ordenação ---

    def test_get_persisted_state_reads_column_widths(self) -> None:
        self.tab.catalog_tree.column("codigo", width=123)

        state = self.tab.get_persisted_state()

        self.assertEqual(state["column_widths"]["codigo"], 123)

    def test_get_persisted_state_omits_sort_when_never_sorted(self) -> None:
        state = self.tab.get_persisted_state()
        self.assertNotIn("sort", state)

    def test_get_persisted_state_includes_active_sort(self) -> None:
        self.tab._on_sort_column("preco")

        state = self.tab.get_persisted_state()

        self.assertEqual(state["sort"], {"field": "preco", "reverse": False})

    def test_apply_persisted_state_restores_column_widths(self) -> None:
        self.tab.apply_persisted_state({"column_widths": {"codigo": 200}})

        self.assertEqual(self.tab.catalog_tree.column("codigo", "width"), 200)

    def test_apply_persisted_state_restores_sort(self) -> None:
        self.tab.apply_persisted_state({"sort": {"field": "descricao", "reverse": True}})

        self.assertEqual(self.tab._sort_field, "descricao")
        self.assertTrue(self.tab._sort_reverse)
        codigos = [self.tab.catalog_filtered_products[int(iid)].codigo for iid in self.tab.catalog_tree.get_children()]
        self.assertEqual(codigos, ["1002", "1001"])


if __name__ == "__main__":
    unittest.main()
