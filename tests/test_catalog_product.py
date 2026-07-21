import unittest

from core.catalog_product import CatalogProduct


class CatalogProductTests(unittest.TestCase):
    def test_search_blob_is_precomputed_case_and_accent_insensitive(self):
        product = CatalogProduct(
            codigo="1001",
            descricao="Anel de Prata com Coração",
            preco=59.9,
            categoria="Anéis",
            numeracao="16",
            fornecedor="DIP-15",
        )

        self.assertIn("coracao", product.search_blob)
        self.assertIn("aneis", product.search_blob)
        self.assertIn("dip-15", product.search_blob)
        self.assertIn("1001", product.search_blob)
        self.assertIn("16", product.search_blob)
        # deve estar tudo em minusculas, sem acento
        self.assertEqual(product.search_blob, product.search_blob.lower())

    def test_attributes_dict_allows_future_fields_without_breaking(self):
        product = CatalogProduct(
            codigo="1001",
            descricao="Anel",
            preco=None,
            categoria="Aneis",
            numeracao="",
            fornecedor="DIP-15",
            attributes={"subcategoria": "Prata 925", "peso": "3g"},
        )
        self.assertEqual(product.attributes["subcategoria"], "Prata 925")
        self.assertEqual(product.attributes["peso"], "3g")

    def test_attributes_defaults_to_empty_dict(self):
        product = CatalogProduct(
            codigo="1001", descricao="Anel", preco=None, categoria="Aneis", numeracao="", fornecedor="DIP-15"
        )
        self.assertEqual(product.attributes, {})

    def test_preco_can_be_none(self):
        product = CatalogProduct(
            codigo="1001", descricao="Anel", preco=None, categoria="Aneis", numeracao="", fornecedor="DIP-15"
        )
        self.assertIsNone(product.preco)

    def test_display_category_defaults_to_categoria(self):
        product = CatalogProduct(
            codigo="1001", descricao="Anel", preco=None, categoria="Aneis", numeracao="", fornecedor="DIP-15"
        )
        self.assertEqual(product.display_category, "Aneis")

    def test_display_category_reflects_categoria_changes(self):
        product = CatalogProduct(
            codigo="1001", descricao="Anel", preco=None, categoria="Aneis", numeracao="", fornecedor="DIP-15"
        )
        product.categoria = "Brincos"
        self.assertEqual(product.display_category, "Brincos")

    def test_catalog_product_has_no_print_quantity_field(self):
        """CatalogProduct representa só o produto — quantidade de impressão
        é responsabilidade de PrintItem (core/print_item.py), não dele."""
        product = CatalogProduct(
            codigo="1001", descricao="Anel", preco=None, categoria="Aneis", numeracao="", fornecedor="DIP-15"
        )
        self.assertFalse(hasattr(product, "quantidade"))
        with self.assertRaises(TypeError):
            CatalogProduct(
                codigo="1001",
                descricao="Anel",
                preco=None,
                categoria="Aneis",
                numeracao="",
                fornecedor="DIP-15",
                quantidade=5,
            )


if __name__ == "__main__":
    unittest.main()
