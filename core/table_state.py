"""Persistência de estado de uma tabela (largura de colunas + ordenação
ativa) entre execuções do programa — usado por qualquer tela com uma
Treeview, para que a interface volte exatamente como o usuário a deixou.

Sem dependência de Tkinter: opera sobre qualquer objeto que se comporte
como uma Treeview (só usa `tree["columns"]` e `tree.column(...)`), então é
testável com um objeto falso, sem abrir nenhuma janela.
"""

from __future__ import annotations

from typing import Any

from core.column_sort import ColumnSorter, SortDirection


def get_column_widths(tree: Any) -> dict[str, int]:
    """Lê a largura atual de cada coluna da tabela."""
    return {column: tree.column(column, "width") for column in tree["columns"]}


def apply_column_widths(tree: Any, widths: dict[str, int]) -> None:
    """Aplica larguras salvas anteriormente — ignora colunas que não
    existem mais na tabela (ex.: coluna removida numa versão futura)."""
    columns = set(tree["columns"])
    for column, width in widths.items():
        if column in columns:
            tree.column(column, width=width)


def get_sorter_state(sorter: ColumnSorter) -> dict[str, str] | None:
    """Retorna a coluna/direção de ordenação ativa, ou None se nenhuma
    ordenação foi aplicada ainda."""
    if sorter.active_column is None:
        return None
    return {"column": sorter.active_column, "direction": sorter.direction.value}


def apply_sorter_state(sorter: ColumnSorter, state: dict[str, str] | None) -> None:
    """Restaura a coluna/direção de ordenação salva — só entra em vigor no
    próximo `reapply()`/`sort()` do chamador (não reordena nenhuma lista
    aqui, só ajusta o estado do ColumnSorter)."""
    if not state:
        return

    column = state.get("column")
    direction = state.get("direction")
    valid_directions = (SortDirection.ASCENDING.value, SortDirection.DESCENDING.value)
    if column in sorter.key_funcs and direction in valid_directions:
        sorter.active_column = column
        sorter.direction = SortDirection(direction)
