"""core/table_state.py — persistência de largura de colunas e ordenação
ativa de uma tabela. Testado com um objeto falso (sem Tk), já que o
módulo só depende de `tree["columns"]`/`tree.column(...)`."""

import unittest

from core.column_sort import ColumnSorter, SortDirection
from core.table_state import apply_column_widths, apply_sorter_state, get_column_widths, get_sorter_state


class FakeTree:
    def __init__(self, columns: tuple[str, ...], widths: dict[str, int]) -> None:
        self._columns = columns
        self._widths = dict(widths)

    def __getitem__(self, key: str):
        if key == "columns":
            return self._columns
        raise KeyError(key)

    def column(self, name: str, option: str | None = None, width: int | None = None):
        if width is not None:
            self._widths[name] = width
            return None
        if option == "width":
            return self._widths.get(name)
        raise ValueError(option)


class ColumnWidthPersistenceTests(unittest.TestCase):
    def test_get_column_widths_reads_every_column(self) -> None:
        tree = FakeTree(("codigo", "descricao"), {"codigo": 100, "descricao": 300})

        self.assertEqual(get_column_widths(tree), {"codigo": 100, "descricao": 300})

    def test_apply_column_widths_sets_saved_widths(self) -> None:
        tree = FakeTree(("codigo", "descricao"), {"codigo": 100, "descricao": 300})

        apply_column_widths(tree, {"codigo": 150, "descricao": 400})

        self.assertEqual(get_column_widths(tree), {"codigo": 150, "descricao": 400})

    def test_apply_column_widths_ignores_columns_that_no_longer_exist(self) -> None:
        tree = FakeTree(("codigo",), {"codigo": 100})

        apply_column_widths(tree, {"codigo": 150, "coluna_removida": 999})

        self.assertEqual(get_column_widths(tree), {"codigo": 150})


class SorterStatePersistenceTests(unittest.TestCase):
    def test_get_sorter_state_returns_none_when_nothing_sorted_yet(self) -> None:
        sorter = ColumnSorter({"codigo": lambda item: item})

        self.assertIsNone(get_sorter_state(sorter))

    def test_get_sorter_state_reflects_active_column_and_direction(self) -> None:
        sorter = ColumnSorter({"codigo": lambda item: item})
        sorter.toggle("codigo")

        self.assertEqual(get_sorter_state(sorter), {"column": "codigo", "direction": "ascending"})

    def test_apply_sorter_state_restores_column_and_direction(self) -> None:
        sorter = ColumnSorter({"codigo": lambda item: item, "preco": lambda item: item})

        apply_sorter_state(sorter, {"column": "preco", "direction": "descending"})

        self.assertEqual(sorter.active_column, "preco")
        self.assertEqual(sorter.direction, SortDirection.DESCENDING)

    def test_apply_sorter_state_ignores_none(self) -> None:
        sorter = ColumnSorter({"codigo": lambda item: item})

        apply_sorter_state(sorter, None)

        self.assertIsNone(sorter.active_column)

    def test_apply_sorter_state_ignores_unknown_column(self) -> None:
        """Coluna salva não existe mais nesta versão da tabela — ignora em
        vez de quebrar (mesmo espírito de apply_column_widths)."""
        sorter = ColumnSorter({"codigo": lambda item: item})

        apply_sorter_state(sorter, {"column": "coluna_removida", "direction": "ascending"})

        self.assertIsNone(sorter.active_column)

    def test_apply_sorter_state_ignores_invalid_direction(self) -> None:
        sorter = ColumnSorter({"codigo": lambda item: item})

        apply_sorter_state(sorter, {"column": "codigo", "direction": "invalida"})

        self.assertIsNone(sorter.active_column)


if __name__ == "__main__":
    unittest.main()
