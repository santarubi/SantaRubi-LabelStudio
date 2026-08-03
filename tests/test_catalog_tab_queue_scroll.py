"""Correção de UX (v1.1): alterar a quantidade de um item da Fila de
Impressão (+/- ou edição direta) não pode mais fazer a lista voltar ao
topo. Antes, qualquer mudança de quantidade disparava um redesenho
completo dos cartões (_refresh_queue_view -> _render_queue_cards, que
destrói e recria todos os widgets), o que reiniciava a posição da
scrollbar do Canvas. Agora só o rótulo do item alterado é atualizado
(ver CatalogTab._update_card_quantity_display/_end_edit_quantity) — os
demais cartões, a posição do scroll, a seleção e o foco não são tocados.

Não cobre a lógica de negócio da fila (core/print_queue.py já tem seus
próprios testes) nem os fluxos de edição já cobertos em
tests/test_catalog_tab_queue_editing.py — só a preservação do estado
visual da lista."""

from __future__ import annotations

import tkinter as tk
import unittest
from typing import Any

from core.catalog_datasource import DataSource
from core.catalog_repository import CatalogRepository
from core.catalog_service import CatalogService
from core.catalog_settings import CatalogSettings
from ui.catalog_tab import CatalogTab

PRODUCT_COUNT = 40


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
class QueueScrollSelectionFocusPreservedTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = tk.Tk()
        # Tamanho realista e fora da área visível (não withdraw — uma
        # janela escondida não recebe foco real de teclado nem deixa seus
        # widgets "viewable", quebrando os testes de foco abaixo).
        self.root.geometry("1400x700+3000+3000")
        self.root.deiconify()

        self.config: dict[str, Any] = {}
        self.tab = CatalogTab(self.root, FakeConfigManager(), self.config)

        rows = [
            {
                "CODIGO": f"{1000 + i}",
                "DESCRICAO": f"Produto {i:02d}",
                "PRECO": 10.0 + i,
                "CATEGORIA": "Aneis",
                "NUMERO": "16",
                "QTD": 1,
            }
            for i in range(PRODUCT_COUNT)
        ]
        source = FakeDataSource({"DIP-15": rows})
        settings = CatalogSettings(selected_sheets=["DIP-15"], column_map=COLUMN_MAP)
        repository = CatalogRepository(source)
        service = CatalogService(repository, settings)
        service.reload()
        self.tab.service = service
        self.tab.catalog_filtered_products = service.apply_filters()
        self.tab._load_catalog_table()

        # Adiciona todos os produtos à fila, o suficiente para exigir
        # rolagem real dentro do Canvas.
        self.tab.catalog_tree.selection_set(
            [str(i) for i in range(len(self.tab.catalog_filtered_products))]
        )
        self.tab._on_add_to_queue()
        self.root.update_idletasks()
        self.root.update()

        self.codigos_em_ordem = [item.codigo for item in [p for p in self.tab.catalog_filtered_products]]

        # Rola até a metade da lista e guarda a posição para comparar depois.
        self.tab.queue_canvas.update_idletasks()
        self.tab.queue_canvas.yview_moveto(0.5)
        self.root.update()
        self.scroll_before = self.tab.queue_canvas.yview()
        self.assertGreater(
            self.scroll_before[0], 0.0, "pré-condição: a fila precisa estar rolada para o teste fazer sentido"
        )

    def tearDown(self) -> None:
        self.root.destroy()

    def _middle_codigo(self) -> str:
        """Um código que não está no topo nem no fim da fila."""
        return self.tab.print_queue.to_list()[PRODUCT_COUNT // 2].product.codigo

    # ------------------------------------------------------------------
    # Scrollbar
    # ------------------------------------------------------------------

    def test_incrementing_a_middle_item_keeps_scroll_position(self) -> None:
        codigo = self._middle_codigo()

        self.tab._on_increment_queue_item(codigo)
        self.root.update()

        self.assertEqual(self.tab.queue_canvas.yview(), self.scroll_before)

    def test_decrementing_a_middle_item_keeps_scroll_position(self) -> None:
        codigo = self._middle_codigo()
        self.tab._on_increment_queue_item(codigo)  # garante quantidade >= 2 antes de decrementar
        self.root.update()
        scroll_after_setup = self.tab.queue_canvas.yview()

        self.tab._on_decrement_queue_item(codigo)
        self.root.update()

        self.assertEqual(self.tab.queue_canvas.yview(), scroll_after_setup)

    def test_committing_a_direct_edit_keeps_scroll_position(self) -> None:
        codigo = self._middle_codigo()

        self.tab._commit_quantity_edit(codigo, "42")

        self.assertEqual(self.tab.queue_canvas.yview(), self.scroll_before)

    def test_several_consecutive_quantity_changes_never_reset_scroll_to_top(self) -> None:
        codigos = [item.product.codigo for item in self.tab.print_queue.to_list()[10:20]]

        for codigo in codigos:
            self.tab._on_increment_queue_item(codigo)
            self.root.update()
            self.assertEqual(
                self.tab.queue_canvas.yview(),
                self.scroll_before,
                f"scroll voltou ao topo depois de incrementar {codigo}",
            )

    # ------------------------------------------------------------------
    # Seleção e foco
    # ------------------------------------------------------------------

    def test_selection_is_preserved_after_incrementing_another_item(self) -> None:
        selected_codigo = self.tab.print_queue.to_list()[3].product.codigo
        self.tab._on_select_queue_card(selected_codigo)
        self.root.update()

        other_codigo = self._middle_codigo()
        self.tab._on_increment_queue_item(other_codigo)

        self.assertEqual(self.tab._selected_queue_codigo, selected_codigo)

    def test_card_widget_identity_is_preserved_after_incrementing(self) -> None:
        """Prova de que o cartão não foi destruído/recriado — mesma
        instância de widget antes e depois, o que por sua vez garante que
        o foco de teclado (ligado ao widget) nunca é perdido."""
        codigo = self._middle_codigo()
        card_before = self.tab._queue_card_widgets[codigo]["card"]

        self.tab._on_increment_queue_item(codigo)

        card_after = self.tab._queue_card_widgets[codigo]["card"]
        self.assertIs(card_after, card_before)

    def test_keyboard_focus_stays_on_the_same_widget_after_incrementing(self) -> None:
        codigo = self._middle_codigo()
        card = self.tab._queue_card_widgets[codigo]["card"]
        self.root.focus_force()
        card.focus_set()
        self.root.update()
        self.assertEqual(str(self.root.focus_get()), str(card))

        self.tab._on_increment_queue_item(codigo)
        self.root.update()

        self.assertEqual(str(self.root.focus_get()), str(card))

    def test_other_cards_are_not_destroyed_by_an_unrelated_increment(self) -> None:
        codigo = self._middle_codigo()
        other_codigo = self.tab.print_queue.to_list()[0].product.codigo
        other_card_before = self.tab._queue_card_widgets[other_codigo]["card"]

        self.tab._on_increment_queue_item(codigo)

        other_card_after = self.tab._queue_card_widgets[other_codigo]["card"]
        self.assertIs(other_card_after, other_card_before)
        self.assertTrue(other_card_after.winfo_exists())

    # ------------------------------------------------------------------
    # Ordenação
    # ------------------------------------------------------------------

    def test_order_of_items_is_unchanged_after_quantity_edits(self) -> None:
        order_before = [item.product.codigo for item in self.tab.print_queue.to_list()]

        for codigo in order_before[5:15]:
            self.tab._on_increment_queue_item(codigo)
        self.tab._commit_quantity_edit(order_before[20], "99")

        order_after = [item.product.codigo for item in self.tab.print_queue.to_list()]
        self.assertEqual(order_after, order_before)


if __name__ == "__main__":
    unittest.main()
