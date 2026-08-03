"""Normalização de texto para comparação de pesquisa.

Diferente de `catalog_excel_source.normalize_header` (que ignora só caixa,
espaços e quebras de linha, preservando acentos, para localizar colunas),
esta função também remove acentuação — usada para pesquisa de produtos,
onde "cafe" deve encontrar "Café".

Também concentra parse_multiple_codes(): compartilhada entre
ui/product_search_dialog.py (pesquisa Jueri) e core/catalog_service.py
(Catálogo Integrado) — mora em core/ porque core/ nunca pode depender de
ui/, mas ambos podem depender de core/.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any


def normalize_search_text(value: Any) -> str:
    """Remove acentuação e caixa para comparação de pesquisa."""
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    return text.strip().lower()


_LIST_DELIMITERS = re.compile(r"[,;\n]+")


def _looks_like_code(token: str) -> bool:
    """Códigos (codigo_barras) da Santa Rubi são sempre numéricos, de 6
    dígitos (ex.: "181021") — nunca têm letra. Usado apenas para decidir
    se espaço é delimitador de lista (ver parse_multiple_codes); evita
    confundir uma busca de texto livre como "anel ouro" com uma lista de
    códigos."""
    return token.isdigit()


def parse_multiple_codes(text: str) -> list[str] | None:
    """Detecta se `text` é uma lista de códigos em vez de um único termo
    de busca livre.

    Vírgula, ponto e vírgula e quebra de linha são delimitadores
    inequívocos de lista. Espaço só conta como delimitador de lista
    quando TODOS os tokens resultantes parecem código — isso evita
    quebrar uma busca de texto livre por descrição com várias palavras
    (ex.: "anel ouro" continua sendo um único termo de busca).

    Retorna a lista de códigos, sem duplicados, na ordem informada — ou
    None se `text` deve ser tratado como um único termo de busca (inclui
    o caso de um único código, que se comporta exatamente como uma busca
    normal por texto).
    """
    text = text.strip()
    if not text:
        return None

    if _LIST_DELIMITERS.search(text):
        tokens = _LIST_DELIMITERS.split(text)
    else:
        tokens = text.split()
        if len(tokens) < 2 or not all(_looks_like_code(token) for token in tokens):
            return None

    codes: list[str] = []
    for token in tokens:
        code = token.strip()
        if code and code not in codes:
            codes.append(code)

    return codes if len(codes) > 1 else None
