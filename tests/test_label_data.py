import dataclasses
import unittest

from core.label_data import LabelData


class LabelDataTests(unittest.TestCase):
    def test_holds_the_five_required_fields(self):
        label = LabelData(codigo="1001", descricao="Anel", categoria="Aneis", numero="16", preco=59.9)

        self.assertEqual(label.codigo, "1001")
        self.assertEqual(label.descricao, "Anel")
        self.assertEqual(label.categoria, "Aneis")
        self.assertEqual(label.numero, "16")
        self.assertEqual(label.preco, 59.9)

    def test_is_frozen(self):
        label = LabelData(codigo="1001", descricao="Anel", categoria="Aneis", numero="16", preco=59.9)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            label.codigo = "9999"

    def test_equality_is_by_value(self):
        first = LabelData(codigo="1001", descricao="Anel", categoria="Aneis", numero="16", preco=59.9)
        second = LabelData(codigo="1001", descricao="Anel", categoria="Aneis", numero="16", preco=59.9)
        self.assertEqual(first, second)

    def test_accepts_none_price_and_empty_number(self):
        label = LabelData(codigo="1001", descricao="Anel", categoria="Aneis", numero="", preco=None)
        self.assertIsNone(label.preco)
        self.assertEqual(label.numero, "")


if __name__ == "__main__":
    unittest.main()
