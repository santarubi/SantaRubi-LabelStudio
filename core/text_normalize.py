"""Normalização de texto para comparação de pesquisa.

Diferente de `catalog_excel_source.normalize_header` (que ignora só caixa,
espaços e quebras de linha, preservando acentos, para localizar colunas),
esta função também remove acentuação — usada para pesquisa de produtos,
onde "cafe" deve encontrar "Café".
"""

from __future__ import annotations

import unicodedata
from typing import Any


def normalize_search_text(value: Any) -> str:
    """Remove acentuação e caixa para comparação de pesquisa."""
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    return text.strip().lower()
