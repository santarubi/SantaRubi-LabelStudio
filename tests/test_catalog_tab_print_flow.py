"""Integração da Fila de Impressão com o pipeline de impressão existente
(v2.5): PrintQueue -> PrintQueueAdapter -> ZplBuilder.build_row() ->
PrinterService.print_raw(). Nenhum teste aqui envia dados para uma
impressora real — build_row()/print_raw() são sempre mocados na fronteira
com o hardware (win32print).
"""

from __future__ import annotations

import tkinter as tk
import unittest
from typing import Any
from unittest.mock import patch

from core.catalog_datasource import DataSource
from core.catalog_repository import CatalogRepository
from core.catalog_service import CatalogService
from core.catalog_settings import CatalogSettings
from core.printer import PrinterService
from core.zpl_builder import ZplBuilder
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


class FakeThread:
    """Substitui threading.Thread nos testes: nunca inicia sozinha — o
    teste decide quando "a thread" roda, para poder inspecionar o estado
    da interface durante a impressão de forma determinística."""

    last_instance: "FakeThread | None" = None

    def __init__(self, target=None, args=(), kwargs=None, daemon=None):
        self.target = target
        self.args = args
        self.kwargs = kwargs or {}
        FakeThread.last_instance = self

    def start(self) -> None:
        pass

    def run_now(self) -> None:
        self.target(*self.args, **self.kwargs)


def _tk_available() -> bool:
    try:
        root = tk.Tk()
        root.destroy()
        return True
    except tk.TclError:
        return False


@unittest.skipUnless(_tk_available(), "ambiente de teste sem display Tk disponível")
class CatalogTabPrintFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        FakeThread.last_instance = None

        self.root = tk.Tk()
        self.root.geometry("1400x900+3000+3000")
        self.root.deiconify()

        self.config: dict[str, Any] = {}
        self.tab = CatalogTab(self.root, FakeConfigManager(), self.config)
        self.tab.printer_var.set("ELGIN-TESTE")

        source = FakeDataSource(
            {
                "DIP-15": [
                    {"CODIGO": "1001", "DESCRICAO": "Anel Coração", "PRECO": 59.9,
                     "CATEGORIA": "Aneis", "NUMERO": "16", "QTD": 2},
                    {"CODIGO": "1002", "DESCRICAO": "Brinco Flor", "PRECO": 89.9,
                     "CATEGORIA": "Brincos", "NUMERO": "", "QTD": 3},
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

    def tearDown(self) -> None:
        self.root.destroy()

    def _select_rows(self, *indices: int) -> None:
        self.tab.catalog_tree.selection_set([str(i) for i in indices])

    def _fill_queue(self) -> None:
        self._select_rows(0, 1)  # 1001 qtd=2, 1002 qtd=3 -> 5 etiquetas, 2 produtos
        self.tab._on_add_to_queue()

    # ------------------------------------------------------------------
    # Fila vazia
    # ------------------------------------------------------------------

    def test_printing_empty_queue_shows_friendly_message_and_does_not_start(self):
        with patch("ui.catalog_tab.messagebox.showinfo") as mock_showinfo, \
             patch("ui.catalog_tab.threading.Thread", FakeThread):
            self.tab._on_print_queue()
            mock_showinfo.assert_called_once()

        self.assertFalse(self.tab._printing_in_progress)
        self.assertIsNone(FakeThread.last_instance)

    def test_print_button_disabled_when_queue_is_empty(self):
        self.assertEqual(str(self.tab.print_queue_button["state"]), "disabled")

    # ------------------------------------------------------------------
    # Fila preenchida -> build_row() -> print_raw() (mocados)
    # ------------------------------------------------------------------

    def test_print_button_enabled_once_queue_has_items(self):
        self._fill_queue()
        self.assertEqual(str(self.tab.print_queue_button["state"]), "normal")

    def test_printing_converts_queue_via_adapter_and_calls_build_row_and_print_raw(self):
        self._fill_queue()
        FakeThread.last_instance = None

        with patch.object(ZplBuilder, "build_row", return_value="ZPL-MOCK") as mock_build_row, \
             patch.object(PrinterService, "print_raw") as mock_print_raw, \
             patch("ui.catalog_tab.log_print_job") as mock_log, \
             patch("ui.catalog_tab.messagebox.askyesno", return_value=False), \
             patch("ui.catalog_tab.threading.Thread", FakeThread):

            self.tab._on_print_queue()
            FakeThread.last_instance.run_now()
            self.root.update()

        mock_build_row.assert_called()
        total_labels_sent = sum(len(call.args[0]) for call in mock_build_row.call_args_list)
        self.assertEqual(total_labels_sent, 5, "5 etiquetas (1001 x2 + 1002 x3) deveriam ter sido enviadas")

        mock_print_raw.assert_called_with("ZPL-MOCK")
        mock_log.assert_called_once()

    def test_never_sends_anything_to_a_real_printer(self):
        """Confirma que PrinterService.print_raw (unica fronteira real com
        o hardware/win32print) esta sempre mocado nestes testes."""
        self._fill_queue()
        with patch.object(PrinterService, "print_raw") as mock_print_raw, \
             patch("ui.catalog_tab.log_print_job"), \
             patch("ui.catalog_tab.messagebox.askyesno", return_value=False), \
             patch("ui.catalog_tab.threading.Thread", FakeThread):
            self.tab._on_print_queue()
            FakeThread.last_instance.run_now()
            self.root.update()

        # se print_raw tivesse sido chamado de verdade (sem mock), teria
        # levantado RuntimeError ("Nenhuma impressora foi selecionada" ou
        # falha de win32print) muito antes de chegar aqui. 5 etiquetas / 3
        # colunas = 2 linhas -> 2 chamadas.
        self.assertEqual(mock_print_raw.call_count, 2)

    # ------------------------------------------------------------------
    # Botões desabilitados durante a impressão
    # ------------------------------------------------------------------

    def test_buttons_disabled_while_printing_in_progress(self):
        self._fill_queue()

        with patch.object(ZplBuilder, "build_row", return_value="ZPL-MOCK"), \
             patch.object(PrinterService, "print_raw"), \
             patch("ui.catalog_tab.log_print_job"), \
             patch("ui.catalog_tab.messagebox.askyesno", return_value=False), \
             patch("ui.catalog_tab.threading.Thread", FakeThread):

            self.tab._on_print_queue()

            self.assertTrue(self.tab._printing_in_progress)
            self.assertEqual(str(self.tab.print_queue_button["state"]), "disabled")
            self.assertEqual(str(self.tab.add_to_queue_button["state"]), "disabled")
            self.assertEqual(str(self.tab.remove_from_queue_button["state"]), "disabled")
            self.assertEqual(str(self.tab.clear_queue_button["state"]), "disabled")

            FakeThread.last_instance.run_now()
            self.root.update()

    def test_buttons_reenabled_after_printing_finishes(self):
        self._fill_queue()

        with patch.object(ZplBuilder, "build_row", return_value="ZPL-MOCK"), \
             patch.object(PrinterService, "print_raw"), \
             patch("ui.catalog_tab.log_print_job"), \
             patch("ui.catalog_tab.messagebox.askyesno", return_value=False), \
             patch("ui.catalog_tab.threading.Thread", FakeThread):

            self.tab._on_print_queue()
            FakeThread.last_instance.run_now()
            self.root.update()

        self.assertFalse(self.tab._printing_in_progress)
        self.assertEqual(str(self.tab.print_queue_button["state"]), "normal")
        self.assertEqual(str(self.tab.add_to_queue_button["state"]), "normal")
        self.assertEqual(str(self.tab.remove_from_queue_button["state"]), "normal")
        self.assertEqual(str(self.tab.clear_queue_button["state"]), "normal")

    def test_quantity_editing_disabled_while_printing(self):
        self._fill_queue()

        with patch.object(ZplBuilder, "build_row", return_value="ZPL-MOCK"), \
             patch.object(PrinterService, "print_raw"), \
             patch("ui.catalog_tab.log_print_job"), \
             patch("ui.catalog_tab.messagebox.askyesno", return_value=False), \
             patch("ui.catalog_tab.threading.Thread", FakeThread):

            self.tab._on_print_queue()

            card = self.tab.queue_items_frame.winfo_children()[0]
            quantity_row = card.winfo_children()[2]
            minus_button, quantidade_label, plus_button = quantity_row.winfo_children()
            self.assertEqual(str(minus_button["state"]), "disabled")
            self.assertEqual(str(plus_button["state"]), "disabled")

            FakeThread.last_instance.run_now()
            self.root.update()

    # ------------------------------------------------------------------
    # Sucesso: perguntas de confirmação e limpeza
    # ------------------------------------------------------------------

    def test_success_confirmed_and_clear_confirmed_empties_queue(self):
        self._fill_queue()

        with patch.object(ZplBuilder, "build_row", return_value="ZPL-MOCK"), \
             patch.object(PrinterService, "print_raw"), \
             patch("ui.catalog_tab.log_print_job"), \
             patch("ui.catalog_tab.messagebox.askyesno", return_value=True), \
             patch("ui.catalog_tab.threading.Thread", FakeThread):

            self.tab._on_print_queue()
            FakeThread.last_instance.run_now()
            self.root.update()

        self.assertTrue(self.tab.print_queue.is_empty())

    def test_success_confirmed_but_clear_declined_keeps_queue(self):
        self._fill_queue()
        answers = iter([True, False])  # sucesso? sim / limpar? nao

        with patch.object(ZplBuilder, "build_row", return_value="ZPL-MOCK"), \
             patch.object(PrinterService, "print_raw"), \
             patch("ui.catalog_tab.log_print_job"), \
             patch("ui.catalog_tab.messagebox.askyesno", side_effect=lambda *a, **k: next(answers)), \
             patch("ui.catalog_tab.threading.Thread", FakeThread):

            self.tab._on_print_queue()
            FakeThread.last_instance.run_now()
            self.root.update()

        self.assertEqual(self.tab.print_queue.count(), 2, "fila deveria ser mantida quando o usuario recusa limpar")

    def test_success_declined_keeps_queue_without_asking_to_clear(self):
        self._fill_queue()

        with patch.object(ZplBuilder, "build_row", return_value="ZPL-MOCK"), \
             patch.object(PrinterService, "print_raw"), \
             patch("ui.catalog_tab.log_print_job"), \
             patch("ui.catalog_tab.messagebox.askyesno", return_value=False) as mock_ask, \
             patch("ui.catalog_tab.threading.Thread", FakeThread):

            self.tab._on_print_queue()
            FakeThread.last_instance.run_now()
            self.root.update()

        self.assertEqual(mock_ask.call_count, 1, "nao deveria perguntar sobre limpar se a impressao nao foi confirmada")
        self.assertEqual(self.tab.print_queue.count(), 2)

    # ------------------------------------------------------------------
    # Erro: fila nunca é perdida nem limpa automaticamente
    # ------------------------------------------------------------------

    def test_error_during_printing_shows_friendly_message(self):
        self._fill_queue()

        with patch.object(ZplBuilder, "build_row", return_value="ZPL-MOCK"), \
             patch.object(PrinterService, "print_raw", side_effect=RuntimeError("Unable to open printer")), \
             patch("ui.catalog_tab.log_print_job") as mock_log, \
             patch("ui.catalog_tab.messagebox.showerror") as mock_showerror, \
             patch("ui.catalog_tab.threading.Thread", FakeThread):

            self.tab._on_print_queue()
            FakeThread.last_instance.run_now()
            self.root.update()

        mock_showerror.assert_called_once()
        mock_log.assert_called_once_with(2, 5, unittest.mock.ANY, "falha")

    def test_error_during_printing_never_loses_the_queue(self):
        self._fill_queue()

        with patch.object(ZplBuilder, "build_row", return_value="ZPL-MOCK"), \
             patch.object(PrinterService, "print_raw", side_effect=RuntimeError("Unable to open printer")), \
             patch("ui.catalog_tab.log_print_job"), \
             patch("ui.catalog_tab.messagebox.showerror"), \
             patch("ui.catalog_tab.threading.Thread", FakeThread):

            self.tab._on_print_queue()
            FakeThread.last_instance.run_now()
            self.root.update()

        self.assertEqual(self.tab.print_queue.count(), 2)
        self.assertEqual(self.tab.print_queue.total_labels(), 5)

    def test_error_reenables_buttons(self):
        self._fill_queue()

        with patch.object(ZplBuilder, "build_row", return_value="ZPL-MOCK"), \
             patch.object(PrinterService, "print_raw", side_effect=RuntimeError("boom")), \
             patch("ui.catalog_tab.log_print_job"), \
             patch("ui.catalog_tab.messagebox.showerror"), \
             patch("ui.catalog_tab.threading.Thread", FakeThread):

            self.tab._on_print_queue()
            FakeThread.last_instance.run_now()
            self.root.update()

        self.assertFalse(self.tab._printing_in_progress)
        self.assertEqual(str(self.tab.print_queue_button["state"]), "normal")

    def test_missing_printer_shows_warning_and_does_not_start(self):
        self._fill_queue()
        self.tab.printer_var.set("")

        with patch("ui.catalog_tab.messagebox.showwarning") as mock_showwarning, \
             patch("ui.catalog_tab.threading.Thread", FakeThread):
            FakeThread.last_instance = None
            self.tab._on_print_queue()
            mock_showwarning.assert_called_once()

        self.assertIsNone(FakeThread.last_instance)
        self.assertFalse(self.tab._printing_in_progress)


if __name__ == "__main__":
    unittest.main()
