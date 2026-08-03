"""Interface principal do Santa Rubi Label Studio.

Duas abas: "API Jueri" (pesquisa e integração com a API Jueri) e
"Planilha Excel" (catálogo, fila de impressão e disparo da impressão —
implementada em ui/catalog_tab.py). Esta janela apresenta a estrutura
visual, sem lógica de negócio: pesquisa/ordenação/filtro vivem em
core/, a fila de impressão em core/print_queue.py.
"""

from __future__ import annotations

import tkinter as tk
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
from core.config import ConfigManager
from core.queue_feedback import describe_queue_addition
from core.table_state import apply_column_widths, apply_sorter_state, get_column_widths, get_sorter_state
from ui.catalog_tab import CatalogTab
from ui.product_search_dialog import ProductSearchDialog
from ui.settings_dialog import SettingsDialog
from ui.toast import Toast
from ui.treeview_selection import enable_drag_selection

APP_TITLE = "Santa Rubi Label Studio"
WINDOW_SIZE = "1000x700"

JUERI_RESULTS_MAX_HISTORY = 6

JUERI_RESULTS_COLUMNS: dict[str, tuple[str, str, int, bool]] = {
    # coluna: (texto do cabeçalho, alinhamento, largura, expande)
    "codigo": ("Código", "w", 100, False),
    "descricao": ("Descrição", "w", 320, True),
    "categoria": ("Categoria", "w", 160, False),
    "estoque": ("Estoque", "center", 90, False),
    "cadastro": ("Cadastro", "center", 110, False),
    "preco": ("Preço", "e", 100, False),
}


class MainWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)

        self.config_manager = ConfigManager()
        self.config: dict[str, Any] = self.config_manager.load()

        window_state = self.config.get("window_state", "zoomed")
        self.root.geometry(self.config.get("window_geometry", WINDOW_SIZE))
        self.root.minsize(1000, 700)
        if window_state == "zoomed":
            self.root.state("zoomed")
        self.root.configure(bg="#f4f6f8")

        # Cache em memória do CategoriesAPI — carregado uma única vez, no
        # primeiro uso, e reaproveitado em todas as pesquisas Jueri seguintes.
        self._jueri_categories_api: CategoriesAPI | None = None
        self._jueri_dialog: ProductSearchDialog | None = None
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
        self.jueri_client_var = tk.StringVar(value="—")
        self.jueri_last_sync_var = tk.StringVar(value="Nunca")
        self.jueri_result_count_var = tk.StringVar(value="0")
        self.jueri_queue_count_var = tk.StringVar(value="0")
        self.jueri_queue_labels_var = tk.StringVar(value="0")
        self.jueri_queue_updated_var = tk.StringVar(value="—")

        self._setup_style()
        self._build_widgets()

    def _setup_style(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("TLabel", font=("Segoe UI", 10))
        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"), foreground="#0f172a")
        style.configure("Subtitle.TLabel", font=("Segoe UI", 10), foreground="#64748b")
        style.configure("Header.TFrame", background="#ffffff")
        style.configure("Sidebar.TFrame", background="#111827")
        style.configure("Sidebar.TLabel", foreground="#f8fafc", background="#111827")
        style.configure("Sidebar.TRadiobutton", foreground="#f8fafc", background="#111827")
        style.configure("DetailValue.TLabel", foreground="#334155", background="#ffffff")
        style.configure("Content.TFrame", background="#f4f6f8")
        style.configure("Card.TFrame", background="#ffffff")
        style.configure("Slim.Horizontal.TProgressbar", thickness=18)
        style.configure("App.TButton", font=("Segoe UI", 10), padding=(10, 8))
        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), padding=(10, 8))
        style.map(
            "Primary.TButton",
            background=[("active", "#2563eb"), ("!disabled", "#1d4ed8")],
            foreground=[("active", "#ffffff"), ("!disabled", "#ffffff")],
        )

    def _build_widgets(self):
        app_header = ttk.Frame(self.root, style="Header.TFrame", padding=(16, 12))
        app_header.pack(fill="x")
        app_header.grid_columnconfigure(0, weight=1)
        ttk.Label(app_header, text=APP_TITLE, style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Button(
            app_header, text="Configurações", style="App.TButton", command=self._open_settings
        ).grid(row=0, column=1, sticky="e")

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)
        self.notebook.bind("<<NotebookTabChanged>>", self._on_notebook_tab_changed)

        self._build_jueri_tab()
        self._build_catalog_tab()

        self.catalog_tab.apply_persisted_state(self.config.get("catalog_state", {}))
        self._refresh_jueri_queue_summary()

        last_tab_index = self.config.get("last_tab_index", 0)
        if last_tab_index in (0, 1):
            self.notebook.select(last_tab_index)

        self._bind_shortcuts()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _bind_shortcuts(self) -> None:
        """Melhoria 6 — atalhos globais. F3/Ctrl+P/Ctrl+L funcionam com
        qualquer aba em foco; Ctrl+F muda para a Planilha Excel e foca a
        pesquisa de lá (ESC/ENTER da janela de pesquisa Jueri vivem em
        ui/product_search_dialog.py, que é uma janela independente)."""
        self.root.bind_all("<F3>", lambda _event: self._on_search_jueri_product())
        self.root.bind_all("<Control-f>", self._on_ctrl_f_shortcut)
        self.root.bind_all("<Control-F>", self._on_ctrl_f_shortcut)
        self.root.bind_all("<Control-p>", lambda _event: self.catalog_tab._on_print_queue())
        self.root.bind_all("<Control-P>", lambda _event: self.catalog_tab._on_print_queue())
        self.root.bind_all("<Control-l>", lambda _event: self.catalog_tab._on_clear_queue())
        self.root.bind_all("<Control-L>", lambda _event: self.catalog_tab._on_clear_queue())

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
        self.config_manager.save(self.config)

    # ------------------------------------------------------------------
    # Aba "API Jueri" — painel de integração + resumo da fila + favoritos
    # + histórico de pesquisas + resultado da última pesquisa. Nenhuma
    # lógica de pesquisa/paginação é feita aqui: a janela
    # ProductSearchDialog é quem consulta a ProductsAPI; esta aba só
    # espelha o resultado já obtido por ela.
    # ------------------------------------------------------------------

    def _build_jueri_tab(self) -> None:
        self.jueri_tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.jueri_tab_frame, text="API Jueri")

        container = ttk.Frame(self.jueri_tab_frame, style="Content.TFrame", padding=16)
        container.pack(fill="both", expand=True)
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(3, weight=1)

        top_row = ttk.Frame(container)
        top_row.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        top_row.grid_columnconfigure(0, weight=1)
        top_row.grid_columnconfigure(1, weight=0, minsize=240)
        self._build_jueri_integration_panel(top_row)
        self._build_jueri_queue_summary_panel(top_row)

        self._build_jueri_favorites_panel(container)
        self._build_jueri_history_panel(container)
        self._build_jueri_results_panel(container)

        self._render_jueri_favorite_buttons()
        self._render_jueri_history_buttons()
        self._refresh_jueri_connection_status()
        self._load_jueri_results_table()

    def _build_stat_cell(
        self, parent: ttk.Frame, row: int, column: int, label_text: str, value_var: tk.StringVar, columnspan: int = 1
    ) -> None:
        cell = ttk.Frame(parent)
        cell.grid(row=row, column=column, columnspan=columnspan, sticky="w", padx=(0, 24), pady=(0, 4))
        ttk.Label(cell, text=label_text, style="Subtitle.TLabel").pack(anchor="w")
        ttk.Label(cell, textvariable=value_var, font=("Segoe UI", 11, "bold")).pack(anchor="w")

    def _build_jueri_integration_panel(self, parent: ttk.Frame) -> None:
        panel = ttk.Frame(parent, style="Card.TFrame", padding=16)
        panel.grid(row=0, column=0, sticky="nsew")
        panel.grid_columnconfigure(4, weight=1)

        ttk.Label(panel, text="Integração Jueri", font=("Segoe UI", 13, "bold")).grid(
            row=0, column=0, columnspan=5, sticky="w", pady=(0, 12)
        )

        self._build_stat_cell(panel, 1, 0, "Status da conexão", self.jueri_status_var)
        self._build_stat_cell(panel, 1, 1, "Cliente", self.jueri_client_var)
        self._build_stat_cell(panel, 1, 2, "Última sincronização", self.jueri_last_sync_var)
        self._build_stat_cell(panel, 1, 3, "Produtos encontrados", self.jueri_result_count_var)

        ttk.Button(
            panel,
            text="Pesquisar Produtos (F3)",
            style="Primary.TButton",
            command=lambda: self._on_search_jueri_product(),
        ).grid(row=1, column=4, sticky="e", padx=(12, 0))

    def _build_jueri_queue_summary_panel(self, parent: ttk.Frame) -> None:
        panel = ttk.Frame(parent, style="Card.TFrame", padding=16)
        panel.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_columnconfigure(1, weight=1)

        ttk.Label(panel, text="Fila de Impressão", font=("Segoe UI", 12, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 10)
        )
        self._build_stat_cell(panel, 1, 0, "Produtos", self.jueri_queue_count_var)
        self._build_stat_cell(panel, 1, 1, "Etiquetas", self.jueri_queue_labels_var)
        self._build_stat_cell(panel, 2, 0, "Última atualização", self.jueri_queue_updated_var, columnspan=2)

    def _build_jueri_favorites_panel(self, container: ttk.Frame) -> None:
        favorites_panel = ttk.LabelFrame(container, text="Pesquisas Favoritas", padding=12)
        favorites_panel.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        self.jueri_favorites_row = ttk.Frame(favorites_panel)
        self.jueri_favorites_row.pack(fill="x", anchor="w")

    def _build_jueri_history_panel(self, container: ttk.Frame) -> None:
        history_panel = ttk.LabelFrame(container, text="Pesquisas Recentes", padding=12)
        history_panel.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        self.jueri_history_row = ttk.Frame(history_panel)
        self.jueri_history_row.pack(fill="x", anchor="w")

    def _build_jueri_results_panel(self, container: ttk.Frame) -> None:
        results_panel = ttk.LabelFrame(container, text="Resultado da Última Pesquisa", padding=12)
        results_panel.grid(row=3, column=0, sticky="nsew")
        results_panel.grid_columnconfigure(0, weight=1)
        results_panel.grid_rowconfigure(0, weight=1)

        table_frame = ttk.Frame(results_panel)
        table_frame.grid(row=0, column=0, sticky="nsew")
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)

        columns = tuple(JUERI_RESULTS_COLUMNS.keys())
        self.jueri_results_tree = ttk.Treeview(
            table_frame, columns=columns, show="headings", selectmode="extended"
        )
        self.jueri_results_tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.jueri_results_tree.yview)
        self.jueri_results_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        for column, (text, anchor, width, stretch) in JUERI_RESULTS_COLUMNS.items():
            self.jueri_results_tree.heading(
                column, text=text, command=lambda c=column: self._on_sort_jueri_column(c), anchor=anchor
            )
            self.jueri_results_tree.column(column, anchor=anchor, width=width, minwidth=70, stretch=stretch)

        apply_column_widths(self.jueri_results_tree, self.config.get("jueri_results_column_widths", {}))
        apply_sorter_state(self._jueri_sorter, self.config.get("jueri_results_sort"))

        enable_drag_selection(self.jueri_results_tree)
        self.jueri_results_tree.bind("<Control-a>", self._on_jueri_select_all_shortcut)
        self.jueri_results_tree.bind("<Control-A>", self._on_jueri_select_all_shortcut)

        footer = ttk.Frame(results_panel)
        footer.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        footer.grid_columnconfigure(0, weight=1)
        self.jueri_toast_label = tk.Label(footer, text="", font=("Segoe UI", 9, "bold"), anchor="w", justify="left")
        self.jueri_toast_label.grid(row=0, column=0, sticky="w")
        self.jueri_toast = Toast(self.jueri_toast_label)

        buttons_row = ttk.Frame(footer)
        buttons_row.grid(row=0, column=1, sticky="e")
        ttk.Button(
            buttons_row, text="Nova Pesquisa", style="App.TButton", command=lambda: self._on_search_jueri_product()
        ).pack(side="left", padx=(0, 8))
        ttk.Button(
            buttons_row,
            text="Adicionar Selecionados à Fila",
            style="Primary.TButton",
            command=self._on_add_jueri_selection_to_queue,
        ).pack(side="left", padx=(0, 8))
        ttk.Button(
            buttons_row, text="Limpar Resultado", style="App.TButton", command=self._on_clear_jueri_results
        ).pack(side="left")

    def _build_catalog_tab(self) -> None:
        self.catalog_tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.catalog_tab_frame, text="Planilha Excel")
        self.catalog_tab = CatalogTab(self.catalog_tab_frame, self.config_manager, self.config)

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self.root, self.config_manager, self.config)
        self.root.wait_window(dialog)
        self._refresh_jueri_connection_status()

    def _refresh_jueri_connection_status(self) -> None:
        credentials = JueriCredentials.from_config(self.config)
        if not credentials.enabled:
            self.jueri_status_var.set("Desabilitada")
        elif not credentials.cliente_sistema or not credentials.token:
            self.jueri_status_var.set("Credenciais incompletas")
        else:
            self.jueri_status_var.set("Habilitada")
        self.jueri_client_var.set(credentials.cliente_sistema or "—")

    def _refresh_jueri_queue_summary(self) -> None:
        """Melhoria 3 — resumo da fila (nunca a fila completa). Chamado
        sempre que produtos são adicionados pela API Jueri, e também ao
        voltar para esta aba, para nunca mostrar números desatualizados."""
        self.jueri_queue_count_var.set(str(self.catalog_tab.print_queue.count()))
        self.jueri_queue_labels_var.set(str(self.catalog_tab.print_queue.total_labels()))
        self.jueri_queue_updated_var.set(datetime.now().strftime("%H:%M"))

    def _on_search_jueri_product(self, prefill: dict[str, str] | None = None) -> None:
        """Abre a pesquisa de produtos Jueri — produtos escolhidos vão
        para a mesma fila de impressão da aba Planilha Excel. `prefill`
        (usado pelos botões de "Pesquisas Recentes"/"Pesquisas Favoritas")
        reabre a janela já com o mesmo texto/intervalo de datas de uma
        pesquisa anterior. Se a janela já estiver aberta, só traz ela para
        frente em vez de abrir uma segunda (F3 pode ser pressionado com o
        diálogo em foco)."""
        if self._jueri_dialog is not None and self._jueri_dialog.winfo_exists():
            self._jueri_dialog.lift()
            self._jueri_dialog.focus_force()
            return

        credentials = JueriCredentials.from_config(self.config)
        if not credentials.enabled:
            messagebox.showwarning(
                APP_TITLE,
                "A integração com o Jueri está desabilitada. Habilite em "
                "Configurações antes de pesquisar.",
            )
            return

        client = JueriClient(JUERI_BASE_URL, credentials)
        products_api = ProductsAPI(client)
        if self._jueri_categories_api is None:
            self._jueri_categories_api = CategoriesAPI(client)

        prefill = prefill or {}
        self._jueri_dialog = ProductSearchDialog(
            self.root,
            products_api,
            on_add_selected=self._on_jueri_products_selected,
            initial_query=prefill.get("query", ""),
            initial_data_inicial=prefill.get("data_inicial", ""),
            initial_data_final=prefill.get("data_final", ""),
        )

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
            catalog_product = product.to_catalog_product(self._jueri_categories_api)
            if self.catalog_tab.print_queue.contains(catalog_product):
                updated += 1
            else:
                added += 1
            self.catalog_tab.add_product_to_queue(catalog_product)

        if self._jueri_dialog is not None:
            self._record_jueri_search_history(self._jueri_dialog)
            self.jueri_last_search_results = list(self._jueri_dialog.results)
            self._load_jueri_results_table()
            self._update_jueri_sync_status()

        self._refresh_jueri_queue_summary()
        self.jueri_toast.show(describe_queue_addition(added, updated))

    def _record_jueri_search_history(self, dialog: ProductSearchDialog) -> None:
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
    def _describe_jueri_search(dialog: ProductSearchDialog) -> str:
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
                    self._resolve_jueri_category(product) or "—",
                    self._format_jueri_stock(product.quantidade),
                    self._format_jueri_date(product.data_criacao),
                    self._format_jueri_price(product.preco_principal),
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
            catalog_product = product.to_catalog_product(self._jueri_categories_api)
            if self.catalog_tab.print_queue.contains(catalog_product):
                updated += 1
            else:
                added += 1
            self.catalog_tab.add_product_to_queue(catalog_product)

        self._refresh_jueri_queue_summary()
        self.jueri_toast.show(describe_queue_addition(added, updated))

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
