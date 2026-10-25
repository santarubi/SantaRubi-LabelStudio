"""Regressões visuais estruturais do Design System Santa Rubi."""

from __future__ import annotations

import unittest

from ui import design_system


class DesignSystemTests(unittest.TestCase):
    def test_official_palette_and_interface_font_are_centralized(self) -> None:
        self.assertEqual(design_system.PRIMARY, "#947F5E")
        self.assertEqual(design_system.BACKGROUND, "#F1EBD7")
        self.assertEqual(design_system.FONT_FAMILY, "Segoe UI")

    def test_interaction_tokens_cover_primary_and_destructive_states(self) -> None:
        self.assertTrue(design_system.PRIMARY_HOVER)
        self.assertTrue(design_system.PRIMARY_PRESSED)
        self.assertTrue(design_system.DESTRUCTIVE)
        self.assertTrue(design_system.DESTRUCTIVE_HOVER)
        self.assertTrue(design_system.DESTRUCTIVE_PRESSED)


if __name__ == "__main__":
    unittest.main()
