"""Aba "Catálogo Integrado".

Configuração da fonte de dados (arquivo, abas, mapeamento de colunas),
teste de configuração, tabela do catálogo (carregado em memória via
CatalogRepository) e a Fila de Impressão (PrintQueue), incluindo o disparo
da impressão reaproveitando o motor existente (ZplBuilder/PrinterService).

Esta classe é apenas apresentação: lê controles da interface, chama
métodos de CatalogService/PrintQueue e atualiza tabela/cartões/contadores
— nenhuma pesquisa, filtro, ordenação ou regra de negócio do catálogo é
feita aqui. Toda essa lógica vive em core/catalog_service.py.

Fluxo: DataSource -> Repository -> CatalogService -> CatalogTab (interface)
-> PrintQueue -> PrintQueueAdapter -> ZplBuilder -> PrinterService.
"""

from __future__ import annotations

import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk
from typing import Any

from core.catalog_excel_source import ExcelCatalogSource
from core.catalog_product import CatalogProduct
from core.catalog_repository import CatalogRepository
from core.catalog_service import CATEGORY_ALL, SUPPLIER_ALL, CatalogService
from core.catalog_settings import CATALOG_FIELD_LABELS, CATALOG_FIELDS, CatalogSettings
from core.catalog_validator import CatalogConfigurationValidator, ValidationReport
from core.config import ConfigManager
from core.label_data import LabelData
from core.print_item import PrintItem, normalize_quantity
from core.print_layout import BATCH_COLUMN_PITCH, BATCH_ROW_COLUMNS
from core.print_log import log_print_job
from core.print_queue import PrintQueue
from core.print_queue_adapter import PrintQueueAdapter
from core.printer import PrinterService
from core.zpl_builder import ZplBuilder

APP_TITLE = "Santa Rubi Label Studio"


class CatalogTab:
    """Constrói e gerencia a aba do Catálogo Integrado (configuração + navegação)."""

    def __init__(self, parent: tk.Widget, config_manager: ConfigManager, config: dict[str, Any]):
        self.config_manager = config_manager
        self.config = config
        self.settings = CatalogSettings.from_config(config)

        self.repository: CatalogRepository | None = None
        self.service: CatalogService | None = None

        self.file_path_var = tk.StringVar(value=self.settings.file_path)
        self.sheet_vars: dict[str, tk.BooleanVar] = {}
        self.column_vars: dict[str, tk.StringVar] = {
            internal_field: tk.StringVar(value=self.settings.column_map.get(internal_field, ""))
            for internal_field in CATALOG_FIELDS
        }

        self.catalog_search_var = tk.StringVar()
        self.supplier_var = tk.StringVar(value=SUPPLIER_ALL)
        self.category_filter_var = tk.StringVar(value=CATEGORY_ALL)
        self.catalog_summary_var = tk.StringVar(value="Total: 0 | Exibindo: 0")
        self.last_reload_var = tk.StringVar(value=self._format_last_reload(self.settings.last_reload))
        self.catalog_filtered_products: list[CatalogProduct] = []

        self._sort_field: str | None = None
        self._sort_reverse = False

        self.print_queue = PrintQueue()
        self._selected_queue_codigo: str | None = None
        self._printing_in_progress = False
        self._tk_root = parent.winfo_toplevel()
        self.printer_var = tk.StringVar(value=self.config.get("last_printer", ""))

        self._build_widgets(parent)
        self._load_printer_list()

        if self.settings.file_path:
            self._load_sheets(default_all_checked=False)

        if self._has_complete_settings():
            self._try_initial_load()

        self._refresh_queue_view()

    def _build_widgets(self, parent: tk.Widget) -> None:
        container = ttk.Frame(parent, padding=12)
        container.pack(fill="both", expand=True)
        container.grid_columnconfigure(0, weight=7)
        container.grid_columnconfigure(1, weight=3, minsize=280)
        container.grid_rowconfigure(0, weight=1)

        left_frame = ttk.Frame(container)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        left_frame.grid_columnconfigure(0, weight=1)

        # --- Barra superior compacta: toggle do painel + ações + última atualização ---
        top_bar = ttk.Frame(left_frame)
        top_bar.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        top_bar.grid_columnconfigure(3, weight=1)

        self.toggle_config_button = ttk.Button(
            top_bar, text="▼ Configuração", command=self._on_toggle_configuration
        )
        self.toggle_config_button.grid(row=0, column=0, padx=(0, 6))
        ttk.Button(
            top_bar, text="Recarregar Catálogo", style="Primary.TButton", command=self._on_reload_catalog
        ).grid(row=0, column=1, padx=(0, 6))
        ttk.Button(top_bar, text="Testar Configuração", command=self._on_test_configuration).grid(
            row=0, column=2, padx=(0, 12)
        )
        ttk.Label(top_bar, textvariable=self.last_reload_var, style="Subtitle.TLabel").grid(
            row=0, column=3, sticky="e"
        )

        # --- Painel de configuração — recolhível (arquivo, abas, mapeamento,
        # resultado do teste). Ocultá-lo libera espaço para a tabela crescer. ---
        self.config_panel = ttk.Frame(left_frame)
        self.config_panel.grid(row=1, column=0, sticky="ew", pady=(0, 6))
        self.config_panel.grid_columnconfigure(0, weight=1)

        file_row = ttk.Frame(self.config_panel)
        file_row.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        file_row.grid_columnconfigure(1, weight=1)
        ttk.Label(file_row, text="Arquivo:").grid(row=0, column=0, sticky="w", padx=(0, 6))
        ttk.Entry(file_row, textvariable=self.file_path_var, state="readonly").grid(
            row=0, column=1, sticky="ew", padx=(0, 8)
        )
        ttk.Button(file_row, text="Selecionar Arquivo", command=self._on_select_file).grid(row=0, column=2)

        config_row = ttk.Frame(self.config_panel)
        config_row.grid(row=1, column=0, sticky="ew", pady=(0, 6))
        config_row.grid_columnconfigure(0, weight=1)
        config_row.grid_columnconfigure(1, weight=1)

        sheets_frame = ttk.LabelFrame(config_row, text="Abas", padding=8)
        sheets_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.sheets_container = ttk.Frame(sheets_frame)
        self.sheets_container.pack(fill="x")
        self.sheets_placeholder = ttk.Label(
            self.sheets_container, text="Selecione um arquivo para listar as abas.", style="Subtitle.TLabel"
        )
        self.sheets_placeholder.pack(anchor="w")

        mapping_frame = ttk.LabelFrame(config_row, text="Mapeamento de colunas", padding=8)
        mapping_frame.grid(row=0, column=1, sticky="nsew")
        mapping_frame.grid_columnconfigure(1, weight=1)
        self.column_comboboxes: dict[str, ttk.Combobox] = {}
        for row, internal_field in enumerate(CATALOG_FIELDS):
            ttk.Label(mapping_frame, text=CATALOG_FIELD_LABELS[internal_field]).grid(
                row=row, column=0, sticky="w", padx=(0, 8), pady=2
            )
            combobox = ttk.Combobox(
                mapping_frame, textvariable=self.column_vars[internal_field], state="readonly"
            )
            combobox.grid(row=row, column=1, sticky="ew", pady=2)
            combobox.bind("<<ComboboxSelected>>", lambda _event: self._save_settings())
            self.column_comboboxes[internal_field] = combobox

        report_frame = ttk.LabelFrame(self.config_panel, text="Resultado do teste", padding=8)
        report_frame.grid(row=2, column=0, sticky="ew")
        self.report_text = tk.Text(report_frame, height=4, wrap="word", state="disabled")
        self.report_text.pack(fill="both", expand=True)

        # --- Linha intermediária: filtros (fornecedor, categoria, pesquisa) ---
        filters_row = ttk.Frame(left_frame)
        filters_row.grid(row=2, column=0, sticky="ew", pady=(0, 6))
        filters_row.grid_columnconfigure(0, weight=0, minsize=160)
        filters_row.grid_columnconfigure(1, weight=0, minsize=160)
        filters_row.grid_columnconfigure(2, weight=1)

        ttk.Label(filters_row, text="Fornecedor").grid(row=0, column=0, sticky="w", pady=(0, 2))
        self.supplier_combobox = ttk.Combobox(
            filters_row, textvariable=self.supplier_var, values=[SUPPLIER_ALL], state="readonly"
        )
        self.supplier_combobox.grid(row=1, column=0, sticky="ew", padx=(0, 8))
        self.supplier_combobox.bind("<<ComboboxSelected>>", self._on_supplier_filter_change)

        ttk.Label(filters_row, text="Categoria").grid(row=0, column=1, sticky="w", pady=(0, 2))
        self.category_combobox = ttk.Combobox(
            filters_row, textvariable=self.category_filter_var, values=[CATEGORY_ALL], state="readonly"
        )
        self.category_combobox.grid(row=1, column=1, sticky="ew", padx=(0, 8))
        self.category_combobox.bind("<<ComboboxSelected>>", self._on_category_filter_change)

        ttk.Label(filters_row, text="Pesquisar produto").grid(row=0, column=2, sticky="w", pady=(0, 2))
        ttk.Entry(filters_row, textvariable=self.catalog_search_var).grid(row=1, column=2, sticky="ew")
        self.catalog_search_var.trace_add("write", lambda *_: self._on_catalog_search_change())

        # --- Tabela — ocupa praticamente toda a largura e altura restantes ---
        table_frame = ttk.Frame(left_frame)
        table_frame.grid(row=3, column=0, sticky="nsew")
        left_frame.grid_rowconfigure(3, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)

        self.catalog_tree = ttk.Treeview(
            table_frame,
            columns=("fornecedor", "codigo", "descricao", "categoria", "numeracao", "quantidade", "preco"),
            show="headings",
            # Seleção padrão do Treeview: clique único, Ctrl (múltipla) e
            # Shift (contínua) — necessário para "Adicionar à Fila" operar
            # sobre vários produtos de uma vez.
            selectmode="extended",
        )
        self.catalog_tree.grid(row=0, column=0, sticky="nsew")
        vertical_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.catalog_tree.yview)
        self.catalog_tree.configure(yscrollcommand=vertical_scroll.set)
        vertical_scroll.grid(row=0, column=1, sticky="ns")

        # Atalho Ctrl+A: seleciona todos os produtos exibidos na tabela
        # principal (mesmo padrão já usado na aba "Impressão").
        self.catalog_tree.bind("<Control-a>", self._on_select_all_products_shortcut)
        self.catalog_tree.bind("<Control-A>", self._on_select_all_products_shortcut)

        # As colunas (exceto Quantidade, ver nota abaixo) são clicáveis para
        # ordenar — cada uma só aciona service.sort_by(campo); adicionar um
        # novo critério não exige tocar em nada aqui além de registrar o
        # campo no SORT_KEY_FUNCTIONS do CatalogService.
        self.catalog_tree.heading("fornecedor", text="Fornecedor", command=lambda: self._on_sort_column("fornecedor"))
        self.catalog_tree.heading("codigo", text="Código", command=lambda: self._on_sort_column("codigo"))
        self.catalog_tree.heading("descricao", text="Descrição", command=lambda: self._on_sort_column("descricao"))
        self.catalog_tree.heading("categoria", text="Categoria", command=lambda: self._on_sort_column("categoria"))
        self.catalog_tree.heading("numeracao", text="Numeração", command=lambda: self._on_sort_column("numeracao"))
        # Quantidade não tem critério de ordenação no CatalogService —
        # cabeçalho sem comando, só exibição.
        self.catalog_tree.heading("quantidade", text="Quantidade")
        self.catalog_tree.heading("preco", text="Preço", command=lambda: self._on_sort_column("preco"))

        self.catalog_tree.column("fornecedor", anchor="w", width=90, minwidth=70, stretch=False)
        self.catalog_tree.column("codigo", anchor="center", width=80, minwidth=70, stretch=False)
        self.catalog_tree.column("descricao", anchor="w", width=340, minwidth=180, stretch=True)
        self.catalog_tree.column("categoria", anchor="w", width=130, minwidth=100, stretch=False)
        self.catalog_tree.column("numeracao", anchor="center", width=80, minwidth=70, stretch=False)
        self.catalog_tree.column("quantidade", anchor="center", width=80, minwidth=70, stretch=False)
        self.catalog_tree.column("preco", anchor="e", width=90, minwidth=80, stretch=False)

        # --- Rodapé: contadores + ação de enviar a seleção para a fila ---
        footer = ttk.Frame(left_frame)
        footer.grid(row=4, column=0, sticky="ew", pady=(6, 0))
        footer.grid_columnconfigure(0, weight=1)
        ttk.Label(footer, textvariable=self.catalog_summary_var, style="Subtitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self.add_to_queue_button = ttk.Button(
            footer, text="Adicionar à Fila", style="Primary.TButton", command=self._on_add_to_queue
        )
        self.add_to_queue_button.grid(row=0, column=1, sticky="e")

        # --- Painel lateral direito: Fila de Impressão ---
        self._build_print_queue_panel(container)

        self._apply_configuration_visibility()

    def _build_print_queue_panel(self, container: tk.Widget) -> None:
        queue_panel = ttk.Frame(container, style="Card.TFrame", padding=12)
        queue_panel.grid(row=0, column=1, sticky="nsew")
        queue_panel.grid_columnconfigure(0, weight=1)
        queue_panel.grid_rowconfigure(1, weight=1)

        ttk.Label(queue_panel, text="Fila de Impressão", font=("Segoe UI", 12, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 8)
        )

        list_area = ttk.Frame(queue_panel)
        list_area.grid(row=1, column=0, sticky="nsew")
        list_area.grid_columnconfigure(0, weight=1)
        list_area.grid_rowconfigure(0, weight=1)

        self.queue_canvas = tk.Canvas(list_area, highlightthickness=0, bg="#ffffff")
        self.queue_canvas.grid(row=0, column=0, sticky="nsew")
        queue_scrollbar = ttk.Scrollbar(list_area, orient="vertical", command=self.queue_canvas.yview)
        queue_scrollbar.grid(row=0, column=1, sticky="ns")
        self.queue_canvas.configure(yscrollcommand=queue_scrollbar.set)

        self.queue_items_frame = tk.Frame(self.queue_canvas, bg="#ffffff")
        self._queue_canvas_window = self.queue_canvas.create_window((0, 0), window=self.queue_items_frame, anchor="nw")
        self.queue_items_frame.bind(
            "<Configure>", lambda _event: self.queue_canvas.configure(scrollregion=self.queue_canvas.bbox("all"))
        )
        self.queue_canvas.bind(
            "<Configure>", lambda event: self.queue_canvas.itemconfigure(self._queue_canvas_window, width=event.width)
        )

        queue_footer = ttk.Frame(queue_panel)
        queue_footer.grid(row=2, column=0, sticky="ew", pady=(8, 8))
        self.queue_count_var = tk.StringVar(value="Produtos na fila: 0")
        self.queue_total_var = tk.StringVar(value="Total de etiquetas: 0")
        ttk.Label(queue_footer, textvariable=self.queue_count_var, style="Subtitle.TLabel").pack(anchor="w")
        ttk.Label(queue_footer, textvariable=self.queue_total_var, style="Subtitle.TLabel").pack(anchor="w")

        queue_buttons = ttk.Frame(queue_panel)
        queue_buttons.grid(row=3, column=0, sticky="ew")
        queue_buttons.grid_columnconfigure(0, weight=1)
        queue_buttons.grid_columnconfigure(1, weight=1)
        self.remove_from_queue_button = ttk.Button(
            queue_buttons, text="Remover", command=self._on_remove_from_queue, state="disabled"
        )
        self.remove_from_queue_button.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.clear_queue_button = ttk.Button(
            queue_buttons, text="Limpar Fila", command=self._on_clear_queue, state="disabled"
        )
        self.clear_queue_button.grid(row=0, column=1, sticky="ew", padx=(4, 0))

        printer_row = ttk.Frame(queue_panel)
        printer_row.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        printer_row.grid_columnconfigure(0, weight=1)
        ttk.Label(printer_row, text="Impressora", style="Subtitle.TLabel").grid(row=0, column=0, sticky="w")
        self.queue_printer_combobox = ttk.Combobox(printer_row, textvariable=self.printer_var, state="readonly")
        self.queue_printer_combobox.grid(row=1, column=0, sticky="ew")
        self.queue_printer_combobox.bind("<<ComboboxSelected>>", self._on_queue_printer_selected)

        self.print_queue_button = ttk.Button(
            queue_panel, text="Imprimir Fila", style="Primary.TButton", command=self._on_print_queue, state="disabled"
        )
        self.print_queue_button.grid(row=5, column=0, sticky="ew", pady=(8, 0))

    def _load_printer_list(self) -> None:
        """Popula o combobox de impressora e seleciona a última utilizada —
        mesma chave de configuração ("last_printer") e mesmo PrinterService
        já usados pela aba "Impressão", para que as duas abas compartilhem a
        mesma preferência de impressora."""
        printers = PrinterService().list_printers()
        self.queue_printer_combobox["values"] = printers

        if not printers:
            self.printer_var.set("")
            return

        last_printer = self.config.get("last_printer")
        if last_printer in printers:
            self.printer_var.set(last_printer)
            return

        default_printer = PrinterService().get_default_printer()
        self.printer_var.set(default_printer if default_printer in printers else printers[0])

    def _on_queue_printer_selected(self, _event: Any = None) -> None:
        self.config["last_printer"] = self.printer_var.get()
        self.config_manager.save(self.config)

    def _on_toggle_configuration(self) -> None:
        """Alterna o painel de configuração (arquivo/abas/mapeamento/
        resultado do teste) entre visível e recolhido, liberando espaço
        para a tabela crescer quando recolhido. Estado persistido."""
        self.settings.configuration_expanded = not self.settings.configuration_expanded
        self._apply_configuration_visibility()
        self._save_settings()

    def _apply_configuration_visibility(self) -> None:
        if self.settings.configuration_expanded:
            self.config_panel.grid()
            self.toggle_config_button.configure(text="▼ Configuração")
        else:
            self.config_panel.grid_remove()
            self.toggle_config_button.configure(text="▶ Configuração")

    # ------------------------------------------------------------------
    # Fila de Impressão — a interface nunca manipula listas de PrintItem
    # diretamente; toda leitura/alteração passa pelos métodos do PrintQueue.
    # ------------------------------------------------------------------

    def _on_add_to_queue(self) -> None:
        if self._printing_in_progress or self.service is None:
            return

        selected_ids = self.catalog_tree.selection()
        if not selected_ids:
            messagebox.showinfo(APP_TITLE, "Selecione ao menos um produto para adicionar à fila.")
            return

        for iid in selected_ids:
            product = self.catalog_filtered_products[int(iid)]
            print_item = self.service.create_print_item(product)
            if self.print_queue.contains(product):
                self.print_queue.increment(product, amount=print_item.quantity)
            else:
                self.print_queue.add(product, quantity=print_item.quantity)

        self._refresh_queue_view()

    def _on_remove_from_queue(self) -> None:
        if self._printing_in_progress or self._selected_queue_codigo is None:
            return

        item = self._find_queue_item_by_codigo(self._selected_queue_codigo)
        if item is None:
            return

        self.print_queue.remove(item.product)
        self._selected_queue_codigo = None
        self._refresh_queue_view()

    def _on_clear_queue(self) -> None:
        if self._printing_in_progress:
            return

        self.print_queue.clear()
        self._selected_queue_codigo = None
        self._refresh_queue_view()

    def _find_queue_item_by_codigo(self, codigo: str) -> PrintItem | None:
        for item in self.print_queue:
            if item.product.codigo == codigo:
                return item
        return None

    def _on_select_queue_card(self, codigo: str) -> None:
        self._selected_queue_codigo = codigo
        self._render_queue_cards()

    def _on_increment_queue_item(self, codigo: str) -> None:
        if self._printing_in_progress:
            return
        item = self._find_queue_item_by_codigo(codigo)
        if item is None:
            return
        self.print_queue.increment(item.product)
        self._refresh_queue_view()

    def _on_decrement_queue_item(self, codigo: str) -> None:
        if self._printing_in_progress:
            return
        item = self._find_queue_item_by_codigo(codigo)
        if item is None:
            return
        self.print_queue.decrement(item.product)
        self._refresh_queue_view()

    def _on_delete_key(self, codigo: str) -> None:
        if self._printing_in_progress:
            return
        self._selected_queue_codigo = codigo
        self._on_remove_from_queue()

    def _on_select_all_products_shortcut(self, _event: Any = None) -> str:
        self.catalog_tree.selection_set(self.catalog_tree.get_children())
        return "break"

    @staticmethod
    def _parse_quantity_input(raw_value: str) -> float | None:
        """None significa "não é um número" — nesse caso a edição é
        descartada e o valor anterior é mantido (nunca levanta exceção)."""
        text = raw_value.strip()
        if text == "":
            return None
        try:
            return float(text)
        except ValueError:
            return None

    def _on_start_edit_quantity(self, codigo: str, quantity_row: tk.Widget, quantity_label: tk.Label) -> None:
        if self._printing_in_progress:
            return
        item = self._find_queue_item_by_codigo(codigo)
        if item is None:
            return

        quantity_label.pack_forget()

        entry_var = tk.StringVar(value=str(item.quantity))
        entry = tk.Entry(quantity_row, textvariable=entry_var, width=4, justify="center")
        entry.pack(side="left", padx=4)
        entry.focus_set()
        entry.select_range(0, "end")

        def commit(_event: Any = None) -> None:
            entry.unbind("<FocusOut>")
            self._commit_quantity_edit(codigo, entry_var.get())

        entry.bind("<Return>", commit)
        entry.bind("<FocusOut>", commit)

    def _commit_quantity_edit(self, codigo: str, raw_value: str) -> None:
        """Aplica a edição direta via PrintQueue.update_quantity(). Se o
        valor digitado não for um número, a fila não é alterada — o
        próximo _refresh_queue_view() simplesmente redesenha o valor
        anterior, sem lançar exceção."""
        item = self._find_queue_item_by_codigo(codigo)
        if item is None:
            self._refresh_queue_view()
            return

        parsed = self._parse_quantity_input(raw_value)
        if parsed is not None:
            self.print_queue.update_quantity(item.product, parsed)

        self._refresh_queue_view()

    def _refresh_queue_view(self) -> None:
        """Único ponto de atualização da fila — chamado sempre que o
        PrintQueue muda, para manter cartões, contadores e estado dos
        botões sempre sincronizados com ele."""
        self._render_queue_cards()
        self._update_queue_summary()
        self._update_queue_button_states()

    def _render_queue_cards(self) -> None:
        for child in self.queue_items_frame.winfo_children():
            child.destroy()

        selected_card: tk.Frame | None = None

        for item in self.print_queue.to_list():
            codigo_do_item = item.product.codigo
            is_selected = codigo_do_item == self._selected_queue_codigo
            bg = "#dbeafe" if is_selected else "#ffffff"

            card = tk.Frame(self.queue_items_frame, bg=bg, highlightthickness=1, highlightbackground="#dbe2ea")
            card.pack(fill="x", padx=4, pady=(4, 0))
            # takefocus permite que o cartão receba foco de teclado ao ser
            # selecionado, para que o atalho DEL (ligado só a este widget)
            # nunca interfira com o Entry de edição de quantidade.
            card.configure(takefocus=True)
            card.bind("<Delete>", lambda _event, codigo=codigo_do_item: self._on_delete_key(codigo))
            if is_selected:
                selected_card = card

            descricao_label = tk.Label(
                card, text=item.product.descricao, bg=bg, font=("Segoe UI", 10, "bold"),
                anchor="w", justify="left", wraplength=220,
            )
            descricao_label.pack(fill="x", padx=6, pady=(6, 0))

            codigo_label = tk.Label(card, text=item.product.codigo, bg=bg, fg="#64748b", font=("Segoe UI", 9), anchor="w")
            codigo_label.pack(fill="x", padx=6)

            quantity_row = tk.Frame(card, bg=bg)
            quantity_row.pack(padx=6, pady=(2, 6))

            edit_controls_state = "disabled" if self._printing_in_progress else "normal"

            tk.Button(
                quantity_row, text="-", width=2, state=edit_controls_state,
                command=lambda codigo=codigo_do_item: self._on_decrement_queue_item(codigo),
            ).pack(side="left")

            quantidade_label = tk.Label(quantity_row, text=str(item.quantity), bg=bg, font=("Segoe UI", 10, "bold"), width=4)
            quantidade_label.pack(side="left", padx=4)
            if not self._printing_in_progress:
                quantidade_label.bind(
                    "<Double-Button-1>",
                    lambda _event, codigo=codigo_do_item, row=quantity_row, label=quantidade_label:
                        self._on_start_edit_quantity(codigo, row, label),
                )

            tk.Button(
                quantity_row, text="+", width=2, state=edit_controls_state,
                command=lambda codigo=codigo_do_item: self._on_increment_queue_item(codigo),
            ).pack(side="left")

            for widget in (card, descricao_label, codigo_label, quantidade_label):
                widget.bind("<Button-1>", lambda _event, codigo=codigo_do_item: self._on_select_queue_card(codigo))

        if selected_card is not None:
            selected_card.focus_set()

    def _update_queue_summary(self) -> None:
        self.queue_count_var.set(f"Produtos na fila: {self._format_count(self.print_queue.count())}")
        self.queue_total_var.set(f"Total de etiquetas: {self._format_count(self.print_queue.total_labels())}")

    def _update_queue_button_states(self) -> None:
        has_items = not self.print_queue.is_empty()
        printing = self._printing_in_progress

        queue_action_state = "normal" if (has_items and not printing) else "disabled"
        self.remove_from_queue_button.configure(state=queue_action_state)
        self.clear_queue_button.configure(state=queue_action_state)
        self.print_queue_button.configure(state=queue_action_state)

        self.add_to_queue_button.configure(state="disabled" if printing else "normal")

    # ------------------------------------------------------------------
    # Impressão da fila — reutiliza integralmente o motor de impressão já
    # existente (ZplBuilder.build_row + PrinterService.print_raw, os mesmos
    # usados pela aba "Impressão"). PrintQueueAdapter só converte os dados;
    # nenhuma regra de impressão nova é criada aqui.
    # ------------------------------------------------------------------

    def _on_print_queue(self) -> None:
        if self._printing_in_progress:
            return

        if self.print_queue.is_empty():
            messagebox.showinfo(APP_TITLE, "A fila de impressão está vazia. Adicione produtos antes de imprimir.")
            return

        printer_name = self.printer_var.get()
        if not printer_name:
            messagebox.showwarning(APP_TITLE, "Selecione uma impressora antes de imprimir.")
            return

        labels = PrintQueueAdapter.to_label_data(self.print_queue)
        product_count = self.print_queue.count()
        total_labels = self.print_queue.total_labels()

        self._printing_in_progress = True
        self._refresh_queue_view()

        thread = threading.Thread(
            target=self._run_queue_print_job,
            args=(labels, printer_name, product_count, total_labels),
            daemon=True,
        )
        thread.start()

    def _run_queue_print_job(
        self, labels: list[LabelData], printer_name: str, product_count: int, total_labels: int
    ) -> None:
        """Executado em thread separada para não travar a interface —
        mesmo padrão já usado pela impressão em lote da aba "Impressão"."""
        start_time = time.time()
        try:
            printer_service = PrinterService(printer_name)
            zpl_builder = ZplBuilder()

            rows = [labels[i : i + BATCH_ROW_COLUMNS] for i in range(0, len(labels), BATCH_ROW_COLUMNS)]
            row_width = BATCH_COLUMN_PITCH * BATCH_ROW_COLUMNS
            for row in rows:
                zpl = zpl_builder.build_row(row, column_pitch=BATCH_COLUMN_PITCH, total_width=row_width)
                printer_service.print_raw(zpl)
        except Exception as exc:
            elapsed = time.time() - start_time
            log_print_job(product_count, total_labels, elapsed, "falha")
            self._tk_root.after(0, self._on_print_job_error, exc)
            return

        elapsed = time.time() - start_time
        log_print_job(product_count, total_labels, elapsed, "sucesso")
        self._tk_root.after(0, self._on_print_job_finished)

    def _on_print_job_finished(self) -> None:
        """Nunca limpa a fila sozinho: só pergunta, e só apaga se o usuário
        confirmar as duas perguntas — sucesso e limpeza."""
        self._printing_in_progress = False
        self._refresh_queue_view()

        if messagebox.askyesno(APP_TITLE, "A impressão foi concluída com sucesso?"):
            if messagebox.askyesno(APP_TITLE, "Deseja limpar a fila de impressão?"):
                self.print_queue.clear()
                self._selected_queue_codigo = None
                self._refresh_queue_view()

    def _on_print_job_error(self, exc: Exception) -> None:
        """Erro nunca apaga a fila — o usuário pode corrigir (impressora,
        papel etc.) e tentar novamente sem perder o que já montou."""
        self._printing_in_progress = False
        self._refresh_queue_view()
        messagebox.showerror(APP_TITLE, f"Não foi possível concluir a impressão: {exc}")

    # ------------------------------------------------------------------
    # Configuração: arquivo, abas, mapeamento
    # ------------------------------------------------------------------

    def _get_repository(self, file_path: str | None = None) -> CatalogRepository:
        """Retorna o repositório atual, recriando-o apenas se o arquivo
        configurado mudou — preserva o cache em memória entre chamadas."""
        path = file_path if file_path is not None else self.file_path_var.get()
        if self.repository is None or str(self.repository.data_source.file_path) != path:
            self.repository = CatalogRepository(ExcelCatalogSource(path))
        return self.repository

    def _ensure_service(self) -> CatalogService:
        """Retorna o CatalogService atual, recriando-o apenas se o
        repositório mudou (arquivo diferente) — preserva pesquisa/filtro/
        ordenação em vigor entre chamadas."""
        repository = self._get_repository()
        if self.service is None or self.service.repository is not repository:
            self.service = CatalogService(repository, self.settings)
        return self.service

    def _on_select_file(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Selecione o arquivo Excel do catálogo",
            filetypes=[("Arquivos Excel", "*.xlsx"), ("Todos os arquivos", "*")],
        )
        if not file_path:
            return

        self.file_path_var.set(file_path)
        self._save_settings()
        self._load_sheets(default_all_checked=True)
        self._clear_catalog_view()

    def _load_sheets(self, default_all_checked: bool) -> None:
        file_path = self.file_path_var.get()
        if not file_path:
            return

        try:
            sheets = self._get_repository().list_sheets()
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Não foi possível ler as abas do arquivo: {exc}")
            return

        checked = set(sheets) if default_all_checked else set(self.settings.selected_sheets)
        self._rebuild_sheet_checkboxes(sheets, checked)
        self._refresh_column_options()
        self._save_settings()

    def _rebuild_sheet_checkboxes(self, sheets: list[str], checked: set[str]) -> None:
        for child in self.sheets_container.winfo_children():
            child.destroy()
        self.sheet_vars = {}

        if not sheets:
            ttk.Label(self.sheets_container, text="Nenhuma aba encontrada no arquivo.").pack(anchor="w")
            return

        for name in sheets:
            var = tk.BooleanVar(value=name in checked)
            self.sheet_vars[name] = var
            ttk.Checkbutton(
                self.sheets_container, text=name, variable=var, command=self._on_sheet_toggle
            ).pack(anchor="w")

    def _on_sheet_toggle(self) -> None:
        self._refresh_column_options()
        self._save_settings()

    def _selected_sheet_names(self) -> list[str]:
        return [name for name, var in self.sheet_vars.items() if var.get()]

    def _refresh_column_options(self) -> None:
        selected_sheets = self._selected_sheet_names()
        if not selected_sheets:
            headers: list[str] = []
        else:
            try:
                headers = self._get_repository().get_available_headers(selected_sheets)
            except Exception as exc:
                messagebox.showerror(APP_TITLE, f"Não foi possível ler os cabeçalhos: {exc}")
                headers = []

        for combobox in self.column_comboboxes.values():
            combobox["values"] = headers

    def _save_settings(self) -> None:
        self.settings.file_path = self.file_path_var.get()
        self.settings.selected_sheets = self._selected_sheet_names()
        self.settings.column_map = {
            internal_field: var.get() for internal_field, var in self.column_vars.items() if var.get()
        }
        self.settings.save_to(self.config)
        self.config_manager.save(self.config)

    def _has_complete_settings(self) -> bool:
        return bool(
            self.settings.file_path
            and self.settings.selected_sheets
            and all(self.settings.column_map.get(internal_field) for internal_field in CATALOG_FIELDS)
        )

    def _on_test_configuration(self) -> None:
        self._save_settings()

        if not self.settings.file_path:
            messagebox.showwarning(APP_TITLE, "Selecione um arquivo Excel antes de testar a configuração.")
            return

        try:
            data_source = ExcelCatalogSource(self.settings.file_path)
            report = CatalogConfigurationValidator(data_source).validate(self.settings)
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Falha ao testar a configuração: {exc}")
            return

        self._show_report(report)

    def _show_report(self, report: ValidationReport) -> None:
        text = self._format_report(report)
        self.report_text.configure(state="normal")
        self.report_text.delete("1.0", tk.END)
        self.report_text.insert("1.0", text)
        self.report_text.configure(state="disabled")

    def _format_report(self, report: ValidationReport) -> str:
        lines: list[str] = []
        lines.append(("✔" if report.file_found else "✘") + " Arquivo encontrado")

        if report.file_found:
            lines.append(f"✔ {len(report.sheets_found)} aba(s) selecionada(s)")
            lines.append(("✔" if report.all_columns_found else "✘") + " Todas as colunas localizadas")
            if report.all_columns_found:
                total = f"{report.total_products:,}".replace(",", ".")
                lines.append(f"✔ {total} produtos encontrados")

        if report.issues:
            lines.append("")
            for issue in report.issues:
                lines.append(f"✘ {issue.message}")

        lines.append("")
        lines.append("Configuração válida." if report.is_valid else "Configuração inválida — corrija os itens acima.")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Catálogo: apenas apresentação — lê controles, chama CatalogService,
    # atualiza tabela/contadores. Nenhuma pesquisa/filtro/ordenação aqui.
    # ------------------------------------------------------------------

    def _try_initial_load(self) -> None:
        """Carrega o catálogo automaticamente na abertura, se a configuração
        salva já estiver completa. Falha silenciosamente (deixa o catálogo
        vazio) para não interromper a abertura do programa com um erro."""
        try:
            service = self._ensure_service()
            service.reload()
        except Exception:
            return

        self._refresh_filter_options()
        self._refresh_catalog_view()

    def _on_reload_catalog(self) -> None:
        self._save_settings()

        if not self._has_complete_settings():
            messagebox.showwarning(
                APP_TITLE,
                "Configure o arquivo, as abas e o mapeamento de todas as colunas antes de carregar o catálogo.",
            )
            return

        try:
            service = self._ensure_service()
            products = service.reload()
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Não foi possível carregar o catálogo: {exc}")
            return

        self._save_settings()  # persiste o last_reload atualizado pelo service

        self._refresh_filter_options()
        self._refresh_catalog_view()
        self.last_reload_var.set(self._format_last_reload(self.settings.last_reload))
        messagebox.showinfo(APP_TITLE, f"Catálogo recarregado: {len(products)} produto(s) encontrado(s).")

    def _clear_catalog_view(self) -> None:
        self.repository = None
        self.service = None
        self.catalog_filtered_products = []
        self.supplier_combobox["values"] = [SUPPLIER_ALL]
        self.supplier_var.set(SUPPLIER_ALL)
        self.category_combobox["values"] = [CATEGORY_ALL]
        self.category_filter_var.set(CATEGORY_ALL)
        self._load_catalog_table()
        self._update_catalog_summary()

    def _refresh_filter_options(self) -> None:
        """Atualiza os valores dos combobox de fornecedor/categoria a
        partir do CatalogService — nunca calculados aqui na interface."""
        if self.service is None:
            return

        suppliers = self.service.get_suppliers()
        self.supplier_combobox["values"] = suppliers
        if self.supplier_var.get() not in suppliers:
            self.supplier_var.set(SUPPLIER_ALL)

        categories = self.service.get_categories()
        self.category_combobox["values"] = categories
        if self.category_filter_var.get() not in categories:
            self.category_filter_var.set(CATEGORY_ALL)

    def _on_catalog_search_change(self) -> None:
        if self.service is None:
            return
        self.service.search(self.catalog_search_var.get())
        self._refresh_catalog_view()

    def _on_supplier_filter_change(self, _event: Any = None) -> None:
        if self.service is None:
            return
        self.service.filter_supplier(self.supplier_var.get())
        self._refresh_catalog_view()

    def _on_category_filter_change(self, _event: Any = None) -> None:
        if self.service is None:
            return
        self.service.filter_category(self.category_filter_var.get())
        self._refresh_catalog_view()

    def _on_sort_column(self, field: str) -> None:
        if self.service is None:
            return
        reverse = self._sort_field == field and not self._sort_reverse
        self._sort_field = field
        self._sort_reverse = reverse
        self.service.sort_by(field, reverse=reverse)
        self._refresh_catalog_view()

    def _refresh_catalog_view(self) -> None:
        """Pede ao CatalogService o resultado já filtrado/ordenado e só
        desenha — a interface nunca decide o que aparece."""
        if self.service is None:
            self.catalog_filtered_products = []
        else:
            self.catalog_filtered_products = self.service.apply_filters()
        self._load_catalog_table()
        self._update_catalog_summary()

    def _load_catalog_table(self) -> None:
        self.catalog_tree.delete(*self.catalog_tree.get_children())
        for index, product in enumerate(self.catalog_filtered_products):
            preco_texto = f"{product.preco:.2f}" if product.preco is not None else ""
            # Quantidade padrão vive em attributes (não é mais campo do
            # produto) — normalize_quantity() é a mesma regra que
            # CatalogService.create_print_item() usa ao montar um PrintItem.
            quantidade_padrao = normalize_quantity(product.attributes.get("default_quantity"))
            self.catalog_tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    product.fornecedor,
                    product.codigo,
                    product.descricao,
                    product.display_category,
                    product.numeracao,
                    quantidade_padrao,
                    preco_texto,
                ),
            )

    def _update_catalog_summary(self) -> None:
        total = self.service.get_statistics().total_products if self.service is not None else 0
        showing = len(self.catalog_filtered_products)
        self.catalog_summary_var.set(
            f"Total: {self._format_count(total)} | Exibindo: {self._format_count(showing)}"
        )

    def _format_count(self, value: int) -> str:
        return f"{value:,}".replace(",", ".")

    def _format_last_reload(self, value: str | None) -> str:
        if not value:
            return "Última atualização: nunca"
        try:
            parsed = datetime.strptime(value, "%Y-%m-%d %H:%M")
            return f"Última atualização: {parsed.strftime('%d/%m/%Y %H:%M')}"
        except ValueError:
            return f"Última atualização: {value}"
