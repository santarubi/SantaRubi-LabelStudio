import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from core.catalog_excel_source import ExcelCatalogSource, normalize_header


class NormalizeHeaderTests(unittest.TestCase):
    def test_ignores_case_extra_spaces_and_line_breaks(self):
        self.assertEqual(
            normalize_header("PREÇO DE\nVENDA FINAL"),
            normalize_header("preço   de venda    final"),
        )
        self.assertEqual(normalize_header("  Código  "), normalize_header("CÓDIGO"))

    def test_handles_none(self):
        self.assertEqual(normalize_header(None), "")


class ExcelCatalogSourceTests(unittest.TestCase):
    def _build_workbook(self, temp_dir: str) -> Path:
        file_path = Path(temp_dir) / "catalogo.xlsx"
        workbook = Workbook()

        sheet1 = workbook.active
        sheet1.title = "DIP-15"
        sheet1.append(["CÓDIGO SANTA RUBI", "DESCRIÇÃO PROD (SISTEMA)", "PREÇO DE VENDA FINAL", "CATEGORIA", "TAMANHO Nº"])
        sheet1.append(["1001", "Anel Prata", 59.9, "Aneis", "16"])
        sheet1.append(["1002", "Brinco Ouro", 89.9, "Brincos", None])
        sheet1.append([None, None, None, None, None])  # linha totalmente vazia, nao deve contar

        sheet2 = workbook.create_sheet("TESTES")
        sheet2.append(["CODIGO", "DESCRICAO"])
        sheet2.append(["9999", "Produto de teste"])

        workbook.save(file_path)
        return file_path

    def test_list_sheets(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = self._build_workbook(temp_dir)
            source = ExcelCatalogSource(file_path)
            self.assertEqual(source.list_sheets(), ["DIP-15", "TESTES"])

    def test_get_headers(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = self._build_workbook(temp_dir)
            source = ExcelCatalogSource(file_path)
            headers = source.get_headers(["DIP-15", "TESTES"])
            self.assertEqual(
                headers["DIP-15"],
                ["CÓDIGO SANTA RUBI", "DESCRIÇÃO PROD (SISTEMA)", "PREÇO DE VENDA FINAL", "CATEGORIA", "TAMANHO Nº"],
            )
            self.assertEqual(headers["TESTES"], ["CODIGO", "DESCRICAO"])

    def test_count_rows_ignores_header_and_blank_rows(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = self._build_workbook(temp_dir)
            source = ExcelCatalogSource(file_path)
            counts = source.count_rows(["DIP-15", "TESTES"])
            self.assertEqual(counts["DIP-15"], 2)
            self.assertEqual(counts["TESTES"], 1)

    def test_read_rows_returns_dicts_with_sheet_tag(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = self._build_workbook(temp_dir)
            source = ExcelCatalogSource(file_path)
            rows = source.read_rows(["DIP-15"])
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["CÓDIGO SANTA RUBI"], "1001")
            self.assertEqual(rows[0]["_sheet"], "DIP-15")

    def test_missing_file_raises(self):
        source = ExcelCatalogSource("arquivo_que_nao_existe.xlsx")
        with self.assertRaises(FileNotFoundError):
            source.list_sheets()


if __name__ == "__main__":
    unittest.main()
