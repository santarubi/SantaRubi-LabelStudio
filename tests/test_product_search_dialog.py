import tkinter as tk
import unittest
from typing import Any
from unittest.mock import patch

from app.api.exceptions import JueriConnectionError
from app.api.product import Product
from app.api.products import ProductSearchResult
from ui.product_search_dialog import ProductSearchDialog


class FakeProductsAPI:
    def __init__(
        self,
        result: ProductSearchResult | None = None,
        error: Exception | None = None,
        multi_result: list[Product] | None = None,
        all_pages_result: list[Product] | None = None,
    ) -> None:
        self.result = result
        self.error = error
        self.multi_result = multi_result
        self.all_pages_result = all_pages_result
        self.calls: list[dict[str, Any]] = []
        self.multi_calls: list[dict[str, Any]] = []
        self.all_pages_calls: list[dict[str, Any]] = []

    def search_products(self, **kwargs: Any) -> ProductSearchResult:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.result if self.result is not None else ProductSearchResult(products=[])

    def search_multiple_products(self, codes: list[str], **extra_filters: Any) -> list[Product]:
        self.multi_calls.append({"codes": list(codes), **extra_filters})
        if self.error is not None:
            raise self.error
        return self.multi_result if self.multi_result is not None else []

    def search_all_pages(self, **filters: Any) -> list[Product]:
        self.all_pages_calls.append(filters)
        if self.error is not None:
            raise self.error
        return self.all_pages_result if self.all_pages_result is not None else []


class SequencedFakeProductsAPI:
    """Retorna uma resposta diferente a cada chamada, na ordem dada —
    usado só onde o teste precisa que a 1ª chamada (carga automática) se
    comporte diferente da 2ª (busca manual)."""

    def __init__(self, responses: list[ProductSearchResult | Exception]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def search_products(self, **kwargs: Any) -> ProductSearchResult:
        self.calls.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def build_product(**overrides: Any) -> Product:
    fields = {
        "id": 1,
        "descricao": "Anel de ouro 18k",
        "referencia": "totam",
        "codigo_barras": "30856875",
        "peso": 3.33,
    }
    fields.update(overrides)
    product = Product.from_api(fields)
    return product


class ProductSearchDialogTests(unittest.TestCase):
    def setUp(self) -> None:
        try:
            self.root = tk.Tk()
            self.root.withdraw()
        except tk.TclError as exc:
            self.skipTest(f"Sem display disponível para testes de Tkinter: {exc}")

    def _build_dialog(self, products_api, on_add_selected=None) -> ProductSearchDialog:
        dialog = ProductSearchDialog(self.root, products_api, on_add_selected=on_add_selected)

        def _safe_destroy() -> None:
            try:
                if dialog.winfo_exists():
                    dialog.destroy()
            except tk.TclError:
                pass

        self.addCleanup(_safe_destroy)
        return dialog

    def tearDown(self) -> None:
        self.root.destroy()

    def test_opening_the_dialog_loads_first_page_without_a_search_filter(self):
        product = build_product()
        api = FakeProductsAPI(result=ProductSearchResult(products=[product]))

        dialog = self._build_dialog(api)

        self.assertEqual(api.calls, [{"search": None}])
        children = dialog.results_tree.get_children()
        self.assertEqual(len(children), 1)
        self.assertEqual(dialog.status_var.get(), "1 produto(s) encontrado(s).")

    def test_opening_the_dialog_with_no_products_shows_message(self):
        api = FakeProductsAPI(result=ProductSearchResult(products=[]))

        dialog = self._build_dialog(api)

        self.assertEqual(api.calls, [{"search": None}])
        self.assertEqual(dialog.results_tree.get_children(), ())
        self.assertEqual(dialog.status_var.get(), "Nenhum produto encontrado.")

    def test_opening_the_dialog_with_api_error_shows_message(self):
        api = FakeProductsAPI(error=JueriConnectionError("Sem conexão com a internet."))

        dialog = self._build_dialog(api)

        self.assertIn("Sem conexão com a internet.", dialog.status_var.get())
        self.assertEqual(dialog.results_tree.get_children(), ())

    def test_refresh_button_exists_and_reruns_current_search_immediately(self):
        api = FakeProductsAPI(result=ProductSearchResult(products=[]))
        dialog = self._build_dialog(api)
        api.calls.clear()

        dialog.search_var.set("anel")  # só agenda via debounce, não executa
        dialog._on_refresh()

        self.assertEqual(api.calls, [{"search": "anel"}])

    def test_refresh_cancels_pending_debounced_search(self):
        api = FakeProductsAPI(result=ProductSearchResult(products=[]))
        dialog = self._build_dialog(api)

        dialog.search_var.set("anel")
        self.assertIsNotNone(dialog._debounce_job)

        dialog._on_refresh()

        self.assertIsNone(dialog._debounce_job)

    def test_run_search_populates_treeview_with_results(self):
        varejo_price = {"id": 1, "nome": "Varejo", "pivot": {"preco": 49.99}}
        product = build_product(tipo_preco=[varejo_price])
        api = FakeProductsAPI(result=ProductSearchResult(products=[product]))
        dialog = self._build_dialog(api)
        api.calls.clear()

        dialog.search_var.set("anel")
        dialog._run_search()

        self.assertEqual(api.calls, [{"search": "anel"}])
        children = dialog.results_tree.get_children()
        self.assertEqual(len(children), 1)
        values = dialog.results_tree.item(children[0], "values")
        self.assertEqual(values, ("30856875", "Anel de ouro 18k", "R$ 49.99", "3.33 g"))
        self.assertEqual(dialog.status_var.get(), "1 produto(s) encontrado(s).")

    def test_run_search_with_no_results_shows_message(self):
        api = FakeProductsAPI(result=ProductSearchResult(products=[]))
        dialog = self._build_dialog(api)

        dialog.search_var.set("inexistente")
        dialog._run_search()

        self.assertEqual(dialog.results_tree.get_children(), ())
        self.assertEqual(dialog.status_var.get(), "Nenhum produto encontrado.")

    def test_run_search_error_after_successful_initial_load_clears_results(self):
        product = build_product()
        api = SequencedFakeProductsAPI(
            [
                ProductSearchResult(products=[product]),
                JueriConnectionError("Sem conexão com a internet."),
            ]
        )
        dialog = self._build_dialog(api)
        self.assertEqual(len(dialog.results_tree.get_children()), 1)

        dialog.search_var.set("anel")
        dialog._run_search()

        self.assertEqual(dialog.results_tree.get_children(), ())
        self.assertIn("Sem conexão com a internet.", dialog.status_var.get())

    def test_typing_debounces_and_cancels_previous_pending_search(self):
        api = FakeProductsAPI()
        dialog = self._build_dialog(api)

        with patch.object(dialog, "after", wraps=dialog.after) as mock_after, patch.object(
            dialog, "after_cancel", wraps=dialog.after_cancel
        ) as mock_after_cancel:
            dialog._on_search_changed()
            dialog._on_search_changed()

            self.assertEqual(mock_after.call_count, 2)
            mock_after_cancel.assert_called_once()

        if dialog._debounce_job is not None:
            dialog.after_cancel(dialog._debounce_job)

    def test_single_code_search_uses_search_products_not_multiple(self):
        api = FakeProductsAPI(result=ProductSearchResult(products=[]))
        dialog = self._build_dialog(api)
        api.calls.clear()

        dialog.search_var.set("181021")
        dialog._run_search()

        self.assertEqual(api.calls, [{"search": "181021"}])
        self.assertEqual(api.multi_calls, [])

    def test_comma_separated_codes_use_search_multiple_products(self):
        products = [
            build_product(id=1, codigo_barras="181021", descricao="ALIANCA"),
            build_product(id=2, codigo_barras="181050", descricao="ANEL"),
        ]
        api = FakeProductsAPI(multi_result=products)
        dialog = self._build_dialog(api)

        dialog.search_var.set("181021,181050")
        dialog._run_search()

        self.assertEqual(api.multi_calls, [{"codes": ["181021", "181050"]}])
        self.assertEqual(api.calls, [{"search": None}])  # só a carga automática inicial
        children = dialog.results_tree.get_children()
        self.assertEqual(len(children), 2)
        self.assertEqual(dialog.status_var.get(), "2 produto(s) encontrado(s).")

    def test_space_separated_codes_use_search_multiple_products(self):
        products = [build_product(id=1, codigo_barras="181021")]
        api = FakeProductsAPI(multi_result=products)
        dialog = self._build_dialog(api)

        dialog.search_var.set("181021 181050")
        dialog._run_search()

        self.assertEqual(api.multi_calls, [{"codes": ["181021", "181050"]}])

    def test_multi_word_description_search_does_not_use_search_multiple_products(self):
        api = FakeProductsAPI(result=ProductSearchResult(products=[]))
        dialog = self._build_dialog(api)
        api.calls.clear()

        dialog.search_var.set("anel ouro")
        dialog._run_search()

        self.assertEqual(api.calls, [{"search": "anel ouro"}])
        self.assertEqual(api.multi_calls, [])

    def test_today_button_fills_both_dates_and_searches_with_iso_dates(self):
        from datetime import date

        api = FakeProductsAPI(all_pages_result=[])
        dialog = self._build_dialog(api)

        dialog._on_quick_today()

        expected = date.today().isoformat()
        self.assertEqual(dialog.data_inicial_var.get(), date.today().strftime("%d/%m/%Y"))
        self.assertEqual(dialog.data_final_var.get(), date.today().strftime("%d/%m/%Y"))
        self.assertEqual(
            api.all_pages_calls[-1],
            {"search": None, "data_criacao_inicial": expected, "data_criacao_final": expected},
        )

    def test_yesterday_button_fills_both_dates_and_searches_with_iso_dates(self):
        from datetime import date, timedelta

        api = FakeProductsAPI(all_pages_result=[])
        dialog = self._build_dialog(api)

        dialog._on_quick_yesterday()

        expected = (date.today() - timedelta(days=1)).isoformat()
        self.assertEqual(
            api.all_pages_calls[-1],
            {"search": None, "data_criacao_inicial": expected, "data_criacao_final": expected},
        )

    def test_clear_dates_button_removes_date_filter(self):
        api = FakeProductsAPI(all_pages_result=[], result=ProductSearchResult(products=[]))
        dialog = self._build_dialog(api)
        dialog._on_quick_today()

        dialog._on_clear_dates()

        self.assertEqual(dialog.data_inicial_var.get(), "")
        self.assertEqual(dialog.data_final_var.get(), "")
        self.assertEqual(api.calls[-1], {"search": None})  # voltou ao caminho sem filtro de data

    def test_only_data_inicial_filled_sends_only_that_param(self):
        api = FakeProductsAPI(all_pages_result=[])
        dialog = self._build_dialog(api)

        dialog.data_inicial_var.set("20/07/2026")
        dialog._on_refresh()

        self.assertEqual(api.all_pages_calls[-1], {"search": None, "data_criacao_inicial": "2026-07-20"})

    def test_both_dates_filled_sends_both_params(self):
        api = FakeProductsAPI(all_pages_result=[])
        dialog = self._build_dialog(api)

        dialog.data_inicial_var.set("20/07/2026")
        dialog.data_final_var.set("23/07/2026")
        dialog._on_refresh()

        self.assertEqual(
            api.all_pages_calls[-1],
            {"search": None, "data_criacao_inicial": "2026-07-20", "data_criacao_final": "2026-07-23"},
        )

    def test_invalid_date_shows_friendly_error_and_does_not_call_api(self):
        api = FakeProductsAPI(all_pages_result=[])
        dialog = self._build_dialog(api)
        calls_before = len(api.all_pages_calls)

        dialog.data_inicial_var.set("31/13/2026")
        dialog._on_refresh()

        self.assertEqual(len(api.all_pages_calls), calls_before)
        self.assertIn("inválida", dialog.status_var.get())
        self.assertEqual(dialog.results_tree.get_children(), ())

    def test_final_date_before_inicial_shows_friendly_error_and_does_not_call_api(self):
        api = FakeProductsAPI(all_pages_result=[])
        dialog = self._build_dialog(api)
        calls_before = len(api.all_pages_calls)

        dialog.data_inicial_var.set("23/07/2026")
        dialog.data_final_var.set("20/07/2026")
        dialog._on_refresh()

        self.assertEqual(len(api.all_pages_calls), calls_before)
        self.assertIn("Data Final", dialog.status_var.get())

    def test_description_search_combined_with_date_uses_search_all_pages(self):
        product = build_product(descricao="Anel de ouro")
        api = FakeProductsAPI(all_pages_result=[product])
        dialog = self._build_dialog(api)

        dialog.search_var.set("anel")
        dialog.data_inicial_var.set("23/07/2026")
        dialog.data_final_var.set("23/07/2026")
        dialog._on_refresh()

        self.assertEqual(
            api.all_pages_calls[-1],
            {"search": "anel", "data_criacao_inicial": "2026-07-23", "data_criacao_final": "2026-07-23"},
        )
        self.assertEqual(len(dialog.results_tree.get_children()), 1)

    def test_multi_code_search_combined_with_date_uses_search_multiple_products_with_date_params(self):
        products = [build_product(id=1, codigo_barras="181021")]
        api = FakeProductsAPI(multi_result=products)
        dialog = self._build_dialog(api)

        dialog.search_var.set("181021,181050")
        dialog.data_inicial_var.set("23/07/2026")
        dialog.data_final_var.set("23/07/2026")
        dialog._on_refresh()

        self.assertEqual(
            api.multi_calls[-1],
            {
                "codes": ["181021", "181050"],
                "data_criacao_inicial": "2026-07-23",
                "data_criacao_final": "2026-07-23",
            },
        )

    def test_results_tree_allows_multiple_selection(self):
        api = FakeProductsAPI(result=ProductSearchResult(products=[]))
        dialog = self._build_dialog(api)
        self.assertEqual(str(dialog.results_tree["selectmode"]), "extended")

    def test_add_selected_with_nothing_selected_shows_friendly_message_and_does_not_call_callback(self):
        added_batches: list[list[Product]] = []
        api = FakeProductsAPI(result=ProductSearchResult(products=[build_product()]))
        dialog = self._build_dialog(api, on_add_selected=added_batches.append)

        dialog._on_add_selected()

        self.assertEqual(added_batches, [])
        self.assertEqual(dialog.status_var.get(), "Nenhum produto selecionado.")
        self.assertTrue(dialog.winfo_exists(), "dialogo nao deveria fechar")

    def test_add_selected_with_one_product_calls_callback_with_a_list(self):
        added_batches: list[list[Product]] = []
        product = build_product()
        api = FakeProductsAPI(result=ProductSearchResult(products=[product]))
        dialog = self._build_dialog(api, on_add_selected=added_batches.append)

        dialog.results_tree.selection_set(["0"])
        dialog._on_add_selected()

        self.assertEqual(added_batches, [[product]])

    def test_add_selected_with_multiple_products_sends_all_of_them_in_one_call(self):
        added_batches: list[list[Product]] = []
        products = [
            build_product(id=1, codigo_barras="181021"),
            build_product(id=2, codigo_barras="181050"),
            build_product(id=3, codigo_barras="181110"),
        ]
        api = FakeProductsAPI(result=ProductSearchResult(products=products))
        dialog = self._build_dialog(api, on_add_selected=added_batches.append)

        dialog.results_tree.selection_set(["0", "2"])  # pula o do meio de proposito
        dialog._on_add_selected()

        self.assertEqual(added_batches, [[products[0], products[2]]])

    def test_dialog_does_not_close_after_adding_selected(self):
        api = FakeProductsAPI(result=ProductSearchResult(products=[build_product()]))
        dialog = self._build_dialog(api, on_add_selected=lambda _products: None)

        dialog.results_tree.selection_set(["0"])
        dialog._on_add_selected()

        self.assertTrue(dialog.winfo_exists(), "usuario deve poder continuar pesquisando e adicionando mais")
        self.assertIn("adicionado", dialog.status_var.get())

    def test_adding_selected_clears_the_selection_afterwards(self):
        api = FakeProductsAPI(result=ProductSearchResult(products=[build_product()]))
        dialog = self._build_dialog(api, on_add_selected=lambda _products: None)

        dialog.results_tree.selection_set(["0"])
        dialog._on_add_selected()

        self.assertEqual(dialog.results_tree.selection(), ())

    def test_select_all_button_selects_every_result_row(self):
        products = [build_product(id=i, codigo_barras=str(i)) for i in range(3)]
        api = FakeProductsAPI(result=ProductSearchResult(products=products))
        dialog = self._build_dialog(api)

        dialog._on_select_all()

        self.assertEqual(len(dialog.results_tree.selection()), 3)

    def test_clear_selection_button_deselects_everything(self):
        products = [build_product(id=i, codigo_barras=str(i)) for i in range(3)]
        api = FakeProductsAPI(result=ProductSearchResult(products=products))
        dialog = self._build_dialog(api)
        dialog._on_select_all()

        dialog._on_clear_selection()

        self.assertEqual(dialog.results_tree.selection(), ())

    def test_selection_count_label_updates_on_selection_change(self):
        products = [build_product(id=i, codigo_barras=str(i)) for i in range(3)]
        api = FakeProductsAPI(result=ProductSearchResult(products=products))
        dialog = self._build_dialog(api)

        self.assertEqual(dialog.selection_count_var.get(), "0 produto(s) selecionado(s).")

        dialog._on_select_all()
        self.assertEqual(dialog.selection_count_var.get(), "3 produto(s) selecionado(s).")

        dialog._on_clear_selection()
        self.assertEqual(dialog.selection_count_var.get(), "0 produto(s) selecionado(s).")

    def test_double_click_adds_only_that_product_without_closing(self):
        added_batches: list[list[Product]] = []
        products = [build_product(id=1, codigo_barras="181021"), build_product(id=2, codigo_barras="181050")]
        api = FakeProductsAPI(result=ProductSearchResult(products=products))
        dialog = self._build_dialog(api, on_add_selected=added_batches.append)

        dialog.results_tree.selection_set(["1"])
        dialog._on_double_click_add()

        self.assertEqual(added_batches, [[products[1]]])
        self.assertTrue(dialog.winfo_exists())

    def test_double_click_with_no_selection_does_nothing(self):
        added_batches: list[list[Product]] = []
        api = FakeProductsAPI(result=ProductSearchResult(products=[build_product()]))
        dialog = self._build_dialog(api, on_add_selected=added_batches.append)

        dialog._on_double_click_add()

        self.assertEqual(added_batches, [])

    def test_works_without_a_callback_configured(self):
        """on_add_selected é opcional — não deve lançar exceção se ausente."""
        api = FakeProductsAPI(result=ProductSearchResult(products=[build_product()]))
        dialog = self._build_dialog(api)

        dialog.results_tree.selection_set(["0"])
        dialog._on_add_selected()  # não deve levantar

        self.assertIn("adicionado", dialog.status_var.get())

    def test_cancel_button_closes_dialog_without_calling_callback(self):
        added_batches: list[list[Product]] = []
        api = FakeProductsAPI()
        dialog = self._build_dialog(api, on_add_selected=added_batches.append)

        dialog._on_cancel()

        self.assertEqual(added_batches, [])
        self.assertFalse(dialog.winfo_exists())

    # ------------------------------------------------------------------
    # Ordenação de colunas (core.column_sort.ColumnSorter)
    # ------------------------------------------------------------------

    def test_clicking_codigo_header_sorts_ascending_numerically(self):
        products = [
            build_product(id=1, codigo_barras="181100"),
            build_product(id=2, codigo_barras="181001"),
            build_product(id=3, codigo_barras="181010"),
        ]
        api = FakeProductsAPI(result=ProductSearchResult(products=products))
        dialog = self._build_dialog(api)

        dialog._on_sort_column("codigo")

        codes = [dialog.results_tree.item(iid, "values")[0] for iid in dialog.results_tree.get_children()]
        self.assertEqual(codes, ["181001", "181010", "181100"])

    def test_clicking_codigo_header_twice_sorts_descending(self):
        products = [
            build_product(id=1, codigo_barras="181100"),
            build_product(id=2, codigo_barras="181001"),
            build_product(id=3, codigo_barras="181010"),
        ]
        api = FakeProductsAPI(result=ProductSearchResult(products=products))
        dialog = self._build_dialog(api)

        dialog._on_sort_column("codigo")
        dialog._on_sort_column("codigo")

        codes = [dialog.results_tree.item(iid, "values")[0] for iid in dialog.results_tree.get_children()]
        self.assertEqual(codes, ["181100", "181010", "181001"])

    def test_clicking_codigo_header_three_times_returns_to_ascending(self):
        products = [build_product(id=1, codigo_barras="181100"), build_product(id=2, codigo_barras="181001")]
        api = FakeProductsAPI(result=ProductSearchResult(products=products))
        dialog = self._build_dialog(api)

        dialog._on_sort_column("codigo")
        dialog._on_sort_column("codigo")
        dialog._on_sort_column("codigo")

        codes = [dialog.results_tree.item(iid, "values")[0] for iid in dialog.results_tree.get_children()]
        self.assertEqual(codes, ["181001", "181100"])

    def test_sorting_by_descricao_is_alphabetical(self):
        products = [
            build_product(id=1, codigo_barras="1", descricao="Colar"),
            build_product(id=2, codigo_barras="2", descricao="Anel"),
            build_product(id=3, codigo_barras="3", descricao="Brinco"),
        ]
        api = FakeProductsAPI(result=ProductSearchResult(products=products))
        dialog = self._build_dialog(api)

        dialog._on_sort_column("descricao")

        descriptions = [dialog.results_tree.item(iid, "values")[1] for iid in dialog.results_tree.get_children()]
        self.assertEqual(descriptions, ["Anel", "Brinco", "Colar"])

    def test_sorting_by_preco_is_numeric_not_textual(self):
        varejo = lambda preco: [{"id": 1, "nome": "Varejo", "pivot": {"preco": preco}}]
        products = [
            build_product(id=1, codigo_barras="1", tipo_preco=varejo(100.0)),
            build_product(id=2, codigo_barras="2", tipo_preco=varejo(9.0)),
            build_product(id=3, codigo_barras="3", tipo_preco=varejo(20.0)),
        ]
        api = FakeProductsAPI(result=ProductSearchResult(products=products))
        dialog = self._build_dialog(api)

        dialog._on_sort_column("preco")

        precos = [dialog.results_tree.item(iid, "values")[2] for iid in dialog.results_tree.get_children()]
        self.assertEqual(precos, ["R$ 9.00", "R$ 20.00", "R$ 100.00"])

    def test_products_without_price_sort_last(self):
        varejo = [{"id": 1, "nome": "Varejo", "pivot": {"preco": 50.0}}]
        products = [
            build_product(id=1, codigo_barras="1", tipo_preco=[]),  # sem preco Varejo
            build_product(id=2, codigo_barras="2", tipo_preco=varejo),
        ]
        api = FakeProductsAPI(result=ProductSearchResult(products=products))
        dialog = self._build_dialog(api)

        dialog._on_sort_column("preco")

        codes = [dialog.results_tree.item(iid, "values")[0] for iid in dialog.results_tree.get_children()]
        self.assertEqual(codes, ["2", "1"])  # o sem preco fica por ultimo

    def test_sort_persists_across_a_new_search(self):
        """Refinar a busca não deveria descartar a ordenação já escolhida."""
        first_batch = [build_product(id=1, codigo_barras="181100"), build_product(id=2, codigo_barras="181001")]
        second_batch = [build_product(id=3, codigo_barras="181200"), build_product(id=4, codigo_barras="181050")]
        api = FakeProductsAPI(result=ProductSearchResult(products=first_batch))
        dialog = self._build_dialog(api)
        dialog._on_sort_column("codigo")  # ascendente

        api.result = ProductSearchResult(products=second_batch)
        dialog._run_search()

        codes = [dialog.results_tree.item(iid, "values")[0] for iid in dialog.results_tree.get_children()]
        self.assertEqual(codes, ["181050", "181200"])

    def test_selection_survives_sorting_by_index_remapping(self):
        """Depois de ordenar, o iid de cada linha aponta pro produto certo
        em self.results — selecionar/adicionar continua funcionando."""
        added_batches: list[list[Product]] = []
        products = [
            build_product(id=1, codigo_barras="181100", descricao="Z"),
            build_product(id=2, codigo_barras="181001", descricao="A"),
        ]
        api = FakeProductsAPI(result=ProductSearchResult(products=products))
        dialog = self._build_dialog(api, on_add_selected=added_batches.append)

        dialog._on_sort_column("codigo")  # products[1] (181001) agora vem primeiro
        dialog.results_tree.selection_set(["0"])
        dialog._on_add_selected()

        self.assertEqual(added_batches, [[products[1]]])

    # --- Melhoria 6 (atalhos): ESC fecha a janela, ENTER executa a pesquisa ---

    def test_initial_query_and_dates_prefill_the_search_fields(self):
        """Usado pelos botões de "Pesquisas Recentes"/"Favoritas" da
        MainWindow para reabrir a pesquisa já preenchida."""
        api = FakeProductsAPI(result=ProductSearchResult(products=[]))

        dialog = ProductSearchDialog(
            self.root,
            api,
            initial_query="181021",
            initial_data_inicial="01/01/2026",
            initial_data_final="10/01/2026",
        )

        def _safe_destroy() -> None:
            try:
                if dialog.winfo_exists():
                    dialog.destroy()
            except tk.TclError:
                pass

        self.addCleanup(_safe_destroy)

        self.assertEqual(dialog.search_var.get(), "181021")
        self.assertEqual(dialog.data_inicial_var.get(), "01/01/2026")
        self.assertEqual(dialog.data_final_var.get(), "10/01/2026")

    def test_escape_closes_the_dialog(self):
        # Bindings de tecla propagam pela cadeia (widget focado -> classe
        # -> toplevel), então o teste gera o evento no mesmo lugar que um
        # usuário real teria: o widget com foco dentro do diálogo.
        api = FakeProductsAPI(result=ProductSearchResult(products=[]))
        dialog = self._build_dialog(api)
        # self.root fica escondido (withdraw) no setUp desta classe — sem
        # mapear janela+diálogo e forçar o foco, o Windows não roteia o
        # evento de teclado sintético até o binding do Toplevel.
        self.root.deiconify()
        dialog.deiconify()
        dialog.lift()
        dialog.focus_force()
        self.root.update()

        dialog.event_generate("<Escape>")
        self.root.update()

        self.assertFalse(dialog.winfo_exists())

    def test_enter_runs_the_search_immediately_bypassing_debounce(self):
        api = FakeProductsAPI(result=ProductSearchResult(products=[]))
        dialog = self._build_dialog(api)
        self.root.deiconify()
        dialog.deiconify()
        dialog.lift()
        dialog.focus_force()
        self.root.update()
        api.calls.clear()

        dialog.search_var.set("181021")
        # Ainda dentro do debounce — não pesquisou de novo sozinho.
        self.assertEqual(api.calls, [])

        dialog.event_generate("<Return>")
        self.root.update()

        self.assertEqual(api.calls, [{"search": "181021"}])


if __name__ == "__main__":
    unittest.main()
