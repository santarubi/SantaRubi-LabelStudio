import unittest

from core.catalog_product import CatalogProduct
from core.print_item import PrintItem, normalize_quantity


def _product() -> CatalogProduct:
    return CatalogProduct(
        codigo="1001", descricao="Anel de Prata", preco=59.9, categoria="Aneis", numeracao="16", fornecedor="DIP-15"
    )


class NormalizeQuantityTests(unittest.TestCase):
    def test_none_becomes_one(self):
        self.assertEqual(normalize_quantity(None), 1)

    def test_empty_string_becomes_one(self):
        self.assertEqual(normalize_quantity(""), 1)
        self.assertEqual(normalize_quantity("   "), 1)

    def test_invalid_text_becomes_one(self):
        self.assertEqual(normalize_quantity("abc"), 1)
        self.assertEqual(normalize_quantity("N/A"), 1)

    def test_decimal_is_truncated_to_int(self):
        self.assertEqual(normalize_quantity(5.9), 5)
        self.assertEqual(normalize_quantity("3.2"), 3)

    def test_valid_integer_is_kept(self):
        self.assertEqual(normalize_quantity(7), 7)
        self.assertEqual(normalize_quantity("10"), 10)

    def test_zero_and_negative_are_clamped_to_one(self):
        self.assertEqual(normalize_quantity(0), 1)
        self.assertEqual(normalize_quantity(-5), 1)
        self.assertEqual(normalize_quantity(-0.5), 1)
        self.assertEqual(normalize_quantity("-3"), 1)


class PrintItemTests(unittest.TestCase):
    def test_default_quantity_is_one(self):
        item = PrintItem(product=_product())
        self.assertEqual(item.quantity, 1)

    def test_holds_a_reference_to_the_product(self):
        product = _product()
        item = PrintItem(product=product, quantity=3)
        self.assertIs(item.product, product)
        self.assertEqual(item.quantity, 3)

    def test_quantity_never_zero(self):
        self.assertEqual(PrintItem(product=_product(), quantity=0).quantity, 1)

    def test_quantity_never_negative(self):
        self.assertEqual(PrintItem(product=_product(), quantity=-10).quantity, 1)

    def test_quantity_rejects_invalid_text(self):
        self.assertEqual(PrintItem(product=_product(), quantity="dez").quantity, 1)

    def test_quantity_accepts_decimal_and_truncates(self):
        self.assertEqual(PrintItem(product=_product(), quantity=4.8).quantity, 4)

    def test_creating_a_print_item_does_not_mutate_the_product(self):
        product = _product()
        PrintItem(product=product, quantity=50)
        self.assertFalse(hasattr(product, "quantidade"))
        self.assertFalse(hasattr(product, "quantity"))


if __name__ == "__main__":
    unittest.main()
