"""Painel "Integração Jueri" da aba API Jueri (ui/main_window.py) —
histórico de pesquisas recentes, tabela "Resultado da Última Pesquisa"
(ordenação, seleção, envio para a fila) e status da conexão.

Não cobre a pesquisa em si (ProductsAPI/JueriSearchPanel já têm seus
próprios testes) nem a fila de impressão (core/print_queue.py já tem os
seus) — só as interações novas desta reorganização de interface.
"""

from __future__ import annotations

import tkinter as tk
import unittest
from typing import Any
from unittest.mock import patch

from app.api.product import Product, ProductPrice
from core.catalog_product import CatalogProduct
from ui.main_window import MainWindow


class FakeConfigManager:
    def __init__(self) -> None:
        self.saved: list[dict[str, Any]] = []

    def save(self, config: dict[str, Any]) -> None:
        self.saved.append(dict(config))


class FakeCategoriesAPI:
    def __init__(self, names: dict[int, str], subcategory_names: dict[int, str] | None = None) -> None:
        self.names = names
        self.subcategory_names = subcategory_names or {}

    def nome_categoria(self, categoria_id: int | None) -> str | None:
        if categoria_id is None:
            return None
        return self.names.get(categoria_id)

    def nome_subcategoria(self, subcategoria_id: int | None) -> str | None:
        if subcategoria_id is None:
            return None
        return self.subcategory_names.get(subcategoria_id)


class FakePrintQueue:
    """Réplica mínima de core/print_queue.py — só o suficiente para
    FakeCatalogTab responder contains()/count()/total_labels() de forma
    consistente com o que foi adicionado."""

    def __init__(self) -> None:
        self._codes: set[str] = set()

    def contains(self, product: CatalogProduct) -> bool:
        return product.codigo in self._codes

    def count(self) -> int:
        return len(self._codes)

    def total_labels(self) -> int:
        return len(self._codes)


class FakeCatalogTab:
    def __init__(self) -> None:
        self.added: list[CatalogProduct] = []
        self.print_queue = FakePrintQueue()

    def add_product_to_queue(self, product: CatalogProduct) -> None:
        self.added.append(product)
        self.print_queue._codes.add(product.codigo)


def _product(
    id_: int,
    codigo: str,
    descricao: str,
    quantidade: int | None = None,
    data_criacao: str | None = None,
    preco: float | None = None,
    categoria_id: int | None = None,
    subcategoria_id: int | None = None,
) -> Product:
    tipo_preco = [ProductPrice(id=1, nome="Varejo", preco=preco)] if preco is not None else []
    return Product(
        id=id_,
        codigo_barras=codigo,
        descricao=descricao,
        quantidade=quantidade,
        data_criacao=data_criacao,
        fk_categoria_id=categoria_id,
        fk_subcategoria_id=subcategoria_id,
        tipo_preco=tipo_preco,
    )


def _tk_available() -> bool:
    try:
        root = tk.Tk()
        root.destroy()
        return True
    except tk.TclError:
        return False


def _build_window(root: tk.Tk) -> MainWindow:
    """Constrói uma MainWindow sem tocar no config.json real do usuário —
    replica o que MainWindow.__init__ faz, trocando ConfigManager() (lê
    disco) por um FakeConfigManager em memória."""
    window = MainWindow.__new__(MainWindow)
    window.root = root
    window.root.geometry("1200x800+0+0")
    window.config_manager = FakeConfigManager()
    window.config = {}

    window._jueri_categories_api = None
    window._jueri_dialog = None
    window.jueri_last_search_results = []
    window.jueri_search_history = []
    window.jueri_favorite_searches = []

    from core.column_sort import ColumnSorter, numeric_or_text

    window._jueri_sorter = ColumnSorter(
        {
            "codigo": lambda product: numeric_or_text(product.codigo_barras),
            "descricao": lambda product: product.descricao,
            "categoria": lambda product: window._resolve_jueri_category(product),
            "estoque": lambda product: product.quantidade,
            "cadastro": lambda product: product.data_criacao,
            "preco": lambda product: product.preco_principal,
        }
    )

    window.jueri_status_var = tk.StringVar(value="Desabilitada")
    window.jueri_client_var = tk.StringVar(value="—")
    window.jueri_last_sync_var = tk.StringVar(value="Nunca")
    window.jueri_result_count_var = tk.StringVar(value="0")
    window.jueri_queue_count_var = tk.StringVar(value="0")
    window.jueri_queue_labels_var = tk.StringVar(value="0")
    window.jueri_queue_updated_var = tk.StringVar(value="—")

    window._setup_style()
    window._build_widgets()
    return window


@unittest.skipUnless(_tk_available(), "ambiente de teste sem display Tk disponível")
class JueriResultsTableTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = tk.Tk()
        self.window = _build_window(self.root)
        self.window.catalog_tab = FakeCatalogTab()
        self.window._jueri_categories_api = FakeCategoriesAPI({1: "Anéis"})

    def tearDown(self) -> None:
        self.root.destroy()

    def test_load_results_table_formats_columns(self) -> None:
        self.window.jueri_last_search_results = [
            _product(1, "181021", "ANEL SOLITÁRIO", quantidade=5, data_criacao="2026-07-20 10:00:00", preco=59.9, categoria_id=1),
        ]
        self.window._load_jueri_results_table()

        values = [str(value) for value in self.window.jueri_results_tree.item("0")["values"]]
        self.assertEqual(
            values,
            ["181021", "ANEL SOLITÁRIO", "R$ 59.90", "—", "—", "Anéis", "5", "20/07/2026"],
        )
        self.assertEqual(self.window.jueri_result_count_var.get(), "1")

    def test_load_results_table_shows_dash_for_missing_fields(self) -> None:
        self.window.jueri_last_search_results = [_product(1, "181021", "ANEL")]
        self.window._load_jueri_results_table()

        values = [str(value) for value in self.window.jueri_results_tree.item("0")["values"]]
        self.assertEqual(values, ["181021", "ANEL", "—", "—", "—", "—", "—", "—"])

    def test_sort_estoque_is_numeric_not_textual(self) -> None:
        """Regressão: estoque "8" não pode ordenar depois de "30" como texto."""
        self.window.jueri_last_search_results = [
            _product(1, "A", "A", quantidade=30),
            _product(2, "B", "B", quantidade=8),
            _product(3, "C", "C", quantidade=100),
        ]

        self.window._on_sort_jueri_column("estoque")
        ascending = [p.quantidade for p in self.window.jueri_last_search_results]
        self.assertEqual(ascending, [8, 30, 100])

        self.window._on_sort_jueri_column("estoque")
        descending = [p.quantidade for p in self.window.jueri_last_search_results]
        self.assertEqual(descending, [100, 30, 8])

    def test_sort_preco_puts_missing_prices_last_both_directions(self) -> None:
        self.window.jueri_last_search_results = [
            _product(1, "A", "A", preco=10.0),
            _product(2, "B", "B"),
            _product(3, "C", "C", preco=5.0),
        ]

        self.window._on_sort_jueri_column("preco")
        self.assertEqual([p.id for p in self.window.jueri_last_search_results], [3, 1, 2])

        self.window._on_sort_jueri_column("preco")
        self.assertEqual([p.id for p in self.window.jueri_last_search_results], [1, 3, 2])

    def test_clear_results_empties_table(self) -> None:
        self.window.jueri_last_search_results = [_product(1, "181021", "ANEL")]
        self.window._load_jueri_results_table()

        self.window._on_clear_jueri_results()

        self.assertEqual(self.window.jueri_last_search_results, [])
        self.assertEqual(self.window.jueri_results_tree.get_children(), ())
        self.assertEqual(self.window.jueri_result_count_var.get(), "0")


@unittest.skipUnless(_tk_available(), "ambiente de teste sem display Tk disponível")
class JueriAddSelectionToQueueTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = tk.Tk()
        self.window = _build_window(self.root)
        self.window.catalog_tab = FakeCatalogTab()
        self.window._jueri_categories_api = FakeCategoriesAPI({})
        self.window.jueri_last_search_results = [
            _product(1, "181021", "ANEL", quantidade=5, preco=59.9),
            _product(2, "181050", "ALIANÇA", quantidade=2, preco=75.9),
        ]
        self.window._load_jueri_results_table()

    def tearDown(self) -> None:
        self.root.destroy()

    def test_adds_selected_rows_to_the_print_queue_and_stays_on_jueri_tab(self) -> None:
        """Melhoria 1: não troca mais de aba automaticamente."""
        self.window.jueri_results_tree.selection_set(["0", "1"])
        self.window.notebook.select(0)

        self.window._on_add_jueri_selection_to_queue()

        codigos = {product.codigo for product in self.window.catalog_tab.added}
        self.assertEqual(codigos, {"181021", "181050"})
        self.assertEqual(self.window.notebook.index(self.window.notebook.select()), 0)

    def test_partial_selection_only_adds_selected_rows(self) -> None:
        self.window.jueri_results_tree.selection_set(["1"])

        self.window._on_add_jueri_selection_to_queue()

        self.assertEqual(len(self.window.catalog_tab.added), 1)
        self.assertEqual(self.window.catalog_tab.added[0].codigo, "181050")

    def test_print_mapping_uses_subcategory_name_instead_of_category_name(self) -> None:
        self.window._jueri_categories_api = FakeCategoriesAPI(
            {10: "COLARES"},
            {20: "BANHADO PRATA"},
        )
        self.window.jueri_last_search_results = [
            _product(
                1,
                "181021",
                "COLAR",
                categoria_id=10,
                subcategoria_id=20,
            )
        ]
        self.window._load_jueri_results_table()
        self.window.jueri_results_tree.selection_set(["0"])

        self.window._on_add_jueri_selection_to_queue()

        self.assertEqual(self.window.catalog_tab.added[0].categoria, "BANHADO PRATA")

    @patch("ui.main_window.messagebox.showinfo")
    def test_no_selection_shows_warning_and_adds_nothing(self, mock_showinfo) -> None:
        self.window._on_add_jueri_selection_to_queue()

        mock_showinfo.assert_called_once()
        self.assertEqual(self.window.catalog_tab.added, [])


@unittest.skipUnless(_tk_available(), "ambiente de teste sem display Tk disponível")
class JueriSearchHistoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = tk.Tk()
        self.window = _build_window(self.root)

    def tearDown(self) -> None:
        self.root.destroy()

    def _fake_dialog(self, query: str = "", inicio: str = "", fim: str = ""):
        return type(
            "FakeDialog",
            (),
            {
                "search_var": type("V", (), {"get": lambda self: query})(),
                "data_inicial_var": type("V", (), {"get": lambda self: inicio})(),
                "data_final_var": type("V", (), {"get": lambda self: fim})(),
                "results": [],
            },
        )()

    def test_describe_uses_query_text_when_present(self) -> None:
        dialog = self._fake_dialog(query="181021,181050")
        self.assertEqual(MainWindow._describe_jueri_search(dialog), "181021,181050")

    def test_describe_uses_todays_date_range(self) -> None:
        from app.api.date_filters import today_br

        dialog = self._fake_dialog(inicio=today_br(), fim=today_br())
        self.assertEqual(MainWindow._describe_jueri_search(dialog), "Hoje")

    def test_describe_uses_yesterdays_date_range(self) -> None:
        from app.api.date_filters import yesterday_br

        dialog = self._fake_dialog(inicio=yesterday_br(), fim=yesterday_br())
        self.assertEqual(MainWindow._describe_jueri_search(dialog), "Ontem")

    def test_describe_falls_back_to_date_range_text(self) -> None:
        dialog = self._fake_dialog(inicio="01/01/2026", fim="10/01/2026")
        self.assertEqual(MainWindow._describe_jueri_search(dialog), "01/01/2026 a 10/01/2026")

    def test_describe_falls_back_when_nothing_set(self) -> None:
        dialog = self._fake_dialog()
        self.assertEqual(MainWindow._describe_jueri_search(dialog), "Todos os produtos")

    def test_record_history_dedupes_by_label_keeping_most_recent_first(self) -> None:
        self.window._record_jueri_search_history(self._fake_dialog(query="A"))
        self.window._record_jueri_search_history(self._fake_dialog(query="B"))
        self.window._record_jueri_search_history(self._fake_dialog(query="A"))

        labels = [entry["label"] for entry in self.window.jueri_search_history]
        self.assertEqual(labels, ["A", "B"])

    def test_record_history_caps_at_six_entries(self) -> None:
        for index in range(8):
            self.window._record_jueri_search_history(self._fake_dialog(query=f"Q{index}"))

        self.assertEqual(len(self.window.jueri_search_history), 6)
        self.assertEqual(self.window.jueri_search_history[0]["label"], "Q7")


@unittest.skipUnless(_tk_available(), "ambiente de teste sem display Tk disponível")
class JueriConnectionStatusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = tk.Tk()
        self.window = _build_window(self.root)

    def tearDown(self) -> None:
        self.root.destroy()

    def test_status_disabled_when_integration_not_enabled(self) -> None:
        self.window.config = {"jueri": {"enabled": False}}
        self.window._refresh_jueri_connection_status()
        self.assertEqual(self.window.jueri_status_var.get(), "Desconectado")

    def test_status_incomplete_when_enabled_but_missing_credentials(self) -> None:
        self.window.config = {"jueri": {"enabled": True, "cliente_sistema": "", "token": ""}}
        self.window._refresh_jueri_connection_status()
        self.assertEqual(self.window.jueri_status_var.get(), "Desconectado")

    def test_status_enabled_with_complete_credentials(self) -> None:
        self.window.config = {"jueri": {"enabled": True, "cliente_sistema": "santarubi", "token": "abc"}}
        self.window._refresh_jueri_connection_status()
        self.assertEqual(self.window.jueri_status_var.get(), "Conectado")


@unittest.skipUnless(_tk_available(), "ambiente de teste sem display Tk disponível")
class UniversalQueueLayoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = tk.Tk()
        self.window = _build_window(self.root)
        self.root.update_idletasks()

    def tearDown(self) -> None:
        self.root.destroy()

    def test_queue_is_outside_notebook_and_survives_tab_switches(self) -> None:
        queue_widget = self.window.catalog_tab.queue_canvas
        ancestor = queue_widget.master
        while ancestor is not None:
            self.assertIsNot(ancestor, self.window.notebook)
            ancestor = getattr(ancestor, "master", None)

        self.window.notebook.select(self.window.catalog_tab_frame)
        self.window.notebook.select(self.window.jueri_tab_frame)
        self.assertIs(self.window.catalog_tab.queue_canvas, queue_widget)

    def test_main_divider_is_horizontal_and_starts_near_65_percent(self) -> None:
        self.root.update()
        self.window._restore_main_pane()
        available = self.window.main_paned.winfo_width() - 6
        ratio = self.window.main_paned.sashpos(0) / available

        self.assertEqual(str(self.window.main_paned.cget("orient")), "horizontal")
        self.assertAlmostEqual(ratio, 0.65, delta=0.03)

    def test_jueri_search_is_embedded_and_operational_header_has_no_client_id(self) -> None:
        ancestor = self.window.jueri_search_panel.master
        while ancestor is not None and ancestor is not self.window.jueri_tab_frame:
            self.assertNotIsInstance(ancestor, tk.Toplevel)
            ancestor = getattr(ancestor, "master", None)
        self.assertIs(ancestor, self.window.jueri_tab_frame)

        texts: list[str] = []
        status_bindings = 0
        pending = [self.root]
        while pending:
            widget = pending.pop()
            pending.extend(widget.winfo_children())
            try:
                text = str(widget.cget("text"))
                if text:
                    texts.append(text)
            except tk.TclError:
                pass
            try:
                status_bindings += str(widget.cget("textvariable")) == str(self.window.jueri_status_var)
            except tk.TclError:
                pass

        self.assertNotIn("Cliente", texts)
        self.assertEqual(status_bindings, 1)

    def test_queue_shows_items_from_both_origins(self) -> None:
        excel = CatalogProduct("100", "Excel", 10.0, "", "", "Aba", {"origem": "excel"})
        jueri = CatalogProduct("200", "Jueri", 20.0, "", "", "Jueri", {"origem": "jueri"})
        self.window.catalog_tab.add_product_to_queue(excel)
        self.window.catalog_tab.add_product_to_queue(jueri)

        origin_texts = [
            card.winfo_children()[3].cget("text")
            for card in self.window.catalog_tab.queue_items_frame.winfo_children()
        ]
        self.assertEqual(origin_texts, ["Origem: Excel", "Origem: Jueri"])

    def test_queue_keeps_a_usable_minimum_width(self) -> None:
        self.root.update()
        self.window.main_paned.sashpos(0, self.window.main_paned.winfo_width())
        self.window._restore_main_pane()
        self.root.update_idletasks()
        queue_width = self.window.main_paned.winfo_width() - self.window.main_paned.sashpos(0)
        self.assertGreaterEqual(queue_width, 280)


class JueriDateFormattingTests(unittest.TestCase):
    def test_formats_datetime_string(self) -> None:
        self.assertEqual(MainWindow._format_jueri_date("2026-07-20 10:15:00"), "20/07/2026")

    def test_formats_date_only_string(self) -> None:
        self.assertEqual(MainWindow._format_jueri_date("2026-07-20"), "20/07/2026")

    def test_returns_dash_for_missing_value(self) -> None:
        self.assertEqual(MainWindow._format_jueri_date(None), "—")
        self.assertEqual(MainWindow._format_jueri_date(""), "—")

    def test_falls_back_to_raw_value_for_unknown_format(self) -> None:
        self.assertEqual(MainWindow._format_jueri_date("não é uma data"), "não é uma data")


class JueriFilterConfigTests(unittest.TestCase):
    def test_saving_filters_preserves_credentials_and_other_settings(self) -> None:
        window = MainWindow.__new__(MainWindow)
        window.config = {"jueri": {"enabled": True, "token": "segredo"}, "last_printer": "ELGIN"}
        window.config_manager = FakeConfigManager()

        window._save_jueri_search_filters({"stock": "Com estoque", "query": "anel"})

        self.assertEqual(window.config["jueri"]["token"], "segredo")
        self.assertEqual(window.config["last_printer"], "ELGIN")
        self.assertEqual(window.config["jueri_search_filters"]["stock"], "Com estoque")


if __name__ == "__main__":
    unittest.main()
