import unittest

from core.zpl_builder import ZplBuilder


class ZplBuilderRowTests(unittest.TestCase):
    def setUp(self):
        self.builder = ZplBuilder()
        self.column_pitch = 264
        self.total_width = self.column_pitch * 3

    def _product(self, codigo):
        return {
            "codigo": codigo,
            "categoria": "CATEGORIA",
            "descricao": "DESCRICAO",
            "numero": "10",
            "preco": 9.9,
        }

    def _expected_fields(self, products):
        fields = []
        for index, product in enumerate(products):
            fields.extend(self.builder._build_fields(product, x_offset=index * self.column_pitch))
        return "\n".join(fields)

    def test_build_row_one_product_fills_only_first_column(self):
        products = [self._product("111111")]
        zpl = self.builder.build_row(products, column_pitch=self.column_pitch, total_width=self.total_width)

        self.assertTrue(zpl.startswith("^XA"))
        self.assertTrue(zpl.endswith("^XZ"))
        self.assertIn(f"^PW{self.total_width}", zpl)
        self.assertIn(self._expected_fields(products), zpl)
        self.assertEqual(zpl.count("^BCN"), 1)
        self.assertEqual(zpl.count("R$"), 1)

    def test_build_row_two_products_fills_first_two_columns_only(self):
        products = [self._product("111111"), self._product("222222")]
        zpl = self.builder.build_row(products, column_pitch=self.column_pitch, total_width=self.total_width)

        self.assertIn(f"^PW{self.total_width}", zpl)
        self.assertIn(self._expected_fields(products), zpl)
        self.assertEqual(zpl.count("^BCN"), 2)
        self.assertEqual(zpl.count("R$"), 2)

    def test_build_row_three_products_fills_all_columns(self):
        products = [self._product("111111"), self._product("222222"), self._product("333333")]
        zpl = self.builder.build_row(products, column_pitch=self.column_pitch, total_width=self.total_width)

        self.assertIn(f"^PW{self.total_width}", zpl)
        self.assertIn(self._expected_fields(products), zpl)
        self.assertEqual(zpl.count("^BCN"), 3)
        self.assertEqual(zpl.count("R$"), 3)

    def test_build_row_default_total_width_uses_column_pitch_times_products(self):
        products = [self._product("111111"), self._product("222222")]
        zpl = self.builder.build_row(products, column_pitch=self.column_pitch)
        self.assertIn(f"^PW{self.column_pitch * len(products)}", zpl)


if __name__ == "__main__":
    unittest.main()
