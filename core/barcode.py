"""Geração de código de barras Code128 para o Santa Rubi Label Studio.

Este módulo é responsável apenas pela criação da imagem do código de barras.
A lógica de layout continua no renderer.
"""

from __future__ import annotations

from typing import Any

from PIL import Image
from barcode import Code128
from barcode.writer import ImageWriter


class BarcodeGenerator:
    """Gera uma imagem de código de barras Code128 pronta para uso."""

    def __init__(self, value: str):
        self.value = str(value)

    def generate_image(self, width: int = 240, height: int = 60) -> Image.Image:
        """Retorna uma imagem Pillow com o código de barras gerado."""
        barcode = Code128(self.value, writer=ImageWriter())
        image = barcode.render()

        if not isinstance(image, Image.Image):
            image = Image.open(image)

        image = image.convert("RGBA")

        if width and height:
            image = image.resize((width, height), Image.LANCZOS)

        return image
