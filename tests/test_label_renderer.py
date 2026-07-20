import unittest

from core.label_renderer import LabelRenderer


class LabelRendererTests(unittest.TestCase):
    def test_render_image_returns_expected_size(self):
        renderer = LabelRenderer(canvas=None)
        product = {
            "codigo": "12345",
            "categoria": "Bebidas",
            "descricao": "Produto de teste",
            "numero": "10",
            "preco": 37.9,
        }

        image = renderer.render_image(product)

        self.assertEqual(image.size, (300, 220))


if __name__ == "__main__":
    unittest.main()
