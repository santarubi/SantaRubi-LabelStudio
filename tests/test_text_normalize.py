import unittest

from core.text_normalize import normalize_search_text


class NormalizeSearchTextTests(unittest.TestCase):
    def test_ignores_case(self):
        self.assertEqual(normalize_search_text("ANEL"), normalize_search_text("anel"))

    def test_ignores_accents(self):
        self.assertEqual(normalize_search_text("Coração"), "coracao")
        self.assertEqual(normalize_search_text("café"), "cafe")

    def test_handles_none(self):
        self.assertEqual(normalize_search_text(None), "")

    def test_strips_whitespace(self):
        self.assertEqual(normalize_search_text("  Anel  "), "anel")


if __name__ == "__main__":
    unittest.main()
