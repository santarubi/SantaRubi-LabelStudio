"""Seleção contínua por arraste na tabela do Catálogo Integrado — usa
exatamente ui.treeview_selection.enable_drag_selection (mesmo componente
da pesquisa Jueri) e prova que continua compatível com o fluxo existente
de "Adicionar à Fila"."""

from __future__ import annotations

import tkinter as tk
import unittest
from typing import Any

from core.catalog_datasource import DataSource
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
class CatalogTabDragSelectionTests(unittest.TestCase):
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
                    {"CODIGO": "1003", "DESCRICAO": "Anel C", "PRECO": 30.0, "CATEGORIA": "Aneis", "NUMERO": "18", "QTD": 3},
                    {"CODIGO": "1004", "DESCRICAO": "Anel D", "PRECO": 40.0, "CATEGORIA": "Aneis", "NUMERO": "19", "QTD": 4},
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

    def _row_center(self, iid: str) -> tuple[int, int]:
        bbox = self.tab.catalog_tree.bbox(iid)
        if not bbox:
            self.skipTest(f"linha {iid} sem geometria visível neste ambiente")
        x, y, width, height = bbox
        return x + width // 2, y + height // 2

    def _drag(self, from_iid: str, to_iid: str) -> None:
        tree = self.tab.catalog_tree
        x0, y0 = self._row_center(from_iid)
        x1, y1 = self._row_center(to_iid)
        tree.event_generate("<ButtonPress-1>", x=x0, y=y0)
        self.root.update()
        tree.event_generate("<B1-Motion>", x=x1, y=y1)
        self.root.update()
        tree.event_generate("<ButtonRelease-1>", x=x1, y=y1)
        self.root.update()

    def test_drag_selects_a_contiguous_range_in_the_catalog_table(self):
        self._drag("0", "2")
        self.assertEqual(set(self.tab.catalog_tree.selection()), {"0", "1", "2"})

    def test_drag_selected_range_can_be_added_to_the_print_queue(self):
        """Compatibilidade: a seleção feita por arraste funciona com
        exatamente o mesmo fluxo "Adicionar à Fila" de sempre."""
        self._drag("0", "2")

        self.tab._on_add_to_queue()

        self.assertEqual(self.tab.print_queue.count(), 3)
        codigos = {item.product.codigo for item in self.tab.print_queue.items()}
        self.assertEqual(codigos, {"1001", "1002", "1003"})


if __name__ == "__main__":
    unittest.main()
