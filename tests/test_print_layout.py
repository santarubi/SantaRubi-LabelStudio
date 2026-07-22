"""Garante que core.print_layout é a única fonte de constantes físicas de
layout: ZplBuilder e as duas telas que montam trabalhos de impressão em
lote (ui/main_window.py e ui/catalog_tab.py) devem importar os mesmos
valores de lá, nunca redeclará-los."""

import unittest

import ui.catalog_tab as catalog_tab
import ui.main_window as main_window
from core import print_layout
from core.zpl_builder import ZplBuilder

EXPECTED_VALUES = {
    "LABEL_WIDTH_DOTS": 240,
    "LABEL_HEIGHT_DOTS": 120,
    "BOLD_CHAR_WIDTH_RATIO": 0.55,
    "REGULAR_CHAR_WIDTH_RATIO": 0.55,
    "BOLD_FONT": "0",
    "REGULAR_FONT": "0",
    "LEFT_MARGIN": 38,
    "RIGHT_MARGIN": 12,
    "BARCODE_TOP": 6,
    "BARCODE_HEIGHT": 30,
    "BARCODE_MODULE_WIDTH": 2,
    "BARCODE_VISUAL_OFFSET_X": 6,
    "CODE128_SYMBOL_MODULES": 11,
    "CODE128_STOP_MODULES": 13,
    "CODE_ROW_Y": 44,
    "CODE_FONT_SIZE": 20,
    "CATEGORY_ROW_Y": 66,
    "CATEGORY_FONT_SIZE": 13,
    "DESCRIPTION_ROW_Y": 81,
    "DESCRIPTION_FONT_SIZE": 15,
    "DESCRIPTION_MAX_CHARS": 26,
    "DESCRIPTION_RIGHT_MARGIN": 4,
    "LAST_ROW_Y": 98,
    "NUMBER_FONT_SIZE": 16,
    "NUMBER_COLUMN_WIDTH": 55,
    "PRICE_FONT_SIZE": 18,
    "BATCH_ROW_COLUMNS": 3,
    "BATCH_COLUMN_PITCH": 264,
}


class PrintLayoutValuesTests(unittest.TestCase):
    def test_all_expected_constants_exist_with_unchanged_values(self):
        for name, expected_value in EXPECTED_VALUES.items():
            with self.subTest(constant=name):
                self.assertTrue(hasattr(print_layout, name), f"core.print_layout deveria ter {name}")
                self.assertEqual(getattr(print_layout, name), expected_value)


class ZplBuilderReusesPrintLayoutTests(unittest.TestCase):
    """ZplBuilder não deve ter nenhum valor próprio: seus atributos de
    classe são o mesmo objeto/valor de core.print_layout."""

    CLASS_ATTRIBUTES = [
        "LEFT_MARGIN", "RIGHT_MARGIN", "BARCODE_TOP", "BARCODE_HEIGHT", "BARCODE_MODULE_WIDTH",
        "BARCODE_VISUAL_OFFSET_X", "CODE128_SYMBOL_MODULES", "CODE128_STOP_MODULES",
        "CODE_ROW_Y", "CODE_FONT_SIZE", "CATEGORY_ROW_Y", "CATEGORY_FONT_SIZE",
        "DESCRIPTION_ROW_Y", "DESCRIPTION_FONT_SIZE", "DESCRIPTION_MAX_CHARS",
        "DESCRIPTION_RIGHT_MARGIN", "LAST_ROW_Y", "NUMBER_FONT_SIZE", "NUMBER_COLUMN_WIDTH",
        "PRICE_FONT_SIZE",
    ]

    def test_class_attributes_match_print_layout(self):
        for name in self.CLASS_ATTRIBUTES:
            with self.subTest(constant=name):
                self.assertEqual(getattr(ZplBuilder, name), getattr(print_layout, name))

    def test_module_level_constants_match_print_layout(self):
        import core.zpl_builder as zpl_builder_module

        for name in ["LABEL_WIDTH_DOTS", "LABEL_HEIGHT_DOTS", "BOLD_CHAR_WIDTH_RATIO",
                     "REGULAR_CHAR_WIDTH_RATIO", "BOLD_FONT", "REGULAR_FONT"]:
            with self.subTest(constant=name):
                self.assertEqual(getattr(zpl_builder_module, name), getattr(print_layout, name))


class NoDuplicatedBatchConstantsTests(unittest.TestCase):
    """ui/main_window.py e ui/catalog_tab.py importam BATCH_ROW_COLUMNS/
    BATCH_COLUMN_PITCH de core.print_layout — não redeclaram o valor."""

    def test_main_window_imports_batch_constants_from_print_layout(self):
        self.assertIs(main_window.BATCH_ROW_COLUMNS, print_layout.BATCH_ROW_COLUMNS)
        self.assertIs(main_window.BATCH_COLUMN_PITCH, print_layout.BATCH_COLUMN_PITCH)

    def test_catalog_tab_imports_batch_constants_from_print_layout(self):
        self.assertIs(catalog_tab.BATCH_ROW_COLUMNS, print_layout.BATCH_ROW_COLUMNS)
        self.assertIs(catalog_tab.BATCH_COLUMN_PITCH, print_layout.BATCH_COLUMN_PITCH)

    def test_print_layout_module_source_has_the_only_literal_264_pitch_assignment(self):
        """Confere que so' core/print_layout.py de fato ATRIBUI o literal
        264 a uma constante — os demais módulos apenas importam o nome."""
        import ast
        import inspect

        for module in (main_window, catalog_tab):
            source = inspect.getsource(module)
            tree = ast.parse(source)
            literal_assignments = [
                node for node in ast.walk(tree)
                if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == "BATCH_COLUMN_PITCH" for target in node.targets)
            ]
            self.assertEqual(
                literal_assignments, [],
                f"{module.__name__} não deveria atribuir BATCH_COLUMN_PITCH diretamente, só importar",
            )


if __name__ == "__main__":
    unittest.main()
