import unittest
from types import SimpleNamespace

from ui.main_window import MainWindow


class BatchFlowTests(unittest.TestCase):
    def test_get_print_products_uses_loaded_rows(self):
        window = MainWindow.__new__(MainWindow)
        window.reader = SimpleNamespace(
            error_message=None,
            rows=[
                {"CODIGO": "1", "CATEGORIA": "A", "DESCRICAO": "A", "PRECO": 1.0, "NUMERO": 1},
                {"CODIGO": "2", "CATEGORIA": "B", "DESCRICAO": "B", "PRECO": 2.0, "NUMERO": 2},
            ],
        )
        window.mode_var = SimpleNamespace(get=lambda: "batch")
        window.quantity_mode_var = SimpleNamespace(get=lambda: "all")
        window.from_var = SimpleNamespace(get=lambda: "")
        window.to_var = SimpleNamespace(get=lambda: "")

        products = window._get_print_products()

        self.assertEqual(len(products), 2)
        self.assertEqual(products[0]["codigo"], "1")
        self.assertEqual(products[1]["codigo"], "2")

    def test_parse_quantity_defaults_to_one_when_empty(self):
        window = MainWindow.__new__(MainWindow)

        self.assertEqual(window._parse_quantity(None), 1)
        self.assertEqual(window._parse_quantity(""), 1)
        self.assertEqual(window._parse_quantity("0"), 0)
        self.assertEqual(window._parse_quantity("3"), 3)


if __name__ == "__main__":
    unittest.main()
