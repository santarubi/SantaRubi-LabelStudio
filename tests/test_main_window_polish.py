"""Rodada de polimento (v1.0): permanência na aba API Jueri após adicionar
à fila (Melhoria 1), resumo da fila (Melhoria 3), pesquisas favoritas
(Melhoria 4), persistência de interface (Melhoria 5) e atalhos globais
(Melhoria 6). Ver também tests/test_main_window_jueri_panel.py (rodada
anterior), tests/test_catalog_tab_polish.py, tests/test_toast.py e
tests/test_table_state.py — cada um cobre a fatia que lhe cabe."""

from __future__ import annotations

import tkinter as tk
import unittest
from typing import Any

from app.api.product import Product, ProductPrice
from core.catalog_product import CatalogProduct
from ui.main_window import MainWindow


class FakeConfigManager:
    def save(self, config: dict[str, Any]) -> None:
        pass


class FakePrintQueue:
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


def _product(id_: int, codigo: str, descricao: str = "produto") -> Product:
    return Product(id=id_, codigo_barras=codigo, descricao=descricao, tipo_preco=[])


def _tk_available() -> bool:
    try:
        root = tk.Tk()
        root.destroy()
        return True
    except tk.TclError:
        return False


def _build_window(root: tk.Tk, config: dict[str, Any] | None = None) -> MainWindow:
    """Réplica de MainWindow.__init__ trocando ConfigManager() (lê disco)
    por um FakeConfigManager em memória — mesma técnica usada em
    test_main_window_jueri_panel.py."""
    window = MainWindow.__new__(MainWindow)
    window.root = root
    window.config_manager = FakeConfigManager()
    window.config = config if config is not None else {}

    window_state = window.config.get("window_state", "zoomed")
    window.root.geometry(window.config.get("window_geometry", "1200x800+0+0"))
    if window_state == "zoomed":
        try:
            window.root.state("zoomed")
        except tk.TclError:
            pass

    window._jueri_categories_api = None
    window._jueri_dialog = None
    window.jueri_last_search_results = []
    window.jueri_search_history = []
    window.jueri_favorite_searches = list(window.config.get("jueri_favorites", []))

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
class StaysOnJueriTabTests(unittest.TestCase):
    """Melhoria 1 — não troca mais de aba automaticamente."""

    def setUp(self) -> None:
        self.root = tk.Tk()
        self.window = _build_window(self.root)
        self.window.catalog_tab = FakeCatalogTab()
        self.window.notebook.select(0)

    def tearDown(self) -> None:
        self.root.destroy()

    def test_confirming_products_from_the_search_dialog_stays_on_jueri_tab(self) -> None:
        class FakeDialog:
            search_var = tk.StringVar(value="")
            data_inicial_var = tk.StringVar(value="")
            data_final_var = tk.StringVar(value="")
            results: list[Product] = [_product(1, "181021")]

        self.window._jueri_dialog = FakeDialog()

        self.window._on_jueri_products_selected([_product(1, "181021")])

        self.assertEqual(self.window.notebook.index(self.window.notebook.select()), 0)
        self.assertEqual(len(self.window.catalog_tab.added), 1)


@unittest.skipUnless(_tk_available(), "ambiente de teste sem display Tk disponível")
class QueueSummaryTests(unittest.TestCase):
    """Melhoria 3 — resumo da fila na aba API Jueri (não a fila completa)."""

    def setUp(self) -> None:
        self.root = tk.Tk()
        self.window = _build_window(self.root)
        self.window.catalog_tab = FakeCatalogTab()

    def tearDown(self) -> None:
        self.root.destroy()

    def test_summary_updates_after_adding_from_search_dialog(self) -> None:
        class FakeDialog:
            search_var = tk.StringVar(value="")
            data_inicial_var = tk.StringVar(value="")
            data_final_var = tk.StringVar(value="")
            results: list[Product] = []

        self.window._jueri_dialog = FakeDialog()

        self.window._on_jueri_products_selected([_product(1, "181021"), _product(2, "181050")])

        self.assertEqual(self.window.jueri_queue_count_var.get(), "2")
        self.assertEqual(self.window.jueri_queue_labels_var.get(), "2")
        self.assertNotEqual(self.window.jueri_queue_updated_var.get(), "—")

    def test_summary_updates_after_adding_from_results_table(self) -> None:
        self.window.jueri_last_search_results = [_product(1, "181021")]
        self.window._load_jueri_results_table()
        self.window.jueri_results_tree.selection_set(["0"])

        self.window._on_add_jueri_selection_to_queue()

        self.assertEqual(self.window.jueri_queue_count_var.get(), "1")

    def test_refresh_queue_summary_reflects_current_queue_state(self) -> None:
        self.window.catalog_tab.add_product_to_queue(
            CatalogProduct(codigo="1", descricao="A", preco=None, categoria="", numeracao="", fornecedor="Jueri")
        )
        self.window.catalog_tab.add_product_to_queue(
            CatalogProduct(codigo="2", descricao="B", preco=None, categoria="", numeracao="", fornecedor="Jueri")
        )

        self.window._refresh_jueri_queue_summary()

        self.assertEqual(self.window.jueri_queue_count_var.get(), "2")
        self.assertEqual(self.window.jueri_queue_labels_var.get(), "2")


@unittest.skipUnless(_tk_available(), "ambiente de teste sem display Tk disponível")
class JueriFavoritesTests(unittest.TestCase):
    """Melhoria 4 — favoritar, remover e reexecutar pesquisas; persistem
    entre execuções via config.json."""

    def setUp(self) -> None:
        self.root = tk.Tk()
        self.window = _build_window(self.root)

    def tearDown(self) -> None:
        self.root.destroy()

    def test_add_favorite_persists_to_config_and_renders_button(self) -> None:
        entry = {"label": "Promoção Julho", "query": "promo julho", "data_inicial": "", "data_final": ""}

        self.window._on_add_jueri_favorite(entry)

        self.assertEqual(self.window.jueri_favorite_searches, [entry])
        self.assertEqual(self.window.config["jueri_favorites"], [entry])
        texts = [
            grandchild.cget("text")
            for chip in self.window.jueri_favorites_row.winfo_children()
            for grandchild in chip.winfo_children()
        ]
        self.assertTrue(any("Promoção Julho" in text for text in texts))

    def test_adding_the_same_favorite_twice_does_not_duplicate(self) -> None:
        entry = {"label": "Ouro", "query": "ouro", "data_inicial": "", "data_final": ""}

        self.window._on_add_jueri_favorite(entry)
        self.window._on_add_jueri_favorite(entry)

        self.assertEqual(len(self.window.jueri_favorite_searches), 1)

    def test_remove_favorite_updates_state_and_config(self) -> None:
        entry = {"label": "Prata", "query": "prata", "data_inicial": "", "data_final": ""}
        self.window._on_add_jueri_favorite(entry)

        self.window._on_remove_jueri_favorite(entry)

        self.assertEqual(self.window.jueri_favorite_searches, [])
        self.assertEqual(self.window.config["jueri_favorites"], [])

    def test_favorites_load_from_config_on_startup(self) -> None:
        saved = [{"label": "Rebaixa Agosto", "query": "rebaixa", "data_inicial": "", "data_final": ""}]
        root2 = tk.Tk()
        try:
            window2 = _build_window(root2, config={"jueri_favorites": saved})
            self.assertEqual(window2.jueri_favorite_searches, saved)
        finally:
            root2.destroy()

    def test_reexecuting_a_favorite_opens_the_search_dialog_prefilled(self) -> None:
        entry = {"label": "Ouro", "query": "ouro", "data_inicial": "", "data_final": ""}
        self.window._on_add_jueri_favorite(entry)
        self.window.config["jueri"] = {"enabled": True, "cliente_sistema": "x", "token": "y"}

        captured: dict[str, Any] = {}
        original = self.window._on_search_jueri_product

        def spy(prefill=None):
            captured["prefill"] = prefill

        self.window._on_search_jueri_product = spy
        # Simula o clique no botão ★ chamando o mesmo caminho que o botão usa.
        self.window._on_search_jueri_product(prefill=entry)
        self.window._on_search_jueri_product = original

        self.assertEqual(captured["prefill"], entry)


@unittest.skipUnless(_tk_available(), "ambiente de teste sem display Tk disponível")
class InterfacePersistenceTests(unittest.TestCase):
    """Melhoria 5 — aba ativa, tamanho/posição da janela, largura de
    colunas e ordenação são lembradas entre execuções."""

    def setUp(self) -> None:
        self.root = tk.Tk()
        self.window = _build_window(self.root)
        self.window.catalog_tab = FakeCatalogTab()
        self.window.catalog_tab.get_persisted_state = lambda: {"column_widths": {"codigo": 111}}

    def tearDown(self) -> None:
        self.root.destroy()

    def test_save_interface_state_records_last_tab_index(self) -> None:
        self.window.notebook.select(1)

        self.window._save_interface_state()

        self.assertEqual(self.window.config["last_tab_index"], 1)

    def test_save_interface_state_records_jueri_table_column_widths(self) -> None:
        self.window.jueri_results_tree.column("codigo", width=222)

        self.window._save_interface_state()

        self.assertEqual(self.window.config["jueri_results_column_widths"]["codigo"], 222)

    def test_save_interface_state_records_jueri_sort(self) -> None:
        self.window.jueri_last_search_results = [_product(1, "2"), _product(2, "1")]
        self.window._on_sort_jueri_column("codigo")

        self.window._save_interface_state()

        self.assertEqual(self.window.config["jueri_results_sort"], {"column": "codigo", "direction": "ascending"})

    def test_save_interface_state_delegates_catalog_state_to_catalog_tab(self) -> None:
        self.window._save_interface_state()

        self.assertEqual(self.window.config["catalog_state"], {"column_widths": {"codigo": 111}})

    def test_save_interface_state_records_window_geometry_when_not_zoomed(self) -> None:
        try:
            self.root.state("normal")
        except tk.TclError:
            self.skipTest("gerenciador de janelas não suporta state('normal') neste ambiente")
        self.root.update()

        self.window._save_interface_state()

        self.assertEqual(self.window.config["window_state"], "normal")
        self.assertIn("window_geometry", self.window.config)

    def test_column_widths_and_sort_are_restored_on_next_startup(self) -> None:
        saved_config = {
            "jueri_results_column_widths": {"codigo": 333},
            "jueri_results_sort": {"column": "descricao", "direction": "descending"},
        }
        root2 = tk.Tk()
        try:
            window2 = _build_window(root2, config=saved_config)
            self.assertEqual(window2.jueri_results_tree.column("codigo", "width"), 333)
            self.assertEqual(window2._jueri_sorter.active_column, "descricao")
        finally:
            root2.destroy()

    def test_last_tab_index_is_restored_on_next_startup(self) -> None:
        root2 = tk.Tk()
        try:
            window2 = _build_window(root2, config={"last_tab_index": 1})
            self.assertEqual(window2.notebook.index(window2.notebook.select()), 1)
        finally:
            root2.destroy()


@unittest.skipUnless(_tk_available(), "ambiente de teste sem display Tk disponível")
class GlobalShortcutTests(unittest.TestCase):
    """Melhoria 6 — atalhos globais (F3, Ctrl+F, Ctrl+P, Ctrl+L)."""

    def setUp(self) -> None:
        self.root = tk.Tk()
        self.window = _build_window(self.root)
        # event_generate só chega ao binding se a janela realmente tiver o
        # foco do SO — sem isso os testes de teclado ficam instáveis
        # (mesma causa investigada nos atalhos ESC/ENTER do diálogo).
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.root.update()

    def tearDown(self) -> None:
        self.root.destroy()

    def test_f3_opens_the_jueri_search(self) -> None:
        calls: list[Any] = []
        self.window._on_search_jueri_product = lambda prefill=None: calls.append(prefill)

        self.root.event_generate("<F3>")
        self.root.update()

        self.assertEqual(len(calls), 1)

    def test_ctrl_f_switches_to_catalog_tab_and_focuses_search(self) -> None:
        focused: list[bool] = []
        self.window.catalog_tab.focus_search_entry = lambda: focused.append(True)
        self.window.notebook.select(0)

        self.window._on_ctrl_f_shortcut()

        self.assertEqual(self.window.notebook.index(self.window.notebook.select()), 1)
        self.assertEqual(focused, [True])

    def test_ctrl_p_triggers_print_queue(self) -> None:
        calls: list[Any] = []
        self.window.catalog_tab._on_print_queue = lambda: calls.append(True)

        self.root.event_generate("<Control-p>")
        self.root.update()

        self.assertEqual(calls, [True])

    def test_ctrl_l_triggers_clear_queue(self) -> None:
        calls: list[Any] = []
        self.window.catalog_tab._on_clear_queue = lambda: calls.append(True)

        self.root.event_generate("<Control-l>")
        self.root.update()

        self.assertEqual(calls, [True])


if __name__ == "__main__":
    unittest.main()
