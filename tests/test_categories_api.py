import json
import unittest
from unittest.mock import patch

from app.api.auth import JueriCredentials
from app.api.categories import CATEGORIES_PATH, CategoriesAPI
from app.api.client import JueriClient
from app.api.exceptions import JueriDisabledError

RAW_CATEGORIES_RESPONSE = {
    "data": [
        {
            "id": 42926,
            "nome": "AÇO INOX - DOURADO",
            "cfop": "5102",
            "numero_ncm": "71171900",
            "subcategoria": [
                {"id": 93066, "nome": "PULSEIRA", "cfop": "5102", "numero_ncm": "71171900"},
                {"id": 101206, "nome": "ANEL", "cfop": "5102", "numero_ncm": "71171900"},
            ],
        },
        {
            "id": 35734,
            "nome": "PRATA 925",
            "cfop": "5102",
            "numero_ncm": "71131900",
            "subcategoria": [
                {"id": 81734, "nome": "ANEL", "cfop": "5102", "numero_ncm": "71131900"},
            ],
        },
    ]
}


def build_categories_api(**credential_overrides) -> CategoriesAPI:
    fields = {"enabled": True, "cliente_sistema": "SANTARUBI", "token": "abc123"}
    fields.update(credential_overrides)
    credentials = JueriCredentials(**fields)
    client = JueriClient("https://jueri.com.br/sis", credentials, timeout=5)
    return CategoriesAPI(client)


class CategoriesAPITests(unittest.TestCase):
    @patch("app.api.client.urllib.request.urlopen")
    def test_loads_and_caches_categoria_and_subcategoria_names(self, mock_urlopen):
        mock_response = mock_urlopen.return_value.__enter__.return_value
        mock_response.read.return_value = json.dumps(RAW_CATEGORIES_RESPONSE).encode("utf-8")

        categories = build_categories_api()

        self.assertEqual(categories.nome_categoria(42926), "AÇO INOX - DOURADO")
        self.assertEqual(categories.nome_categoria(35734), "PRATA 925")
        self.assertEqual(categories.nome_subcategoria(93066), "PULSEIRA")
        self.assertEqual(categories.nome_subcategoria(101206), "ANEL")
        self.assertEqual(categories.nome_subcategoria(81734), "ANEL")

    @patch("app.api.client.urllib.request.urlopen")
    def test_does_not_make_a_new_request_on_subsequent_lookups(self, mock_urlopen):
        mock_response = mock_urlopen.return_value.__enter__.return_value
        mock_response.read.return_value = json.dumps(RAW_CATEGORIES_RESPONSE).encode("utf-8")

        categories = build_categories_api()

        categories.nome_categoria(42926)
        categories.nome_categoria(35734)
        categories.nome_subcategoria(93066)
        categories.nome_categoria(999)  # id desconhecido também não deve gerar nova chamada

        self.assertEqual(mock_urlopen.call_count, 1)

    @patch("app.api.client.urllib.request.urlopen")
    def test_calls_the_documented_categories_endpoint(self, mock_urlopen):
        mock_response = mock_urlopen.return_value.__enter__.return_value
        mock_response.read.return_value = json.dumps(RAW_CATEGORIES_RESPONSE).encode("utf-8")

        categories = build_categories_api()
        categories.nome_categoria(42926)

        request = mock_urlopen.call_args[0][0]
        expected_path = CATEGORIES_PATH.format(cliente_sistema="SANTARUBI")
        self.assertEqual(request.full_url, f"https://jueri.com.br/sis{expected_path}")

    @patch("app.api.client.urllib.request.urlopen")
    def test_nome_categoria_returns_none_for_unknown_id(self, mock_urlopen):
        mock_response = mock_urlopen.return_value.__enter__.return_value
        mock_response.read.return_value = json.dumps(RAW_CATEGORIES_RESPONSE).encode("utf-8")

        categories = build_categories_api()

        self.assertIsNone(categories.nome_categoria(123456))
        self.assertIsNone(categories.nome_subcategoria(123456))

    def test_nome_categoria_returns_none_for_none_id_without_any_request(self):
        categories = build_categories_api()

        self.assertIsNone(categories.nome_categoria(None))
        self.assertIsNone(categories.nome_subcategoria(None))

    def test_raises_when_integration_disabled(self):
        categories = build_categories_api(enabled=False)

        with self.assertRaises(JueriDisabledError):
            categories.nome_categoria(42926)


if __name__ == "__main__":
    unittest.main()
