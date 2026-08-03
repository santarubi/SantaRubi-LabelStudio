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

import tkinter as tk
from tkinter import ttk
from typing import Callable

from app.api.date_filters import DateFilterError, build_date_range_filter, today_br, yesterday_br
from app.api.exceptions import JueriError
from app.api.product import Product
from app.api.products import ProductsAPI
from core.column_sort import ColumnSorter, numeric_or_text
from core.text_normalize import parse_multiple_codes
from ui.treeview_selection import enable_drag_selection

DEBOUNCE_MS = 300

# Mesmo componente de ordenação usado por ui/catalog_tab.py — código e
# peso são numéricos (codigo_barras é sempre 6 dígitos, mas numeric_or_text
# cai para texto com segurança se algum dia não for), descrição é texto.
_SORT_KEY_FUNCS = {
    "codigo": lambda product: numeric_or_text(product.codigo_barras),
    "descricao": lambda product: product.descricao,
    "preco": lambda product: product.preco_principal,
    "peso": lambda product: product.peso,
}


class ProductSearchDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        products_api: ProductsAPI,
        on_add_selected: Callable[[list[Product]], None] | None = None,
        initial_query: str = "",
        initial_data_inicial: str = "",
        initial_data_final: str = "",
    ) -> None:
        super().__init__(parent)
        self.title("Pesquisar Produtos")
        self.geometry("680x560")
        self.minsize(600, 480)
        self.transient(parent)

        self.products_api = products_api
        self.on_add_selected = on_add_selected
        self.results: list[Product] = []
        self._debounce_job: str | None = None
        self._sorter = ColumnSorter(_SORT_KEY_FUNCS)

        self.search_var = tk.StringVar(value=initial_query)
        self.data_inicial_var = tk.StringVar(value=initial_data_inicial)
        self.data_final_var = tk.StringVar(value=initial_data_final)
        self.status_var = tk.StringVar(value="Carregando produtos...")
        self.selection_count_var = tk.StringVar(value="0 produto(s) selecionado(s).")

        self._build_widgets()
        self.bind("<Escape>", lambda _event: self._on_cancel())
        self.bind("<Return>", lambda _event: self._on_refresh())
        self.grab_set()
        self._run_search()

    def _build_widgets(self) -> None:
        container = ttk.Frame(self, padding=16)
        container.pack(fill="both", expand=True)
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(4, weight=1)

        ttk.Label(container, text="Pesquisar:").grid(row=0, column=0, sticky="w")
        search_row = ttk.Frame(container)
        search_row.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(2, 8))
        search_row.grid_columnconfigure(0, weight=1)

        search_entry = ttk.Entry(search_row, textvariable=self.search_var)
        search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        search_entry.focus_set()
        self.search_var.trace_add("write", lambda *_args: self._on_search_changed())

        ttk.Button(search_row, text="Atualizar", style="App.TButton", command=self._on_refresh).grid(
            row=0, column=1
        )

        date_row = ttk.Frame(container)
        date_row.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        date_row.grid_columnconfigure(0, weight=1)
        date_row.grid_columnconfigure(1, weight=1)

        inicial_col = ttk.Frame(date_row)
        inicial_col.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ttk.Label(inicial_col, text="Data Inicial:").pack(anchor="w")
        inicial_entry = ttk.Entry(inicial_col, textvariable=self.data_inicial_var)
        inicial_entry.pack(fill="x", pady=(2, 0))
        self.data_inicial_var.trace_add("write", lambda *_args: self._on_search_changed())

        final_col = ttk.Frame(date_row)
        final_col.grid(row=0, column=1, sticky="ew")
        ttk.Label(final_col, text="Data Final:").pack(anchor="w")
        final_entry = ttk.Entry(final_col, textvariable=self.data_final_var)
        final_entry.pack(fill="x", pady=(2, 0))
        self.data_final_var.trace_add("write", lambda *_args: self._on_search_changed())

        quick_buttons_row = ttk.Frame(container)
        quick_buttons_row.grid(row=3, column=0, columnspan=2, sticky="w", pady=(0, 8))
        ttk.Button(quick_buttons_row, text="Hoje", style="App.TButton", command=self._on_quick_today).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(
            quick_buttons_row, text="Ontem", style="App.TButton", command=self._on_quick_yesterday
        ).pack(side="left", padx=(0, 8))
        ttk.Button(
            quick_buttons_row, text="Limpar Datas", style="App.TButton", command=self._on_clear_dates
        ).pack(side="left")

        columns = ("codigo", "descricao", "preco", "peso")
        self.results_tree = ttk.Treeview(container, columns=columns, show="headings", selectmode="extended")
        self.results_tree.heading("codigo", text="Código", command=lambda: self._on_sort_column("codigo"))
        self.results_tree.heading(
            "descricao", text="Descrição", command=lambda: self._on_sort_column("descricao")
        )
        self.results_tree.heading(
            "preco", text="Preço (Varejo)", command=lambda: self._on_sort_column("preco")
        )
        self.results_tree.heading("peso", text="Peso", command=lambda: self._on_sort_column("peso"))
        self.results_tree.column("codigo", width=100, anchor="w")
        self.results_tree.column("descricao", width=300, anchor="w")
        self.results_tree.column("preco", width=100, anchor="e")
        self.results_tree.column("peso", width=80, anchor="e")
        self.results_tree.grid(row=4, column=0, sticky="nsew")
        self.results_tree.bind("<Double-1>", lambda _event: self._on_double_click_add())
        self.results_tree.bind("<<TreeviewSelect>>", lambda _event: self._update_selection_count())
        enable_drag_selection(self.results_tree)

        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=4, column=1, sticky="ns")

        ttk.Label(container, textvariable=self.status_var, style="Subtitle.TLabel").grid(
            row=5, column=0, columnspan=2, sticky="w", pady=(8, 2)
        )
        ttk.Label(container, textvariable=self.selection_count_var, style="Subtitle.TLabel").grid(
            row=6, column=0, columnspan=2, sticky="w", pady=(0, 8)
        )

        button_row = ttk.Frame(container)
        button_row.grid(row=7, column=0, columnspan=2, sticky="ew")
        button_row.grid_columnconfigure(2, weight=1)
        ttk.Button(button_row, text="Selecionar Todos", style="App.TButton", command=self._on_select_all).grid(
            row=0, column=0, padx=(0, 8)
        )
        ttk.Button(
            button_row, text="Limpar Seleção", style="App.TButton", command=self._on_clear_selection
        ).grid(row=0, column=1)
        ttk.Button(button_row, text="Cancelar", style="App.TButton", command=self._on_cancel).grid(
            row=0, column=3, padx=(0, 8)
        )
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

    def _run_search(self) -> None:
        # Cancela qualquer debounce pendente (não só zera a variável) —
        # sem isso, um _run_search() disparado por outro caminho (ex.:
        # _on_refresh) deixa o `after()` original órfão, que ainda tenta
        # rodar mais tarde mesmo se a janela já tiver sido fechada.
        if self._debounce_job is not None:
            self.after_cancel(self._debounce_job)
            self._debounce_job = None
        query = self.search_var.get().strip()

        self.results_tree.delete(*self.results_tree.get_children())
        self.results = []

        try:
            date_filter = build_date_range_filter(self.data_inicial_var.get(), self.data_final_var.get())
        except DateFilterError as exc:
            self.status_var.set(str(exc))
            return

        date_params = date_filter.to_params()
        codes = parse_multiple_codes(query) if query else None

        # Caixa vazia sem filtro de data não é "sem resultados" — é "sem
        # filtro": lista a primeira página da API normalmente, tanto na
        # abertura da janela quanto quando o usuário apaga tudo.
        self.status_var.set("Pesquisando..." if (query or date_params) else "Carregando produtos...")
        self.update_idletasks()

        try:
            if codes is not None:
                self.results = self.products_api.search_multiple_products(codes, **date_params)
            elif date_params:
                # Com filtro de data ativo, percorre todas as páginas —
                # o usuário quer todos os produtos do período, não só a
                # primeira página.
                self.results = self.products_api.search_all_pages(search=query or None, **date_params)
            else:
                result = self.products_api.search_products(search=query or None)
                self.results = result.products
        except JueriError as exc:
            self.status_var.set(f"Erro ao pesquisar produtos: {exc.describe()}")
            self._update_selection_count()
            return

        # Se havia uma ordenação ativa, mantém — refinar a busca não deve
        # fazer o usuário perder a ordem que já tinha escolhido.
        self.results = self._sorter.reapply(self.results)
        self._render_results()

        if not self.results:
            self.status_var.set("Nenhum produto encontrado.")
        else:
            self.status_var.set(f"{len(self.results)} produto(s) encontrado(s).")

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
                    self._format_weight(product.peso),
                ),
            )
        self._update_selection_count()

    def _on_sort_column(self, column: str) -> None:
        self.results = self._sorter.sort(self.results, column)
        self._render_results()

    @staticmethod
    def _format_price(preco: float | None) -> str:
        return f"R$ {preco:.2f}" if preco is not None else "—"

    @staticmethod
    def _format_weight(peso: float | None) -> str:
        return f"{peso:g} g" if peso is not None else "—"

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
        self.status_var.set(f"{len(products)} produto(s) adicionado(s) à fila de impressão.")

    def _on_add_selected(self) -> None:
        products = self._selected_products()
        if not products:
            self.status_var.set("Nenhum produto selecionado.")
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
        self.destroy()
