import unittest

from app.api.product import Product, ProductPrice

# Exemplo oficial do endpoint "Visualizar Produto" da documentação Jueri
# (https://jueri.com.br/sis/docs/), reproduzido tal como documentado.
FULL_PRODUCT_PAYLOAD = {
    "id": 2779,
    "descricao": "Anel de ouro 18k",
    "descricao_completa": "officiis",
    "fk_categoria_id": 1,
    "fk_subcategoria_id": 2,
    "referencia": "totam",
    "numero_peca": "sed",
    "largura": 2.32,
    "altura": 2,
    "profundidade": 1.32,
    "peso_loja": 3,
    "milesimos_ouro": 3.2,
    "peso": 3.33,
    "custo_compra_bruto": 10,
    "custo_banho_ouro": 5,
    "custo_banho_rodio": 3,
    "custo_banho_prata": 2,
    "quantidade": 4,
    "localizacao": "Setor 123",
    "numero_ncm": "71179000",
    "cfop": "5102",
    "fk_status_id": 1,
    "observacao": "voluptates",
    "data_criacao": "2021-03-03 18:49:17",
    "data_ultima_alteracao": "2021-03-03 18:49:17",
    "cor": "Ouro",
    "fcp": 0,
    "codigo_barras": "30856875",
    "tipo_preco": [
        {
            "id": 1,
            "nome": "Varejo",
            "pivot": {"preco": 49.99},
        }
    ],
}


class ProductFromApiTests(unittest.TestCase):
    def test_parses_full_payload(self):
        product = Product.from_api(FULL_PRODUCT_PAYLOAD)

        self.assertEqual(product.id, 2779)
        self.assertEqual(product.descricao, "Anel de ouro 18k")
        self.assertEqual(product.descricao_completa, "officiis")
        self.assertEqual(product.referencia, "totam")
        self.assertEqual(product.numero_peca, "sed")
        self.assertEqual(product.codigo_barras, "30856875")
        self.assertEqual(product.cor, "Ouro")
        self.assertEqual(product.localizacao, "Setor 123")
        self.assertEqual(product.observacao, "voluptates")
        self.assertEqual(product.quantidade, 4)
        self.assertEqual(product.peso, 3.33)
        self.assertEqual(product.peso_loja, 3)
        self.assertEqual(product.largura, 2.32)
        self.assertEqual(product.altura, 2)
        self.assertEqual(product.profundidade, 1.32)
        self.assertEqual(product.milesimos_ouro, 3.2)
        self.assertEqual(product.custo_compra_bruto, 10)
        self.assertEqual(product.custo_banho_ouro, 5)
        self.assertEqual(product.custo_banho_rodio, 3)
        self.assertEqual(product.custo_banho_prata, 2)
        self.assertEqual(product.fcp, 0)
        self.assertEqual(product.numero_ncm, "71179000")
        self.assertEqual(product.cfop, "5102")
        self.assertEqual(product.fk_categoria_id, 1)
        self.assertEqual(product.fk_subcategoria_id, 2)
        self.assertEqual(product.fk_status_id, 1)
        self.assertEqual(product.data_criacao, "2021-03-03 18:49:17")
        self.assertEqual(product.data_ultima_alteracao, "2021-03-03 18:49:17")

    def test_parses_tipo_preco_from_pivot(self):
        product = Product.from_api(FULL_PRODUCT_PAYLOAD)

        self.assertEqual(len(product.tipo_preco), 1)
        price = product.tipo_preco[0]
        self.assertIsInstance(price, ProductPrice)
        self.assertEqual(price.id, 1)
        self.assertEqual(price.nome, "Varejo")
        self.assertEqual(price.preco, 49.99)
        self.assertEqual(product.preco_principal, 49.99)

    def test_missing_optional_fields_do_not_raise(self):
        product = Product.from_api({"id": 10})

        self.assertEqual(product.id, 10)
        self.assertIsNone(product.descricao)
        self.assertIsNone(product.referencia)
        self.assertIsNone(product.codigo_barras)
        self.assertIsNone(product.peso)
        self.assertIsNone(product.fk_categoria_id)
        self.assertEqual(product.tipo_preco, [])
        self.assertIsNone(product.preco_principal)

    def test_missing_id_does_not_raise(self):
        product = Product.from_api({})
        self.assertIsNone(product.id)

    def test_empty_tipo_preco_list_is_handled(self):
        product = Product.from_api({"id": 1, "tipo_preco": []})
        self.assertEqual(product.tipo_preco, [])
        self.assertIsNone(product.preco_principal)

    def test_tipo_preco_without_pivot_does_not_raise(self):
        product = Product.from_api({"id": 1, "tipo_preco": [{"id": 5, "nome": "Atacado"}]})

        self.assertEqual(len(product.tipo_preco), 1)
        self.assertEqual(product.tipo_preco[0].nome, "Atacado")
        self.assertIsNone(product.tipo_preco[0].preco)

    def test_preco_principal_ignores_non_varejo_price(self):
        product = Product.from_api(
            {
                "id": 1,
                "tipo_preco": [{"id": 5, "nome": "Atacado", "pivot": {"preco": 30.0}}],
            }
        )
        self.assertIsNone(product.preco_principal)

    def test_preco_principal_finds_varejo_even_when_not_first(self):
        product = Product.from_api(
            {
                "id": 1,
                "tipo_preco": [
                    {"id": 5, "nome": "Atacado", "pivot": {"preco": 30.0}},
                    {"id": 1, "nome": "Varejo", "pivot": {"preco": 49.99}},
                ],
            }
        )
        self.assertEqual(product.preco_principal, 49.99)

    def test_preco_principal_is_case_sensitive(self):
        product = Product.from_api(
            {
                "id": 1,
                "tipo_preco": [{"id": 1, "nome": "varejo", "pivot": {"preco": 49.99}}],
            }
        )
        self.assertIsNone(product.preco_principal)


class FakeCategories:
    """Duplica só a interface que to_label_fields() usa (nome_categoria),
    sem nenhuma mecânica HTTP — testes de CategoriesAPI ficam em
    tests/test_categories_api.py."""

    def __init__(self, mapping: dict) -> None:
        self.mapping = mapping
        self.calls: list = []

    def nome_categoria(self, categoria_id):
        self.calls.append(categoria_id)
        return self.mapping.get(categoria_id)


class ProductToLabelFieldsTests(unittest.TestCase):
    def test_maps_codigo_barras_descricao_numero_peca_and_preco_varejo(self):
        product = Product.from_api(FULL_PRODUCT_PAYLOAD)

        fields = product.to_label_fields()

        self.assertEqual(
            fields,
            {
                "codigo": "30856875",
                "categoria": None,
                "descricao": "Anel de ouro 18k",
                "numero": "sed",
                "preco": 49.99,
                "qtd": 4,
            },
        )

    def test_missing_fields_stay_none_not_invented(self):
        product = Product.from_api({"id": 1})

        fields = product.to_label_fields()

        self.assertIsNone(fields["codigo"])
        self.assertIsNone(fields["descricao"])
        self.assertIsNone(fields["preco"])
        self.assertIsNone(fields["qtd"])

    def test_qtd_maps_from_quantidade(self):
        product = Product.from_api({"id": 1, "quantidade": 2})

        self.assertEqual(product.to_label_fields()["qtd"], 2)

    def test_qtd_is_zero_when_quantidade_is_zero(self):
        """Estoque zerado é um valor real, não "ausente" — não deve virar
        None nem ser trocado por um padrão."""
        product = Product.from_api({"id": 1, "quantidade": 0})

        self.assertEqual(product.to_label_fields()["qtd"], 0)

    def test_qtd_is_none_when_quantidade_is_null(self):
        product = Product.from_api({"id": 1, "quantidade": None})

        self.assertIsNone(product.to_label_fields()["qtd"])

    def test_numero_maps_from_numero_peca(self):
        """Confirmado contra produtos reais: numero_peca é o tamanho de
        aro em produtos ANEL/ALIANÇA (ex.: "30"), null em brincos/pulseiras."""
        product = Product.from_api({"id": 1, "numero_peca": "30"})

        self.assertEqual(product.to_label_fields()["numero"], "30")

    def test_numero_is_none_when_numero_peca_is_null(self):
        product = Product.from_api({"id": 1, "numero_peca": None})

        self.assertIsNone(product.to_label_fields()["numero"])

    def test_categoria_is_none_without_a_categories_argument(self):
        """Sem CategoriesAPI, categoria fica None — nunca expõe o ID cru."""
        product = Product.from_api({"id": 1, "fk_categoria_id": 42926})

        self.assertIsNone(product.to_label_fields()["categoria"])

    def test_categoria_resolves_via_categories_cache(self):
        product = Product.from_api({"id": 1, "fk_categoria_id": 42926})
        categories = FakeCategories({42926: "AÇO INOX - DOURADO"})

        fields = product.to_label_fields(categories)

        self.assertEqual(fields["categoria"], "AÇO INOX - DOURADO")
        self.assertEqual(categories.calls, [42926])

    def test_categoria_is_none_when_id_not_in_cache(self):
        product = Product.from_api({"id": 1, "fk_categoria_id": 999})
        categories = FakeCategories({42926: "AÇO INOX - DOURADO"})

        self.assertIsNone(product.to_label_fields(categories)["categoria"])

    def test_categoria_is_none_when_fk_categoria_id_is_missing(self):
        product = Product.from_api({"id": 1})
        categories = FakeCategories({42926: "AÇO INOX - DOURADO"})

        self.assertIsNone(product.to_label_fields(categories)["categoria"])

    def test_uses_referencia_never_as_codigo(self):
        """codigo_barras é o único campo usado para `codigo` — referencia
        não é um código de barras válido e não deve ser usado como
        substituto mesmo quando codigo_barras está ausente."""
        product = Product.from_api({"id": 1, "referencia": "REF-001"})

        fields = product.to_label_fields()

        self.assertIsNone(fields["codigo"])


class ProductToCatalogProductTests(unittest.TestCase):
    """to_catalog_product() é o que permite um produto do Jueri entrar na
    MESMA PrintQueue/PrintItem que o Catálogo Integrado (Excel) já usa —
    ver core/catalog_product.py e core/print_queue.py."""

    def test_maps_codigo_descricao_preco_and_numeracao(self):
        product = Product.from_api(FULL_PRODUCT_PAYLOAD)

        catalog_product = product.to_catalog_product()

        self.assertEqual(catalog_product.codigo, "30856875")
        self.assertEqual(catalog_product.descricao, "Anel de ouro 18k")
        self.assertEqual(catalog_product.preco, 49.99)
        self.assertEqual(catalog_product.numeracao, "sed")

    def test_fornecedor_marks_the_product_as_coming_from_jueri(self):
        product = Product.from_api({"id": 1})
        self.assertEqual(product.to_catalog_product().fornecedor, "Jueri")

    def test_categoria_resolves_via_categories_cache(self):
        product = Product.from_api({"id": 1, "fk_categoria_id": 42926})
        categories = FakeCategories({42926: "AÇO INOX - DOURADO"})

        catalog_product = product.to_catalog_product(categories)

        self.assertEqual(catalog_product.categoria, "AÇO INOX - DOURADO")

    def test_categoria_is_empty_string_without_categories_argument(self):
        """CatalogProduct.categoria é `str`, não `str | None` — sem
        CategoriesAPI, fica string vazia em vez de None ou do ID cru."""
        product = Product.from_api({"id": 1, "fk_categoria_id": 42926})

        self.assertEqual(product.to_catalog_product().categoria, "")

    def test_missing_fields_become_empty_strings_not_none(self):
        product = Product.from_api({"id": 1})

        catalog_product = product.to_catalog_product()

        self.assertEqual(catalog_product.codigo, "")
        self.assertEqual(catalog_product.descricao, "")
        self.assertEqual(catalog_product.numeracao, "")
        self.assertIsNone(catalog_product.preco)

    def test_default_quantity_attribute_seeds_from_estoque_atual(self):
        """attributes["default_quantity"] é a MESMA chave que
        CatalogService.create_print_item() já lê para semear
        PrintItem.quantity a partir da coluna QTD do Excel — aqui recebe
        o estoque atual da API, sem precisar de nenhuma lógica nova."""
        product = Product.from_api({"id": 1, "quantidade": 2})

        catalog_product = product.to_catalog_product()

        self.assertEqual(catalog_product.attributes["default_quantity"], 2)
        self.assertEqual(catalog_product.attributes["quantidade_estoque"], 2)

    def test_default_quantity_zero_is_preserved_not_replaced(self):
        product = Product.from_api({"id": 1, "quantidade": 0})
        catalog_product = product.to_catalog_product()
        self.assertEqual(catalog_product.attributes["default_quantity"], 0)

    def test_default_quantity_none_when_quantidade_is_null(self):
        product = Product.from_api({"id": 1, "quantidade": None})
        catalog_product = product.to_catalog_product()
        self.assertIsNone(catalog_product.attributes["default_quantity"])

    def test_attributes_include_jueri_id_and_origem_for_traceability(self):
        product = Product.from_api({"id": 12345})
        catalog_product = product.to_catalog_product()
        self.assertEqual(catalog_product.attributes["jueri_id"], 12345)
        self.assertEqual(catalog_product.attributes["origem"], "jueri")

    def test_result_is_usable_as_a_real_print_item(self):
        """Prova de integração: o CatalogProduct convertido funciona sem
        nenhuma adaptação em PrintItem/PrintQueue, exatamente como um
        produto do Excel."""
        from core.print_item import PrintItem
        from core.print_queue import PrintQueue

        product = Product.from_api({"id": 1, "codigo_barras": "181021", "quantidade": 3})
        catalog_product = product.to_catalog_product()

        queue = PrintQueue()
        item = queue.add_or_increment(catalog_product, quantity=catalog_product.attributes["default_quantity"])

        self.assertIsInstance(item, PrintItem)
        self.assertEqual(item.quantity, 3)
        self.assertTrue(queue.contains(catalog_product))


if __name__ == "__main__":
    unittest.main()
