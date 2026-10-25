"""Tokens e estilos visuais do Design System Santa Rubi."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

PRIMARY = "#947F5E"
PRIMARY_HOVER = "#806D50"
PRIMARY_PRESSED = "#705E44"
BACKGROUND = "#F1EBD7"
SURFACE = "#FCFAF3"
SURFACE_HOVER = "#F7F1E3"
SELECTION = "#E4DAC5"
TEXT = "#332F29"
MUTED_TEXT = "#746D62"
BORDER = "#D8CCB5"
FOCUS = "#6F5E43"
DISABLED_BG = "#E9E2D2"
DISABLED_TEXT = "#A39A8B"
DESTRUCTIVE = "#9A5B52"
DESTRUCTIVE_HOVER = "#854B43"
DESTRUCTIVE_PRESSED = "#704039"
FONT_FAMILY = "Segoe UI"


def configure_styles(root: tk.Misc) -> None:
    """Aplica o tema visual sem modificar geometria ou comportamento."""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(".", font=(FONT_FAMILY, 10), background=SURFACE, foreground=TEXT)
    style.configure("TFrame", background=SURFACE)
    style.configure("TLabel", background=SURFACE, foreground=TEXT, font=(FONT_FAMILY, 10))
    style.configure("Title.TLabel", background=SURFACE, foreground=TEXT, font=(FONT_FAMILY, 18, "bold"))
    style.configure("Version.TLabel", background=SURFACE, foreground=MUTED_TEXT, font=(FONT_FAMILY, 9))
    style.configure("SplashTitle.TLabel", background=BACKGROUND, foreground=PRIMARY, font=(FONT_FAMILY, 20, "bold"))
    style.configure("SplashSubtitle.TLabel", background=BACKGROUND, foreground=TEXT, font=(FONT_FAMILY, 12))
    style.configure("SplashVersion.TLabel", background=BACKGROUND, foreground=MUTED_TEXT, font=(FONT_FAMILY, 9))
    style.configure("SplashLoading.TLabel", background=BACKGROUND, foreground=PRIMARY, font=(FONT_FAMILY, 10, "bold"))
    style.configure("AboutTitle.TLabel", background=SURFACE, foreground=TEXT, font=(FONT_FAMILY, 15, "bold"))
    style.configure("AboutText.TLabel", background=SURFACE, foreground=TEXT, font=(FONT_FAMILY, 10))
    style.configure("Subtitle.TLabel", foreground=MUTED_TEXT, font=(FONT_FAMILY, 10))
    style.configure("Header.TFrame", background=SURFACE)
    style.configure("Content.TFrame", background=BACKGROUND)
    style.configure("Card.TFrame", background=SURFACE, bordercolor=BORDER, borderwidth=1, relief="solid")
    style.configure("Card.TLabel", background=SURFACE, foreground=TEXT)
    style.configure("DetailValue.TLabel", foreground=TEXT, background=SURFACE)
    style.configure("TCheckbutton", background=SURFACE, foreground=TEXT, font=(FONT_FAMILY, 10))
    style.configure("TRadiobutton", background=SURFACE, foreground=TEXT, font=(FONT_FAMILY, 10))
    style.map(
        "TCheckbutton",
        background=[("active", SURFACE_HOVER)],
        indicatorcolor=[("selected", PRIMARY), ("!selected", SURFACE)],
    )

    style.configure(
        "TLabelframe",
        background=SURFACE,
        bordercolor=BORDER,
        borderwidth=1,
        relief="solid",
    )
    style.configure(
        "TLabelframe.Label",
        background=SURFACE,
        foreground=PRIMARY_PRESSED,
        font=(FONT_FAMILY, 10, "bold"),
    )

    button_options = {
        "font": (FONT_FAMILY, 10),
        # Mantém a métrica compacta já usada pelos controles funcionais.
        # O refinamento é só de superfície, borda e estados.
        "padding": (10, 8),
        "borderwidth": 1,
        "relief": "flat",
        "anchor": "center",
    }
    style.configure("TButton", **button_options, background=SURFACE, foreground=TEXT, bordercolor=BORDER)
    style.configure("App.TButton", **button_options, background=SURFACE, foreground=TEXT, bordercolor=BORDER)
    style.map(
        "TButton",
        background=[("pressed", SELECTION), ("active", SURFACE_HOVER), ("disabled", DISABLED_BG)],
        foreground=[("disabled", DISABLED_TEXT)],
        bordercolor=[("focus", FOCUS), ("active", PRIMARY), ("!focus", BORDER)],
    )
    style.map(
        "App.TButton",
        background=[("pressed", SELECTION), ("active", SURFACE_HOVER), ("disabled", DISABLED_BG)],
        foreground=[("disabled", DISABLED_TEXT)],
        bordercolor=[("focus", FOCUS), ("active", PRIMARY), ("!focus", BORDER)],
    )
    primary_button_options = {**button_options, "font": (FONT_FAMILY, 10, "bold")}
    style.configure(
        "Primary.TButton",
        **primary_button_options,
        background=PRIMARY,
        foreground="#FFFFFF",
        bordercolor=PRIMARY,
    )
    style.map(
        "Primary.TButton",
        background=[("pressed", PRIMARY_PRESSED), ("active", PRIMARY_HOVER), ("disabled", DISABLED_BG)],
        foreground=[("disabled", DISABLED_TEXT), ("!disabled", "#FFFFFF")],
        bordercolor=[("focus", FOCUS), ("!disabled", PRIMARY)],
    )
    style.configure(
        "Destructive.TButton",
        **button_options,
        background=DESTRUCTIVE,
        foreground="#FFFFFF",
        bordercolor=DESTRUCTIVE,
    )
    style.map(
        "Destructive.TButton",
        background=[("pressed", DESTRUCTIVE_PRESSED), ("active", DESTRUCTIVE_HOVER), ("disabled", DISABLED_BG)],
        foreground=[("disabled", DISABLED_TEXT), ("!disabled", "#FFFFFF")],
        bordercolor=[("focus", FOCUS), ("!disabled", DESTRUCTIVE)],
    )

    field_options = {
        "font": (FONT_FAMILY, 10),
        # Campos continuam baixos o suficiente para não reduzir a área útil
        # das tabelas nas janelas menores.
        "padding": (6, 3),
        "fieldbackground": SURFACE,
        "foreground": TEXT,
        "bordercolor": BORDER,
        "lightcolor": BORDER,
        "darkcolor": BORDER,
        "borderwidth": 1,
        "relief": "flat",
    }
    style.configure("TEntry", **field_options)
    style.configure("TCombobox", **field_options, background=SURFACE, arrowcolor=PRIMARY_PRESSED)
    # O painel de configuração do catálogo reúne várias linhas de campos e
    # checkboxes acima da tabela. Estas métricas são as compactas anteriores
    # ao Design System, para que o painel não consuma a linha expansível onde
    # a TreeView de seleção é exibida.
    catalog_field_options = {**field_options, "padding": (4, 2)}
    style.configure("CatalogConfig.TCombobox", **catalog_field_options, background=SURFACE)
    style.configure(
        "CatalogConfig.TCheckbutton",
        background=SURFACE,
        foreground=TEXT,
        font=(FONT_FAMILY, 10),
        padding=0,
    )
    for field_style in ("TEntry", "TCombobox"):
        style.map(
            field_style,
            fieldbackground=[("readonly", SURFACE), ("disabled", DISABLED_BG)],
            foreground=[("disabled", DISABLED_TEXT), ("readonly", TEXT)],
            bordercolor=[("focus", FOCUS), ("!focus", BORDER)],
            lightcolor=[("focus", FOCUS), ("!focus", BORDER)],
            darkcolor=[("focus", FOCUS), ("!focus", BORDER)],
        )
    style.map(
        "CatalogConfig.TCombobox",
        fieldbackground=[("readonly", SURFACE), ("disabled", DISABLED_BG)],
        foreground=[("disabled", DISABLED_TEXT), ("readonly", TEXT)],
        bordercolor=[("focus", FOCUS), ("!focus", BORDER)],
    )
    style.map(
        "CatalogConfig.TCheckbutton",
        background=[("active", SURFACE_HOVER)],
        indicatorcolor=[("selected", PRIMARY), ("!selected", SURFACE)],
    )

    style.configure("TNotebook", background=BACKGROUND, borderwidth=0, tabmargins=(12, 8, 12, 0))
    style.configure(
        "TNotebook.Tab",
        background="#E5DCC8",
        foreground=MUTED_TEXT,
        font=(FONT_FAMILY, 10, "bold"),
        padding=(20, 10),
        borderwidth=0,
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", SURFACE), ("active", SURFACE_HOVER)],
        foreground=[("selected", PRIMARY_PRESSED), ("active", TEXT)],
        focuscolor=[("focus", FOCUS)],
    )

    style.configure(
        "Treeview",
        background=SURFACE,
        fieldbackground=SURFACE,
        foreground=TEXT,
        bordercolor=BORDER,
        rowheight=28,
        font=(FONT_FAMILY, 10),
    )
    style.map("Treeview", background=[("selected", PRIMARY)], foreground=[("selected", "#FFFFFF")])
    style.configure(
        "Treeview.Heading",
        background="#E9E0CE",
        foreground=TEXT,
        font=(FONT_FAMILY, 10, "bold"),
        padding=(8, 7),
        bordercolor=BORDER,
        relief="flat",
    )
    style.map("Treeview.Heading", background=[("active", SELECTION)])
    style.configure("Slim.Horizontal.TProgressbar", thickness=18, background=PRIMARY, troughcolor=DISABLED_BG)
    style.configure("TScrollbar", background="#E2D8C4", troughcolor=SURFACE, bordercolor=BORDER, arrowcolor=TEXT)
    style.map("TScrollbar", background=[("active", SELECTION), ("pressed", PRIMARY)])
