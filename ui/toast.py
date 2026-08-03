"""Feedback discreto e temporário — nunca um messagebox.

Controla um tk.Label já posicionado pelo chamador (grid/pack é decisão de
quem constrói a tela): só troca o texto/cor e agenda a limpeza automática
alguns segundos depois, sem interromper o que o usuário está fazendo.
"""

from __future__ import annotations

import tkinter as tk

DEFAULT_DURATION_MS = 3500

SUCCESS = ("#166534", "#dcfce7")  # texto, fundo
INFO = ("#1d4ed8", "#dbeafe")


class Toast:
    def __init__(self, label: tk.Label, duration_ms: int = DEFAULT_DURATION_MS) -> None:
        self.label = label
        self.duration_ms = duration_ms
        self._after_id: str | None = None
        # Guarda o fundo original do rótulo para restaurá-lo ao limpar —
        # sem isso, a cor de destaque (verde/azul) ficaria visível como
        # uma caixa vazia depois que o texto desaparece.
        self._idle_bg = label.cget("bg")
        # Cancela o after() pendente se a janela fechar antes do tempo —
        # sem isso, o timer tenta rodar mais tarde contra um widget já
        # destruído (mesma classe de bug já corrigida no debounce de
        # ProductSearchDialog._run_search).
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
