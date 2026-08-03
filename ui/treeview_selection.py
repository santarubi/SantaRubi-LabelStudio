"""Seleção contínua (clique + arraste) para qualquer ttk.Treeview em
selectmode="extended" — extraído do comportamento já usado na tabela de
lote da aba "Impressão" (`_on_table_drag`), generalizado para não
depender de nenhum estado específico daquela tela.

Reutilizado por qualquer lista de produtos: Pesquisa Jueri e Catálogo
Integrado usam exatamente esta implementação.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


def enable_drag_selection(tree: ttk.Treeview) -> None:
    """Permite selecionar várias linhas clicando e arrastando o mouse.

    Ctrl+clique e Shift+clique continuam funcionando normalmente — esta
    função só adiciona bindings (via add="+"), nunca substitui os
    bindings nativos do Treeview que já tratam clique simples e
    modificadores; só entra em ação quando o mouse realmente se move
    para uma linha diferente com o botão pressionado.
    """
    state: dict[str, object] = {
        "anchor": None,
        "active": False,
        "pointer_y": None,
        "scroll_job": None,
    }

    def cancel_scroll() -> None:
        job = state["scroll_job"]
        if job is not None:
            try:
                tree.after_cancel(job)
            except tk.TclError:
                pass
            state["scroll_job"] = None

    def select_through(target: str) -> None:
        anchor = state["anchor"]
        if not anchor or not target:
            return

        all_ids = tree.get_children("")
        if anchor not in all_ids or target not in all_ids:
            return

        start, end = all_ids.index(anchor), all_ids.index(target)
        if start > end:
            start, end = end, start
        range_ids = all_ids[start : end + 1]

        if set(range_ids) != set(tree.selection()):
            tree.selection_set(range_ids)

    def auto_scroll() -> None:
        state["scroll_job"] = None
        if not state["active"]:
            return

        pointer_y = state["pointer_y"]
        if not isinstance(pointer_y, int):
            return

        height = tree.winfo_height()
        direction = -1 if pointer_y < 0 else 1 if pointer_y >= height else 0
        if direction == 0:
            return

        before = tree.yview()
        tree.yview_scroll(direction, "units")
        if tree.yview() != before:
            boundary_y = 1 if direction < 0 else max(1, height - 2)
            select_through(tree.identify_row(boundary_y))
            state["scroll_job"] = tree.after(50, auto_scroll)

    def on_press(event: tk.Event) -> None:
        cancel_scroll()
        state["anchor"] = tree.identify_row(event.y)
        state["active"] = False
        state["pointer_y"] = event.y

    def on_drag(event: tk.Event) -> None:
        anchor = state["anchor"]
        if not anchor:
            return

        state["pointer_y"] = event.y
        target = tree.identify_row(event.y)
        if target != anchor or event.y < 0 or event.y >= tree.winfo_height():
            state["active"] = True
        if not state["active"]:
            return

        if target:
            select_through(target)

        outside = event.y < 0 or event.y >= tree.winfo_height()
        if outside and state["scroll_job"] is None:
            auto_scroll()
        elif not outside:
            cancel_scroll()

    def on_release(_event: tk.Event) -> None:
        cancel_scroll()
        state["anchor"] = None
        state["active"] = False
        state["pointer_y"] = None

    tree.bind("<ButtonPress-1>", on_press, add="+")
    tree.bind("<B1-Motion>", on_drag, add="+")
    tree.bind("<ButtonRelease-1>", on_release, add="+")
