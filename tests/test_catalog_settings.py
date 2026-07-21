import unittest

from core.catalog_settings import CATALOG_FIELD_LABELS, CATALOG_FIELDS, CatalogSettings


class CatalogSettingsTests(unittest.TestCase):
    def test_quantidade_is_a_registered_catalog_field(self):
        self.assertIn("quantidade", CATALOG_FIELDS)
        self.assertEqual(CATALOG_FIELD_LABELS["quantidade"], "Quantidade")

    def test_quantidade_mapping_persists_in_config_json(self):
        settings = CatalogSettings(
            file_path="C:\\Santa Rubi\\Cadastro Geral.xlsx",
            selected_sheets=["DIP-15"],
            column_map={
                "codigo": "CÓDIGO SANTA RUBI",
                "descricao": "DESCRIÇÃO PROD (SISTEMA)",
                "preco": "PREÇO DE VENDA FINAL",
                "categoria": "CATEGORIA",
                "numeracao": "TAMANHO Nº",
                "quantidade": "QTD",
            },
        )

        config: dict = {}
        settings.save_to(config)

        self.assertEqual(config["catalog_integrado"]["column_map"]["quantidade"], "QTD")

        reloaded = CatalogSettings.from_config(config)
        self.assertEqual(reloaded.column_map["quantidade"], "QTD")

    def test_from_config_defaults_when_missing(self):
        settings = CatalogSettings.from_config({})
        self.assertEqual(settings.file_path, "")
        self.assertEqual(settings.selected_sheets, [])
        self.assertEqual(settings.column_map, {})
        self.assertEqual(settings.version, 1)
        self.assertIsNone(settings.last_reload)

    def test_save_and_reload_round_trip(self):
        settings = CatalogSettings(
            file_path="C:\\Santa Rubi\\Cadastro Geral.xlsx",
            selected_sheets=["DIP-15", "IW-13"],
            column_map={"codigo": "CÓDIGO SANTA RUBI", "preco": "PREÇO DE VENDA FINAL"},
            version=1,
            last_reload="2026-07-21 14:35",
        )

        config: dict = {}
        settings.save_to(config)

        reloaded = CatalogSettings.from_config(config)
        self.assertEqual(reloaded.file_path, settings.file_path)
        self.assertEqual(reloaded.selected_sheets, settings.selected_sheets)
        self.assertEqual(reloaded.column_map, settings.column_map)
        self.assertEqual(reloaded.version, 1)
        self.assertEqual(reloaded.last_reload, "2026-07-21 14:35")

    def test_last_reload_persists_across_reload_cycles(self):
        config: dict = {}
        settings = CatalogSettings(file_path="a.xlsx")
        settings.save_to(config)
        self.assertIsNone(CatalogSettings.from_config(config).last_reload)

        settings.last_reload = "2026-07-21 14:35"
        settings.save_to(config)
        self.assertEqual(CatalogSettings.from_config(config).last_reload, "2026-07-21 14:35")

    def test_save_does_not_affect_other_config_keys(self):
        config = {"last_printer": "ELGIN L42 PRO FULL"}
        settings = CatalogSettings(file_path="arquivo.xlsx", selected_sheets=["A"], column_map={})
        settings.save_to(config)

        self.assertEqual(config["last_printer"], "ELGIN L42 PRO FULL")
        self.assertIn("catalog_integrado", config)

    def test_configuration_expanded_defaults_to_true(self):
        settings = CatalogSettings.from_config({})
        self.assertTrue(settings.configuration_expanded)

    def test_configuration_expanded_persists_when_collapsed(self):
        config: dict = {}
        settings = CatalogSettings(file_path="a.xlsx", configuration_expanded=False)
        settings.save_to(config)

        self.assertEqual(config["catalog_integrado"]["configuration_expanded"], False)
        self.assertFalse(CatalogSettings.from_config(config).configuration_expanded)

    def test_configuration_expanded_persists_when_expanded(self):
        config: dict = {}
        settings = CatalogSettings(file_path="a.xlsx", configuration_expanded=True)
        settings.save_to(config)
        self.assertTrue(CatalogSettings.from_config(config).configuration_expanded)

    def test_toggling_configuration_expanded_round_trips(self):
        config: dict = {}
        settings = CatalogSettings(file_path="a.xlsx")
        settings.save_to(config)
        self.assertTrue(CatalogSettings.from_config(config).configuration_expanded)

        settings.configuration_expanded = False
        settings.save_to(config)
        self.assertFalse(CatalogSettings.from_config(config).configuration_expanded)


if __name__ == "__main__":
    unittest.main()
