"""Renderer visual da etiqueta do Santa Rubi Label Studio.

Este módulo concentra toda a responsabilidade de desenho da etiqueta para que
possa ser reutilizado em pré-visualização, impressão, PDF e PNG no futuro.
"""

from __future__ import annotations

from typing import Any

from PIL import Image, ImageDraw, ImageFont

from core.barcode import BarcodeGenerator

BLACK = "#000000"


class LabelRenderer:
    """Responsável por renderizar a etiqueta em um canvas Tkinter."""

    LABEL_WIDTH = 240
    LABEL_HEIGHT = 120

    def __init__(self, canvas: Any):
        self.canvas = canvas

    # SAFE_RIGHT=230/235 cortaram categoria/preço em duas rodadas seguidas —
    # 218 foi o último valor confirmado sem corte, então voltei a ele em vez
    # de insistir mais à direita. Para "jogar tudo mais para a direita" sem
    # arriscar a direita de novo, subi o SAFE_LEFT bem mais (havia folga
    # sobrando à esquerda na foto), estreitando a área em vez de deslocá-la.
    SAFE_LEFT = 45
    SAFE_RIGHT = 218  # último valor confirmado sem corte
    CENTER_X = (SAFE_LEFT + SAFE_RIGHT) // 2  # 131
    CENTER_CONTENT_WIDTH = SAFE_RIGHT - SAFE_LEFT  # 173

    RIGHT_EDGE = SAFE_RIGHT
    RIGHT_MAX_WIDTH = CENTER_CONTENT_WIDTH

    LEFT_EDGE = SAFE_LEFT

    # Barcode colado na borda superior, e altura reduzida (estava alto demais).
    BARCODE_TOP = 1
    BARCODE_HEIGHT = 38
    BARCODE_WIDTH = CENTER_CONTENT_WIDTH

    # Linhas recalculadas a partir do novo topo/altura do barcode.
    CODE_ROW_Y = 40
    CATEGORY_ROW_Y = 57
    DESCRIPTION_ROW_Y = 73
    LAST_ROW_Y = 88

    CODE_FONT_SIZE = 16
    CATEGORY_FONT_SIZE = 15
    DESCRIPTION_FONT_SIZE = 13
    NUMBER_FONT_SIZE = 13
    PRICE_FONT_SIZE = 18

    # Só negrito: em resolução térmica baixa, traços finos de fonte regular
    # se quebram ("falhado") no threshold do driver. Negrito sobrevive bem.
    FONT_PREFERENCES = (
        "DejaVuSans-Bold.ttf",
        "arialbd.ttf",
        "LiberationSans-Bold.ttf",
        "NotoSans-Bold.ttf",
    )

    def _load_font(self, size: int) -> Any:
        """Carrega a primeira fonte TrueType em negrito disponível."""
        for font_name in self.FONT_PREFERENCES:
            try:
                return ImageFont.truetype(font_name, size)
            except OSError:
                continue
        return ImageFont.load_default(size=size)

    def render_image(self, product: dict[str, Any]) -> Image.Image:
        """Gera a etiqueta 240x120: barcode grande colado no topo, código
        centralizado logo abaixo, categoria à direita, descrição centralizada
        e número (esquerda) + preço (direita) na última linha.
        """
        image = Image.new("RGB", (self.LABEL_WIDTH, self.LABEL_HEIGHT), "white")
        draw = ImageDraw.Draw(image)

        font_codigo = self._load_font(self.CODE_FONT_SIZE)
        font_categoria = self._load_font(self.CATEGORY_FONT_SIZE)
        font_descricao = self._load_font(self.DESCRIPTION_FONT_SIZE)
        font_numero = self._load_font(self.NUMBER_FONT_SIZE)
        font_preco = self._load_font(self.PRICE_FONT_SIZE)

        codigo = self._format_value(product.get("codigo"))
        categoria = self._format_value(product.get("categoria"))
        descricao = self._format_value(product.get("descricao"))
        numero = self._format_value(product.get("numero"))
        preco_texto = f"R$ {self._format_value(product.get('preco'))}"

        if codigo != "—":
            barcode_image = BarcodeGenerator(codigo).generate_image(
                width=self.BARCODE_WIDTH, height=self.BARCODE_HEIGHT, show_text=False
            )
            barcode_x = self.CENTER_X - self.BARCODE_WIDTH // 2
            image.paste(barcode_image, (barcode_x, self.BARCODE_TOP), barcode_image)
        else:
            self._draw_centered(draw, "BARCODE", font_codigo, self.BARCODE_TOP + 15, BLACK)

        codigo_linha = self._truncate_text(draw, codigo, font_codigo, self.CENTER_CONTENT_WIDTH)
        self._draw_centered(draw, codigo_linha, font_codigo, self.CODE_ROW_Y, BLACK)

        categoria_linha = self._truncate_text(draw, categoria, font_categoria, self.RIGHT_MAX_WIDTH)
        categoria_x = self.RIGHT_EDGE - draw.textlength(categoria_linha, font=font_categoria)
        draw.text((categoria_x, self.CATEGORY_ROW_Y), categoria_linha, font=font_categoria, fill=BLACK)

        descricao_linha = self._truncate_text(draw, descricao, font_descricao, self.CENTER_CONTENT_WIDTH)
        self._draw_centered(draw, descricao_linha, font_descricao, self.DESCRIPTION_ROW_Y, BLACK)

        if numero != "—":
            numero_linha = self._truncate_text(draw, numero, font_numero, self.RIGHT_EDGE - self.LEFT_EDGE)
            draw.text((self.LEFT_EDGE, self.LAST_ROW_Y), numero_linha, font=font_numero, fill=BLACK)

        preco_linha = self._truncate_text(draw, preco_texto, font_preco, self.RIGHT_MAX_WIDTH)
        preco_x = self.RIGHT_EDGE - draw.textlength(preco_linha, font=font_preco)
        draw.text((preco_x, self.LAST_ROW_Y), preco_linha, font=font_preco, fill=BLACK)

        # Threshold duro (sem anti-aliasing) para preto/branco puro: evita que
        # bordas cinzas dos textos sejam ditheradas de forma inconsistente
        # pelo driver da impressora térmica, causando o efeito "falhado".
        return image.convert("L").point(lambda p: 0 if p < 160 else 255).convert("RGB")

    def _draw_centered(self, draw: ImageDraw.ImageDraw, text: str, font: Any, y: int, fill: str) -> None:
        """Desenha uma linha de texto centralizada horizontalmente no canvas."""
        width = draw.textlength(text, font=font)
        draw.text((self.CENTER_X - width / 2, y), text, font=font, fill=fill)

    def _format_value(self, value: Any) -> str:
        """Formata valores para exibição na etiqueta."""
        if value is None:
            return "—"
        if isinstance(value, float):
            return f"{value:.2f}"
        return str(value)

    def _truncate_text(self, draw: ImageDraw.ImageDraw, text: str, font: Any, max_width: int) -> str:
        """Trunca o texto com reticências para caber em uma única linha de max_width pixels."""
        if draw.textlength(text, font=font) <= max_width:
            return text

        ellipsis = "..."
        truncated = text
        while truncated and draw.textlength(truncated + ellipsis, font=font) > max_width:
            truncated = truncated[:-1]

        return f"{truncated.rstrip()}{ellipsis}" if truncated else ellipsis
