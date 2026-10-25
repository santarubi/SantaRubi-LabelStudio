"""Recursos visuais e metadados oficiais da Santa Rubi."""

from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from PIL import Image, ImageTk

from app.version import APP_VERSION
from ui.design_system import configure_styles

APP_NAME = "Santa Rubi Label Studio"
COMPANY_NAME = "Santa Rubi Semijoias"
COPYRIGHT = "© 2026 Santa Rubi Semijoias"
ICON_FILENAME = "santa-rubi-app.ico"
PRIMARY = "#947F5E"
BACKGROUND = "#F1EBD7"


def asset_path(filename: str) -> Path:
    """Localiza recursos tanto no código-fonte quanto no executável."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / "assets" / filename


def apply_window_icon(window: tk.Misc) -> None:
    """Aplica o mesmo ícone oficial sem interferir no ciclo da janela."""
    try:
        window.iconbitmap(str(asset_path(ICON_FILENAME)))
    except tk.TclError:
        # Ambientes sem suporte nativo a .ico (como alguns runners Tk) não
        # devem impedir a abertura da interface.
        pass


def load_brand_icon(master: tk.Misc, size: int) -> ImageTk.PhotoImage:
    """Carrega a arte oficial do aplicativo no tamanho visual solicitado."""
    with Image.open(asset_path(ICON_FILENAME)) as icon:
        resized = icon.convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
    return ImageTk.PhotoImage(resized, master=master)


class SplashScreen(tk.Toplevel):
    """Splash estática e breve, exibida enquanto a interface é construída."""

    def __init__(self, parent: tk.Tk) -> None:
        super().__init__(parent)
        configure_styles(parent)
        self.overrideredirect(True)
        self.configure(bg=BACKGROUND, highlightbackground=PRIMARY, highlightthickness=1)
        self.resizable(False, False)
        apply_window_icon(self)

        container = tk.Frame(self, bg=BACKGROUND, padx=42, pady=30)
        container.pack(fill="both", expand=True)
        self._brand_icon = load_brand_icon(self, 76)
        tk.Label(
            container,
            image=self._brand_icon,
            bg=BACKGROUND,
            borderwidth=0,
            highlightthickness=0,
        ).pack(pady=(0, 12))
        ttk.Label(container, text="Santa Rubi", style="SplashTitle.TLabel").pack()
        ttk.Label(container, text="Label Studio", style="SplashSubtitle.TLabel").pack(pady=(0, 12))
        ttk.Label(container, text=APP_VERSION, style="SplashVersion.TLabel").pack()
        ttk.Label(container, text="Loading...", style="SplashLoading.TLabel").pack(pady=(16, 0))

        self.update_idletasks()
        width, height = self.winfo_width(), self.winfo_height()
        x = (self.winfo_screenwidth() - width) // 2
        y = (self.winfo_screenheight() - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")


class AboutDialog(tk.Toplevel):
    """Informações institucionais, sem dados de depuração."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent)
        self.title("Sobre — Santa Rubi Label Studio")
        self.transient(parent)
        self.resizable(False, False)
        apply_window_icon(self)

        container = ttk.Frame(self, padding=(32, 26))
        container.pack(fill="both", expand=True)
        self._brand_icon = load_brand_icon(self, 58)
        tk.Label(
            container,
            image=self._brand_icon,
            bg=BACKGROUND,
            borderwidth=0,
            highlightthickness=0,
        ).pack(pady=(0, 12))
        ttk.Label(container, text=APP_NAME, style="AboutTitle.TLabel").pack()
        ttk.Label(container, text=APP_VERSION, style="Subtitle.TLabel").pack(pady=(2, 14))
        ttk.Label(container, text=COMPANY_NAME, style="AboutText.TLabel").pack()
        ttk.Label(container, text=COPYRIGHT, style="AboutText.TLabel").pack(pady=(2, 12))
        ttk.Label(container, text="Python • Tkinter", style="Subtitle.TLabel").pack()
        ttk.Button(container, text="Fechar", style="App.TButton", command=self.destroy).pack(pady=(18, 0))
        self.update_idletasks()
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        x = parent_x + max(0, (parent_width - self.winfo_width()) // 2)
        y = parent_y + max(0, (parent_height - self.winfo_height()) // 2)
        self.geometry(f"+{x}+{y}")
        self.lift()
        self.grab_set()
