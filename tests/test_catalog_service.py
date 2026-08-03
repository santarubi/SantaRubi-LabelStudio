import unittest
from typing import Any

from core.catalog_datasource import DataSource
from core.catalog_repository import CatalogRepository
from core.catalog_service import CATEGORY_ALL, SUPPLIER_ALL, CatalogService
from core.catalog_settings import CatalogSettings


class FakeDataSource(DataSource):
    """DataSource em memória com contadores de chamadas — usada para provar
    que pesquisa/filtro/ordenação do CatalogService nunca releem a origem."""

    def __init__(self, sheets_data: dict[str, list[dict[str, Any]]]):
        self.sheets_data = sheets_data
        self.read_rows_calls = 0
        self.list_sheets_calls = 0

    def list_sheets(self) -> list[str]:
        self.list_sheets_calls += 1
        return list(self.sheets_data.keys())

    def get_headers(self, sheet_names: list[str]) -> dict[str, list[str]]:
        headers: dict[str, list[str]] = {}
        for name in sheet_names:
            rows = self.sheets_data.get(name, [])
            headers[name] = list(rows[0].keys()) if rows else []
        return headers

    def count_rows(self, sheet_names: list[str]) -> dict[str, int]:
        return {name: len(self.sheets_data.get(name, [])) for name in sheet_names}

    def read_rows(self, sheet_names: list[str]) -> list[dict[str, Any]]:
        self.read_rows_calls += 1
        rows: list[dict[str, Any]] = []
        for name in sheet_names:
            for row in self.sheets_data.get(name, []):
                row_with_sheet = dict(row)
                row_with_sheet["_sheet"] = name
                rows.append(row_with_sheet)
        return rows


COLUMN_MAP = {
    "codigo": "CODIGO",
    "descricao": "DESCRICAO",
    "preco": "PRECO",
    "categoria": "CATEGORIA",
    "numeracao": "NUMERO",
    "quantidade": "QTD",
}


def build_service() -> tuple[CatalogService, FakeDataSource, CatalogSettings]:
    source = FakeDataSource(
        {
            "DIP-15": [
                {"CODIGO": "1001", "DESCRICAO": "Anel de Prata com Coração", "PRECO": 59.9,
                 "CATEGORIA": "Aneis", "NUMERO": "16", "QTD": 5},
                {"CODIGO": "1002", "DESCRICAO": "Brinco Pino Flor", "PRECO": 89.9,
                 "CATEGORIA": "Brincos", "NUMERO": "", "QTD": None},
            ],
            "IW-13": [
                {"CODIGO": "2001", "DESCRICAO": "Colar Folheado a Ouro", "PRECO": 129.9,
                 "CATEGORIA": "Colares", "NUMERO": "", "QTD": 2},
                {"CODIGO": "2002", "DESCRICAO": "Anel Solitario Zirconia", "PRECO": 39.9,
                 "CATEGORIA": "Aneis", "NUMERO": "18", "QTD": "abc"},
            ],
        }
    )
    settings = CatalogSettings(selected_sheets=["DIP-15", "IW-13"], column_map=COLUMN_MAP)
    repository = CatalogRepository(source)
    service = CatalogService(repository, settings)
    service.reload()
    return service, source, settings


class CatalogServiceSearchTests(unittest.TestCase):
    def test_search_is_case_and_accent_insensitive(self):
        service, source, _ = build_service()
        calls_before = source.read_rows_calls

        service.search("coracao")
        results = service.apply_filters()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].codigo, "1001")
        self.assertEqual(source.read_rows_calls, calls_before, "pesquisa nao deveria reler a fonte")

    def test_empty_search_returns_everything(self):
        service, _, _ = build_service()
        service.search("")
        self.assertEqual(len(service.apply_filters()), 4)


class CatalogServiceMultiCodeSearchTests(unittest.TestCase):
    """Reaproveita core.text_normalize.parse_multiple_codes — o mesmo
    parser usado pela pesquisa Jueri (ui/product_search_dialog.py)."""

    def test_single_code_behaves_exactly_like_before(self):
        service, _, _ = build_service()
        service.search("1001")
        results = service.apply_filters()
        self.assertEqual([p.codigo for p in results], ["1001"])

    def test_comma_separated_codes_returns_all_matches(self):
        service, _, _ = build_service()
        service.search("1001,2001")
        results = service.apply_filters()
        self.assertEqual(sorted(p.codigo for p in results), ["1001", "2001"])

    def test_semicolon_separated_codes(self):
        service, _, _ = build_service()
        service.search("1001;2001")
        results = service.apply_filters()
        self.assertEqual(sorted(p.codigo for p in results), ["1001", "2001"])

    def test_newline_separated_codes(self):
        service, _, _ = build_service()
        service.search("1001\n2001")
        results = service.apply_filters()
        self.assertEqual(sorted(p.codigo for p in results), ["1001", "2001"])

    def test_space_separated_codes(self):
        service, _, _ = build_service()
        service.search("1001 2001")
        results = service.apply_filters()
        self.assertEqual(sorted(p.codigo for p in results), ["1001", "2001"])

    def test_three_codes_at_once(self):
        service, _, _ = build_service()
        service.search("1001,1002,2001")
        results = service.apply_filters()
        self.assertEqual(sorted(p.codigo for p in results), ["1001", "1002", "2001"])

    def test_repeated_code_in_a_valid_list_does_not_duplicate_results(self):
        service, _, _ = build_service()
        service.search("1001,2001,1001")
        results = service.apply_filters()
        self.assertEqual(sorted(p.codigo for p in results), ["1001", "2001"])

    def test_nonexistent_codes_are_ignored_keeping_the_rest(self):
        service, _, _ = build_service()
        service.search("1001,9999")
        results = service.apply_filters()
        self.assertEqual([p.codigo for p in results], ["1001"])

    def test_all_nonexistent_codes_returns_empty(self):
        service, _, _ = build_service()
        service.search("8888,9999")
        self.assertEqual(service.apply_filters(), [])

    def test_multi_word_description_search_is_not_treated_as_code_list(self):
        """Não deve alterar o comportamento da busca por descrição."""
        service, _, _ = build_service()
        service.search("de prata")
        results = service.apply_filters()
        self.assertEqual([p.codigo for p in results], ["1001"])

    def test_multi_code_search_combines_with_supplier_and_category_filters(self):
        service, _, _ = build_service()
        service.filter_supplier("DIP-15")
        service.search("1001,2001")  # 2001 e do outro fornecedor
        results = service.apply_filters()
        self.assertEqual([p.codigo for p in results], ["1001"])


class CatalogServiceFilterTests(unittest.TestCase):
    def test_filter_supplier(self):
        service, source, _ = build_service()
        calls_before = source.read_rows_calls

        service.filter_supplier("IW-13")
        results = service.apply_filters()

        self.assertEqual(len(results), 2)
        self.assertTrue(all(p.fornecedor == "IW-13" for p in results))
        self.assertEqual(source.read_rows_calls, calls_before)

    def test_filter_supplier_all_returns_everything(self):
        service, _, _ = build_service()
        service.filter_supplier(SUPPLIER_ALL)
        self.assertEqual(len(service.apply_filters()), 4)

    def test_filter_category_uses_display_category(self):
        service, source, _ = build_service()
        calls_before = source.read_rows_calls

        service.filter_category("Aneis")
        results = service.apply_filters()

        self.assertEqual(len(results), 2)
        self.assertTrue(all(p.display_category == "Aneis" for p in results))
        self.assertEqual(source.read_rows_calls, calls_before)

    def test_filter_supplier_and_category_and_search_combine(self):
        service, _, _ = build_service()
        service.filter_supplier("IW-13")
        service.filter_category("Aneis")
        service.search("zirconia")
        results = service.apply_filters()
        self.assertEqual([p.codigo for p in results], ["2002"])


class CatalogServiceSortTests(unittest.TestCase):
    def test_sort_by_codigo_descending(self):
        service, source, _ = build_service()
        calls_before = source.read_rows_calls

        service.sort_by("codigo", reverse=True)
        results = service.apply_filters()

        self.assertEqual([p.codigo for p in results], ["2002", "2001", "1002", "1001"])
        self.assertEqual(source.read_rows_calls, calls_before)

    def test_sort_by_preco_ascending(self):
        service, _, _ = build_service()
        service.sort_by("preco", reverse=False)
        results = service.apply_filters()
        self.assertEqual([p.preco for p in results], [39.9, 59.9, 89.9, 129.9])

    def test_sort_by_descricao_is_accent_and_case_insensitive(self):
        service, _, _ = build_service()
        service.sort_by("descricao")
        results = service.apply_filters()
        descriptions = [p.descricao for p in results]
        self.assertEqual(descriptions, sorted(descriptions, key=str.lower))

    def test_unknown_sort_field_is_ignored(self):
        service, _, _ = build_service()
        service.sort_by("campo_que_nao_existe")
        # nao deve levantar excecao, so nao ordena
        results = service.apply_filters()
        self.assertEqual(len(results), 4)

    def test_sort_by_numeracao_puts_non_numeric_empty_values_last(self):
        """1001 (16) e 2002 (18) tem numeracao; 1002 e 2001 nao tem."""
        service, _, _ = build_service()
        service.sort_by("numeracao", reverse=False)
        results = service.apply_filters()
        codes = [p.codigo for p in results]
        self.assertEqual(codes[:2], ["1001", "2002"])
        self.assertEqual(set(codes[2:]), {"1002", "2001"})

    def test_sort_by_numeracao_is_numeric_not_textual(self):
        """Regressão do bug corrigido: numeracao "8" tem que vir antes de
        "30" — a implementação anterior comparava como texto e colocava
        "8" depois de "30"."""
        source = FakeDataSource(
            {
                "DIP-15": [
                    {"CODIGO": "1001", "DESCRICAO": "A", "PRECO": 1.0, "CATEGORIA": "Aneis", "NUMERO": "30"},
                    {"CODIGO": "1002", "DESCRICAO": "B", "PRECO": 1.0, "CATEGORIA": "Aneis", "NUMERO": "8"},
                    {"CODIGO": "1003", "DESCRICAO": "C", "PRECO": 1.0, "CATEGORIA": "Aneis", "NUMERO": "17"},
                ],
            }
        )
        settings = CatalogSettings(selected_sheets=["DIP-15"], column_map=COLUMN_MAP)
        repository = CatalogRepository(source)
        service = CatalogService(repository, settings)
        service.reload()

        service.sort_by("numeracao", reverse=False)
        codes = [p.codigo for p in service.apply_filters()]

        self.assertEqual(codes, ["1002", "1003", "1001"])  # 8, 17, 30

    def test_sort_by_preco_empty_stays_last_regardless_of_direction(self):
        source = FakeDataSource(
            {
                "DIP-15": [
                    {"CODIGO": "1001", "DESCRICAO": "A", "PRECO": None, "CATEGORIA": "X", "NUMERO": ""},
                    {"CODIGO": "1002", "DESCRICAO": "B", "PRECO": 10.0, "CATEGORIA": "X", "NUMERO": ""},
                    {"CODIGO": "1003", "DESCRICAO": "C", "PRECO": 5.0, "CATEGORIA": "X", "NUMERO": ""},
                ],
            }
        )
        settings = CatalogSettings(selected_sheets=["DIP-15"], column_map=COLUMN_MAP)
        repository = CatalogRepository(source)
        service = CatalogService(repository, settings)
        service.reload()

        service.sort_by("preco", reverse=False)
        ascending = [p.codigo for p in service.apply_filters()]
        self.assertEqual(ascending, ["1003", "1002", "1001"])

        service.sort_by("preco", reverse=True)
        descending = [p.codigo for p in service.apply_filters()]
        self.assertEqual(descending, ["1002", "1003", "1001"], "vazio nao pode virar primeiro ao inverter")

    def test_sort_by_quantidade_is_numeric(self):
        """Quantidade não é campo de CatalogProduct — vem de
        attributes["default_quantity"] (coluna QTD), mas a coluna exibida
        na tabela precisa ser ordenável mesmo assim."""
        service, _, _ = build_service()
        service.sort_by("quantidade", reverse=False)
        results = service.apply_filters()
        codes = [p.codigo for p in results]
        # 2001 tem QTD=2, 1001 tem QTD=5 -> 2001 antes de 1001 ascendente
        self.assertLess(codes.index("2001"), codes.index("1001"))


class CatalogServiceStatisticsTests(unittest.TestCase):
    def test_get_statistics(self):
        service, source, settings = build_service()
        calls_before = source.read_rows_calls

        stats = service.get_statistics()

        self.assertEqual(stats.total_products, 4)
        self.assertEqual(stats.supplier_count, 2)
        self.assertEqual(stats.category_count, 3)  # Aneis, Brincos, Colares
        self.assertEqual(stats.last_reload, settings.last_reload)
        self.assertIsNotNone(stats.last_reload)
        self.assertEqual(source.read_rows_calls, calls_before)

    def test_get_statistics_independent_of_active_filters(self):
        service, _, _ = build_service()
        service.filter_supplier("IW-13")
        service.search("colar")
        stats = service.get_statistics()
        self.assertEqual(stats.total_products, 4, "estatisticas devem refletir o catalogo todo, nao o filtro atual")

    def test_get_suppliers_includes_todos_first(self):
        service, _, _ = build_service()
        self.assertEqual(service.get_suppliers(), [SUPPLIER_ALL, "DIP-15", "IW-13"])

    def test_get_categories_includes_todos_first(self):
        service, _, _ = build_service()
        self.assertEqual(service.get_categories(), [CATEGORY_ALL, "Aneis", "Brincos", "Colares"])


class CatalogServiceClearFiltersTests(unittest.TestCase):
    def test_clear_filters_resets_search_filter_and_sort(self):
        service, _, _ = build_service()
        service.search("anel")
        service.filter_supplier("DIP-15")
        service.filter_category("Aneis")
        service.sort_by("preco", reverse=True)
        self.assertEqual(len(service.apply_filters()), 1)

        service.clear_filters()
        results = service.apply_filters()
        self.assertEqual(len(results), 4)


class CatalogServiceReloadTests(unittest.TestCase):
    def test_reload_rereads_source_and_updates_last_reload(self):
        service, source, settings = build_service()
        calls_before = source.read_rows_calls
        self.assertIsNotNone(settings.last_reload)

        service.reload()

        self.assertEqual(source.read_rows_calls, calls_before + 1, "reload() deve reler a fonte de proposito")

    def test_reload_picks_up_new_data(self):
        service, source, _ = build_service()
        source.sheets_data["DIP-15"].append(
            {"CODIGO": "1003", "DESCRICAO": "Pulseira Prata", "PRECO": 49.9, "CATEGORIA": "Pulseiras", "NUMERO": ""}
        )
        service.reload()
        self.assertEqual(len(service.apply_filters()), 5)


class CatalogServiceCreatePrintItemTests(unittest.TestCase):
    """create_print_item() usa a quantidade padrão configurada na coluna
    QTD (guardada em product.attributes["default_quantity"] pelo
    Repository) para montar um PrintItem — CatalogProduct em si nunca tem
    quantidade."""

    def test_uses_default_quantity_from_configured_qtd_column(self):
        service, _, _ = build_service()
        product = next(p for p in service.repository.products if p.codigo == "1001")

        item = service.create_print_item(product)

        self.assertIs(item.product, product)
        self.assertEqual(item.quantity, 5)

    def test_falls_back_to_one_when_sheet_has_no_quantity(self):
        service, _, _ = build_service()
        product = next(p for p in service.repository.products if p.codigo == "1002")  # QTD=None na planilha

        item = service.create_print_item(product)

        self.assertEqual(item.quantity, 1)

    def test_invalid_quantity_in_sheet_falls_back_to_one(self):
        service, _, _ = build_service()
        product = next(p for p in service.repository.products if p.codigo == "2002")  # QTD="abc"

        item = service.create_print_item(product)

        self.assertEqual(item.quantity, 1)

    def test_created_print_item_does_not_add_quantity_to_product(self):
        service, _, _ = build_service()
        product = next(p for p in service.repository.products if p.codigo == "1001")
        service.create_print_item(product)
        self.assertFalse(hasattr(product, "quantidade"))


if __name__ == "__main__":
    unittest.main()
