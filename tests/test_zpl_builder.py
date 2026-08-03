import unittest

from core.label_data import LabelData
from core.zpl_builder import ZplBuilder


class ZplBuilderRowTests(unittest.TestCase):
    def setUp(self):
        self.builder = ZplBuilder()
        self.column_pitch = 264
        self.total_width = self.column_pitch * 3

    def _product(self, codigo):
        return LabelData(
            codigo=codigo,
            categoria="CATEGORIA",
            descricao="DESCRICAO",
            numero="10",
            preco=9.9,
        )

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


class ZplBuilderBuildAcceptsDictTests(unittest.TestCase):
    """build() continua aceitando dict (usado pela impressão unitária/teste
    da aba "Impressão") — internamente converte para LabelData antes de
    montar os campos, sem alterar nenhum cálculo/posicionamento."""

    def test_build_from_dict_matches_build_row_from_equivalent_label_data(self):
        builder = ZplBuilder()
        product_dict = {
            "codigo": "111111",
            "categoria": "CATEGORIA",
            "descricao": "DESCRICAO",
            "numero": "10",
            "preco": 9.9,
        }

        zpl_from_dict = builder.build(product_dict)

        label = LabelData(**product_dict)
        zpl_from_row = builder.build_row([label], column_pitch=240, total_width=240)

        # build() usa ^PW/^LL de uma etiqueta só; build_row() com uma coluna
        # e mesma largura produz exatamente os mesmos campos internos.
        for line in builder._build_fields(label):
            self.assertIn(line, zpl_from_dict)
            self.assertIn(line, zpl_from_row)


class ZplBuilderDescriptionLayoutTests(unittest.TestCase):
    def test_long_description_is_width_limited_before_single_line_field_block(self):
        builder = ZplBuilder()
        label = LabelData(
            codigo="131848",
            categoria="COLAR",
            descricao="COLAR COURINO COUNTRY FERRADURA",
            numero="",
            preco=49.9,
        )

        description_field = next(
            line for line in builder._build_fields(label)
            if f",{builder.DESCRIPTION_ROW_Y}^FB" in line
        )

        self.assertIn("^FB198,1,0,C,0", description_field)
        self.assertIn("^FDCOLAR COURINO COUNTRY FE^FS", description_field)
        self.assertNotIn("COLAR COURINO COUNTRY FERR", description_field)
        self.assertNotIn("...", description_field)

    def test_description_that_already_fits_is_unchanged(self):
        builder = ZplBuilder()
        label = LabelData(
            codigo="131848",
            categoria="COLAR",
            descricao="COLAR COURINO",
            numero="",
            preco=49.9,
        )

        description_field = next(
            line for line in builder._build_fields(label)
            if f",{builder.DESCRIPTION_ROW_Y}^FB" in line
        )

        self.assertIn("^FDCOLAR COURINO^FS", description_field)
        self.assertNotIn("...", description_field)


if __name__ == "__main__":
    unittest.main()
