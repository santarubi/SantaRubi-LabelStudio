"""Geração de código de barras Code128 para o Santa Rubi Label Studio.

Este módulo é responsável apenas pela criação da imagem do código de barras.
A lógica de layout continua no renderer.
"""

from __future__ import annotations

from PIL import Image
from barcode import Code128
from barcode.writer import ImageWriter, pt2mm

MM_PER_INCH = 25.4
BARCODE_DPI = 300
BARCODE_QUIET_ZONE_MM = 2.0
BARCODE_MARGIN_MM = 0.15  # margem interna mínima, para o barcode ficar colado na caixa pedida


class BarcodeGenerator:
    """Gera uma imagem de código de barras Code128 pronta para uso."""

    def __init__(self, value: str):
        self.value = str(value)

    def generate_image(self, width: int = 240, height: int = 60, show_text: bool = True) -> Image.Image:
        """Retorna uma imagem Pillow com o código de barras já gerado nativamente perto do tamanho pedido."""
        writer = ImageWriter(dpi=BARCODE_DPI)
        writer.margin_top = BARCODE_MARGIN_MM
        writer.margin_bottom = BARCODE_MARGIN_MM
        barcode = Code128(self.value, writer=writer)
        modules_per_line = len(barcode.build()[0])

        width_mm = width * MM_PER_INCH / BARCODE_DPI
        height_mm = height * MM_PER_INCH / BARCODE_DPI

        module_width = max((width_mm - 2 * BARCODE_QUIET_ZONE_MM) / modules_per_line, 0.05)

        text_height_mm = (pt2mm(writer.font_size) / 2 + writer.text_distance) if show_text else 0.0
        module_height = max(
            height_mm - writer.margin_top - writer.margin_bottom - text_height_mm, 1.0
        )

        image = barcode.render(
            {
                "module_width": module_width,
                "module_height": module_height,
                "quiet_zone": BARCODE_QUIET_ZONE_MM,
                "write_text": show_text,
            }
        )

        if not isinstance(image, Image.Image):
            image = Image.open(image)

        return image.convert("RGBA")
