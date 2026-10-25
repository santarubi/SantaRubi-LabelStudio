import unittest

from core.text_normalize import parse_multiple_codes


class ParseMultipleCodesTests(unittest.TestCase):
    def test_single_code_returns_none(self):
        """Comportamento atual preservado: um único código é tratado como
        termo de busca único, não como lista."""
        self.assertIsNone(parse_multiple_codes("181021"))

    def test_single_free_text_word_returns_none(self):
        self.assertIsNone(parse_multiple_codes("anel"))

    def test_multi_word_free_text_description_returns_none(self):
        """Busca de descrição com várias palavras não deve ser confundida
        com uma lista de códigos separados por espaço."""
        self.assertIsNone(parse_multiple_codes("anel ouro"))
        self.assertIsNone(parse_multiple_codes("colar prata 925"))

    def test_empty_string_returns_none(self):
        self.assertIsNone(parse_multiple_codes(""))
        self.assertIsNone(parse_multiple_codes("   "))

    def test_comma_separated_codes(self):
        self.assertEqual(
            parse_multiple_codes("181021,181050,181110,181330"),
            ["181021", "181050", "181110", "181330"],
        )

    def test_comma_separated_codes_with_spaces(self):
        self.assertEqual(
            parse_multiple_codes("181021, 181050, 181110"),
            ["181021", "181050", "181110"],
        )

    def test_newline_separated_codes(self):
        self.assertEqual(
            parse_multiple_codes("181021\n181050\n181110"),
            ["181021", "181050", "181110"],
        )

    def test_semicolon_separated_codes(self):
        self.assertEqual(
            parse_multiple_codes("181021;181050;181110"),
            ["181021", "181050", "181110"],
        )

    def test_space_separated_codes(self):
        self.assertEqual(
            parse_multiple_codes("181021 181050 181110"),
            ["181021", "181050", "181110"],
        )

    def test_space_separated_tokens_with_letters_are_not_treated_as_code_list(self):
        """codigo_barras é sempre numérico (6 dígitos) — tokens com letra
        separados por espaço não são reconhecidos como lista de códigos
        (evita falso positivo com texto livre)."""
        self.assertIsNone(parse_multiple_codes("10001A 10051C"))

    def test_duplicated_codes_are_removed_preserving_order(self):
        self.assertEqual(
            parse_multiple_codes("181021,181050,181021,181110,181050"),
            ["181021", "181050", "181110"],
        )

    def test_mixed_delimiters(self):
        self.assertEqual(
            parse_multiple_codes("181021,181050;181110\n181330"),
            ["181021", "181050", "181110", "181330"],
        )

    def test_trailing_comma_with_single_code_returns_none(self):
        """Depois de remover vazios, sobra só 1 código — trata como termo
        único (não uma lista de 1 item)."""
        self.assertIsNone(parse_multiple_codes("181021,"))

    def test_duplicated_single_code_returns_none(self):
        """Mesmo código repetido continua sendo, na prática, um único
        código — não deve virar uma "lista de 1"."""
        self.assertIsNone(parse_multiple_codes("181021,181021"))


if __name__ == "__main__":
    unittest.main()
