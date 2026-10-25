"""Painéis redimensionáveis da aba Planilha Excel."""

from __future__ import annotations

import tkinter as tk
import unittest
from tkinter import ttk
from unittest.mock import patch

from ui.catalog_tab import (
    CONFIGURATION_PANEL_MIN_HEIGHT,
    MAIN_PANEL_MIN_WIDTH,
    PRODUCTS_PANEL_MIN_HEIGHT,
    QUEUE_PANEL_MIN_WIDTH,
    CatalogTab,
)


class FakeConfigManager:
    def save(self, config: dict) -> None:
        pass


def _tk_available() -> bool:
    try:
        root = tk.Tk()
        root.destroy()
        return True
    except tk.TclError:
        return False


@unittest.skipUnless(_tk_available(), "ambiente de teste sem display Tk disponível")
class CatalogTabResizablePaneTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = tk.Tk()
        self.root.geometry("1200x900+0+0")
        self.tab = CatalogTab(self.root, FakeConfigManager(), {})
        self.root.update_idletasks()
        self.root.update()

    def tearDown(self) -> None:
        self.root.destroy()

    def test_creates_horizontal_and_vertical_native_paned_windows(self) -> None:
        self.assertIsInstance(self.tab.horizontal_paned, ttk.Panedwindow)
        self.assertIsInstance(self.tab.vertical_paned, ttk.Panedwindow)
        self.assertEqual(len(self.tab.horizontal_paned.panes()), 2)
        self.assertEqual(len(self.tab.vertical_paned.panes()), 2)

    def test_sashes_respect_safe_minimums(self) -> None:
        self.tab.horizontal_paned.sashpos(0, 0)
        self.tab.vertical_paned.sashpos(0, 0)
        self.tab._clamp_horizontal_sash()
        self.tab._clamp_vertical_sash()

        horizontal_minimum, _ = self.tab._horizontal_bounds()
        vertical_minimum, _ = self.tab._vertical_bounds()
        self.assertEqual(self.tab.horizontal_paned.sashpos(0), horizontal_minimum)
        self.assertEqual(self.tab.vertical_paned.sashpos(0), vertical_minimum)
        self.assertGreaterEqual(horizontal_minimum, min(MAIN_PANEL_MIN_WIDTH, self.tab.horizontal_paned.winfo_width() // 2))
        self.assertGreaterEqual(vertical_minimum, min(CONFIGURATION_PANEL_MIN_HEIGHT, self.tab.vertical_paned.winfo_height() // 2))

    def test_cursor_indicates_each_resizable_divider(self) -> None:
        self.tab.horizontal_paned.event_generate(
            "<Motion>", x=self.tab.horizontal_paned.sashpos(0), y=30
        )
        self.tab.vertical_paned.event_generate(
            "<Motion>", x=30, y=self.tab.vertical_paned.sashpos(0)
        )
        self.root.update()

        self.assertNotEqual(str(self.tab.horizontal_paned.cget("cursor")), "")
        self.assertNotEqual(str(self.tab.vertical_paned.cget("cursor")), "")

    def test_table_expands_when_configuration_pane_is_reduced(self) -> None:
        _, vertical_maximum = self.tab._vertical_bounds()
        self.tab.vertical_paned.sashpos(0, vertical_maximum)
        self.root.update()
        smaller_table_height = self.tab.catalog_tree.winfo_height()

        vertical_minimum, _ = self.tab._vertical_bounds()
        self.tab.vertical_paned.sashpos(0, vertical_minimum)
        self.root.update()

        self.assertGreater(self.tab.catalog_tree.winfo_height(), smaller_table_height)
        self.assertGreaterEqual(self.tab.catalog_tree.winfo_height(), PRODUCTS_PANEL_MIN_HEIGHT - 80)

    def test_horizontal_sash_can_expand_the_queue_panel(self) -> None:
        horizontal_minimum, _ = self.tab._horizontal_bounds()
        self.tab.horizontal_paned.sashpos(0, horizontal_minimum)
        self.root.update()
        expanded_queue_width = self.tab.queue_canvas.winfo_width()

        _, horizontal_maximum = self.tab._horizontal_bounds()
        self.tab.horizontal_paned.sashpos(0, horizontal_maximum)
        self.root.update()

        self.assertGreater(expanded_queue_width, self.tab.queue_canvas.winfo_width())

    def test_pane_positions_are_persisted_and_restored(self) -> None:
        horizontal_minimum, _ = self.tab._horizontal_bounds()
        vertical_minimum, _ = self.tab._vertical_bounds()
        self.tab.horizontal_paned.sashpos(0, horizontal_minimum + 20)
        self.tab.vertical_paned.sashpos(0, vertical_minimum + 20)
        self.root.update()
        state = self.tab.get_persisted_state()

        second_root = tk.Toplevel(self.root)
        second_root.geometry("1200x900+0+0")
        second_tab = CatalogTab(second_root, FakeConfigManager(), {})
        second_tab.apply_persisted_state(state)
        second_root.update_idletasks()
        second_root.update()

        self.assertEqual(second_tab.horizontal_paned.sashpos(0), state["horizontal_sash"])
        self.assertEqual(second_tab.vertical_paned.sashpos(0), state["vertical_sash"])
        second_root.destroy()

    def test_out_of_range_saved_positions_are_clamped_on_smaller_window(self) -> None:
        self.root.geometry("900x700+0+0")
        self.root.update()
        self.tab.apply_persisted_state({"horizontal_sash": 5000, "vertical_sash": 5000})
        self.root.update_idletasks()
        self.root.update()

        _, horizontal_maximum = self.tab._horizontal_bounds()
        _, vertical_maximum = self.tab._vertical_bounds()
        self.assertEqual(self.tab.horizontal_paned.sashpos(0), horizontal_maximum)
        self.assertEqual(self.tab.vertical_paned.sashpos(0), vertical_maximum)
        self.assertGreater(self.tab.queue_canvas.winfo_width(), 0)
        self.assertGreater(self.tab.catalog_tree.winfo_height(), 0)


@unittest.skipUnless(_tk_available(), "ambiente de teste sem display Tk disponível")
class CatalogMappingVisibilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = tk.Tk()
        self.root.geometry("1200x800+0+0")
        self.config = {
            "catalog_integrado": {
                "file_path": "catalogo-existente.xlsx",
                "selected_sheets": ["PRATA", "OURO"],
                "column_map": {
                    "codigo": "CODIGO",
                    "descricao": "DESCRICAO",
                    "preco": "PRECO",
                    "categoria": "SUBCATEGORIA",
                    "numeracao": "NUMERO",
                    "quantidade": "QTD",
                },
                "configuration_expanded": True,
            }
        }
        with (
            patch.object(CatalogTab, "_load_sheets"),
            patch.object(CatalogTab, "_try_initial_load"),
        ):
            self.tab = CatalogTab(self.root, FakeConfigManager(), self.config)
        self.tab._rebuild_sheet_checkboxes(["PRATA", "OURO"], {"PRATA"})
        self.root.update()

    def tearDown(self) -> None:
        self.root.destroy()

    def test_complete_existing_mapping_starts_collapsed_but_sheets_remain_visible(self) -> None:
        self.assertFalse(self.tab.settings.configuration_expanded)
        self.assertFalse(self.tab.mapping_details.winfo_ismapped())
        self.assertTrue(self.tab.config_scroll_area.winfo_ismapped())
        sheet_labels = [child.cget("text") for child in self.tab.sheets_container.winfo_children()]
        self.assertEqual(sheet_labels, ["PRATA", "OURO"])
        self.assertEqual(self.tab.toggle_config_button.cget("text"), "Mostrar mapeamento de colunas")

    def test_mapping_can_be_shown_and_hidden_without_losing_values_or_sheet_selection(self) -> None:
        original_map = dict(self.tab.settings.column_map)
        self.tab._on_toggle_configuration()
        self.root.update()
        self.assertTrue(self.tab.mapping_details.winfo_ismapped())
        self.assertEqual(self.tab.toggle_config_button.cget("text"), "Ocultar mapeamento de colunas")

        self.tab._on_toggle_configuration()
        self.root.update()

        self.assertFalse(self.tab.mapping_details.winfo_ismapped())
        self.assertEqual(self.tab.settings.column_map, original_map)
        self.assertTrue(self.tab.sheet_vars["PRATA"].get())
        self.assertFalse(self.tab.sheet_vars["OURO"].get())

    def test_combobox_visual_selection_is_cleared_without_changing_mapping(self) -> None:
        self.tab._on_toggle_configuration()
        combobox = self.tab.column_comboboxes["categoria"]
        combobox.selection_range(0, tk.END)
        expected = self.tab.column_vars["categoria"].get()

        combobox.event_generate("<<ComboboxSelected>>")
        self.root.update()

        self.assertEqual(self.tab.column_vars["categoria"].get(), expected)
        self.assertFalse(combobox.selection_present())

    def test_incomplete_new_install_keeps_mapping_open_for_initial_configuration(self) -> None:
        with (
            patch.object(CatalogTab, "_load_sheets"),
            patch.object(CatalogTab, "_try_initial_load"),
        ):
            new_tab = CatalogTab(tk.Toplevel(self.root), FakeConfigManager(), {})
        try:
            self.root.update()
            self.assertTrue(new_tab.settings.configuration_expanded)
            self.assertTrue(new_tab.mapping_details.winfo_ismapped())
        finally:
            new_tab._tk_root.destroy()


if __name__ == "__main__":
    unittest.main()
