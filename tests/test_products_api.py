import json
import unittest
import urllib.parse
import urllib.error
from unittest.mock import MagicMock, patch

from app.api.auth import JueriCredentials
from app.api.client import JueriClient
from app.api.exceptions import JueriConnectionError, JueriDisabledError
from app.api.products import PRODUCTS_PATH, ProductsAPI

PAGINATED_RESPONSE = {
    "current_page": 1,
    "data": [
        {
            "id": 2779,
            "descricao": "Anel de ouro 18k",
            "referencia": "totam",
            "peso": 3.33,
            "tipo_preco": [{"id": 1, "nome": "Varejo", "pivot": {"preco": 49.99}}],
        },
        {"id": 2780, "descricao": "Brinco de prata"},
    ],
    "first_page_url": "https://jueri.com.br/sis/api/v1/1/produto?page=1",
    "from": 1,
    "next_page_url": None,
    "path": "https://jueri.com.br/sis/api/v1/1/produto",
    "per_page": 15,
    "prev_page_url": None,
    "to": 2,
}


def build_products_api(**credential_overrides) -> ProductsAPI:
    fields = {"enabled": True, "cliente_sistema": "SANTARUBI", "token": "abc123"}
    fields.update(credential_overrides)
    credentials = JueriCredentials(**fields)
    client = JueriClient("https://jueri.com.br/sis", credentials, timeout=5)
    return ProductsAPI(client)


class ProductsAPISearchTests(unittest.TestCase):
    @patch("app.api.client.urllib.request.urlopen")
    def test_search_products_parses_paginated_result(self, mock_urlopen):
        mock_response = mock_urlopen.return_value.__enter__.return_value
        mock_response.read.return_value = json.dumps(PAGINATED_RESPONSE).encode("utf-8")

        products_api = build_products_api()
        result = products_api.search_products(search="anel")

        self.assertEqual(len(result.products), 2)
        self.assertEqual(result.products[0].id, 2779)
        self.assertEqual(result.products[0].descricao, "Anel de ouro 18k")
        self.assertEqual(result.products[0].preco_principal, 49.99)
        self.assertEqual(result.products[1].id, 2780)
        self.assertIsNone(result.products[1].preco_principal)

        self.assertEqual(result.current_page, 1)
        self.assertEqual(result.per_page, 15)
        self.assertEqual(result.from_item, 1)
        self.assertEqual(result.to_item, 2)
        self.assertIsNone(result.next_page_url)

    @patch("app.api.client.urllib.request.urlopen")
    def test_search_products_sends_only_provided_filters(self, mock_urlopen):
        mock_response = mock_urlopen.return_value.__enter__.return_value
        mock_response.read.return_value = json.dumps(PAGINATED_RESPONSE).encode("utf-8")

        products_api = build_products_api()
        products_api.search_products(search="anel", categoria_id=1, page=2)

        request = mock_urlopen.call_args[0][0]
        parsed = urllib.parse.urlparse(request.full_url)
        query = urllib.parse.parse_qs(parsed.query)

        expected_path = "/sis" + PRODUCTS_PATH.format(cliente_sistema="SANTARUBI")
        self.assertEqual(parsed.path, expected_path)
        self.assertEqual(query, {"search": ["anel"], "categoria_id": ["1"], "page": ["2"]})

    @patch("app.api.client.urllib.request.urlopen")
    def test_search_products_without_filters_sends_no_query_string(self, mock_urlopen):
        mock_response = mock_urlopen.return_value.__enter__.return_value
        mock_response.read.return_value = json.dumps(PAGINATED_RESPONSE).encode("utf-8")

        products_api = build_products_api()
        products_api.search_products()

        request = mock_urlopen.call_args[0][0]
        self.assertNotIn("?", request.full_url)

    def test_search_products_raises_when_integration_disabled(self):
        products_api = build_products_api(enabled=False)
        with self.assertRaises(JueriDisabledError):
            products_api.search_products(search="anel")

    @patch("app.api.client.urllib.request.urlopen")
    def test_search_products_propagates_connection_errors(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("sem rede")

        products_api = build_products_api()
        with self.assertRaises(JueriConnectionError):
            products_api.search_products(search="anel")

    @patch("app.api.client.urllib.request.urlopen")
    def test_search_products_with_no_results(self, mock_urlopen):
        empty_response = dict(PAGINATED_RESPONSE, data=[])
        mock_response = mock_urlopen.return_value.__enter__.return_value
        mock_response.read.return_value = json.dumps(empty_response).encode("utf-8")

        products_api = build_products_api()
        result = products_api.search_products(search="inexistente")

        self.assertEqual(result.products, [])


def _paginated_body(data: list) -> bytes:
    return json.dumps(
        {
            "current_page": 1,
            "data": data,
            "first_page_url": "https://jueri.com.br/sis/api/v1/1/produto?page=1",
            "from": 1 if data else None,
            "next_page_url": None,
            "path": "https://jueri.com.br/sis/api/v1/1/produto",
            "per_page": 15,
            "prev_page_url": None,
            "to": len(data) or None,
        }
    ).encode("utf-8")


def make_urlopen_side_effect(products_by_code: dict):
    """Simula a API respondendo de forma diferente para cada `search=` da
    requisição — necessário porque search_multiple_products() faz uma
    chamada HTTP por código."""

    def _side_effect(request, timeout=None):
        parsed = urllib.parse.urlparse(request.full_url)
        query = urllib.parse.parse_qs(parsed.query)
        code = query.get("search", [None])[0]
        product = products_by_code.get(code)
        data = [product] if product is not None else []

        mock_response = MagicMock()
        mock_response.read.return_value = _paginated_body(data)
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = False
        return mock_response

    return _side_effect


class ProductsAPISearchMultipleTests(unittest.TestCase):
    @patch("app.api.client.urllib.request.urlopen")
    def test_merges_results_from_each_code(self, mock_urlopen):
        mock_urlopen.side_effect = make_urlopen_side_effect(
            {
                "181021": {"id": 1, "codigo_barras": "181021", "descricao": "ALIANCA"},
                "181050": {"id": 2, "codigo_barras": "181050", "descricao": "ANEL"},
            }
        )

        products_api = build_products_api()
        results = products_api.search_multiple_products(["181021", "181050"])

        self.assertEqual([p.codigo_barras for p in results], ["181021", "181050"])
        self.assertEqual(mock_urlopen.call_count, 2)

    @patch("app.api.client.urllib.request.urlopen")
    def test_ignores_codes_with_no_results_but_keeps_the_rest(self, mock_urlopen):
        mock_urlopen.side_effect = make_urlopen_side_effect(
            {
                "181021": {"id": 1, "codigo_barras": "181021", "descricao": "ALIANCA"},
                "181050": {"id": 2, "codigo_barras": "181050", "descricao": "ANEL"},
                # "999999" ausente do dicionário -> API retorna lista vazia para ele
            }
        )

        products_api = build_products_api()
        results = products_api.search_multiple_products(["181021", "999999", "181050"])

        self.assertEqual([p.codigo_barras for p in results], ["181021", "181050"])
        self.assertEqual(mock_urlopen.call_count, 3)

    @patch("app.api.client.urllib.request.urlopen")
    def test_deduplicates_repeated_codes_before_searching(self, mock_urlopen):
        mock_urlopen.side_effect = make_urlopen_side_effect(
            {"181021": {"id": 1, "codigo_barras": "181021", "descricao": "ALIANCA"}}
        )

        products_api = build_products_api()
        results = products_api.search_multiple_products(["181021", "181021", "181021"])

        self.assertEqual(len(results), 1)
        self.assertEqual(mock_urlopen.call_count, 1)

    @patch("app.api.client.urllib.request.urlopen")
    def test_results_are_sorted_by_codigo_barras(self, mock_urlopen):
        mock_urlopen.side_effect = make_urlopen_side_effect(
            {
                "181330": {"id": 3, "codigo_barras": "181330", "descricao": "C"},
                "181021": {"id": 1, "codigo_barras": "181021", "descricao": "A"},
                "181110": {"id": 2, "codigo_barras": "181110", "descricao": "B"},
            }
        )

        products_api = build_products_api()
        # Códigos informados fora de ordem — resultado deve vir ordenado.
        results = products_api.search_multiple_products(["181330", "181021", "181110"])

        self.assertEqual([p.codigo_barras for p in results], ["181021", "181110", "181330"])

    @patch("app.api.client.urllib.request.urlopen")
    def test_deduplicates_by_product_id_across_codes(self, mock_urlopen):
        # Mesmo produto "encontrado" pelos dois códigos (ex.: busca parcial
        # casando em mais de um termo) não deve aparecer duas vezes.
        same_product = {"id": 1, "codigo_barras": "181021", "descricao": "ALIANCA"}
        mock_urlopen.side_effect = make_urlopen_side_effect({"181021": same_product, "18102": same_product})

        products_api = build_products_api()
        results = products_api.search_multiple_products(["181021", "18102"])

        self.assertEqual(len(results), 1)

    def test_empty_code_list_returns_empty_without_any_request(self):
        products_api = build_products_api()

        with patch("app.api.client.urllib.request.urlopen") as mock_urlopen:
            results = products_api.search_multiple_products([])

        self.assertEqual(results, [])
        mock_urlopen.assert_not_called()

    def test_raises_when_integration_disabled(self):
        products_api = build_products_api(enabled=False)
        with self.assertRaises(JueriDisabledError):
            products_api.search_multiple_products(["181021"])

    @patch("app.api.client.urllib.request.urlopen")
    def test_forwards_extra_filters_to_each_code_search(self, mock_urlopen):
        """Combinação lista de códigos + data: cada busca individual
        recebe o filtro de data também."""
        mock_urlopen.side_effect = make_urlopen_side_effect(
            {"181021": {"id": 1, "codigo_barras": "181021", "descricao": "ALIANCA"}}
        )

        products_api = build_products_api()
        products_api.search_multiple_products(
            ["181021"], data_criacao_inicial="2026-07-23", data_criacao_final="2026-07-23"
        )

        request = mock_urlopen.call_args[0][0]
        query = urllib.parse.parse_qs(urllib.parse.urlparse(request.full_url).query)
        self.assertEqual(query["data_criacao_inicial"], ["2026-07-23"])
        self.assertEqual(query["data_criacao_final"], ["2026-07-23"])


def make_paginated_urlopen_side_effect(pages: list[list[dict]]):
    """Simula respostas paginadas: pages[0] é a página 1, pages[1] a
    página 2, etc. Toda página exceto a última tem next_page_url
    preenchido."""

    def _side_effect(request, timeout=None):
        parsed = urllib.parse.urlparse(request.full_url)
        query = urllib.parse.parse_qs(parsed.query)
        page_number = int(query.get("page", ["1"])[0])
        index = page_number - 1
        data = pages[index] if index < len(pages) else []
        has_next = index + 1 < len(pages)

        body = json.dumps(
            {
                "current_page": page_number,
                "data": data,
                "first_page_url": "https://jueri.com.br/sis/api/v1/1/produto?page=1",
                "from": 1 if data else None,
                "next_page_url": f"https://jueri.com.br/sis/api/v1/1/produto?page={page_number + 1}"
                if has_next
                else None,
                "path": "https://jueri.com.br/sis/api/v1/1/produto",
                "per_page": 1000,
                "prev_page_url": None,
                "to": len(data) or None,
            }
        ).encode("utf-8")

        mock_response = MagicMock()
        mock_response.read.return_value = body
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = False
        return mock_response

    return _side_effect


class ProductsAPISearchAllPagesTests(unittest.TestCase):
    @patch("app.api.client.urllib.request.urlopen")
    def test_walks_all_pages_until_next_page_url_is_none(self, mock_urlopen):
        page1 = [{"id": 1, "codigo_barras": "181001"}, {"id": 2, "codigo_barras": "181002"}]
        page2 = [{"id": 3, "codigo_barras": "181003"}]
        mock_urlopen.side_effect = make_paginated_urlopen_side_effect([page1, page2])

        products_api = build_products_api()
        results = products_api.search_all_pages(data_criacao_inicial="2026-07-22")

        self.assertEqual([p.codigo_barras for p in results], ["181001", "181002", "181003"])
        self.assertEqual(mock_urlopen.call_count, 2)

    @patch("app.api.client.urllib.request.urlopen")
    def test_stops_after_a_single_page_when_next_page_url_is_none(self, mock_urlopen):
        page1 = [{"id": 1, "codigo_barras": "181001"}]
        mock_urlopen.side_effect = make_paginated_urlopen_side_effect([page1])

        products_api = build_products_api()
        results = products_api.search_all_pages(data_criacao_inicial="2026-07-22")

        self.assertEqual(len(results), 1)
        self.assertEqual(mock_urlopen.call_count, 1)

    @patch("app.api.client.urllib.request.urlopen")
    def test_uses_per_page_1000_by_default(self, mock_urlopen):
        mock_urlopen.side_effect = make_paginated_urlopen_side_effect([[]])

        products_api = build_products_api()
        products_api.search_all_pages(data_criacao_inicial="2026-07-22")

        request = mock_urlopen.call_args[0][0]
        query = urllib.parse.parse_qs(urllib.parse.urlparse(request.full_url).query)
        self.assertEqual(query["per_page"], ["1000"])

    @patch("app.api.client.urllib.request.urlopen")
    def test_combines_with_description_search(self, mock_urlopen):
        mock_urlopen.side_effect = make_paginated_urlopen_side_effect(
            [[{"id": 1, "codigo_barras": "181001", "descricao": "ANEL DE OURO"}]]
        )

        products_api = build_products_api()
        results = products_api.search_all_pages(search="anel", data_criacao_inicial="2026-07-23")

        self.assertEqual(len(results), 1)
        request = mock_urlopen.call_args[0][0]
        query = urllib.parse.parse_qs(urllib.parse.urlparse(request.full_url).query)
        self.assertEqual(query["search"], ["anel"])
        self.assertEqual(query["data_criacao_inicial"], ["2026-07-23"])

    @patch("app.api.client.urllib.request.urlopen")
    def test_empty_result_returns_empty_list(self, mock_urlopen):
        mock_urlopen.side_effect = make_paginated_urlopen_side_effect([[]])

        products_api = build_products_api()
        results = products_api.search_all_pages(data_criacao_inicial="2026-07-23")

        self.assertEqual(results, [])

    @patch("app.api.client.urllib.request.urlopen")
    def test_stops_at_safety_cap_instead_of_looping_forever(self, mock_urlopen):
        """Se a API sempre devolvesse next_page_url preenchido (bug/loop),
        o Launcher/diálogo não pode travar para sempre."""

        def _always_has_next(request, timeout=None):
            body = json.dumps(
                {
                    "current_page": 1,
                    "data": [],
                    "first_page_url": "https://jueri.com.br/sis/api/v1/1/produto?page=1",
                    "from": None,
                    "next_page_url": "https://jueri.com.br/sis/api/v1/1/produto?page=2",
                    "path": "https://jueri.com.br/sis/api/v1/1/produto",
                    "per_page": 1000,
                    "prev_page_url": None,
                    "to": None,
                }
            ).encode("utf-8")
            mock_response = MagicMock()
            mock_response.read.return_value = body
            mock_response.__enter__.return_value = mock_response
            mock_response.__exit__.return_value = False
            return mock_response

        mock_urlopen.side_effect = _always_has_next

        products_api = build_products_api()
        results = products_api.search_all_pages(data_criacao_inicial="2026-07-23")

        self.assertEqual(results, [])
        self.assertEqual(mock_urlopen.call_count, 200)

    def test_raises_when_integration_disabled(self):
        products_api = build_products_api(enabled=False)
        with self.assertRaises(JueriDisabledError):
            products_api.search_all_pages(data_criacao_inicial="2026-07-23")


if __name__ == "__main__":
    unittest.main()
