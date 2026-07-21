import unittest

from core.catalog_product import CatalogProduct
from core.label_data import LabelData
from core.print_queue import PrintQueue
from core.print_queue_adapter import PrintQueueAdapter


def _product(codigo: str, **overrides) -> CatalogProduct:
    defaults = dict(
        codigo=codigo,
        descricao="Anel de Prata",
        preco=59.9,
        categoria="Aneis",
        numeracao="16",
        fornecedor="DIP-15",
    )
    defaults.update(overrides)
    return CatalogProduct(**defaults)


class PrintQueueAdapterEmptyQueueTests(unittest.TestCase):
    def test_empty_queue_produces_empty_list(self):
        queue = PrintQueue()
        self.assertEqual(PrintQueueAdapter.to_label_data(queue), [])


class PrintQueueAdapterConversionTests(unittest.TestCase):
    def test_single_item_expands_to_its_quantity(self):
        queue = PrintQueue()
        queue.add(_product("1001"), quantity=3)

        labels = PrintQueueAdapter.to_label_data(queue)

        self.assertEqual(len(labels), 3)
        self.assertTrue(all(label == labels[0] for label in labels), "todas as copias devem ser identicas")

    def test_returns_label_data_instances(self):
        queue = PrintQueue()
        queue.add(_product("1001"), quantity=1)

        [label] = PrintQueueAdapter.to_label_data(queue)

        self.assertIsInstance(label, LabelData)

    def test_label_has_the_fields_build_row_expects(self):
        queue = PrintQueue()
        queue.add(
            _product("1001", descricao="Anel Coração", preco=59.9, categoria="Aneis", numeracao="16"),
            quantity=1,
        )

        [label] = PrintQueueAdapter.to_label_data(queue)

        self.assertEqual(
            label,
            LabelData(codigo="1001", categoria="Aneis", descricao="Anel Coração", numero="16", preco=59.9),
        )

    def test_multiple_items_are_all_expanded_and_kept_in_order(self):
        queue = PrintQueue()
        queue.add(_product("1001"), quantity=2)
        queue.add(_product("2001"), quantity=1)

        labels = PrintQueueAdapter.to_label_data(queue)

        self.assertEqual([label.codigo for label in labels], ["1001", "1001", "2001"])

    def test_uses_display_category_not_raw_categoria(self):
        product = _product("1001", categoria="Aneis")
        queue = PrintQueue()
        queue.add(product, quantity=1)

        [label] = PrintQueueAdapter.to_label_data(queue)

        self.assertEqual(label.categoria, product.display_category)

    def test_does_not_mutate_the_queue(self):
        queue = PrintQueue()
        queue.add(_product("1001"), quantity=2)

        PrintQueueAdapter.to_label_data(queue)

        self.assertEqual(queue.count(), 1)
        self.assertEqual(queue.total_labels(), 2)


if __name__ == "__main__":
    unittest.main()
