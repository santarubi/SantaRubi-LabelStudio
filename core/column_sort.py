"""Ordenação genérica de colunas — reutilizada por qualquer tela com uma
lista de produtos (Pesquisa Jueri e Catálogo Integrado usam exatamente
esta implementação, cada uma só informando como extrair o valor de cada
coluna do seu próprio modelo).

Sem nenhuma dependência de Tkinter: opera sobre listas Python puras, então
é testável sem abrir nenhuma janela.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Callable, TypeVar

from core.text_normalize import normalize_search_text

T = TypeVar("T")


class SortDirection(Enum):
    ASCENDING = "ascending"
    DESCENDING = "descending"

    def toggled(self) -> "SortDirection":
        return SortDirection.DESCENDING if self is SortDirection.ASCENDING else SortDirection.ASCENDING


def _is_empty(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def _normalized(value: Any) -> Any:
    """Números e datas comparam pelo próprio valor (nunca como texto);
    strings comparam sem acento/caixa, igual à pesquisa."""
    if isinstance(value, str):
        return normalize_search_text(value)
    return value


def sort_items(items: list[T], key_func: Callable[[T], Any], direction: SortDirection) -> list[T]:
    """Ordena `items` por key_func(item), respeitando o tipo do valor
    (número como número, data como data, texto sem acento/caixa) — nunca
    ordena número como texto (ex.: 2 < 10, não "10" < "2").

    Campos vazios (`None` ou string em branco) ficam sempre no final,
    independentemente da direção — não fazem parte da ordenação.
    """
    reverse = direction is SortDirection.DESCENDING

    non_empty = [item for item in items if not _is_empty(key_func(item))]
    empty = [item for item in items if _is_empty(key_func(item))]

    try:
        non_empty.sort(key=lambda item: _normalized(key_func(item)), reverse=reverse)
    except TypeError:
        # Tipos diferentes na mesma coluna (raro) — cai para comparação
        # textual seguro em vez de deixar o sort() explodir.
        non_empty.sort(key=lambda item: normalize_search_text(key_func(item)), reverse=reverse)

    return non_empty + empty


class ColumnSorter:
    """Guarda qual coluna está ativa e em qual direção, alternando
    crescente/decrescente a cada clique repetido no mesmo cabeçalho (e
    reiniciando em crescente ao clicar num cabeçalho diferente) — a mesma
    instância/classe é usada por toda tela com colunas ordenáveis.
    """

    def __init__(self, key_funcs: dict[str, Callable[[Any], Any]] | None = None) -> None:
        self.key_funcs = key_funcs or {}
        self.active_column: str | None = None
        self.direction: SortDirection = SortDirection.ASCENDING

    def toggle(self, column: str) -> SortDirection:
        """Atualiza o estado para um clique no cabeçalho `column` e
        retorna a nova direção — usado por telas que guardam a lista em
        outro lugar (ex.: CatalogService) e só precisam saber campo+direção."""
        if self.active_column == column:
            self.direction = self.direction.toggled()
        else:
            self.active_column = column
            self.direction = SortDirection.ASCENDING
        return self.direction

    def sort(self, items: list[T], column: str) -> list[T]:
        """toggle() + sort_items() com o key_func registrado para
        `column` — usado por telas que mantêm a lista em memória e
        reordenam na hora (ex.: pesquisa Jueri)."""
        direction = self.toggle(column)
        key_func = self.key_funcs.get(column)
        if key_func is None:
            return items
        return sort_items(items, key_func, direction)

    def reapply(self, items: list[T]) -> list[T]:
        """Reaplica a ordenação atual (mesma coluna/direção, sem
        alternar) — usado quando a lista é recarregada (ex.: nova busca)
        e já havia uma ordenação ativa antes."""
        if self.active_column is None:
            return items
        key_func = self.key_funcs.get(self.active_column)
        if key_func is None:
            return items
        return sort_items(items, key_func, self.direction)


def numeric_or_text(value: Any) -> float | str | None:
    """Converte para número quando possível (ex.: "181021", "14"), mantém
    texto quando não é numérico — para colunas como código/numeração, que
    são majoritariamente numéricas mas guardadas como string."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return text
