"""PrintItem — uma solicitação de impressão de um CatalogProduct.

Deliberadamente separado de CatalogProduct: o produto é uma entidade
permanente do catálogo (existe independente de qualquer intenção de
imprimir); PrintItem é uma solicitação de impressão — nasce só quando o
usuário decide imprimir algo, carrega sua própria quantidade (que pode vir
de um padrão da planilha, mas no futuro poderá ser editada livremente sem
que isso altere o produto em si) e é o que efetivamente alimenta o
pipeline de impressão (PrintQueue -> build_row() -> PrinterService),
tornando a impressão independente da origem dos dados do catálogo.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.catalog_product import CatalogProduct


def normalize_quantity(value: Any) -> int:
    """Normaliza uma quantidade de impressão: vazio ou inválido vira 1;
    valores decimais são truncados para inteiro; nunca menor que 1."""
    if value is None:
        return 1
    if isinstance(value, str) and value.strip() == "":
        return 1
    try:
        quantity = int(float(value))
    except (TypeError, ValueError):
        return 1
    return max(1, quantity)


@dataclass
class PrintItem:
    """Uma solicitação de impressão: um produto e quantas etiquetas dele
    devem ser impressas. A quantidade nunca é 0, negativa ou texto — é
    sempre normalizada para um inteiro >= 1 na criação."""

    product: CatalogProduct
    quantity: int = 1

    def __post_init__(self) -> None:
        self.quantity = normalize_quantity(self.quantity)

    def __eq__(self, other: object) -> bool:
        """Dois PrintItem são iguais quando referem-se ao mesmo código de
        produto — nunca por identidade de objeto."""
        if not isinstance(other, PrintItem):
            return NotImplemented
        return self.product.codigo == other.product.codigo
