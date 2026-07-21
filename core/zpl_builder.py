"""Geração de comandos ZPL para impressão nativa da etiqueta.

Diferente do LabelRenderer (que desenha um bitmap para ser enviado via GDI),
este módulo monta o comando ZPL da etiqueta como texto e é enviado como dado
bruto ("RAW") direto para a impressora — sem passar pelo driver Windows, sem
DEVMODE, sem a margem de segurança que o driver GDI impõe. O firmware da
impressora desenha o código de barras, o texto e o posicionamento na
resolução nativa (203 dpi = 240x120 dots para a etiqueta de 30x15mm).

Todas as constantes físicas de layout vêm de core.print_layout — este
módulo não declara nenhum valor próprio, para nunca duplicar calibração.
"""

from __future__ import annotations

import math
from typing import Any

from core import print_layout
from core.label_data import LabelData

LABEL_WIDTH_DOTS = print_layout.LABEL_WIDTH_DOTS
LABEL_HEIGHT_DOTS = print_layout.LABEL_HEIGHT_DOTS

BOLD_CHAR_WIDTH_RATIO = print_layout.BOLD_CHAR_WIDTH_RATIO
REGULAR_CHAR_WIDTH_RATIO = print_layout.REGULAR_CHAR_WIDTH_RATIO
BOLD_FONT = print_layout.BOLD_FONT
REGULAR_FONT = print_layout.REGULAR_FONT


class ZplBuilder:
    """Monta o comando ZPL de uma etiqueta a partir dos dados do produto."""

    LEFT_MARGIN = print_layout.LEFT_MARGIN
    RIGHT_MARGIN = print_layout.RIGHT_MARGIN

    BARCODE_TOP = print_layout.BARCODE_TOP
    BARCODE_HEIGHT = print_layout.BARCODE_HEIGHT
    BARCODE_MODULE_WIDTH = print_layout.BARCODE_MODULE_WIDTH

    # Ajuste fino de alinhamento visual: desloca só o bloco código de barras +
    # código impresso abaixo dele, mantendo o alinhamento relativo entre os
    # dois. Não afeta os demais campos nem a largura calculada do símbolo.
    BARCODE_VISUAL_OFFSET_X = print_layout.BARCODE_VISUAL_OFFSET_X

    # Estrutura fixa de um símbolo Code128: cada caractere (start, dados,
    # checksum) ocupa 11 módulos; o stop ocupa 13 (11 + barra de terminação
    # de 2 módulos) — Zebra ZPL II Programming Guide, comando ^BC.
    CODE128_SYMBOL_MODULES = print_layout.CODE128_SYMBOL_MODULES
    CODE128_STOP_MODULES = print_layout.CODE128_STOP_MODULES

    # Código: centralizado em linha própria, logo abaixo do barcode.
    CODE_ROW_Y = print_layout.CODE_ROW_Y
    CODE_FONT_SIZE = print_layout.CODE_FONT_SIZE

    # Categoria: linha própria, abaixo do código, alinhada à direita.
    CATEGORY_ROW_Y = print_layout.CATEGORY_ROW_Y
    CATEGORY_FONT_SIZE = print_layout.CATEGORY_FONT_SIZE

    DESCRIPTION_ROW_Y = print_layout.DESCRIPTION_ROW_Y
    DESCRIPTION_FONT_SIZE = print_layout.DESCRIPTION_FONT_SIZE
    DESCRIPTION_MAX_CHARS = print_layout.DESCRIPTION_MAX_CHARS
    DESCRIPTION_RIGHT_MARGIN = print_layout.DESCRIPTION_RIGHT_MARGIN

    LAST_ROW_Y = print_layout.LAST_ROW_Y
    NUMBER_FONT_SIZE = print_layout.NUMBER_FONT_SIZE
    NUMBER_COLUMN_WIDTH = print_layout.NUMBER_COLUMN_WIDTH
    PRICE_FONT_SIZE = print_layout.PRICE_FONT_SIZE

    def _format_value(self, value: Any) -> str:
        """Formata valores para exibição na etiqueta."""
        if value is None:
            return ""
        if isinstance(value, float):
            return f"{value:.2f}"
        return str(value)

    def _escape(self, text: str) -> str:
        """Remove caracteres reservados do ZPL (^ e ~) do conteúdo do campo."""
        return text.replace("^", "").replace("~", "")

    def _barcode_width_dots(self, digit_count: int) -> int:
        """Calcula a largura real (em dots) do símbolo Code128 gerado com
        Start Code C explícito (>;): start(1 símbolo) + dados em pares —
        Subset C, 2 dígitos por símbolo — + checksum(1 símbolo) + stop.
        Não é uma estimativa: é a contagem exata de módulos da estrutura
        Code128 para esta string, multiplicada pela largura do módulo (^BY)."""
        data_symbols = math.ceil(digit_count / 2)
        total_modules = (
            self.CODE128_SYMBOL_MODULES  # start code C
            + data_symbols * self.CODE128_SYMBOL_MODULES  # dados (Subset C)
            + self.CODE128_SYMBOL_MODULES  # checksum (mod 103)
            + self.CODE128_STOP_MODULES  # stop + barra de terminação
        )
        return total_modules * self.BARCODE_MODULE_WIDTH

    def _truncate(self, text: str, field_width_dots: int, font_size: int, ratio: float) -> str:
        """Trunca o texto para caber no campo, evitando que a impressora
        quebre/sobreponha linhas quando o texto excede a largura do ^FB."""
        if not text:
            return text

        max_chars = max(1, int(field_width_dots / (font_size * ratio)))
        if len(text) <= max_chars:
            return text
        if max_chars <= 3:
            return text[:max_chars]
        return text[: max_chars - 3].rstrip() + "..."

    def _build_fields(self, label: LabelData, x_offset: int = 0) -> list[str]:
        """Monta só os campos (^FO/^BC/^FD/^FS) de uma etiqueta, deslocados
        horizontalmente por x_offset — usado tanto para uma etiqueta isolada
        quanto para várias etiquetas lado a lado num rolo de várias colunas."""
        codigo = self._escape(self._format_value(label.codigo))
        categoria = self._escape(self._format_value(label.categoria))
        descricao = self._escape(self._format_value(label.descricao))
        numero = self._escape(self._format_value(label.numero))
        preco = f"R$ {self._format_value(label.preco)}"

        left = x_offset + self.LEFT_MARGIN
        content_width = LABEL_WIDTH_DOTS - self.LEFT_MARGIN - self.RIGHT_MARGIN
        description_width = LABEL_WIDTH_DOTS - self.LEFT_MARGIN - self.DESCRIPTION_RIGHT_MARGIN
        price_width = content_width - self.NUMBER_COLUMN_WIDTH - 8
        price_x = left + self.NUMBER_COLUMN_WIDTH + 8

        codigo_linha = self._truncate(codigo, content_width, self.CODE_FONT_SIZE, BOLD_CHAR_WIDTH_RATIO)
        categoria_linha = self._truncate(
            categoria, content_width, self.CATEGORY_FONT_SIZE, REGULAR_CHAR_WIDTH_RATIO
        )
        descricao_linha = descricao[: self.DESCRIPTION_MAX_CHARS]
        numero_linha = self._truncate(
            numero, self.NUMBER_COLUMN_WIDTH, self.NUMBER_FONT_SIZE, REGULAR_CHAR_WIDTH_RATIO
        )
        preco_linha = self._truncate(preco, price_width, self.PRICE_FONT_SIZE, BOLD_CHAR_WIDTH_RATIO)

        lines: list[str] = []

        if codigo:
            barcode_width = self._barcode_width_dots(len(codigo))
            barcode_x = left + max(0, content_width - barcode_width) // 2 + self.BARCODE_VISUAL_OFFSET_X
            lines.append(f"^FO{barcode_x},{self.BARCODE_TOP}")
            lines.append(f"^BY{self.BARCODE_MODULE_WIDTH}")
            lines.append(f"^BCN,{self.BARCODE_HEIGHT},N,N,N")
            # Start Code C explícito (>;): os códigos da Santa Rubi são sempre
            # numéricos com 6 dígitos, então o Subset C compacta 2 dígitos por
            # símbolo em vez de 1 (Subset B, padrão do ^BC sem start code
            # informado — Zebra ZPL II Programming Guide, comando ^BC).
            lines.append(f"^FD>;{codigo}^FS")

        # Negrito: código do produto e preço (destaque). Sem negrito:
        # categoria, descrição e número.
        lines.append(
            f"^FO{left + self.BARCODE_VISUAL_OFFSET_X},{self.CODE_ROW_Y}^FB{content_width},1,0,C,0"
            f"^A{BOLD_FONT}N,{self.CODE_FONT_SIZE},{self.CODE_FONT_SIZE}^FD{codigo_linha}^FS"
        )

        lines.append(
            f"^FO{left},{self.CATEGORY_ROW_Y}^FB{content_width},1,0,R,0"
            f"^A{REGULAR_FONT}N,{self.CATEGORY_FONT_SIZE},{self.CATEGORY_FONT_SIZE}^FD{categoria_linha}^FS"
        )

        lines.append(
            f"^FO{left},{self.DESCRIPTION_ROW_Y}^FB{description_width},1,0,C,0"
            f"^A{REGULAR_FONT}N,{self.DESCRIPTION_FONT_SIZE},{self.DESCRIPTION_FONT_SIZE}^FD{descricao_linha}^FS"
        )

        if numero:
            lines.append(
                f"^FO{left},{self.LAST_ROW_Y}^FB{self.NUMBER_COLUMN_WIDTH},1,0,L,0"
                f"^A{REGULAR_FONT}N,{self.NUMBER_FONT_SIZE},{self.NUMBER_FONT_SIZE}^FD{numero_linha}^FS"
            )
        lines.append(
            f"^FO{price_x},{self.LAST_ROW_Y}^FB{price_width},1,0,R,0"
            f"^A{BOLD_FONT}N,{self.PRICE_FONT_SIZE},{self.PRICE_FONT_SIZE}^FD{preco_linha}^FS"
        )

        return lines

    @staticmethod
    def _to_label_data(product: dict[str, Any]) -> LabelData:
        """Ponte para quem ainda chama build() com um dict (ex.: impressão
        unitária/teste na aba "Impressão") — _build_fields() só entende
        LabelData; nenhum cálculo/posicionamento muda, só o tipo de entrada."""
        return LabelData(
            codigo=product.get("codigo"),
            descricao=product.get("descricao"),
            categoria=product.get("categoria"),
            numero=product.get("numero"),
            preco=product.get("preco"),
        )

    def build(self, product: dict[str, Any]) -> str:
        """Retorna o comando ZPL completo (^XA...^XZ) para uma única etiqueta."""
        lines = [
            "^XA",
            "^CI28",
            f"^PW{LABEL_WIDTH_DOTS}",
            f"^LL{LABEL_HEIGHT_DOTS}",
            *self._build_fields(self._to_label_data(product)),
            "^XZ",
        ]
        return "\n".join(lines)

    def build_row(
        self,
        products: list[LabelData],
        column_pitch: int = LABEL_WIDTH_DOTS,
        total_width: int | None = None,
    ) -> str:
        """Retorna o comando ZPL de 1 a N etiquetas lado a lado num único
        ^XA...^XZ, uma por coluna do rolo — para rolos com mais de uma
        etiqueta por linha (ex.: 3 colunas), em vez de repetir o job inteiro
        (o que faz a impressora repetir a mesma etiqueta em cada coluna).

        `total_width` permite manter a largura da linha fixa na largura
        física total do rolo (ex.: column_pitch * 3 colunas) mesmo quando
        `products` tem menos itens que o rolo comporta — as colunas sem
        produto correspondente simplesmente não recebem nenhum campo, e
        ficam em branco. Se omitido, a largura é `column_pitch * len(products)`
        (comportamento original, para quando a lista já preenche a linha)."""
        if total_width is None:
            total_width = column_pitch * len(products)

        lines = ["^XA", "^CI28", f"^PW{total_width}", f"^LL{LABEL_HEIGHT_DOTS}"]
        for index, product in enumerate(products):
            lines.extend(self._build_fields(product, x_offset=index * column_pitch))
        lines.append("^XZ")
        return "\n".join(lines)
