"""Janela "Pesquisar Produtos" — pesquisa de produtos via API Jueri.

Independente da tela principal, mas alimenta a MESMA fila de impressão
que o Catálogo Integrado usa: "Adicionar Selecionados" converte cada
produto escolhido para CatalogProduct (Product.to_catalog_product()) e
entrega para quem estiver ouvindo via `on_add_selected` — nenhuma lógica
de fila é implementada aqui, só a seleção múltipla e a conversão.

Ao abrir, carrega automaticamente a primeira página (sem filtro de busca).
O botão "Atualizar" repete a busca atual imediatamente, ignorando o
debounce de digitação.

Também aceita colar uma LISTA de códigos (separados por vírgula, ponto e
vírgula, quebra de linha, ou espaço) em vez de um único termo — ver
parse_multiple_codes().

E também filtra por data de cadastro (Data Inicial/Data Final, com atalhos
Hoje/Ontem). Quando um filtro de data está ativo, a pesquisa percorre
automaticamente todas as páginas da API (ver ProductsAPI.search_all_pages)
— o usuário recebe todos os produtos do período, não só os primeiros.

Seleção múltipla: o usuário pode marcar vários produtos (Ctrl/Shift-click,
ou "Selecionar Todos") e clicar "Adicionar Selecionados" quantas vezes
quiser — a janela NÃO fecha sozinha, só quando o usuário clicar Cancelar.
Duplo-clique numa linha adiciona só aquele produto, sem fechar também.
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import ttk
from typing import Any, Callable

from app.api.categories import CategoriesAPI
from app.api.date_filters import DateFilterError, build_date_range_filter, today_br, yesterday_br
from app.api.exceptions import JueriError
from app.api.product import Product
from app.api.products import ProductsAPI
from core.column_sort import ColumnSorter, SortDirection, numeric_or_text, sort_items
from core.text_normalize import parse_multiple_codes
from ui.treeview_selection import enable_drag_selection

DEBOUNCE_MS = 300
STOCK_ALL = "Todos"
STOCK_AVAILABLE = "Com estoque"
STOCK_EMPTY = "Sem estoque"
CATEGORY_ALL = "Todas as categorias"
SUPPLIER_UNAVAILABLE = "Indisponível na API Jueri"

SORT_OPTIONS = {
    "Código": "codigo",
    "Descrição": "descricao",
    "Data de cadastro": "cadastro",
    "Preço": "preco",
    "Estoque": "estoque",
}
DIRECTION_OPTIONS = {"Crescente": SortDirection.ASCENDING, "Decrescente": SortDirection.DESCENDING}

# Mesmo componente de ordenação usado por ui/catalog_tab.py — código e
# peso são numéricos (codigo_barras é sempre 6 dígitos, mas numeric_or_text
# cai para texto com segurança se algum dia não for), descrição é texto.
_SORT_KEY_FUNCS = {
    "codigo": lambda product: numeric_or_text(product.codigo_barras),
    "descricao": lambda product: product.descricao,
    "preco": lambda product: product.preco_principal,
    "peso": lambda product: product.peso,
    "cadastro": lambda product: product.data_criacao,
    "estoque": lambda product: product.quantidade,
}


def filter_products(
    products: list[Product],
    stock_filter: str = STOCK_ALL,
    category_id: int | None = None,
) -> list[Product]:
    """Aplica apenas filtros que usam campos efetivamente presentes no produto Jueri."""
    filtered = list(products)
    if stock_filter == STOCK_AVAILABLE:
        filtered = [product for product in filtered if product.quantidade is not None and product.quantidade > 0]
    elif stock_filter == STOCK_EMPTY:
        filtered = [product for product in filtered if product.quantidade == 0]
    if category_id is not None:
        filtered = [product for product in filtered if product.fk_categoria_id == category_id]
    return filtered


class JueriSearchPanel(ttk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        products_api: ProductsAPI,
        on_add_selected: Callable[[list[Product]], None] | None = None,
        initial_query: str = "",
        initial_data_inicial: str = "",
        initial_data_final: str = "",
        categories_api: CategoriesAPI | None = None,
        initial_filters: dict[str, Any] | None = None,
        on_filters_changed: Callable[[dict[str, Any]], None] | None = None,
        on_status_changed: Callable[[str], None] | None = None,
        on_search_completed: Callable[["JueriSearchPanel"], None] | None = None,
        on_close: Callable[[], None] | None = None,
        async_search: bool = False,
        auto_search: bool = True,
    ) -> None:
        super().__init__(parent)

        self.products_api = products_api
        self.categories_api = categories_api
        self.on_add_selected = on_add_selected
        self.on_filters_changed = on_filters_changed
        self.on_status_changed = on_status_changed
        self.on_search_completed = on_search_completed
        self.on_close = on_close
        self.async_search = async_search
        self.results: list[Product] = []
        self._source_results: list[Product] = []
        self._debounce_job: str | None = None
        self._poll_job: str | None = None
        self._search_generation = 0
        self._search_in_progress = False
        self._loaded_complete = False
        self._header_sort_column: str | None = None
        self._sorter = ColumnSorter(_SORT_KEY_FUNCS)
        self._sorter.key_funcs["categoria"] = lambda product: self._category_name(product)

        saved = initial_filters or {}
        self.search_var = tk.StringVar(value=initial_query or str(saved.get("query", "")))
        self.data_inicial_var = tk.StringVar(value=initial_data_inicial or str(saved.get("data_inicial", "")))
        self.data_final_var = tk.StringVar(value=initial_data_final or str(saved.get("data_final", "")))
        saved_stock = str(saved.get("stock", STOCK_ALL))
        self.stock_var = tk.StringVar(
            value=saved_stock if saved_stock in (STOCK_ALL, STOCK_AVAILABLE, STOCK_EMPTY) else STOCK_ALL
        )
        self.category_var = tk.StringVar(value=str(saved.get("category", CATEGORY_ALL)))
        saved_sort = str(saved.get("sort", "Código"))
        self.sort_var = tk.StringVar(value=saved_sort if saved_sort in SORT_OPTIONS else "Código")
        saved_direction = str(saved.get("direction", "Crescente"))
        self.direction_var = tk.StringVar(
            value=saved_direction if saved_direction in DIRECTION_OPTIONS else "Crescente"
        )
        self._category_ids_by_name: dict[str, int] = {}
        initial_status = "Carregando produtos..." if auto_search else "Configure a integração Jueri para pesquisar."
        self.status_var = tk.StringVar(value=initial_status)
        self.selection_count_var = tk.StringVar(value="0 produto(s) selecionado(s).")
        self.feedback_var = tk.StringVar(value="")

        self._build_widgets()
        self.bind("<Return>", lambda _event: self._on_refresh())
        self.bind("<Destroy>", self._on_destroy, add="+")
        if auto_search:
            self._run_search()

    def _build_widgets(self) -> None:
        container = ttk.Frame(self, padding=(8, 6))
        container.pack(fill="both", expand=True)
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(5, weight=1)

        ttk.Label(container, text="Pesquisar por código ou descrição").grid(row=0, column=0, sticky="w")
        search_row = ttk.Frame(container)
        search_row.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(2, 4))
        search_row.grid_columnconfigure(0, weight=1)

        self.search_entry = ttk.Entry(search_row, textvariable=self.search_var)
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.search_var.trace_add("write", lambda *_args: self._on_search_changed())

        ttk.Button(search_row, text="Atualizar", style="App.TButton", command=self._on_refresh).grid(
            row=0, column=1, padx=(0, 6)
        )
        ttk.Button(search_row, text="Limpar Filtros", style="App.TButton", command=self._on_clear_filters).grid(
            row=0, column=2
        )

        filter_row = ttk.Frame(container)
        filter_row.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        for column in range(4):
            filter_row.grid_columnconfigure(column, weight=1)

        ttk.Label(filter_row, text="Estoque").grid(row=0, column=0, sticky="w")
        stock_combo = ttk.Combobox(
            filter_row,
            textvariable=self.stock_var,
            values=[STOCK_ALL, STOCK_AVAILABLE, STOCK_EMPTY],
            state="readonly",
        )
        stock_combo.grid(row=1, column=0, sticky="ew", padx=(0, 8))
        stock_combo.bind("<<ComboboxSelected>>", self._on_server_filter_changed)

        ttk.Label(filter_row, text="Categoria").grid(row=0, column=1, sticky="w")
        self.category_combobox = ttk.Combobox(
            filter_row, textvariable=self.category_var, values=[CATEGORY_ALL], state="readonly"
        )
        self.category_combobox.grid(row=1, column=1, sticky="ew", padx=(0, 8))
        self.category_combobox.bind("<<ComboboxSelected>>", self._on_server_filter_changed)

        ttk.Label(filter_row, text="Ordenar por").grid(row=0, column=2, sticky="w")
        sort_combo = ttk.Combobox(
            filter_row, textvariable=self.sort_var, values=list(SORT_OPTIONS), state="readonly"
        )
        sort_combo.grid(row=1, column=2, sticky="ew", padx=(0, 8))
        sort_combo.bind("<<ComboboxSelected>>", self._on_local_filter_changed)

        ttk.Label(filter_row, text="Direção").grid(row=0, column=3, sticky="w")
        direction_combo = ttk.Combobox(
            filter_row, textvariable=self.direction_var, values=list(DIRECTION_OPTIONS), state="readonly"
        )
        direction_combo.grid(row=1, column=3, sticky="ew")
        direction_combo.bind("<<ComboboxSelected>>", self._on_local_filter_changed)

        date_row = ttk.Frame(container)
        date_row.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        date_row.grid_columnconfigure(0, weight=1)
        date_row.grid_columnconfigure(1, weight=1)

        inicial_col = ttk.Frame(date_row)
        inicial_col.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ttk.Label(inicial_col, text="Data Inicial:").pack(anchor="w")
        inicial_entry = ttk.Entry(inicial_col, textvariable=self.data_inicial_var)
        inicial_entry.pack(fill="x", pady=(2, 0))
        self.data_inicial_var.trace_add("write", lambda *_args: self._on_search_changed())

        final_col = ttk.Frame(date_row)
        final_col.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        ttk.Label(final_col, text="Data Final:").pack(anchor="w")
        final_entry = ttk.Entry(final_col, textvariable=self.data_final_var)
        final_entry.pack(fill="x", pady=(2, 0))
        self.data_final_var.trace_add("write", lambda *_args: self._on_search_changed())

        quick_buttons_row = ttk.Frame(date_row)
        quick_buttons_row.grid(row=0, column=2, sticky="s")
        ttk.Button(quick_buttons_row, text="Hoje", style="App.TButton", command=self._on_quick_today).pack(
            side="left", padx=(0, 4)
        )
        ttk.Button(
            quick_buttons_row, text="Ontem", style="App.TButton", command=self._on_quick_yesterday
        ).pack(side="left", padx=(0, 4))
        ttk.Button(
            quick_buttons_row, text="Limpar Datas", style="App.TButton", command=self._on_clear_dates
        ).pack(side="left")

        columns = (
            "codigo",
            "descricao",
            "preco",
            "numeracao",
            "subcategoria",
            "categoria",
            "estoque",
            "cadastro",
        )
        self.results_tree = ttk.Treeview(container, columns=columns, show="headings", selectmode="extended")
        self.results_tree.heading("codigo", text="Código", command=lambda: self._on_sort_column("codigo"))
        self.results_tree.heading(
            "descricao", text="Descrição", command=lambda: self._on_sort_column("descricao")
        )
        self.results_tree.heading("preco", text="Preço", command=lambda: self._on_sort_column("preco"))
        self.results_tree.heading("numeracao", text="Numeração")
        self.results_tree.heading("subcategoria", text="Subcategoria")
        self.results_tree.heading("categoria", text="Categoria", command=lambda: self._on_sort_column("categoria"))
        self.results_tree.heading("estoque", text="Estoque", command=lambda: self._on_sort_column("estoque"))
        self.results_tree.heading("cadastro", text="Cadastro", command=lambda: self._on_sort_column("cadastro"))
        self.results_tree.column("codigo", width=80, minwidth=65, anchor="w", stretch=False)
        self.results_tree.column("descricao", width=220, minwidth=140, anchor="w", stretch=True)
        self.results_tree.column("preco", width=80, minwidth=70, anchor="e", stretch=False)
        self.results_tree.column("numeracao", width=75, minwidth=65, anchor="center", stretch=False)
        self.results_tree.column("subcategoria", width=140, minwidth=90, anchor="w", stretch=False)
        self.results_tree.column("categoria", width=110, minwidth=80, anchor="w", stretch=False)
        self.results_tree.column("estoque", width=60, minwidth=55, anchor="center", stretch=False)
        self.results_tree.column("cadastro", width=85, minwidth=80, anchor="center", stretch=False)
        ttk.Label(container, textvariable=self.status_var, style="Subtitle.TLabel").grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(0, 4)
        )

        self.results_tree.grid(row=5, column=0, sticky="nsew")
        self.results_tree.bind("<Double-1>", lambda _event: self._on_double_click_add())
        self.results_tree.bind("<<TreeviewSelect>>", lambda _event: self._update_selection_count())
        enable_drag_selection(self.results_tree)

        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.results_tree.yview)
        horizontal_scrollbar = ttk.Scrollbar(container, orient="horizontal", command=self.results_tree.xview)
        self.results_tree.configure(
            yscrollcommand=scrollbar.set,
            xscrollcommand=horizontal_scrollbar.set,
        )
        scrollbar.grid(row=5, column=1, sticky="ns")
        horizontal_scrollbar.grid(row=6, column=0, sticky="ew")
        ttk.Label(container, textvariable=self.selection_count_var, style="Subtitle.TLabel").grid(
            row=7, column=0, sticky="w", pady=(4, 4)
        )
        ttk.Label(container, textvariable=self.feedback_var, style="Subtitle.TLabel").grid(
            row=7, column=1, sticky="e", pady=(4, 4)
        )

        button_row = ttk.Frame(container)
        button_row.grid(row=8, column=0, columnspan=2, sticky="ew")
        button_row.grid_columnconfigure(2, weight=1)
        ttk.Button(button_row, text="Selecionar Todos", style="App.TButton", command=self._on_select_all).grid(
            row=0, column=0, padx=(0, 8)
        )
        ttk.Button(
            button_row, text="Limpar Seleção", style="App.TButton", command=self._on_clear_selection
        ).grid(row=0, column=1)
        ttk.Button(
            button_row,
            text="Adicionar Selecionados",
            style="Primary.TButton",
            command=self._on_add_selected,
        ).grid(row=0, column=4)

    def _on_search_changed(self) -> None:
        if self._debounce_job is not None:
            self.after_cancel(self._debounce_job)
        self._debounce_job = self.after(DEBOUNCE_MS, self._run_search)

    def _on_refresh(self) -> None:
        """Repete a pesquisa atual imediatamente, ignorando o debounce
        (_run_search() já cancela qualquer job pendente sozinho)."""
        self._run_search()

    def _on_quick_today(self) -> None:
        self.data_inicial_var.set(today_br())
        self.data_final_var.set(today_br())
        self._on_refresh()

    def _on_quick_yesterday(self) -> None:
        self.data_inicial_var.set(yesterday_br())
        self.data_final_var.set(yesterday_br())
        self._on_refresh()

    def _on_clear_dates(self) -> None:
        self.data_inicial_var.set("")
        self.data_final_var.set("")
        self._on_refresh()

    def _on_clear_filters(self) -> None:
        self.search_var.set("")
        self.stock_var.set(STOCK_ALL)
        self.category_var.set(CATEGORY_ALL)
        self.data_inicial_var.set("")
        self.data_final_var.set("")
        self.sort_var.set("Código")
        self.direction_var.set("Crescente")
        self._on_refresh()

    def _on_server_filter_changed(self, _event: Any = None) -> None:
        self._run_search()

    def _on_local_filter_changed(self, _event: Any = None) -> None:
        self._apply_filters_and_sort()
        self._notify_filters_changed()

    def get_filter_state(self) -> dict[str, str]:
        return {
            "stock": self.stock_var.get(),
            "category": self.category_var.get(),
            "query": self.search_var.get().strip(),
            "data_inicial": self.data_inicial_var.get().strip(),
            "data_final": self.data_final_var.get().strip(),
            "sort": self.sort_var.get(),
            "direction": self.direction_var.get(),
        }

    def apply_filter_state(self, state: dict[str, str], run_search: bool = True) -> None:
        self.search_var.set(state.get("query", ""))
        stock = state.get("stock", STOCK_ALL)
        self.stock_var.set(stock if stock in (STOCK_ALL, STOCK_AVAILABLE, STOCK_EMPTY) else STOCK_ALL)
        self.category_var.set(state.get("category", CATEGORY_ALL))
        self.data_inicial_var.set(state.get("data_inicial", ""))
        self.data_final_var.set(state.get("data_final", ""))
        sort = state.get("sort", "Código")
        self.sort_var.set(sort if sort in SORT_OPTIONS else "Código")
        direction = state.get("direction", "Crescente")
        self.direction_var.set(direction if direction in DIRECTION_OPTIONS else "Crescente")
        if run_search:
            self._run_search()

    def focus_search_entry(self) -> None:
        self.search_entry.focus_set()
        if self.search_var.get():
            self.search_entry.select_range(0, tk.END)
            self.search_entry.icursor(tk.END)

    def _notify_filters_changed(self) -> None:
        if self.on_filters_changed is not None:
            self.on_filters_changed(self.get_filter_state())

    def _category_name(self, product: Product) -> str:
        if product.fk_categoria_id is None:
            return ""
        for name, category_id in self._category_ids_by_name.items():
            if category_id == product.fk_categoria_id:
                return name
        return ""

    def _subcategory_name(self, product: Product) -> str:
        if product.fk_subcategoria_id is None or self.categories_api is None:
            return ""
        resolver = getattr(self.categories_api, "nome_subcategoria", None)
        if callable(resolver):
            return resolver(product.fk_subcategoria_id) or ""
        mapping = getattr(self.categories_api, "subcategoria_por_id", {})
        return mapping.get(product.fk_subcategoria_id, "")

    def _category_id(self) -> int | None:
        return self._category_ids_by_name.get(self.category_var.get())

    def _load_category_mapping(self) -> dict[str, int]:
        if self.categories_api is None:
            return dict(self._category_ids_by_name)
        return {
            name: category_id
            for category_id, name in self.categories_api.categoria_por_id.items()
            if name
        }

    def _fetch_products(
        self,
        query: str,
        date_params: dict[str, str],
        stock_filter: str,
        category_name: str,
    ) -> tuple[list[Product], dict[str, int], bool]:
        category_mapping = self._load_category_mapping()
        category_id = category_mapping.get(category_name)
        server_filters: dict[str, Any] = dict(date_params)
        if category_id is not None:
            server_filters["categoria_id"] = category_id
        codes = parse_multiple_codes(query) if query else None
        if codes is not None:
            products = self.products_api.search_multiple_products(codes, **server_filters)
            loaded_complete = True
        elif date_params or stock_filter != STOCK_ALL or category_id is not None:
            products = self.products_api.search_all_pages(search=query or None, **server_filters)
            loaded_complete = True
        else:
            products = self.products_api.search_products(search=query or None).products
            loaded_complete = False
        return products, category_mapping, loaded_complete

    def _run_search(self) -> None:
        if self._debounce_job is not None:
            self.after_cancel(self._debounce_job)
            self._debounce_job = None
        if self._poll_job is not None:
            self.after_cancel(self._poll_job)
            self._poll_job = None

        query = self.search_var.get().strip()
        try:
            date_filter = build_date_range_filter(self.data_inicial_var.get(), self.data_final_var.get())
        except DateFilterError as exc:
            self.results_tree.delete(*self.results_tree.get_children())
            self.results = []
            self.status_var.set(str(exc))
            self._notify_filters_changed()
            return

        self._search_generation += 1
        generation = self._search_generation
        date_params = date_filter.to_params()
        stock_filter = self.stock_var.get()
        category_name = self.category_var.get()
        self._search_in_progress = True
        if self.on_status_changed is not None:
            self.on_status_changed("Atualizando")
        self.results_tree.delete(*self.results_tree.get_children())
        self.results = []
        self.status_var.set("Pesquisando..." if (query or date_params) else "Carregando produtos...")
        self._notify_filters_changed()

        result_queue: queue.Queue[
            tuple[list[Product], dict[str, int], bool, JueriError | None]
        ] = queue.Queue()

        def execute() -> None:
            try:
                products, category_mapping, loaded_complete = self._fetch_products(
                    query, date_params, stock_filter, category_name
                )
                error: JueriError | None = None
            except JueriError as exc:
                products, category_mapping, loaded_complete, error = [], {}, False, exc
            result_queue.put((products, category_mapping, loaded_complete, error))

        if self.async_search:
            threading.Thread(target=execute, daemon=True).start()
            self._poll_job = self.after(40, lambda: self._poll_search_result(generation, result_queue))
        else:
            execute()
            products, category_mapping, loaded_complete, error = result_queue.get_nowait()
            self._finish_search(generation, products, category_mapping, loaded_complete, error)

    def _poll_search_result(
        self,
        generation: int,
        result_queue: queue.Queue[tuple[list[Product], dict[str, int], bool, JueriError | None]],
    ) -> None:
        self._poll_job = None
        if generation != self._search_generation or not self.winfo_exists():
            return
        try:
            products, category_mapping, loaded_complete, error = result_queue.get_nowait()
        except queue.Empty:
            self._poll_job = self.after(40, lambda: self._poll_search_result(generation, result_queue))
            return
        self._finish_search(generation, products, category_mapping, loaded_complete, error)

    def _finish_search(
        self,
        generation: int,
        products: list[Product],
        category_mapping: dict[str, int],
        loaded_complete: bool,
        error: JueriError | None,
    ) -> None:
        if generation != self._search_generation or not self.winfo_exists():
            return
        self._search_in_progress = False
        if error is not None:
            self._source_results = []
            self.results = []
            self.status_var.set(f"Erro ao pesquisar produtos: {error.describe()}")
            if self.on_status_changed is not None:
                self.on_status_changed("Erro")
            self._update_selection_count()
            return

        self._category_ids_by_name = category_mapping
        self._loaded_complete = loaded_complete
        category_values = [CATEGORY_ALL, *sorted(category_mapping)]
        self.category_combobox["values"] = category_values
        if self.category_var.get() not in category_values:
            self.category_var.set(CATEGORY_ALL)
        self._source_results = list(products)
        self._apply_filters_and_sort()
        if self.on_status_changed is not None:
            self.on_status_changed("Conectado")
        if self.on_search_completed is not None:
            self.on_search_completed(self)

    def _apply_filters_and_sort(self) -> None:
        category_id = self._category_id()
        filtered = filter_products(self._source_results, self.stock_var.get(), category_id)
        field = SORT_OPTIONS.get(self.sort_var.get(), "codigo")
        direction = DIRECTION_OPTIONS.get(self.direction_var.get(), SortDirection.ASCENDING)
        key_func = self._sorter.key_funcs.get(field, _SORT_KEY_FUNCS["codigo"])
        self.results = sort_items(filtered, key_func, direction)
        self._render_results()
        if not self.results:
            self.status_var.set("Nenhum produto encontrado.")
        elif len(self.results) == len(self._source_results) and self._loaded_complete:
            self.status_var.set(f"{len(self.results)} produto(s) encontrado(s).")
        elif len(self.results) == len(self._source_results):
            self.status_var.set(f"{len(self.results)} produto(s) na página carregada.")
        else:
            self.status_var.set(
                f"{len(self.results)} produto(s) exibido(s) de {len(self._source_results)} carregado(s)."
            )

    def _render_results(self) -> None:
        self.results_tree.delete(*self.results_tree.get_children())
        for index, product in enumerate(self.results):
            self.results_tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    product.codigo_barras or "",
                    product.descricao or "",
                    self._format_price(product.preco_principal),
                    product.numero_peca or "—",
                    self._subcategory_name(product) or "—",
                    self._category_name(product) or "—",
                    product.quantidade if product.quantidade is not None else "—",
                    self._format_date(product.data_criacao),
                ),
            )
        self._update_selection_count()

    def _on_sort_column(self, column: str) -> None:
        label = next((label for label, field in SORT_OPTIONS.items() if field == column), None)
        if label is None:
            return
        if self._header_sort_column == column:
            self.direction_var.set(
                "Decrescente" if self.direction_var.get() == "Crescente" else "Crescente"
            )
        else:
            self.sort_var.set(label)
            self.direction_var.set("Crescente")
        self._header_sort_column = column
        self._apply_filters_and_sort()
        self._notify_filters_changed()

    @staticmethod
    def _format_price(preco: float | None) -> str:
        return f"R$ {preco:.2f}" if preco is not None else "—"

    @staticmethod
    def _format_weight(peso: float | None) -> str:
        return f"{peso:g} g" if peso is not None else "—"

    @staticmethod
    def _format_date(raw: str | None) -> str:
        if not raw:
            return "—"
        return raw[8:10] + "/" + raw[5:7] + "/" + raw[:4] if len(raw) >= 10 else raw

    def _update_selection_count(self) -> None:
        count = len(self.results_tree.selection())
        self.selection_count_var.set(f"{count} produto(s) selecionado(s).")

    def _on_select_all(self) -> None:
        self.results_tree.selection_set(self.results_tree.get_children())
        # selection_set() dispara <<TreeviewSelect>> de forma assíncrona
        # (só processado quando o loop de eventos do Tk roda) — chama
        # direto para a contagem ficar correta imediatamente.
        self._update_selection_count()

    def _on_clear_selection(self) -> None:
        self.results_tree.selection_remove(self.results_tree.selection())
        self._update_selection_count()

    def _selected_products(self) -> list[Product]:
        products: list[Product] = []
        for iid in self.results_tree.selection():
            index = int(iid)
            if 0 <= index < len(self.results):
                products.append(self.results[index])
        return products

    def _add_products(self, products: list[Product]) -> None:
        if self.on_add_selected is not None:
            self.on_add_selected(products)
        self.feedback_var.set(f"{len(products)} produto(s) adicionado(s) à fila.")

    def _on_add_selected(self) -> None:
        products = self._selected_products()
        if not products:
            self.feedback_var.set("Nenhum produto selecionado.")
            return
        self._add_products(products)
        # A janela não fecha sozinha — o usuário pode pesquisar de novo e
        # continuar adicionando. Só limpa a seleção já processada.
        self.results_tree.selection_remove(self.results_tree.selection())
        self._update_selection_count()

    def _on_double_click_add(self) -> None:
        selection = self.results_tree.selection()
        if not selection:
            return
        index = int(selection[0])
        if not (0 <= index < len(self.results)):
            return
        self._add_products([self.results[index]])

    def _on_cancel(self) -> None:
        self._search_generation += 1
        self._cancel_pending_jobs()
        self._notify_filters_changed()
        if self.on_close is not None:
            self.on_close()

    def _on_destroy(self, event: tk.Event) -> None:
        if event.widget is self:
            self._cancel_pending_jobs()

    def _cancel_pending_jobs(self) -> None:
        for attribute in ("_debounce_job", "_poll_job"):
            job = getattr(self, attribute, None)
            if job is not None:
                try:
                    self.after_cancel(job)
                except tk.TclError:
                    pass
                setattr(self, attribute, None)


class ProductSearchDialog(tk.Toplevel):
    """Invólucro legado do painel de pesquisa.

    A aplicação principal usa :class:`JueriSearchPanel` embutido. Este diálogo
    permanece apenas para compatibilidade com integrações e testes existentes,
    sem manter uma segunda implementação da pesquisa.
    """

    def __init__(
        self,
        parent: tk.Misc,
        products_api: ProductsAPI,
        on_add_selected: Callable[[list[Product]], None] | None = None,
        initial_query: str = "",
        initial_data_inicial: str = "",
        initial_data_final: str = "",
        categories_api: CategoriesAPI | None = None,
        initial_filters: dict[str, Any] | None = None,
        on_filters_changed: Callable[[dict[str, Any]], None] | None = None,
        on_status_changed: Callable[[str], None] | None = None,
        async_search: bool = False,
    ) -> None:
        super().__init__(parent)
        self.title("Pesquisar Produtos")
        self.geometry("940x650")
        self.minsize(760, 560)
        self.transient(parent)
        self.panel = JueriSearchPanel(
            self,
            products_api,
            on_add_selected=on_add_selected,
            initial_query=initial_query,
            initial_data_inicial=initial_data_inicial,
            initial_data_final=initial_data_final,
            categories_api=categories_api,
            initial_filters=initial_filters,
            on_filters_changed=on_filters_changed,
            on_status_changed=on_status_changed,
            on_close=self.destroy,
            async_search=async_search,
        )
        self.panel.pack(fill="both", expand=True)
        self.bind("<Escape>", lambda _event: self.destroy())
        self.bind("<Return>", lambda _event: self.panel._on_refresh())
        self.grab_set()
        self.panel.focus_search_entry()

    def __getattr__(self, name: str) -> Any:
        panel = object.__getattribute__(self, "__dict__").get("panel")
        if panel is not None and hasattr(panel, name):
            return getattr(panel, name)
        raise AttributeError(name)
