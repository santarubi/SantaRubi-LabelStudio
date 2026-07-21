"""Edição direta da quantidade na Fila de Impressão (v2.4).

Cobre: botões [+]/[-] (PrintQueue.increment/decrement), edição via duplo
clique + Entry (PrintQueue.update_quantity, com restauração do valor
anterior para entradas inválidas/vazias), atalhos DEL (remover selecionado)
e Ctrl+A (selecionar tudo na tabela principal), e sincronização automática
dos totais — tudo sempre lido/escrito exclusivamente através do PrintQueue.
"""

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
class CatalogTabQueueEditingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = tk.Tk()
        # Posicionada fora da area visivel (em vez de root.withdraw()): uma
        # janela "withdrawn" (ou minuscula) no Windows nunca recebe foco
        # real de teclado nem deixa seus widgets "viewable", o que impede
        # eventos sinteticos como <Return> de serem entregues ao Entry de
        # edicao — por isso usa um tamanho realista, so' deslocado da tela.
        self.root.geometry("1400x900+3000+3000")
        self.root.deiconify()

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

        self.tab.service = service
        self.tab.catalog_filtered_products = service.apply_filters()
        self.tab._load_catalog_table()

        self.product_a = self.tab.catalog_filtered_products[0]  # 1001, qtd padrao 5
        self.product_b = self.tab.catalog_filtered_products[1]  # 1002, qtd padrao 2

    def tearDown(self) -> None:
        self.root.destroy()

    def _select_rows(self, *indices: int) -> None:
        self.tab.catalog_tree.selection_set([str(i) for i in indices])

    def _add_both_to_queue(self) -> None:
        self._select_rows(0, 1)
        self.tab._on_add_to_queue()

    def _find_card(self, codigo: str) -> tk.Frame:
        for card in self.tab.queue_items_frame.winfo_children():
            codigo_label = card.winfo_children()[1]
            if codigo_label.cget("text") == codigo:
                return card
        raise AssertionError(f"cartão para o código {codigo} não encontrado")

    def _quantity_widgets(self, codigo: str) -> tuple[tk.Frame, tk.Label]:
        card = self._find_card(codigo)
        quantity_row = card.winfo_children()[2]
        quantity_label = quantity_row.winfo_children()[1]
        return quantity_row, quantity_label

    # ------------------------------------------------------------------
    # [+] / [-]
    # ------------------------------------------------------------------

    def test_increment_button_increases_quantity(self):
        self._add_both_to_queue()
        self.tab._on_increment_queue_item(self.product_a.codigo)

        item = self.tab.print_queue.find(self.product_a)
        self.assertEqual(item.quantity, 6)

    def test_increment_updates_totals_immediately(self):
        self._add_both_to_queue()
        self.tab._on_increment_queue_item(self.product_a.codigo)

        self.assertEqual(self.tab.queue_total_var.get(), "Total de etiquetas: 8")
        self.assertEqual(self.tab.queue_count_var.get(), "Produtos na fila: 2")

    def test_decrement_button_decreases_quantity(self):
        self._add_both_to_queue()
        self.tab._on_decrement_queue_item(self.product_a.codigo)

        item = self.tab.print_queue.find(self.product_a)
        self.assertEqual(item.quantity, 4)

    def test_decrement_never_goes_below_one(self):
        self._add_both_to_queue()
        for _ in range(10):
            self.tab._on_decrement_queue_item(self.product_b.codigo)  # comeca em 2

        item = self.tab.print_queue.find(self.product_b)
        self.assertEqual(item.quantity, 1)

    # ------------------------------------------------------------------
    # Edição direta (duplo clique -> Entry)
    # ------------------------------------------------------------------

    def test_double_click_replaces_label_with_entry_prefilled(self):
        self._add_both_to_queue()
        quantity_row, quantity_label = self._quantity_widgets(self.product_a.codigo)

        self.tab._on_start_edit_quantity(self.product_a.codigo, quantity_row, quantity_label)

        entries = [w for w in quantity_row.winfo_children() if isinstance(w, tk.Entry)]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].get(), "5")

    def test_enter_commits_new_quantity(self):
        self._add_both_to_queue()
        quantity_row, quantity_label = self._quantity_widgets(self.product_a.codigo)
        self.tab._on_start_edit_quantity(self.product_a.codigo, quantity_row, quantity_label)
        entry = [w for w in quantity_row.winfo_children() if isinstance(w, tk.Entry)][0]

        entry.delete(0, "end")
        entry.insert(0, "9")
        entry.focus_force()
        self.root.update()
        entry.event_generate("<Return>")
        self.root.update()

        self.assertEqual(self.tab.print_queue.find(self.product_a).quantity, 9)

    def test_focus_out_commits_new_quantity(self):
        self._add_both_to_queue()
        quantity_row, quantity_label = self._quantity_widgets(self.product_a.codigo)
        self.tab._on_start_edit_quantity(self.product_a.codigo, quantity_row, quantity_label)
        entry = [w for w in quantity_row.winfo_children() if isinstance(w, tk.Entry)][0]

        entry.delete(0, "end")
        entry.insert(0, "7")
        entry.event_generate("<FocusOut>")
        self.root.update()

        self.assertEqual(self.tab.print_queue.find(self.product_a).quantity, 7)

    def test_invalid_text_restores_previous_value(self):
        self._add_both_to_queue()
        self.tab._commit_quantity_edit(self.product_a.codigo, "abc")
        self.assertEqual(self.tab.print_queue.find(self.product_a).quantity, 5)

    def test_empty_value_restores_previous_value(self):
        self._add_both_to_queue()
        self.tab._commit_quantity_edit(self.product_a.codigo, "   ")
        self.assertEqual(self.tab.print_queue.find(self.product_a).quantity, 5)

    def test_decimal_value_is_truncated(self):
        self._add_both_to_queue()
        self.tab._commit_quantity_edit(self.product_a.codigo, "3.9")
        self.assertEqual(self.tab.print_queue.find(self.product_a).quantity, 3)

    def test_negative_value_is_clamped_to_one(self):
        self._add_both_to_queue()
        self.tab._commit_quantity_edit(self.product_a.codigo, "-4")
        self.assertEqual(self.tab.print_queue.find(self.product_a).quantity, 1)

    def test_committing_invalid_value_never_raises(self):
        self._add_both_to_queue()
        try:
            self.tab._commit_quantity_edit(self.product_a.codigo, "###")
        except Exception as exc:  # pragma: no cover - a falha e' o proprio teste
            self.fail(f"_commit_quantity_edit nao deveria levantar excecao: {exc}")

    def test_edit_redraws_from_print_queue_only(self):
        """Depois de confirmar, o cartao exibido deve vir de um redesenho
        completo (_refresh_queue_view), nao de uma atualizacao manual do
        widget antigo — o Entry usado na edicao deixa de existir."""
        self._add_both_to_queue()
        quantity_row, quantity_label = self._quantity_widgets(self.product_a.codigo)
        self.tab._on_start_edit_quantity(self.product_a.codigo, quantity_row, quantity_label)

        self.tab._commit_quantity_edit(self.product_a.codigo, "8")

        _, new_quantity_label = self._quantity_widgets(self.product_a.codigo)
        self.assertEqual(new_quantity_label.cget("text"), "8")

    # ------------------------------------------------------------------
    # Atalhos: DEL e Ctrl+A
    # ------------------------------------------------------------------

    def test_delete_key_binding_registered_on_each_card(self):
        self._add_both_to_queue()
        card = self._find_card(self.product_a.codigo)
        self.assertTrue(card.bind("<Delete>"), "cartao deveria ter um binding para <Delete>")

    def test_delete_removes_the_targeted_item(self):
        self._add_both_to_queue()
        self.tab._on_delete_key(self.product_a.codigo)

        self.assertFalse(self.tab.print_queue.contains(self.product_a))
        self.assertTrue(self.tab.print_queue.contains(self.product_b))

    def test_delete_updates_totals(self):
        self._add_both_to_queue()
        self.tab._on_delete_key(self.product_a.codigo)

        self.assertEqual(self.tab.queue_count_var.get(), "Produtos na fila: 1")
        self.assertEqual(self.tab.queue_total_var.get(), "Total de etiquetas: 2")

    def test_ctrl_a_binding_registered_on_catalog_tree(self):
        self.assertTrue(self.tab.catalog_tree.bind("<Control-a>"))

    def test_ctrl_a_selects_all_products_in_main_table(self):
        result = self.tab._on_select_all_products_shortcut()

        all_ids = set(self.tab.catalog_tree.get_children())
        self.assertEqual(set(self.tab.catalog_tree.selection()), all_ids)
        self.assertEqual(result, "break")


if __name__ == "__main__":
    unittest.main()
