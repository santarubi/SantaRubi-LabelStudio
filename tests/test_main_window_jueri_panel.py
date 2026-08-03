"""Painel "Integração Jueri" da aba API Jueri (ui/main_window.py) —
histórico de pesquisas recentes, tabela "Resultado da Última Pesquisa"
(ordenação, seleção, envio para a fila) e status da conexão.

Não cobre a pesquisa em si (ProductsAPI/ProductSearchDialog já têm seus
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
    def save(self, config: dict[str, Any]) -> None:
        pass


class FakeCategoriesAPI:
    def __init__(self, names: dict[int, str]) -> None:
        self.names = names

    def nome_categoria(self, categoria_id: int | None) -> str | None:
        if categoria_id is None:
            return None
        return self.names.get(categoria_id)


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
) -> Product:
    tipo_preco = [ProductPrice(id=1, nome="Varejo", preco=preco)] if preco is not None else []
    return Product(
        id=id_,
        codigo_barras=codigo,
        descricao=descricao,
        quantidade=quantidade,
        data_criacao=data_criacao,
        fk_categoria_id=categoria_id,
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
        self.assertEqual(values, ["181021", "ANEL SOLITÁRIO", "Anéis", "5", "20/07/2026", "R$ 59.90"])
        self.assertEqual(self.window.jueri_result_count_var.get(), "1")

    def test_load_results_table_shows_dash_for_missing_fields(self) -> None:
        self.window.jueri_last_search_results = [_product(1, "181021", "ANEL")]
        self.window._load_jueri_results_table()

        values = [str(value) for value in self.window.jueri_results_tree.item("0")["values"]]
        self.assertEqual(values, ["181021", "ANEL", "—", "—", "—", "—"])

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
        self.assertEqual(self.window.jueri_status_var.get(), "Desabilitada")

    def test_status_incomplete_when_enabled_but_missing_credentials(self) -> None:
        self.window.config = {"jueri": {"enabled": True, "cliente_sistema": "", "token": ""}}
        self.window._refresh_jueri_connection_status()
        self.assertEqual(self.window.jueri_status_var.get(), "Credenciais incompletas")

    def test_status_enabled_with_complete_credentials(self) -> None:
        self.window.config = {"jueri": {"enabled": True, "cliente_sistema": "santarubi", "token": "abc"}}
        self.window._refresh_jueri_connection_status()
        self.assertEqual(self.window.jueri_status_var.get(), "Habilitada")
        self.assertEqual(self.window.jueri_client_var.get(), "santarubi")


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


if __name__ == "__main__":
    unittest.main()
