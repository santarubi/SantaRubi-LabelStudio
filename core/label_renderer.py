"""Renderer visual da etiqueta do Santa Rubi Label Studio.

Este módulo concentra toda a responsabilidade de desenho da etiqueta para que
possa ser reutilizado em pré-visualização, impressão, PDF e PNG no futuro.
"""

from __future__ import annotations

from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageTk

from core.barcode import BarcodeGenerator


class LabelRenderer:
    """Responsável por renderizar a etiqueta em um canvas Tkinter."""

    def __init__(self, canvas: Any):
        self.canvas = canvas

    def render_image(self, product: dict[str, Any]) -> Image.Image:
        """Gera uma imagem Pillow da etiqueta com o mesmo layout visual da pré-visualização."""
        image = Image.new("RGBA", (300, 220), "white")
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default()
        draw.rectangle((10, 10, 289, 209), outline="#0f172a", width=2)
        draw.rectangle((30, 30, 269, 69), outline="#475569", width=1)

        codigo = self._format_value(product.get("codigo"))
        if codigo != "—":
            barcode_image = BarcodeGenerator(codigo).generate_image(width=180, height=38)
            image.paste(barcode_image, (60, 30), barcode_image)
        else:
            draw.text((110, 40), "BARCODE", font=font, fill="#334155")

        categoria = self._format_value(product.get("categoria"))
        descricao = self._format_value(product.get("descricao"))
        numero = self._format_value(product.get("numero"))
        preco = self._format_value(product.get("preco"))

        draw.text((110, 80), codigo, font=font, fill="#111827")
        draw.text((110, 100), categoria, font=font, fill="#334155")

        description_lines = self._wrap_text(descricao, 26)
        y_position = 124
        for line in description_lines:
            draw.text((50, y_position), line, font=font, fill="#0f172a")
            y_position += 12

        if numero != "—":
            draw.text((40, 165), numero, font=font, fill="#0f172a")

        draw.text((180, 165), f"R$ {preco}", font=font, fill="#0f172a")

        return image

    def draw_placeholder(self) -> None:
        """Desenha a pré-visualização vazia da etiqueta."""
        self.canvas.delete("all")
        self.canvas.create_rectangle(10, 10, 290, 210, outline="#cbd5e1", width=2)
        self.canvas.create_text(
            150,
            110,
            text="Pré-visualização da etiqueta",
            font=("Segoe UI", 10, "bold"),
            fill="#64748b",
        )

    def draw_label(self, product: dict[str, Any]) -> None:
        """Desenha a etiqueta com os dados do produto."""
        self.canvas.delete("all")
        self.canvas.create_rectangle(10, 10, 290, 210, outline="#0f172a", width=2)

        self.canvas.create_rectangle(30, 30, 270, 70, outline="#475569", width=1)

        codigo = self._format_value(product.get("codigo"))
        if codigo != "—":
            barcode_image = BarcodeGenerator(codigo).generate_image(width=180, height=38)
            photo = ImageTk.PhotoImage(barcode_image)
            self.canvas.image = photo
            self.canvas.create_image(150, 50, image=photo)
        else:
            self.canvas.create_text(150, 50, text="BARCODE", font=("Segoe UI", 10, "bold"), fill="#334155")
        categoria = self._format_value(product.get("categoria"))
        descricao = self._format_value(product.get("descricao"))
        numero = self._format_value(product.get("numero"))
        preco = self._format_value(product.get("preco"))

        self.canvas.create_text(150, 85, text=codigo, font=("Segoe UI", 10, "bold"), fill="#111827")
        self.canvas.create_text(150, 105, text=categoria, font=("Segoe UI", 9), fill="#334155")

        description_lines = self._wrap_text(descricao, 26)
        y_position = 126
        for line in description_lines:
            self.canvas.create_text(150, y_position, text=line, font=("Segoe UI", 8), fill="#0f172a")
            y_position += 12

        if numero != "—":
            self.canvas.create_text(90, 175, text=numero, font=("Segoe UI", 9, "bold"), fill="#0f172a")

        self.canvas.create_text(220, 175, text=f"R$ {preco}", font=("Segoe UI", 9, "bold"), fill="#0f172a")

    def _format_value(self, value: Any) -> str:
        """Formata valores para exibição na etiqueta."""
        if value is None:
            return "—"
        if isinstance(value, float):
            return f"{value:.2f}"
        return str(value)

    def _wrap_text(self, text: str, max_chars: int) -> list[str]:
        """Quebra o texto em várias linhas para caber no espaço da etiqueta."""
        words = text.split()
        lines: list[str] = []
        current_line = ""

        for word in words:
            if len(current_line) + len(word) + 1 <= max_chars:
                current_line = f"{current_line} {word}".strip()
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

        return lines or [text]
