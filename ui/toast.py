"""Feedback discreto e temporário — nunca um messagebox.

Controla um tk.Label já posicionado pelo chamador (grid/pack é decisão de
quem constrói a tela): só troca o texto/cor e agenda a limpeza automática
alguns segundos depois, sem interromper o que o usuário está fazendo.
"""

from __future__ import annotations

import tkinter as tk

from ui.design_system import BACKGROUND

DEFAULT_DURATION_MS = 3500

# Tons suaves, legíveis e coerentes com a paleta institucional. A tupla
# pública permanece igual para não alterar o comportamento dos chamadores.
SUCCESS = ("#3F6B4F", "#E4EFE2")  # texto, fundo
WARNING = ("#7A5A2A", "#F4E8CB")
ERROR = ("#884B45", "#F3E2DF")
INFO = ("#5F5A50", "#E9E2D2")


class Toast:
    def __init__(self, label: tk.Label, duration_ms: int = DEFAULT_DURATION_MS) -> None:
        self.label = label
        self.duration_ms = duration_ms
        self._after_id: str | None = None
        # Guarda o fundo original do rótulo para restaurá-lo ao limpar —
        # sem isso, a cor de destaque (verde/azul) ficaria visível como
        # uma caixa vazia depois que o texto desaparece.
        self._idle_bg = label.cget("bg") or BACKGROUND
        # Cancela o after() pendente se a janela fechar antes do tempo —
        # sem isso, o timer tenta rodar mais tarde contra um widget já
        # destruído (mesma classe de bug já corrigida no debounce de
        # JueriSearchPanel._run_search).
        label.bind("<Destroy>", self._on_destroy, add="+")

    def _on_destroy(self, _event: object = None) -> None:
        if self._after_id is not None:
            try:
                self.label.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None

    def show(self, message: str, style: tuple[str, str] = SUCCESS) -> None:
        fg, bg = style
        if self._after_id is not None:
            self.label.after_cancel(self._after_id)
        self.label.configure(text=message, fg=fg, bg=bg)
        self._after_id = self.label.after(self.duration_ms, self._clear)

    def _clear(self) -> None:
        self._after_id = None
        self.label.configure(text="", bg=self._idle_bg)
