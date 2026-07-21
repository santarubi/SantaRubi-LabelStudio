"""Geração de comandos ZPL para impressão nativa da etiqueta.

Diferente do LabelRenderer (que desenha um bitmap para ser enviado via GDI),
este módulo monta o comando ZPL da etiqueta como texto e é enviado como dado
bruto ("RAW") direto para a impressora — sem passar pelo driver Windows, sem
DEVMODE, sem a margem de segurança que o driver GDI impõe. O firmware da
impressora desenha o código de barras, o texto e o posicionamento na
resolução nativa (203 dpi = 240x120 dots para a etiqueta de 30x15mm).
"""

from __future__ import annotations

import math
from typing import Any

LABEL_WIDTH_DOTS = 240
LABEL_HEIGHT_DOTS = 120

# Estimativa de largura média de caractere, como fração do parâmetro de
# largura pedido — usada só para truncar com segurança em Python, já que a
# impressora não faz "..." sozinha, e um campo que não cabe no ^FB (lines=1)
# fica sobreposto/ilegível em vez de simplesmente cortar.
# 0,6 ficou curto demais; 0,45 sobrepôs; 0,55 é o meio-termo comprovadamente
# seguro (validado em várias impressões).
BOLD_CHAR_WIDTH_RATIO = 0.55
REGULAR_CHAR_WIDTH_RATIO = 0.55

# Tentativa de usar a fonte D para tirar o negrito de categoria/descrição/
# número sobrepôs texto DUAS vezes seguidas, mesmo depois de reduzir bastante
# o tamanho pedido — a fonte D não escala de forma confiável nessa
# impressora. Revertido para a fonte 0 em tudo (estado validado antes desse
# pedido) em vez de arriscar mais uma etiqueta em outra tentativa às cegas.
BOLD_FONT = "0"
REGULAR_FONT = "0"


class ZplBuilder:
    """Monta o comando ZPL de uma etiqueta a partir dos dados do produto."""

    LEFT_MARGIN = 38
    RIGHT_MARGIN = 12

    BARCODE_TOP = 6
    BARCODE_HEIGHT = 30
    BARCODE_MODULE_WIDTH = 2

    # Ajuste fino de alinhamento visual: desloca só o bloco código de barras +
    # código impresso abaixo dele, mantendo o alinhamento relativo entre os
    # dois. Não afeta os demais campos nem a largura calculada do símbolo.
    BARCODE_VISUAL_OFFSET_X = 6

    # Estrutura fixa de um símbolo Code128: cada caractere (start, dados,
    # checksum) ocupa 11 módulos; o stop ocupa 13 (11 + barra de terminação
    # de 2 módulos) — Zebra ZPL II Programming Guide, comando ^BC.
    CODE128_SYMBOL_MODULES = 11
    CODE128_STOP_MODULES = 13

    # Código: centralizado em linha própria, logo abaixo do barcode.
    CODE_ROW_Y = 44
    CODE_FONT_SIZE = 20

    # Categoria: linha própria, abaixo do código, alinhada à direita.
    CATEGORY_ROW_Y = 66
    CATEGORY_FONT_SIZE = 13

    DESCRIPTION_ROW_Y = 81
    DESCRIPTION_FONT_SIZE = 15
    # Corte por quantidade de caracteres, sem cálculo de largura: a impressora
    # decide a quebra/ajuste real. Ajustar este valor conforme teste físico.
    DESCRIPTION_MAX_CHARS = 26
    # Margem direita própria da descrição, menor que RIGHT_MARGIN (12):
    # LEFT_MARGIN (38) é zona morta de hardware confirmada fisicamente e não
    # é reduzida aqui; a direita nunca teve essa confirmação, e a descrição
    # não compartilha linha com nenhum outro campo, então aproveita mais
    # espaço sem risco de invadir código/categoria/número/preço.
    DESCRIPTION_RIGHT_MARGIN = 4

    LAST_ROW_Y = 98
    NUMBER_FONT_SIZE = 13
    NUMBER_COLUMN_WIDTH = 55
    PRICE_FONT_SIZE = 18

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

    def _build_fields(self, product: dict[str, Any], x_offset: int = 0) -> list[str]:
        """Monta só os campos (^FO/^BC/^FD/^FS) de uma etiqueta, deslocados
        horizontalmente por x_offset — usado tanto para uma etiqueta isolada
        quanto para várias etiquetas lado a lado num rolo de várias colunas."""
        codigo = self._escape(self._format_value(product.get("codigo")))
        categoria = self._escape(self._format_value(product.get("categoria")))
        descricao = self._escape(self._format_value(product.get("descricao")))
        numero = self._escape(self._format_value(product.get("numero")))
        preco = f"R$ {self._format_value(product.get('preco'))}"

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

    def build(self, product: dict[str, Any]) -> str:
        """Retorna o comando ZPL completo (^XA...^XZ) para uma única etiqueta."""
        lines = [
            "^XA",
            "^CI28",
            f"^PW{LABEL_WIDTH_DOTS}",
            f"^LL{LABEL_HEIGHT_DOTS}",
            *self._build_fields(product),
            "^XZ",
        ]
        return "\n".join(lines)

    def build_row(
        self,
        products: list[dict[str, Any]],
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
