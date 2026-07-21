import unittest

from core.catalog_product import CatalogProduct
from core.print_item import PrintItem
from core.print_queue import PrintQueue


def _product(codigo: str = "1001") -> CatalogProduct:
    return CatalogProduct(
        codigo=codigo, descricao="Anel de Prata", preco=59.9, categoria="Aneis", numeracao="16", fornecedor="DIP-15"
    )


class PrintQueueTests(unittest.TestCase):
    def test_new_queue_is_empty(self):
        queue = PrintQueue()
        self.assertTrue(queue.is_empty())
        self.assertEqual(queue.count(), 0)
        self.assertEqual(queue.total_labels(), 0)
        self.assertEqual(queue.items(), [])

    def test_add_returns_the_created_item(self):
        queue = PrintQueue()
        product = _product()
        item = queue.add(product, quantity=3)
        self.assertIs(item.product, product)
        self.assertEqual(item.quantity, 3)
        self.assertFalse(queue.is_empty())
        self.assertEqual(queue.count(), 1)

    def test_add_normalizes_quantity(self):
        queue = PrintQueue()
        item = queue.add(_product(), quantity=0)
        self.assertEqual(item.quantity, 1)

    def test_count_vs_total_labels(self):
        queue = PrintQueue()
        queue.add(_product("1001"), quantity=2)
        queue.add(_product("1002"), quantity=5)
        self.assertEqual(queue.count(), 2, "count() e' numero de itens, nao de etiquetas")
        self.assertEqual(queue.total_labels(), 7, "total_labels() soma as quantidades")

    def test_remove_removes_matching_product(self):
        queue = PrintQueue()
        product_a = _product("1001")
        product_b = _product("1002")
        queue.add(product_a, quantity=1)
        queue.add(product_b, quantity=1)

        queue.remove(product_a)

        remaining = queue.items()
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0].product.codigo, "1002")

    def test_remove_nonexistent_product_is_a_no_op(self):
        queue = PrintQueue()
        queue.add(_product("1001"), quantity=1)
        queue.remove(_product("9999"))
        self.assertEqual(queue.count(), 1)

    def test_clear_empties_the_queue(self):
        queue = PrintQueue()
        queue.add(_product("1001"), quantity=2)
        queue.add(_product("1002"), quantity=3)
        queue.clear()
        self.assertTrue(queue.is_empty())
        self.assertEqual(queue.total_labels(), 0)

    def test_items_returns_a_copy_not_the_internal_list(self):
        queue = PrintQueue()
        queue.add(_product(), quantity=1)
        snapshot = queue.items()
        snapshot.clear()
        self.assertEqual(queue.count(), 1, "mutar o retorno de items() nao deve afetar a fila")


class PrintQueueContainsTests(unittest.TestCase):
    def test_contains_true_when_product_in_queue(self):
        queue = PrintQueue()
        product = _product("1001")
        queue.add(product, quantity=1)
        self.assertTrue(queue.contains(product))

    def test_contains_false_when_product_not_in_queue(self):
        queue = PrintQueue()
        queue.add(_product("1001"), quantity=1)
        self.assertFalse(queue.contains(_product("9999")))

    def test_contains_matches_by_codigo_not_object_identity(self):
        queue = PrintQueue()
        queue.add(_product("1001"), quantity=1)
        outro_objeto_mesmo_codigo = _product("1001")
        self.assertTrue(queue.contains(outro_objeto_mesmo_codigo))


class PrintQueueFindTests(unittest.TestCase):
    def test_find_returns_matching_item(self):
        queue = PrintQueue()
        product = _product("1001")
        queue.add(product, quantity=3)
        found = queue.find(product)
        self.assertIsNotNone(found)
        self.assertEqual(found.quantity, 3)

    def test_find_returns_none_when_absent(self):
        queue = PrintQueue()
        self.assertIsNone(queue.find(_product("1001")))


class PrintQueueUpdateQuantityTests(unittest.TestCase):
    def test_update_quantity_updates_existing_item(self):
        queue = PrintQueue()
        product = _product("1001")
        queue.add(product, quantity=1)

        result = queue.update_quantity(product, 9)

        self.assertTrue(result)
        self.assertEqual(queue.find(product).quantity, 9)

    def test_update_quantity_returns_false_when_absent(self):
        queue = PrintQueue()
        result = queue.update_quantity(_product("1001"), 9)
        self.assertFalse(result)

    def test_update_quantity_does_not_create_new_items(self):
        queue = PrintQueue()
        queue.update_quantity(_product("1001"), 9)
        self.assertEqual(queue.count(), 0)

    def test_update_quantity_normalizes_value(self):
        queue = PrintQueue()
        product = _product("1001")
        queue.add(product, quantity=1)
        queue.update_quantity(product, 0)
        self.assertEqual(queue.find(product).quantity, 1)


class PrintQueueIncrementTests(unittest.TestCase):
    def test_increment_increases_existing_quantity(self):
        queue = PrintQueue()
        product = _product("1001")
        queue.add(product, quantity=2)
        queue.increment(product, amount=3)
        self.assertEqual(queue.find(product).quantity, 5)

    def test_increment_default_amount_is_one(self):
        queue = PrintQueue()
        product = _product("1001")
        queue.add(product, quantity=2)
        queue.increment(product)
        self.assertEqual(queue.find(product).quantity, 3)

    def test_increment_creates_item_when_absent(self):
        queue = PrintQueue()
        product = _product("1001")
        queue.increment(product, amount=4)
        self.assertEqual(queue.find(product).quantity, 4)

    def test_increment_keeps_a_single_item_per_product(self):
        queue = PrintQueue()
        product = _product("1001")
        queue.increment(product)
        queue.increment(product)
        queue.increment(product)
        self.assertEqual(queue.count(), 1)
        self.assertEqual(queue.find(product).quantity, 3)

    def test_increment_never_results_in_quantity_below_one(self):
        queue = PrintQueue()
        product = _product("1001")
        queue.add(product, quantity=1)
        queue.increment(product, amount=-10)
        self.assertEqual(queue.find(product).quantity, 1)


class PrintQueueDecrementTests(unittest.TestCase):
    def test_decrement_reduces_existing_quantity(self):
        queue = PrintQueue()
        product = _product("1001")
        queue.add(product, quantity=5)
        queue.decrement(product, amount=2)
        self.assertEqual(queue.find(product).quantity, 3)

    def test_decrement_default_amount_is_one(self):
        queue = PrintQueue()
        product = _product("1001")
        queue.add(product, quantity=5)
        queue.decrement(product)
        self.assertEqual(queue.find(product).quantity, 4)

    def test_decrement_never_goes_below_one(self):
        queue = PrintQueue()
        product = _product("1001")
        queue.add(product, quantity=2)
        queue.decrement(product, amount=10)
        self.assertEqual(queue.find(product).quantity, 1)

    def test_decrement_is_a_no_op_when_product_absent(self):
        queue = PrintQueue()
        result = queue.decrement(_product("1001"))
        self.assertIsNone(result)
        self.assertEqual(queue.count(), 0)


class PrintQueueReplaceTests(unittest.TestCase):
    def test_replace_swaps_all_items(self):
        queue = PrintQueue()
        queue.add(_product("1001"), quantity=1)

        novo_item = queue.add(_product("2001"), quantity=7)
        queue.replace([novo_item])

        self.assertEqual(queue.count(), 1)
        self.assertEqual(queue.find(_product("2001")).quantity, 7)
        self.assertFalse(queue.contains(_product("1001")))

    def test_replace_with_empty_list_clears_queue(self):
        queue = PrintQueue()
        queue.add(_product("1001"), quantity=1)
        queue.replace([])
        self.assertTrue(queue.is_empty())

    def test_replace_does_not_alias_the_provided_list(self):
        queue = PrintQueue()
        item = PrintItem(product=_product("1001"), quantity=1)
        source_list = [item]

        queue.replace(source_list)
        source_list.append(PrintItem(product=_product("2001"), quantity=1))

        self.assertEqual(queue.count(), 1, "replace() deveria copiar a lista, nao guardar referencia a ela")


class PrintQueueToListTests(unittest.TestCase):
    def test_to_list_returns_all_items(self):
        queue = PrintQueue()
        queue.add(_product("1001"), quantity=1)
        queue.add(_product("2001"), quantity=1)
        self.assertEqual(len(queue.to_list()), 2)

    def test_to_list_returns_a_copy_not_the_internal_list(self):
        queue = PrintQueue()
        queue.add(_product("1001"), quantity=1)
        snapshot = queue.to_list()
        snapshot.clear()
        self.assertEqual(queue.count(), 1, "mutar o retorno de to_list() nao deve afetar a fila")


class PrintQueuePythonProtocolTests(unittest.TestCase):
    def test_len_reflects_item_count(self):
        queue = PrintQueue()
        queue.add(_product("1001"), quantity=1)
        queue.add(_product("2001"), quantity=1)
        self.assertEqual(len(queue), 2)

    def test_iter_yields_all_items(self):
        queue = PrintQueue()
        queue.add(_product("1001"), quantity=1)
        queue.add(_product("2001"), quantity=1)
        codigos = [item.product.codigo for item in queue]
        self.assertEqual(codigos, ["1001", "2001"])

    def test_iterating_does_not_expose_internal_list(self):
        queue = PrintQueue()
        queue.add(_product("1001"), quantity=1)
        iterator_list = list(queue)
        iterator_list.clear()
        self.assertEqual(queue.count(), 1)

    def test_contains_operator_matches_by_codigo(self):
        queue = PrintQueue()
        product = _product("1001")
        queue.add(product, quantity=1)
        self.assertIn(product, queue)
        self.assertIn(_product("1001"), queue)
        self.assertNotIn(_product("9999"), queue)


if __name__ == "__main__":
    unittest.main()
