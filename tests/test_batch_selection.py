import unittest

from core.excel_reader import ExcelReader
from ui.main_window import build_batch_product_list


class BatchSelectionTests(unittest.TestCase):
    def test_build_batch_product_list_for_all(self):
        reader = ExcelReader.__new__(ExcelReader)
        reader.rows = [
            {"CODIGO": "1", "CATEGORIA": "A", "DESCRICAO": "A", "PRECO": 1.0, "NUMERO": 1},
            {"CODIGO": "2", "CATEGORIA": "B", "DESCRICAO": "B", "PRECO": 2.0, "NUMERO": 2},
        ]

        products = build_batch_product_list(reader, "all")

        self.assertEqual(len(products), 2)
        self.assertEqual(products[0]["codigo"], "1")
        self.assertEqual(products[1]["codigo"], "2")

    def test_build_batch_product_list_for_range(self):
        reader = ExcelReader.__new__(ExcelReader)
        reader.rows = [
            {"CODIGO": "1", "CATEGORIA": "A", "DESCRICAO": "A", "PRECO": 1.0, "NUMERO": 1},
            {"CODIGO": "2", "CATEGORIA": "B", "DESCRICAO": "B", "PRECO": 2.0, "NUMERO": 2},
            {"CODIGO": "3", "CATEGORIA": "C", "DESCRICAO": "C", "PRECO": 3.0, "NUMERO": 3},
        ]

        products = build_batch_product_list(reader, "range", 2, 3)

        self.assertEqual(len(products), 2)
        self.assertEqual(products[0]["codigo"], "2")
        self.assertEqual(products[1]["codigo"], "3")


if __name__ == "__main__":
    unittest.main()
