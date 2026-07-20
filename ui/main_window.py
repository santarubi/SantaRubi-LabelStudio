"""Interface principal do Santa Rubi Label Studio.

Esta janela apresenta a estrutura visual completa da aplicação, sem
implementação de lógica de negócio.
"""

from pathlib import Path
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any

from PIL import Image, ImageTk

from core.config import ConfigManager
from core.excel_reader import ExcelReader
from core.label_renderer import LabelRenderer
from core.printer import PrinterService

APP_TITLE = "Santa Rubi Label Studio"
WINDOW_SIZE = "1000x700"


class MainWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry(WINDOW_SIZE)
        self.root.minsize(1000, 700)
        self.root.configure(bg="#f4f6f8")

        self.mode_var = tk.StringVar(value="batch")
        self.excel_path_var = tk.StringVar()
        self.printer_var = tk.StringVar(value="Impressora padrão")
        self.layout_var = tk.StringVar(value="Layout Padrão")
        self.quantity_mode_var = tk.StringVar(value="all")
        self.from_var = tk.StringVar()
        self.to_var = tk.StringVar()
        self.product_code_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Status: Pronto.")
        self.reader: ExcelReader | None = None

        self.config_manager = ConfigManager()
        self.config: dict[str, Any] = self.config_manager.load()
        self.all_products: list[dict[str, Any]] = []
        self.filtered_products: list[dict[str, Any]] = []
        self.selected_product_ids: set[str] = set()
        self.sort_column: str | None = None
        self.sort_reverse = False
        self.search_var = tk.StringVar()

        self.loaded_products_count = 0
        self.selected_products_count = 0
        self.labels_to_print_count = 0
        self.loaded_count_var = tk.StringVar(value="Produtos carregados: 0")
        self.selected_count_var = tk.StringVar(value="Selecionados: 0")
        self.labels_count_var = tk.StringVar(value="Etiquetas: 0")

        if self.config.get("last_mode") in ("batch", "quick"):
            self.mode_var.set(self.config["last_mode"])
        self.excel_path_var.set(self.config.get("last_excel_path", ""))
        self.printer_var.set(self.config.get("last_printer", "Impressora padrão"))
        self.layout_var.set(self.config.get("last_layout", "Layout Padrão"))
        if self.config.get("window_geometry"):
            self.root.geometry(self.config["window_geometry"])

        self.quick_code_var = tk.StringVar()
        self.quick_code_display_var = tk.StringVar(value="—")
        self.quick_category_var = tk.StringVar(value="—")
        self.quick_description_var = tk.StringVar(value="—")
        self.quick_number_var = tk.StringVar(value="—")
        self.quick_price_var = tk.StringVar(value="—")

        self.label_renderer: LabelRenderer | None = None
        self.printer_service: PrinterService | None = None
        self.batch_cancelled = False
        self.batch_thread: threading.Thread | None = None
        self.batch_progress_var = tk.DoubleVar(value=0.0)
        self.batch_status_var = tk.StringVar(value="")
        self._current_product: dict[str, Any] | None = None

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
        main_container = ttk.Frame(self.root, style="Content.TFrame", padding=16)
        main_container.pack(fill="both", expand=True)
        main_container.grid_columnconfigure(0, weight=1)
        main_container.grid_rowconfigure(2, weight=1)

        header = ttk.Frame(main_container, style="Header.TFrame", padding=(0, 6))
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        title_label = ttk.Label(header, text=APP_TITLE, style="Title.TLabel")
        title_label.grid(row=0, column=0, sticky="w")

        settings_button = ttk.Button(header, text="Configurações", style="App.TButton")
        settings_button.grid(row=0, column=1, sticky="e")

        top_controls = ttk.Frame(main_container)
        top_controls.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        top_controls.grid_columnconfigure(0, weight=1)
        top_controls.grid_columnconfigure(1, weight=1)
        top_controls.grid_columnconfigure(2, weight=0)

        ttk.Label(top_controls, text="Arquivo Excel").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 4))

        excel_entry_row = ttk.Frame(top_controls)
        excel_entry_row.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        excel_entry_row.grid_columnconfigure(0, weight=1)
        ttk.Entry(excel_entry_row, textvariable=self.excel_path_var).grid(row=0, column=0, sticky="ew")
        ttk.Button(excel_entry_row, text="Selecionar Planilha", style="App.TButton", command=self._on_select_excel).grid(row=0, column=1, padx=(8, 0))

        printer_panel = ttk.Frame(top_controls)
        printer_panel.grid(row=2, column=0, sticky="ew", padx=(0, 8))
        printer_panel.grid_columnconfigure(0, weight=1)
        ttk.Label(printer_panel, text="Impressora").grid(row=0, column=0, sticky="w", pady=(0, 4))
        ttk.Combobox(printer_panel, textvariable=self.printer_var, values=["Impressora padrão", "Impressora 2"], state="readonly").grid(row=1, column=0, sticky="ew")

        layout_panel = ttk.Frame(top_controls)
        layout_panel.grid(row=2, column=1, sticky="ew")
        layout_panel.grid_columnconfigure(0, weight=1)
        ttk.Label(layout_panel, text="Layout").grid(row=0, column=0, sticky="w", pady=(0, 4))
        ttk.Combobox(layout_panel, textvariable=self.layout_var, values=["Layout Padrão", "Layout 2"], state="readonly").grid(row=1, column=0, sticky="ew")

        search_frame = ttk.Frame(top_controls)
        search_frame.grid(row=3, column=0, columnspan=3, sticky="ew")
        search_frame.grid_columnconfigure(0, weight=1)
        ttk.Label(search_frame, text="Pesquisar").grid(row=0, column=0, sticky="w", pady=(0, 4))
        ttk.Entry(search_frame, textvariable=self.search_var).grid(row=1, column=0, sticky="ew")
        self.search_var.trace_add("write", lambda *_: self._on_search_change())

        content_frame = ttk.Frame(main_container)
        content_frame.grid(row=2, column=0, sticky="nsew")
        content_frame.grid_columnconfigure(0, weight=5)
        content_frame.grid_columnconfigure(1, weight=0, minsize=380)
        content_frame.grid_rowconfigure(0, weight=1)

        left_panel = ttk.Frame(content_frame, style="Card.TFrame", padding=12)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))
        left_panel.grid_columnconfigure(0, weight=1)
        left_panel.grid_rowconfigure(1, weight=1)

        selection_buttons = ttk.Frame(left_panel)
        selection_buttons.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        selection_buttons.grid_columnconfigure(0, weight=1)
        selection_buttons.grid_columnconfigure(1, weight=1)
        selection_buttons.grid_columnconfigure(2, weight=1)
        ttk.Button(selection_buttons, text="Selecionar Todos", style="App.TButton", command=self._select_all).grid(row=0, column=0, sticky="ew")
        ttk.Button(selection_buttons, text="Desmarcar Todos", style="App.TButton", command=self._deselect_all).grid(row=0, column=1, sticky="ew", padx=(8, 8))
        ttk.Button(selection_buttons, text="Inverter Seleção", style="App.TButton", command=self._invert_selection).grid(row=0, column=2, sticky="ew")

        table_frame = ttk.Frame(left_panel)
        table_frame.grid(row=1, column=0, sticky="nsew")
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)

        self.product_tree = ttk.Treeview(
            table_frame,
            columns=("selecionar", "codigo", "descricao", "categoria", "qtd", "preco", "numero"),
            show="headings",
            selectmode="extended",
        )
        self.product_tree.grid(row=0, column=0, sticky="nsew")

        vertical_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.product_tree.yview)
        self.product_tree.configure(yscrollcommand=vertical_scroll.set)
        vertical_scroll.grid(row=0, column=1, sticky="ns")

        self.product_tree.heading("selecionar", text="Seleção", command=lambda: self._sort_table("selecionar"), anchor="center")
        self.product_tree.heading("codigo", text="Código", command=lambda: self._sort_table("codigo"), anchor="center")
        self.product_tree.heading("descricao", text="Descrição", command=lambda: self._sort_table("descricao"), anchor="w")
        self.product_tree.heading("categoria", text="Categoria", command=lambda: self._sort_table("categoria"), anchor="w")
        self.product_tree.heading("qtd", text="Quantidade", command=lambda: self._sort_table("qtd"), anchor="center")
        self.product_tree.heading("preco", text="Preço", command=lambda: self._sort_table("preco"), anchor="center")
        self.product_tree.heading("numero", text="Número", command=lambda: self._sort_table("numero"), anchor="center")

        self.product_tree.column("selecionar", anchor="center", width=50, minwidth=50, stretch=False)
        self.product_tree.column("codigo", anchor="center", width=90, minwidth=90, stretch=False)
        self.product_tree.column("descricao", anchor="w", width=240, minwidth=120, stretch=True)
        self.product_tree.column("categoria", anchor="w", width=180, minwidth=120, stretch=False)
        self.product_tree.column("qtd", anchor="center", width=80, minwidth=80, stretch=False)
        self.product_tree.column("preco", anchor="e", width=90, minwidth=90, stretch=False)
        self.product_tree.column("numero", anchor="center", width=70, minwidth=70, stretch=False)


        self.product_tree.bind("<<TreeviewSelect>>", self._on_table_select)
        self.product_tree.bind("<Double-1>", self._on_table_double_click)
        self.product_tree.bind("<Button-1>", self._on_table_click)

        right_panel = ttk.Frame(content_frame, style="Card.TFrame", padding=12)
        right_panel.grid(row=0, column=1, sticky="nsew", pady=(0, 8))
        right_panel.grid_columnconfigure(0, weight=1)
        right_panel.grid_rowconfigure(0, weight=0)
        right_panel.grid_rowconfigure(1, weight=0)
        right_panel.grid_rowconfigure(2, weight=1)
        right_panel.grid_rowconfigure(3, weight=0)
        right_panel.grid_rowconfigure(4, weight=0)

        self.batch_frame = ttk.Frame(right_panel)
        self.batch_frame.grid(row=0, column=0, sticky="ew")
        self.quick_frame = ttk.Frame(right_panel)
        self.quick_frame.grid(row=0, column=0, sticky="ew")
        self._build_batch_content()
        self._build_quick_content()
        self._show_active_mode()

        preview_label = ttk.Label(right_panel, text="Pré-visualização da etiqueta", style="Subtitle.TLabel")
        preview_label.grid(row=1, column=0, sticky="w", pady=(8, 0))

        preview_frame = ttk.Frame(right_panel, style="Card.TFrame")
        preview_frame.grid(row=2, column=0, sticky="nsew", pady=(8, 8))
        preview_frame.grid_columnconfigure(0, weight=1)
        preview_frame.grid_rowconfigure(0, weight=1)
        preview_frame.configure(height=340)

        self.preview_canvas = tk.Canvas(preview_frame, bg="#ffffff", highlightthickness=1, highlightbackground="#dbe2ea")
        self.preview_canvas.grid(row=0, column=0, sticky="nsew", padx=(6, 6), pady=(6, 6))
        self.preview_canvas.bind("<Configure>", self._on_preview_resize)
        self.label_renderer = LabelRenderer(self.preview_canvas)
        self._preview_image_ref = None
        self._draw_preview_placeholder()

        progress_frame = ttk.Frame(right_panel)
        progress_frame.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        progress_frame.grid_columnconfigure(0, weight=1)
        ttk.Progressbar(progress_frame, style="Slim.Horizontal.TProgressbar", variable=self.batch_progress_var, maximum=100).grid(row=0, column=0, sticky="ew")

        preview_button_frame = ttk.Frame(right_panel)
        preview_button_frame.grid(row=4, column=0, sticky="ew")
        preview_button_frame.grid_columnconfigure(0, weight=1)
        preview_button_frame.grid_columnconfigure(1, weight=1)
        preview_button_frame.grid_columnconfigure(2, weight=1)
        ttk.Button(preview_button_frame, text="Visualizar", style="App.TButton", command=self._draw_preview_placeholder).grid(row=0, column=0, sticky="ew")
        ttk.Button(preview_button_frame, text="Imprimir", style="Primary.TButton", command=self._on_print).grid(row=0, column=1, sticky="ew", padx=(8, 8))
        ttk.Button(preview_button_frame, text="Teste de Impressão", style="Primary.TButton", command=self._on_test_print).grid(row=0, column=2, sticky="ew")

        bottom_bar = ttk.Frame(main_container, style="Header.TFrame", padding=(0, 10))
        bottom_bar.grid(row=3, column=0, sticky="ew")
        bottom_bar.grid_columnconfigure(0, weight=1)
        self.bottom_status_var = tk.StringVar(value="Produtos carregados: 0 | Visíveis: 0 | Selecionados: 0 | Etiquetas: 0 | Impressora: Impressora padrão | Layout: Layout Padrão | Status: Pronto")
        ttk.Label(bottom_bar, textvariable=self.bottom_status_var, style="Subtitle.TLabel").grid(row=0, column=0, sticky="w")

    def _build_batch_content(self):
        frame = ttk.LabelFrame(self.batch_frame, text="Configuração de impressão", padding=12)
        frame.pack(fill="x", expand=True)

        quantity_frame = ttk.LabelFrame(frame, text="Quantidade", padding=(12, 10))
        quantity_frame.pack(fill="x", pady=(0, 10))

        ttk.Radiobutton(quantity_frame, text="Todas", variable=self.quantity_mode_var, value="all").grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(quantity_frame, text="Intervalo", variable=self.quantity_mode_var, value="range").grid(row=1, column=0, sticky="w", pady=(6, 8))

        range_row = ttk.Frame(quantity_frame)
        range_row.grid(row=2, column=0, sticky="ew")
        range_row.grid_columnconfigure(1, weight=1)
        ttk.Label(range_row, text="De").grid(row=0, column=0, sticky="w")
        ttk.Entry(range_row, textvariable=self.from_var, width=10).grid(row=0, column=1, sticky="w", padx=(6, 12))
        ttk.Label(range_row, text="Até").grid(row=0, column=2, sticky="w")
        ttk.Entry(range_row, textvariable=self.to_var, width=10).grid(row=0, column=3, sticky="w", padx=(6, 0))

        progress_frame = ttk.LabelFrame(frame, text="Progresso", padding=(12, 10))
        progress_frame.pack(fill="x")
        ttk.Progressbar(progress_frame, style="Slim.Horizontal.TProgressbar", variable=self.batch_progress_var, maximum=100).pack(fill="x")
        ttk.Label(progress_frame, textvariable=self.batch_status_var).pack(anchor="w", pady=(6, 0))

        self.batch_current_var = tk.StringVar(value="")
        ttk.Label(progress_frame, textvariable=self.batch_current_var, foreground="#334155").pack(anchor="w", pady=(4, 0))

    def _build_quick_content(self):
        form_frame = ttk.LabelFrame(self.quick_frame, text="Consulta rápida", padding=16)
        form_frame.pack(fill="both", expand=True)

        ttk.Label(form_frame, text="Código").pack(anchor="w")
        quick_entry = ttk.Entry(form_frame, textvariable=self.quick_code_var, width=50)
        quick_entry.pack(fill="x", pady=(6, 16))
        quick_entry.bind("<Return>", self._on_quick_search)

        details_frame = ttk.LabelFrame(form_frame, text="Detalhes do produto", padding=12)
        details_frame.pack(fill="both", expand=True)

        rows = [
            ("Código", self.quick_code_display_var),
            ("Categoria", self.quick_category_var),
            ("Descrição", self.quick_description_var),
            ("Número", self.quick_number_var),
            ("Preço", self.quick_price_var),
        ]

        for label_text, value_var in rows:
            row = ttk.Frame(details_frame)
            row.pack(fill="x", pady=4)
            ttk.Label(row, text=label_text, width=16).pack(side="left")
            ttk.Label(row, textvariable=value_var, style="DetailValue.TLabel").pack(side="left")

    def _show_active_mode(self):
        if self.mode_var.get() == "quick":
            self.batch_frame.grid_remove()
            self.quick_frame.grid()
        else:
            self.quick_frame.grid_remove()
            self.batch_frame.grid()

    def _parse_int(self, value: str) -> int | None:
        """Converte valores para inteiro, retornando None se não forem válidos."""
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _get_product_list_from_reader(self) -> list[dict[str, Any]]:
        """Constrói uma lista de produtos normalizada a partir do reader carregado."""
        if self.reader is None or self.reader.error_message:
            return []

        products: list[dict[str, Any]] = []
        for index, row in enumerate(self.reader.rows):
            products.append(
                {
                    "_id": f"product_{index}",
                    "codigo": row.get("CODIGO"),
                    "categoria": row.get("CATEGORIA"),
                    "descricao": row.get("DESCRICAO"),
                    "numero": row.get("NUMERO"),
                    "preco": row.get("PRECO"),
                    "qtd": row.get("QTD"),
                }
            )
        return products

    def _apply_search_filter(self, query: str) -> list[dict[str, Any]]:
        """Filtra os produtos carregados com base no texto de pesquisa."""
        if not query:
            return list(self.all_products)

        normalized_query = query.strip().lower()
        filtered: list[dict[str, Any]] = []
        for product in self.all_products:
            if any(
                normalized_query in str(product.get(field, "")).strip().lower()
                for field in ("codigo", "categoria", "descricao", "numero")
            ):
                filtered.append(product)
        return filtered

    def _load_products_into_table(self) -> None:
        """Carrega a lista de produtos filtrados na Treeview de produtos."""
        self.product_tree.delete(*self.product_tree.get_children())

        for product in self.filtered_products:
            selected = product["_id"] in self.selected_product_ids
            self.product_tree.insert(
                "",
                "end",
                iid=product["_id"],
                values=(
                    "✓" if selected else "",
                    self._format_value(product.get("codigo")),
                    self._format_value(product.get("descricao")),
                    self._format_value(product.get("categoria")),
                    self._format_value(product.get("qtd")),
                    self._format_value(product.get("preco")),
                    self._format_value(product.get("numero")),
                ),
            )

        visible_ids = {product["_id"] for product in self.filtered_products}
        self.product_tree.selection_set(self.selected_product_ids.intersection(visible_ids))
        self._refresh_counts()

        if self.selected_product_ids:
            selected_product = next((product for product in self.filtered_products if product["_id"] in self.selected_product_ids), None)
            if selected_product is not None:
                self._current_product = selected_product
                self._draw_label_preview(selected_product)
                return

        self._draw_preview_placeholder()
    def _refresh_counts(self) -> None:
        """Atualiza os contadores de produtos carregados, selecionados e etiquetas."""
        self.loaded_products_count = len(self.all_products)
        self.selected_products_count = len(self.selected_product_ids)
        self.labels_to_print_count = sum(
            self._parse_quantity(product.get("qtd"))
            for product in self.all_products
            if not self.selected_product_ids or product["_id"] in self.selected_product_ids
        )

        self.loaded_count_var.set(f"Produtos carregados: {self.loaded_products_count}")
        self.selected_count_var.set(f"Selecionados: {self.selected_products_count}")
        self.labels_count_var.set(f"Etiquetas: {self.labels_to_print_count}")
        self._refresh_bottom_status()

    def _refresh_bottom_status(self) -> None:
        """Atualiza a barra de status inferior com informações de modo, impressora e status atual."""
        printer = self.printer_var.get() or "Impressora padrão"
        layout = self.layout_var.get() or "Layout Padrão"
        status_text = self.batch_status_var.get() or self.status_var.get()
        mode = "Impressão Rápida" if self.mode_var.get() == "quick" else "Impressão em Lote"
        self.bottom_status_var.set(
            f"Produtos carregados: {self.loaded_products_count} | Visíveis: {len(self.filtered_products)} | Selecionados: {self.selected_products_count} | Etiquetas: {self.labels_to_print_count} | Impressora: {printer} | Layout: {layout} | Status: {status_text}"
        )

    def _parse_quantity(self, value: Any) -> int:
        """Converte valores de quantidade para inteiro, considerando vazios como 1 e zero como zero."""
        if value is None:
            return 1
        if isinstance(value, str) and value.strip() == "":
            return 1
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return 1

    def _fill_quick_details(self, product: dict):
        """Preenche os campos de detalhes do produto na interface."""
        self.quick_code_display_var.set(self._format_value(product.get("codigo")))
        self.quick_category_var.set(self._format_value(product.get("categoria")))
        self.quick_description_var.set(self._format_value(product.get("descricao")))
        self.quick_number_var.set(self._format_value(product.get("numero")))
        self.quick_price_var.set(self._format_value(product.get("preco")))
        self._current_product = product
        self._draw_label_preview(product)

    def _on_test_print(self):
        """Envia uma etiqueta de teste para a impressora selecionada."""
        if not self.printer_var.get():
            messagebox.showwarning(APP_TITLE, "Selecione uma impressora antes de testar a impressão.")
            return

        test_product = {
            "codigo": "999999",
            "categoria": "TESTE",
            "descricao": "ETIQUETA TESTE",
            "numero": "",
            "preco": 0.0,
        }
        self._current_product = test_product
        self._draw_label_preview(test_product)

        self.printer_service = PrinterService(self.printer_var.get())
        try:
            image = self.label_renderer.render_image(test_product) if self.label_renderer is not None else None
            if image is None:
                raise RuntimeError("Renderer da etiqueta não inicializado.")

            self.printer_service.print_image(image)
            self.status_var.set(
                "Status: Teste de impressão enviado. Resolução: 300x220. Imagem: 300x220. "
                "Tamanho físico: 30 mm x 15 mm. DPI: 300."
            )
            messagebox.showinfo(APP_TITLE, "Etiqueta de teste enviada para a impressora.")
        except Exception as exc:
            self.status_var.set(f"Status: Falha ao testar a impressão: {exc}")
            messagebox.showerror(APP_TITLE, f"Não foi possível enviar a etiqueta de teste: {exc}")


    def _clear_quick_details(self):
        """Limpa os campos de detalhes do produto."""
        self.quick_code_display_var.set("—")
        self.quick_category_var.set("—")
        self.quick_description_var.set("—")
        self.quick_number_var.set("—")
        self.quick_price_var.set("—")
        self._current_product = None
        self._draw_preview_placeholder()

    def _format_value(self, value):
        """Formata valores para exibição na interface."""
        if value is None:
            return "—"
        if isinstance(value, float):
            return f"{value:.2f}"
        return str(value)

    def _build_label_image(self):
        """Gera uma imagem Pillow a partir do estado atual da etiqueta."""
        if self.label_renderer is None:
            raise RuntimeError("Renderer da etiqueta não inicializado.")

        if not hasattr(self, "_current_product"):
            raise RuntimeError("Nenhum produto está carregado para impressão.")

        return self.label_renderer.render_image(self._current_product)

    def _draw_preview_placeholder(self):
        """Desenha a pré-visualização vazia da etiqueta."""
        self._render_preview_image(None)

    def _draw_label_preview(self, product: dict):
        """Desenha a etiqueta com os dados do produto."""
        self._render_preview_image(product)

    def _on_preview_resize(self, _: Any) -> None:
        """Redesenha a pré-visualização quando o canvas é redimensionado."""
        if self.selected_product_ids and self._current_product is not None:
            self._render_preview_image(self._current_product)
        else:
            self._render_preview_image(None)

    def _render_preview_image(self, product: dict | None) -> None:
        width = self.preview_canvas.winfo_width()
        height = self.preview_canvas.winfo_height()
        if width < 10 or height < 10:
            return

        self.preview_canvas.delete("all")
        self.preview_canvas.create_rectangle(4, 4, width - 4, height - 4, outline="#e2e8f0", width=2)

        if product is None:
            self.preview_canvas.create_text(
                width / 2,
                height / 2,
                text="Selecione um produto",
                font=("Segoe UI", 11, "bold"),
                fill="#64748b",
            )
            self._preview_image_ref = None
            return

        image = self.label_renderer.render_image(product) if self.label_renderer is not None else None
        if image is None:
            self.preview_canvas.create_text(
                width / 2,
                height / 2,
                text="Selecione um produto",
                font=("Segoe UI", 11, "bold"),
                fill="#64748b",
            )
            self._preview_image_ref = None
            return

        image_ratio = image.width / image.height
        canvas_ratio = width / height
        if canvas_ratio > image_ratio:
            target_height = min(height - 24, image.height)
            target_width = int(target_height * image_ratio)
        else:
            target_width = min(width - 24, image.width)
            target_height = int(target_width / image_ratio)

        target_width = max(1, target_width)
        target_height = max(1, target_height)

        resized = image.resize((target_width, target_height), Image.Resampling.LANCZOS)
        self._preview_image_ref = ImageTk.PhotoImage(resized)
        self.preview_canvas.create_image(width / 2, height / 2, image=self._preview_image_ref)

    def _save_config(self) -> None:
        """Salva as preferências atuais do usuário no arquivo de configuração."""
        self.config["last_mode"] = self.mode_var.get()
        self.config["last_excel_path"] = self.excel_path_var.get()
        self.config["last_printer"] = self.printer_var.get()
        self.config["last_layout"] = self.layout_var.get()
        self.config["window_geometry"] = self.root.winfo_geometry()
        self.config_manager.save(self.config)

    def _on_select_excel(self) -> None:
        """Abre o diálogo para selecionar um arquivo Excel e carrega os produtos."""
        file_path = filedialog.askopenfilename(
            title="Selecione a planilha Excel",
            filetypes=[("Arquivos Excel", "*.xlsx"), ("Todos os arquivos", "*")],
        )
        if not file_path:
            return

        self.excel_path_var.set(file_path)
        self.reader = ExcelReader(file_path)

        if self.reader.error_message:
            messagebox.showerror(APP_TITLE, self.reader.error_message)
            self.status_var.set(f"Status: {self.reader.error_message}")
            self.all_products = []
            self.filtered_products = []
            self.selected_product_ids.clear()
            self._load_products_into_table()
            return

        self.all_products = self._get_product_list_from_reader()
        self.filtered_products = self._apply_search_filter(self.search_var.get())
        self.selected_product_ids.clear()
        self._load_products_into_table()
        self.status_var.set(f"Status: Planilha carregada com {len(self.all_products)} produtos.")
        self._save_config()

    def _on_search_change(self) -> None:
        """Atualiza a lista exibida conforme o texto de pesquisa."""
        self.filtered_products = self._apply_search_filter(self.search_var.get())
        self._load_products_into_table()

    def _on_table_select(self, _: Any) -> None:
        """Atualiza a seleção interna ao selecionar linhas na tabela e redesenha a pré-visualização."""
        self.selected_product_ids = set(self.product_tree.selection())
        self._refresh_counts()

        if self.selected_product_ids:
            selected_id = next(iter(self.selected_product_ids))
            product = next((product for product in self.filtered_products if product["_id"] == selected_id), None)
            if product is not None:
                self._current_product = product
                self._draw_label_preview(product)

    def _on_table_double_click(self, event: tk.Event) -> None:
        """Alterna a seleção do produto duplo clicado e atualiza a pré-visualização."""
        item_id = self.product_tree.identify_row(event.y)
        if not item_id:
            return

        if item_id in self.selected_product_ids:
            self.selected_product_ids.remove(item_id)
        else:
            self.selected_product_ids.add(item_id)

        self._load_products_into_table()

        product = next((product for product in self.filtered_products if product["_id"] == item_id), None)
        if product:
            self._current_product = product
            self._draw_label_preview(product)

    def _on_table_click(self, event: tk.Event) -> None:
        """Permite marcar/desmarcar a seleção clicando na coluna de seleção."""
        column = self.product_tree.identify_column(event.x)
        item_id = self.product_tree.identify_row(event.y)
        if column == "#1" and item_id:
            if item_id in self.selected_product_ids:
                self.selected_product_ids.remove(item_id)
            else:
                self.selected_product_ids.add(item_id)
            self._load_products_into_table()

    def _select_all(self) -> None:
        """Seleciona todos os produtos exibidos na tabela."""
        self.selected_product_ids = {product["_id"] for product in self.filtered_products}
        self._load_products_into_table()

    def _deselect_all(self) -> None:
        """Desmarca todos os produtos."""
        self.selected_product_ids.clear()
        self._load_products_into_table()

    def _invert_selection(self) -> None:
        """Inverte a seleção dos produtos exibidos atualmente."""
        current_ids = {product["_id"] for product in self.filtered_products}
        self.selected_product_ids = {product_id for product_id in current_ids if product_id not in self.selected_product_ids}
        self._load_products_into_table()

    def _sort_table(self, column: str) -> None:
        """Ordena a tabela de produtos por uma coluna específica."""
        if not self.filtered_products:
            return

        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = column
            self.sort_reverse = False

        key_map = {
            "selecionar": lambda item: item["_id"] in self.selected_product_ids,
            "codigo": lambda item: str(item.get("codigo", "")) if item.get("codigo") is not None else "",
            "descricao": lambda item: str(item.get("descricao", "")) if item.get("descricao") is not None else "",
            "categoria": lambda item: str(item.get("categoria", "")) if item.get("categoria") is not None else "",
            "qtd": lambda item: self._parse_int(item.get("qtd")) or 0,
            "preco": lambda item: float(item.get("preco")) if item.get("preco") is not None else 0.0,
            "numero": lambda item: str(item.get("numero", "")) if item.get("numero") is not None else "",
        }

        sort_key = key_map.get(column, lambda item: item.get(column, ""))
        self.filtered_products.sort(key=sort_key, reverse=self.sort_reverse)
        self._load_products_into_table()

    def _get_print_products(self) -> list[dict[str, Any]]:
        """Retorna a lista de produtos a serem impressos, de acordo com o modo de impressão."""
        if self.reader is None or self.reader.error_message:
            return []

        if self.quantity_mode_var.get() == "range":
            start = self._parse_int(self.from_var.get())
            end = self._parse_int(self.to_var.get())
            if start is None or end is None or start > end:
                return []
            return build_batch_product_list(self.reader, "range", start, end)

        return build_batch_product_list(self.reader, "all")

    def _start_print_job(self, products: list[dict[str, Any]]) -> None:
        """Inicia o trabalho de impressão em um thread separado."""
        if not products:
            messagebox.showwarning(APP_TITLE, "Nenhum produto selecionado para impressão.")
            return

        if self.batch_thread is not None and self.batch_thread.is_alive():
            messagebox.showwarning(APP_TITLE, "Há um trabalho de impressão em andamento.")
            return

        self.batch_cancelled = False
        self.batch_progress_var.set(0.0)
        self.batch_status_var.set("Iniciando impressão em lote...")
        self.batch_current_var.set("")

        self.batch_thread = threading.Thread(target=self._run_batch_print, args=(products,), daemon=True)
        self.batch_thread.start()

    def _run_batch_print(self, products: list[dict[str, Any]]) -> None:
        """Executa a impressão de cada produto em lote."""
        try:
            self.printer_service = PrinterService(self.printer_var.get())
            total = len(products)
            for index, product in enumerate(products, start=1):
                if self.batch_cancelled:
                    break

                progress = index / total * 100
                self.root.after(0, self.batch_progress_var.set, progress)
                self.root.after(0, self.batch_status_var.set, f"Imprimindo {index} de {total}...")
                self.root.after(0, self.batch_current_var.set, f"Código: {product.get('codigo')}")

                if self.label_renderer is None:
                    raise RuntimeError("Renderer da etiqueta não inicializado.")

                image = self.label_renderer.render_image(product)
                self.printer_service.print_image(image)
                time.sleep(0.05)

            if self.batch_cancelled:
                self.root.after(0, self.batch_status_var.set, "Impressão em lote cancelada.")
            else:
                self.root.after(0, self.batch_progress_var.set, 100.0)
                self.root.after(0, self.batch_status_var.set, "Impressão em lote concluída.")

            self.root.after(0, self.batch_current_var.set, "")
        except Exception as exc:
            self.root.after(0, self.batch_status_var.set, f"Falha na impressão: {exc}")
            self.root.after(0, messagebox.showerror, APP_TITLE, f"Não foi possível concluir a impressão: {exc}")

    def _cancel_batch_print(self) -> None:
        """Cancela o trabalho de impressão em lote em execução."""
        self.batch_cancelled = True
        self.batch_status_var.set("Solicitação de cancelamento recebida...")

    def _on_print_selected(self) -> None:
        """Imprime apenas os produtos que foram selecionados na tabela."""
        if not self.selected_product_ids:
            messagebox.showwarning(APP_TITLE, "Selecione pelo menos um produto para imprimir.")
            return

        products = [product for product in self.all_products if product["_id"] in self.selected_product_ids]
        self._start_print_job(products)

    def _on_print(self) -> None:
        """Aciona impressão rápida ou selescionada dependendo do modo atual."""
        if self.mode_var.get() == "quick":
            if self._current_product is None:
                messagebox.showwarning(APP_TITLE, "Pesquise um produto antes de imprimir.")
                return

            self.printer_service = PrinterService(self.printer_var.get())
            try:
                if self.label_renderer is None:
                    raise RuntimeError("Renderer da etiqueta não inicializado.")

                image = self.label_renderer.render_image(self._current_product)
                self.printer_service.print_image(image)
                self.status_var.set("Status: Etiqueta rápida enviada para impressão.")
            except Exception as exc:
                self.status_var.set(f"Status: Falha ao imprimir a etiqueta rápida: {exc}")
                messagebox.showerror(APP_TITLE, f"Não foi possível imprimir a etiqueta rápida: {exc}")
        else:
            self._on_print_selected()

    def _on_batch_print(self) -> None:
        """Aciona a impressão em lote com base nos parâmetros atuais."""
        if self.mode_var.get() == "quick":
            messagebox.showwarning(APP_TITLE, "O modo de impressão rápida não suporta impressão em lote.")
            return

        products = self._get_print_products()
        if not products:
            messagebox.showwarning(APP_TITLE, "Nenhum produto disponível para impressão em lote.")
            return

        self._start_print_job(products)

    def _on_quick_search(self, _: Any) -> None:
        """Busca o produto informado no modo de impressão rápida."""
        if self.reader is None or self.reader.error_message:
            messagebox.showwarning(APP_TITLE, "Carregue uma planilha antes de buscar um produto.")
            return

        code = self.quick_code_var.get().strip()
        if not code:
            messagebox.showwarning(APP_TITLE, "Digite um código para buscar.")
            return

        product = self.reader.buscar_produto(code)
        if product is None:
            messagebox.showinfo(APP_TITLE, "Produto não encontrado.")
            self._clear_quick_details()
            return

        self._fill_quick_details(product)


def build_batch_product_list(reader: ExcelReader, mode: str, start: int | None = None, end: int | None = None) -> list[dict]:
    """Seleciona os produtos para impressão em lote com base no modo escolhido."""
    if reader is None or not getattr(reader, "rows", None):
        return []

    rows = list(reader.rows)
    if mode == "range":
        if start is None or end is None or start > end:
            return []
        start_index = start - 1
        end_index = end
        if start_index < 0:
            start_index = 0
        if end_index > len(rows):
            end_index = len(rows)
        selected_rows = rows[start_index:end_index]
    else:
        selected_rows = rows

    products = []
    for row in selected_rows:
        product = {
            "codigo": row.get("CODIGO"),
            "categoria": row.get("CATEGORIA"),
            "descricao": row.get("DESCRICAO"),
            "numero": row.get("NUMERO"),
            "preco": row.get("PRECO"),
            "qtd": row.get("QTD"),
        }
        products.append(product)
    return products
