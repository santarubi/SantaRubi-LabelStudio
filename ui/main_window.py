"""Interface principal do Santa Rubi Label Studio.

Duas abas: "API Jueri" (pesquisa e integração com a API Jueri) e
"Planilha Excel" (catálogo, fila de impressão e disparo da impressão —
implementada em ui/catalog_tab.py). Esta janela apresenta a estrutura
visual, sem lógica de negócio: pesquisa/ordenação/filtro vivem em
core/, a fila de impressão em core/print_queue.py.
"""

from __future__ import annotations

import tkinter as tk
from dataclasses import replace
from datetime import datetime
from tkinter import messagebox, ttk
from typing import Any

from app.api.auth import JueriCredentials
from app.api.categories import CategoriesAPI
from app.api.client import JueriClient
from app.api.connection_test import JUERI_BASE_URL
from app.api.date_filters import today_br, yesterday_br
from app.api.product import Product
from app.api.products import ProductsAPI
from core.column_sort import ColumnSorter, numeric_or_text
from core.catalog_product import CatalogProduct
from core.config import ConfigManager
from core.queue_feedback import describe_queue_addition
from core.table_state import apply_column_widths, apply_sorter_state, get_column_widths, get_sorter_state
from ui.catalog_tab import CatalogTab
from ui.branding import APP_NAME, APP_VERSION, AboutDialog, apply_window_icon
from ui.design_system import BACKGROUND, DESTRUCTIVE, MUTED_TEXT, PRIMARY, SURFACE, configure_styles
from ui.product_search_dialog import JueriSearchPanel
from ui.settings_dialog import SettingsDialog

APP_TITLE = APP_NAME
WINDOW_SIZE = "1000x700"

JUERI_RESULTS_MAX_HISTORY = 6

class MainWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{APP_TITLE} {APP_VERSION}")
        apply_window_icon(self.root)

        self.config_manager = ConfigManager()
        self.config: dict[str, Any] = self.config_manager.load()

        window_state = self.config.get("window_state", "zoomed")
        self.root.geometry(self.config.get("window_geometry", WINDOW_SIZE))
        self.root.minsize(960, 560)
        if window_state == "zoomed":
            self.root.state("zoomed")
        self.root.configure(bg=BACKGROUND)

        # Cache em memória do CategoriesAPI — carregado uma única vez, no
        # primeiro uso, e reaproveitado em todas as pesquisas Jueri seguintes.
        self._jueri_categories_api: CategoriesAPI | None = None
        self.jueri_search_panel: JueriSearchPanel | None = None
        self.jueri_last_search_results: list[Product] = []
        self.jueri_search_history: list[dict[str, str]] = []
        self.jueri_favorite_searches: list[dict[str, str]] = list(self.config.get("jueri_favorites", []))
        self._jueri_sorter = ColumnSorter(
            {
                "codigo": lambda product: numeric_or_text(product.codigo_barras),
                "descricao": lambda product: product.descricao,
                "categoria": lambda product: self._resolve_jueri_category(product),
                "estoque": lambda product: product.quantidade,
                "cadastro": lambda product: product.data_criacao,
                "preco": lambda product: product.preco_principal,
            }
        )

        self.jueri_status_var = tk.StringVar(value="Desabilitada")
        self.jueri_last_sync_var = tk.StringVar(value="Nunca")
        self.jueri_result_count_var = tk.StringVar(value="0")
        self.jueri_queue_count_var = tk.StringVar(value="0")
        self.jueri_queue_labels_var = tk.StringVar(value="0")
        self.jueri_queue_updated_var = tk.StringVar(value="—")
        self.header_printer_var = tk.StringVar(value=self.config.get("last_printer", "Nenhuma"))
        self._main_pane_restored = False

        self._setup_style()
        self._build_widgets()

    def _setup_style(self):
        configure_styles(self.root)

    def _build_widgets(self):
        if not hasattr(self, "header_printer_var"):
            self.header_printer_var = tk.StringVar(value=self.config.get("last_printer", "Nenhuma"))
        if not hasattr(self, "_main_pane_restored"):
            self._main_pane_restored = False
        app_header = ttk.Frame(self.root, style="Header.TFrame", padding=(12, 8))
        app_header.pack(fill="x")
        app_header.grid_columnconfigure(0, weight=1)
        ttk.Label(app_header, text=APP_TITLE, font=("Segoe UI", 15, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(app_header, text="Jueri:", style="Subtitle.TLabel").grid(row=0, column=1, padx=(12, 4))
        self.header_jueri_status_label = tk.Label(
            app_header, textvariable=self.jueri_status_var, bg=SURFACE, fg=MUTED_TEXT, font=("Segoe UI", 10, "bold")
        )
        self.header_jueri_status_label.grid(row=0, column=2, sticky="e")
        ttk.Label(app_header, text="Última sincronização:", style="Subtitle.TLabel").grid(
            row=0, column=3, padx=(10, 4)
        )
        ttk.Label(app_header, textvariable=self.jueri_last_sync_var).grid(row=0, column=4, sticky="e")
        ttk.Label(app_header, text="Impressora:", style="Subtitle.TLabel").grid(
            row=0, column=5, padx=(10, 4)
        )
        ttk.Label(app_header, textvariable=self.header_printer_var, width=25, anchor="w").grid(
            row=0, column=6, sticky="e"
        )
        ttk.Button(
            app_header, text="Configurações", style="App.TButton", command=self._open_settings
        ).grid(row=0, column=7, sticky="e", padx=(10, 0))

        self.main_paned = ttk.Panedwindow(self.root, orient="horizontal")
        self.main_paned.pack(fill="both", expand=True)

        self.notebook = ttk.Notebook(self.main_paned)
        queue_host = ttk.Frame(self.main_paned, padding=(4, 12, 12, 12))
        self.main_paned.add(self.notebook, weight=3)
        self.main_paned.add(queue_host, weight=1)
        self.notebook.bind("<<NotebookTabChanged>>", self._on_notebook_tab_changed)

        self.jueri_tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.jueri_tab_frame, text="API Jueri")
        self.catalog_tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.catalog_tab_frame, text="Planilha Excel")

        self.catalog_tab = CatalogTab(
            self.catalog_tab_frame,
            self.config_manager,
            self.config,
            queue_parent=queue_host,
        )
        self.catalog_tab.printer_var.trace_add("write", self._on_printer_changed)
        self._on_printer_changed()
        self._build_jueri_tab()

        self.catalog_tab.apply_persisted_state(self.config.get("catalog_state", {}))
        self._refresh_jueri_queue_summary()
        self.main_paned.bind("<Configure>", self._restore_main_pane)

        last_tab_index = self.config.get("last_tab_index", 0)
        if last_tab_index in (0, 1):
            self.notebook.select(last_tab_index)

        self._bind_shortcuts()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _bind_shortcuts(self) -> None:
        """Atalhos globais para pesquisa, impressão e limpeza da fila."""
        self.root.bind_all("<F3>", lambda _event: self._on_search_jueri_product())
        self.root.bind_all("<Control-f>", self._on_ctrl_f_shortcut)
        self.root.bind_all("<Control-F>", self._on_ctrl_f_shortcut)
        self.root.bind_all("<Control-p>", lambda _event: self.catalog_tab._on_print_queue())
        self.root.bind_all("<Control-P>", lambda _event: self.catalog_tab._on_print_queue())
        self.root.bind_all("<Control-l>", lambda _event: self.catalog_tab._confirm_clear_queue())
        self.root.bind_all("<Control-L>", lambda _event: self.catalog_tab._confirm_clear_queue())

    def _on_printer_changed(self, *_args: Any) -> None:
        self.header_printer_var.set(self.catalog_tab.printer_var.get() or "Nenhuma selecionada")

    def _set_jueri_status(self, status: str) -> None:
        self.jueri_status_var.set(status)
        color = {
            "Conectado": PRIMARY,
            "Atualizando": PRIMARY,
            "Erro": DESTRUCTIVE,
            "Desconectado": MUTED_TEXT,
        }.get(status, MUTED_TEXT)
        for label_name in ("header_jueri_status_label", "jueri_status_label"):
            label = getattr(self, label_name, None)
            if label is not None:
                label.configure(fg=color)

    def _restore_main_pane(self, _event: Any = None) -> None:
        if self.main_paned.winfo_width() <= 1:
            return
        available = max(1, self.main_paned.winfo_width() - 6)
        minimum_left = min(620, max(1, int(available * 0.55)))
        maximum_left = max(minimum_left, available - min(320, max(1, int(available * 0.45))))
        if self._main_pane_restored:
            requested = self.main_paned.sashpos(0)
        else:
            saved_ratio = self.config.get("main_queue_width_ratio")
            if isinstance(saved_ratio, (int, float)) and 0.55 <= saved_ratio <= 0.8:
                requested = int(available * saved_ratio)
            else:
                requested = int(available * 0.65)
        self.main_paned.sashpos(0, max(minimum_left, min(requested, maximum_left)))
        self._main_pane_restored = True

    def _on_ctrl_f_shortcut(self, _event: Any = None) -> str:
        self.notebook.select(self.catalog_tab_frame)
        self.catalog_tab.focus_search_entry()
        return "break"

    def _on_notebook_tab_changed(self, _event: Any = None) -> None:
        """Evita informações desatualizadas ao voltar para a aba API
        Jueri (ex.: credenciais alteradas em Configurações, ou fila
        alterada manualmente na Planilha Excel)."""
        if self.notebook.select() == str(self.jueri_tab_frame):
            self._refresh_jueri_connection_status()
            self._refresh_jueri_queue_summary()

    def _on_close(self) -> None:
        self._save_interface_state()
        self.root.destroy()

    def _save_interface_state(self) -> None:
        """Melhoria 5 — grava tudo de uma vez ao fechar o programa: aba
        ativa, tamanho/posição da janela, largura de colunas e ordenação
        das duas tabelas principais. Favoritos já são salvos no momento
        em que são adicionados/removidos (ver _save_jueri_favorites)."""
        self.config["last_tab_index"] = self.notebook.index(self.notebook.select())

        state = self.root.state()
        self.config["window_state"] = state
        if state == "normal":
            self.config["window_geometry"] = self.root.geometry()

        self.config["jueri_results_column_widths"] = get_column_widths(self.jueri_results_tree)
        sort_state = get_sorter_state(self._jueri_sorter)
        if sort_state:
            self.config["jueri_results_sort"] = sort_state

        self.config["catalog_state"] = self.catalog_tab.get_persisted_state()
        available_width = max(1, self.main_paned.winfo_width() - 6)
        self.config["main_queue_width_ratio"] = self.main_paned.sashpos(0) / available_width
        self.config_manager.save(self.config)

    # ------------------------------------------------------------------
    # Aba "API Jueri" — pesquisa completa embutida, favoritos e histórico.
    # O componente reutilizável JueriSearchPanel concentra a consulta,
    # filtros, ordenação, seleção e apresentação dos resultados.
    # ------------------------------------------------------------------

    def _build_jueri_tab(self) -> None:
        container = ttk.Frame(self.jueri_tab_frame, style="Content.TFrame", padding=8)
        container.pack(fill="both", expand=True)
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(1, weight=1)

        saved_searches = ttk.Frame(container)
        saved_searches.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        saved_searches.grid_columnconfigure(0, weight=1)
        saved_searches.grid_columnconfigure(1, weight=1)
        self._build_jueri_favorites_panel(saved_searches)
        self._build_jueri_history_panel(saved_searches)

        credentials = JueriCredentials.from_config(self.config)
        client = JueriClient(JUERI_BASE_URL, credentials)
        self._jueri_categories_api = CategoriesAPI(client)
        filters = dict(self.config.get("jueri_search_filters", {}))
        self.jueri_search_panel = JueriSearchPanel(
            container,
            ProductsAPI(client),
            on_add_selected=self._on_jueri_products_selected,
            categories_api=self._jueri_categories_api,
            initial_filters=filters,
            on_filters_changed=self._save_jueri_search_filters,
            on_status_changed=self._set_jueri_status,
            on_search_completed=self._on_jueri_search_completed,
            async_search=True,
            auto_search=bool(credentials.enabled and credentials.cliente_sistema and credentials.token),
        )
        self.jueri_search_panel.grid(row=1, column=0, sticky="nsew")
        self.jueri_results_tree = self.jueri_search_panel.results_tree
        self._jueri_sorter = self.jueri_search_panel._sorter
        apply_column_widths(self.jueri_results_tree, self.config.get("jueri_results_column_widths", {}))
        apply_sorter_state(self._jueri_sorter, self.config.get("jueri_results_sort"))

        self._render_jueri_favorite_buttons()
        self._render_jueri_history_buttons()
        self._refresh_jueri_connection_status()

    def _build_jueri_favorites_panel(self, container: ttk.Frame) -> None:
        favorites_panel = ttk.Frame(container)
        favorites_panel.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ttk.Label(favorites_panel, text="Favoritas:", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 6))
        self.jueri_favorites_row = ttk.Frame(favorites_panel)
        self.jueri_favorites_row.pack(side="left", fill="x", expand=True)

    def _build_jueri_history_panel(self, container: ttk.Frame) -> None:
        history_panel = ttk.Frame(container)
        history_panel.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        ttk.Label(history_panel, text="Recentes:", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 6))
        self.jueri_history_row = ttk.Frame(history_panel)
        self.jueri_history_row.pack(side="left", fill="x", expand=True)

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self.root, self.config_manager, self.config)
        self.root.wait_window(dialog)
        self._refresh_jueri_connection_status()

    def _refresh_jueri_connection_status(self) -> None:
        credentials = JueriCredentials.from_config(self.config)
        if not credentials.enabled:
            self._set_jueri_status("Desconectado")
        elif not credentials.cliente_sistema or not credentials.token:
            self._set_jueri_status("Desconectado")
        else:
            self._set_jueri_status("Conectado")
        if self.jueri_search_panel is not None:
            client = JueriClient(JUERI_BASE_URL, credentials)
            self._jueri_categories_api = CategoriesAPI(client)
            self.jueri_search_panel.products_api = ProductsAPI(client)
            self.jueri_search_panel.categories_api = self._jueri_categories_api

    def _refresh_jueri_queue_summary(self) -> None:
        """Melhoria 3 — resumo da fila (nunca a fila completa). Chamado
        sempre que produtos são adicionados pela API Jueri, e também ao
        voltar para esta aba, para nunca mostrar números desatualizados."""
        self.jueri_queue_count_var.set(str(self.catalog_tab.print_queue.count()))
        self.jueri_queue_labels_var.set(str(self.catalog_tab.print_queue.total_labels()))
        self.jueri_queue_updated_var.set(datetime.now().strftime("%H:%M"))

    def _on_search_jueri_product(self, prefill: dict[str, str] | None = None) -> None:
        """Leva o usuário à pesquisa Jueri embutida; nunca abre Toplevel."""
        self.notebook.select(self.jueri_tab_frame)
        if self.jueri_search_panel is None:
            return
        if prefill:
            filters = dict(self.jueri_search_panel.get_filter_state())
            filters.update(
                {
                    "query": prefill.get("query", ""),
                    "data_inicial": prefill.get("data_inicial", ""),
                    "data_final": prefill.get("data_final", ""),
                }
            )
            self.jueri_search_panel.apply_filter_state(filters, run_search=True)
        self.jueri_search_panel.focus_search_entry()

    def _save_jueri_search_filters(self, filters: dict[str, Any]) -> None:
        self.config["jueri_search_filters"] = dict(filters)
        self.config_manager.save(self.config)

    def _on_jueri_search_completed(self, panel: JueriSearchPanel) -> None:
        self.jueri_last_search_results = list(panel.results)
        self._record_jueri_search_history(panel)
        self._update_jueri_sync_status()

    def _on_jueri_products_selected(self, products: list[Product]) -> None:
        """Produtos escolhidos na pesquisa Jueri entram na MESMA fila de
        impressão (PrintQueue) que a aba Planilha Excel usa — nenhuma
        lógica de fila é implementada aqui: só converte cada produto
        (Product.to_catalog_product()) e delega para
        CatalogTab.add_product_to_queue(). Também espelha o resultado
        completo da última pesquisa (não só os selecionados) na tabela
        desta aba, para que ela funcione como histórico temporário.

        Não muda mais de aba automaticamente (Melhoria 1) — o usuário
        continua na API Jueri e só vê a fila quando clicar manualmente em
        Planilha Excel."""
        added = 0
        updated = 0
        for product in products:
            catalog_product = self._map_jueri_product_for_print(product)
            if self.catalog_tab.print_queue.contains(catalog_product):
                updated += 1
            else:
                added += 1
            self.catalog_tab.add_product_to_queue(catalog_product)

        self._refresh_jueri_queue_summary()

    def _map_jueri_product_for_print(self, product: Product) -> CatalogProduct:
        """Mapeia a classificação usada na etiqueta sem alterar Product.

        A API continua entregando os mesmos IDs e o conversor continua
        produzindo o mesmo CatalogProduct. Somente o valor de `categoria`
        usado pela fila recebe o nome da subcategoria vigente no Jueri.
        """
        catalog_product = product.to_catalog_product()
        subcategoria = None
        if self._jueri_categories_api is not None:
            subcategoria = self._jueri_categories_api.nome_subcategoria(product.fk_subcategoria_id)
        return replace(catalog_product, categoria=subcategoria or "")

    def _record_jueri_search_history(self, dialog: JueriSearchPanel) -> None:
        entry = {
            "label": self._describe_jueri_search(dialog),
            "query": dialog.search_var.get().strip(),
            "data_inicial": dialog.data_inicial_var.get().strip(),
            "data_final": dialog.data_final_var.get().strip(),
        }
        self.jueri_search_history = [
            item for item in self.jueri_search_history if item["label"] != entry["label"]
        ]
        self.jueri_search_history.insert(0, entry)
        self.jueri_search_history = self.jueri_search_history[:JUERI_RESULTS_MAX_HISTORY]
        self._render_jueri_history_buttons()

    @staticmethod
    def _describe_jueri_search(dialog: JueriSearchPanel) -> str:
        query = dialog.search_var.get().strip()
        if query:
            return query

        inicio = dialog.data_inicial_var.get().strip()
        fim = dialog.data_final_var.get().strip()
        if inicio and fim:
            if inicio == fim:
                if inicio == today_br():
                    return "Hoje"
                if inicio == yesterday_br():
                    return "Ontem"
                return inicio
            return f"{inicio} a {fim}"

        return "Todos os produtos"

    def _render_jueri_history_buttons(self) -> None:
        for child in self.jueri_history_row.winfo_children():
            child.destroy()

        if not self.jueri_search_history:
            ttk.Label(
                self.jueri_history_row, text="Nenhuma pesquisa realizada ainda.", style="Subtitle.TLabel"
            ).pack(side="left")
            return

        for entry in self.jueri_search_history:
            chip = ttk.Frame(self.jueri_history_row)
            chip.pack(side="left", padx=(0, 8))
            ttk.Button(
                chip,
                text=entry["label"],
                style="App.TButton",
                command=lambda entry=entry: self._on_search_jueri_product(prefill=entry),
            ).pack(side="left")
            ttk.Button(
                chip,
                text="☆",
                width=2,
                command=lambda entry=entry: self._on_add_jueri_favorite(entry),
            ).pack(side="left", padx=(2, 0))

    # ------------------------------------------------------------------
    # Melhoria 4 — Favoritos: mesmo formato de entrada do histórico
    # (label/query/data_inicial/data_final), persistidos em config.json.
    # ------------------------------------------------------------------

    def _render_jueri_favorite_buttons(self) -> None:
        for child in self.jueri_favorites_row.winfo_children():
            child.destroy()

        if not self.jueri_favorite_searches:
            ttk.Label(
                self.jueri_favorites_row, text="Nenhuma pesquisa favoritada ainda.", style="Subtitle.TLabel"
            ).pack(side="left")
            return

        for entry in self.jueri_favorite_searches:
            chip = ttk.Frame(self.jueri_favorites_row)
            chip.pack(side="left", padx=(0, 8))
            ttk.Button(
                chip,
                text=f"★ {entry['label']}",
                style="App.TButton",
                command=lambda entry=entry: self._on_search_jueri_product(prefill=entry),
            ).pack(side="left")
            ttk.Button(
                chip,
                text="×",
                width=2,
                command=lambda entry=entry: self._on_remove_jueri_favorite(entry),
            ).pack(side="left", padx=(2, 0))

    def _on_add_jueri_favorite(self, entry: dict[str, str]) -> None:
        if any(favorite["label"] == entry["label"] for favorite in self.jueri_favorite_searches):
            return
        self.jueri_favorite_searches.append(dict(entry))
        self._save_jueri_favorites()
        self._render_jueri_favorite_buttons()

    def _on_remove_jueri_favorite(self, entry: dict[str, str]) -> None:
        self.jueri_favorite_searches = [
            favorite for favorite in self.jueri_favorite_searches if favorite["label"] != entry["label"]
        ]
        self._save_jueri_favorites()
        self._render_jueri_favorite_buttons()

    def _save_jueri_favorites(self) -> None:
        self.config["jueri_favorites"] = list(self.jueri_favorite_searches)
        self.config_manager.save(self.config)

    def _resolve_jueri_category(self, product: Product) -> str | None:
        if self._jueri_categories_api is None:
            return None
        return self._jueri_categories_api.nome_categoria(product.fk_categoria_id)

    def _resolve_jueri_subcategory(self, product: Product) -> str | None:
        if self._jueri_categories_api is None:
            return None
        return self._jueri_categories_api.nome_subcategoria(product.fk_subcategoria_id)

    def _update_jueri_sync_status(self) -> None:
        self.jueri_last_sync_var.set(datetime.now().strftime("%d/%m/%Y %H:%M"))

    def _load_jueri_results_table(self) -> None:
        self.jueri_results_tree.delete(*self.jueri_results_tree.get_children())
        for index, product in enumerate(self.jueri_last_search_results):
            self.jueri_results_tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    product.codigo_barras or "—",
                    product.descricao or "—",
                    self._format_jueri_price(product.preco_principal),
                    product.numero_peca or "—",
                    self._resolve_jueri_subcategory(product) or "—",
                    self._resolve_jueri_category(product) or "—",
                    self._format_jueri_stock(product.quantidade),
                    self._format_jueri_date(product.data_criacao),
                ),
            )
        self.jueri_result_count_var.set(str(len(self.jueri_last_search_results)))

    def _on_sort_jueri_column(self, column: str) -> None:
        self.jueri_last_search_results = self._jueri_sorter.sort(self.jueri_last_search_results, column)
        self._load_jueri_results_table()

    def _on_jueri_select_all_shortcut(self, _event: Any = None) -> str:
        self.jueri_results_tree.selection_set(self.jueri_results_tree.get_children())
        return "break"

    def _on_add_jueri_selection_to_queue(self) -> None:
        """Reenvia à fila produtos já presentes na tabela de histórico —
        útil quando o usuário quer adicionar de novo sem reabrir a
        pesquisa. Mesma conversão/destino que a confirmação da janela de
        pesquisa usa (Product.to_catalog_product() -> CatalogTab). Não
        muda de aba (Melhoria 1)."""
        selected_ids = self.jueri_results_tree.selection()
        if not selected_ids:
            messagebox.showinfo(APP_TITLE, "Selecione ao menos um produto para adicionar à fila.")
            return

        products = [
            self.jueri_last_search_results[int(iid)]
            for iid in selected_ids
            if 0 <= int(iid) < len(self.jueri_last_search_results)
        ]
        added = 0
        updated = 0
        for product in products:
            catalog_product = self._map_jueri_product_for_print(product)
            if self.catalog_tab.print_queue.contains(catalog_product):
                updated += 1
            else:
                added += 1
            self.catalog_tab.add_product_to_queue(catalog_product)

        self._refresh_jueri_queue_summary()
        if self.jueri_search_panel is not None:
            self.jueri_search_panel.feedback_var.set(describe_queue_addition(added, updated))

    def _on_clear_jueri_results(self) -> None:
        self.jueri_last_search_results = []
        self._load_jueri_results_table()

    @staticmethod
    def _format_jueri_price(preco: float | None) -> str:
        return f"R$ {preco:.2f}" if preco is not None else "—"

    @staticmethod
    def _format_jueri_stock(quantidade: int | None) -> str:
        return str(quantidade) if quantidade is not None else "—"

    @staticmethod
    def _format_jueri_date(raw: str | None) -> str:
        if not raw:
            return "—"
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(raw, fmt).strftime("%d/%m/%Y")
            except ValueError:
                continue
        return str(raw)
