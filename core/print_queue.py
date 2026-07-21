"""PrintQueue — fila de solicitações de impressão.

Coleção rica: toda manipulação da fila (adicionar, remover, consultar,
ajustar quantidade) acontece através dos métodos públicos desta classe — a
lista interna nunca é exposta diretamente, para que a interface nunca
precise manipular listas, índices ou objetos PrintItem por conta própria.
"""

from __future__ import annotations

from typing import Iterator

from core.catalog_product import CatalogProduct
from core.print_item import PrintItem, normalize_quantity


class PrintQueue:
    """Fila em memória de itens (produto + quantidade) a serem impressos.

    Dois itens são considerados o mesmo produto quando possuem o mesmo
    código (`codigo`) — nunca por identidade de objeto.
    """

    def __init__(self) -> None:
        self._items: list[PrintItem] = []

    def _index_of(self, product: CatalogProduct) -> int | None:
        for index, item in enumerate(self._items):
            if item.product.codigo == product.codigo:
                return index
        return None

    def add(self, product: CatalogProduct, quantity: int = 1) -> PrintItem:
        """Adiciona um novo item à fila e o retorna."""
        item = PrintItem(product=product, quantity=quantity)
        self._items.append(item)
        return item

    def remove(self, product: CatalogProduct) -> None:
        """Remove o item associado a este produto, se existir."""
        index = self._index_of(product)
        if index is not None:
            del self._items[index]

    def clear(self) -> None:
        """Esvazia a fila por completo."""
        self._items.clear()

    def items(self) -> list[PrintItem]:
        """Retorna uma cópia da lista de itens atualmente na fila."""
        return list(self._items)

    def count(self) -> int:
        """Quantidade de itens (linhas) na fila — não a soma de etiquetas."""
        return len(self._items)

    def total_labels(self) -> int:
        """Soma das quantidades de todos os itens — total de etiquetas a imprimir."""
        return sum(item.quantity for item in self._items)

    def is_empty(self) -> bool:
        return not self._items

    def contains(self, product: CatalogProduct) -> bool:
        """True caso já exista um item na fila para este produto."""
        return self._index_of(product) is not None

    def find(self, product: CatalogProduct) -> PrintItem | None:
        """Retorna o PrintItem correspondente ao produto, ou None."""
        index = self._index_of(product)
        return self._items[index] if index is not None else None

    def update_quantity(self, product: CatalogProduct, quantity: int) -> bool:
        """Atualiza a quantidade do item existente. Não cria itens novos:
        retorna False se o produto não estiver na fila, True se atualizou."""
        index = self._index_of(product)
        if index is None:
            return False
        self._items[index].quantity = normalize_quantity(quantity)
        return True

    def increment(self, product: CatalogProduct, amount: int = 1) -> PrintItem:
        """Aumenta a quantidade do item (criando-o se ainda não existir).
        Nunca permite quantidade menor que 1."""
        index = self._index_of(product)
        if index is None:
            return self.add(product, quantity=amount)
        item = self._items[index]
        item.quantity = normalize_quantity(item.quantity + amount)
        return item

    def decrement(self, product: CatalogProduct, amount: int = 1) -> PrintItem | None:
        """Reduz a quantidade do item, nunca abaixo de 1. Sem efeito caso o
        produto não esteja na fila."""
        index = self._index_of(product)
        if index is None:
            return None
        item = self._items[index]
        item.quantity = normalize_quantity(item.quantity - amount)
        return item

    def replace(self, items: list[PrintItem]) -> None:
        """Substitui completamente a fila pelos itens informados (útil para
        futuras importações)."""
        self._items = list(items)

    def to_list(self) -> list[PrintItem]:
        """Retorna uma cópia da lista de itens — nunca a lista interna."""
        return list(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[PrintItem]:
        return iter(list(self._items))

    def __contains__(self, product: CatalogProduct) -> bool:
        return self.contains(product)
