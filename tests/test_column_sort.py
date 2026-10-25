import unittest
from dataclasses import dataclass
from datetime import date

from core.column_sort import ColumnSorter, SortDirection, numeric_or_text, sort_items


@dataclass
class Item:
    codigo: str | None
    descricao: str | None = None
    preco: float | None = None
    criado_em: date | None = None


class SortDirectionTests(unittest.TestCase):
    def test_ascending_toggles_to_descending(self):
        self.assertEqual(SortDirection.ASCENDING.toggled(), SortDirection.DESCENDING)

    def test_descending_toggles_to_ascending(self):
        self.assertEqual(SortDirection.DESCENDING.toggled(), SortDirection.ASCENDING)

    def test_toggling_twice_returns_to_original(self):
        self.assertEqual(SortDirection.ASCENDING.toggled().toggled(), SortDirection.ASCENDING)


class SortItemsNumericTests(unittest.TestCase):
    def test_sorts_numbers_numerically_not_as_text(self):
        """1, 2, 10, 100 — nunca "1", "10", "100", "2" (ordem de texto)."""
        items = [Item(codigo=None, preco=v) for v in [10, 1, 100, 2]]
        result = sort_items(items, lambda i: i.preco, SortDirection.ASCENDING)
        self.assertEqual([i.preco for i in result], [1, 2, 10, 100])

    def test_numbers_descending(self):
        items = [Item(codigo=None, preco=v) for v in [10, 1, 100, 2]]
        result = sort_items(items, lambda i: i.preco, SortDirection.DESCENDING)
        self.assertEqual([i.preco for i in result], [100, 10, 2, 1])

    def test_numeric_strings_via_numeric_or_text_helper(self):
        items = [Item(codigo=c) for c in ["181100", "181001", "181010"]]
        result = sort_items(items, lambda i: numeric_or_text(i.codigo), SortDirection.ASCENDING)
        self.assertEqual([i.codigo for i in result], ["181001", "181010", "181100"])

    def test_ring_size_style_strings_sort_numerically_not_lexicographically(self):
        """Exemplo do bug que a implementação anterior tinha: "8" viria
        depois de "30" numa ordenação de texto pura."""
        items = [Item(codigo=None, descricao=n) for n in ["14", "8", "30", "17"]]
        result = sort_items(items, lambda i: numeric_or_text(i.descricao), SortDirection.ASCENDING)
        self.assertEqual([i.descricao for i in result], ["8", "14", "17", "30"])


class SortItemsTextTests(unittest.TestCase):
    def test_sorts_alphabetically_ascending(self):
        items = [Item(codigo=None, descricao=d) for d in ["Colar", "Anel", "Brinco"]]
        result = sort_items(items, lambda i: i.descricao, SortDirection.ASCENDING)
        self.assertEqual([i.descricao for i in result], ["Anel", "Brinco", "Colar"])

    def test_sorts_alphabetically_descending(self):
        items = [Item(codigo=None, descricao=d) for d in ["Colar", "Anel", "Brinco"]]
        result = sort_items(items, lambda i: i.descricao, SortDirection.DESCENDING)
        self.assertEqual([i.descricao for i in result], ["Colar", "Brinco", "Anel"])

    def test_ignores_case_and_accents(self):
        # normalizado: "agua" < "anel" < "colar"
        items = [Item(codigo=None, descricao=d) for d in ["colar", "Água", "anel"]]
        result = sort_items(items, lambda i: i.descricao, SortDirection.ASCENDING)
        self.assertEqual([i.descricao for i in result], ["Água", "anel", "colar"])


class SortItemsDateTests(unittest.TestCase):
    def test_sorts_chronologically_not_alphabetically(self):
        items = [
            Item(codigo=None, criado_em=date(2026, 12, 1)),
            Item(codigo=None, criado_em=date(2026, 1, 5)),
            Item(codigo=None, criado_em=date(2026, 2, 20)),
        ]
        result = sort_items(items, lambda i: i.criado_em, SortDirection.ASCENDING)
        self.assertEqual(
            [i.criado_em for i in result],
            [date(2026, 1, 5), date(2026, 2, 20), date(2026, 12, 1)],
        )


class SortItemsEmptyLastTests(unittest.TestCase):
    def test_empty_strings_stay_last_ascending(self):
        items = [Item(codigo=None, descricao=d) for d in ["Colar", "", "Anel"]]
        result = sort_items(items, lambda i: i.descricao, SortDirection.ASCENDING)
        self.assertEqual([i.descricao for i in result], ["Anel", "Colar", ""])

    def test_empty_strings_stay_last_descending(self):
        """Vazio nunca "sobe" pra frente ao inverter a direção."""
        items = [Item(codigo=None, descricao=d) for d in ["Colar", "", "Anel"]]
        result = sort_items(items, lambda i: i.descricao, SortDirection.DESCENDING)
        self.assertEqual([i.descricao for i in result], ["Colar", "Anel", ""])

    def test_none_values_stay_last(self):
        items = [Item(codigo=None, preco=v) for v in [5.0, None, 1.0]]
        result = sort_items(items, lambda i: i.preco, SortDirection.ASCENDING)
        self.assertEqual([i.preco for i in result], [1.0, 5.0, None])

    def test_whitespace_only_string_counts_as_empty(self):
        items = [Item(codigo=None, descricao=d) for d in ["Colar", "   ", "Anel"]]
        result = sort_items(items, lambda i: i.descricao, SortDirection.ASCENDING)
        self.assertEqual([i.descricao for i in result], ["Anel", "Colar", "   "])

    def test_multiple_empty_items_all_stay_at_the_end(self):
        items = [Item(codigo=None, descricao=d) for d in ["", "Colar", None, "Anel"]]
        result = sort_items(items, lambda i: i.descricao, SortDirection.ASCENDING)
        self.assertEqual(result[:2], [items[3], items[1]])  # Anel, Colar
        self.assertEqual({i.descricao for i in result[2:]}, {"", None})


class SortItemsMixedTypeSafetyTests(unittest.TestCase):
    def test_does_not_raise_when_column_has_mixed_types(self):
        """Caso raro (dados inconsistentes) — nunca deve travar a tela."""
        items = [Item(codigo=None, descricao="10"), Item(codigo=None, descricao="anel")]

        def mixed_key(item):
            try:
                return float(item.descricao)
            except ValueError:
                return item.descricao

        result = sort_items(items, mixed_key, SortDirection.ASCENDING)
        self.assertEqual(len(result), 2)


class ColumnSorterToggleTests(unittest.TestCase):
    def test_first_click_is_ascending(self):
        sorter = ColumnSorter()
        direction = sorter.toggle("codigo")
        self.assertEqual(direction, SortDirection.ASCENDING)

    def test_second_click_same_column_is_descending(self):
        sorter = ColumnSorter()
        sorter.toggle("codigo")
        direction = sorter.toggle("codigo")
        self.assertEqual(direction, SortDirection.DESCENDING)

    def test_third_click_same_column_returns_to_ascending(self):
        sorter = ColumnSorter()
        sorter.toggle("codigo")
        sorter.toggle("codigo")
        direction = sorter.toggle("codigo")
        self.assertEqual(direction, SortDirection.ASCENDING)

    def test_clicking_a_different_column_resets_to_ascending(self):
        sorter = ColumnSorter()
        sorter.toggle("codigo")
        sorter.toggle("codigo")  # agora descendente
        direction = sorter.toggle("descricao")
        self.assertEqual(direction, SortDirection.ASCENDING)
        self.assertEqual(sorter.active_column, "descricao")


class ColumnSorterSortTests(unittest.TestCase):
    def test_sort_uses_registered_key_func_for_the_column(self):
        sorter = ColumnSorter({"preco": lambda i: i.preco})
        items = [Item(codigo=None, preco=v) for v in [3, 1, 2]]

        result = sorter.sort(items, "preco")

        self.assertEqual([i.preco for i in result], [1, 2, 3])

    def test_sort_toggles_direction_on_repeated_calls(self):
        sorter = ColumnSorter({"preco": lambda i: i.preco})
        items = [Item(codigo=None, preco=v) for v in [3, 1, 2]]

        sorter.sort(items, "preco")
        result = sorter.sort(items, "preco")

        self.assertEqual([i.preco for i in result], [3, 2, 1])

    def test_sort_with_unregistered_column_returns_items_unchanged(self):
        sorter = ColumnSorter({"preco": lambda i: i.preco})
        items = [Item(codigo=None, preco=v) for v in [3, 1, 2]]

        result = sorter.sort(items, "campo_desconhecido")

        self.assertEqual([i.preco for i in result], [3, 1, 2])


class ColumnSorterReapplyTests(unittest.TestCase):
    def test_reapply_with_no_active_sort_returns_items_unchanged(self):
        sorter = ColumnSorter({"preco": lambda i: i.preco})
        items = [Item(codigo=None, preco=v) for v in [3, 1, 2]]
        self.assertEqual([i.preco for i in sorter.reapply(items)], [3, 1, 2])

    def test_reapply_uses_current_column_and_direction_without_toggling(self):
        sorter = ColumnSorter({"preco": lambda i: i.preco})
        sorter.sort([Item(codigo=None, preco=1)], "preco")  # ascendente

        items = [Item(codigo=None, preco=v) for v in [3, 1, 2]]
        result_a = sorter.reapply(items)
        result_b = sorter.reapply(items)

        self.assertEqual([i.preco for i in result_a], [1, 2, 3])
        self.assertEqual([i.preco for i in result_b], [1, 2, 3], "reapply nao deveria alternar a direcao")

    def test_reapply_after_toggling_to_descending(self):
        sorter = ColumnSorter({"preco": lambda i: i.preco})
        items = [Item(codigo=None, preco=v) for v in [3, 1, 2]]
        sorter.sort(items, "preco")  # ascendente
        sorter.sort(items, "preco")  # descendente

        self.assertEqual([i.preco for i in sorter.reapply(items)], [3, 2, 1])


if __name__ == "__main__":
    unittest.main()
