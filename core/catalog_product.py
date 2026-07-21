"""Representação de um produto do Catálogo Integrado.

Independente da origem dos dados (Excel hoje; SQLite, API ou outra fonte
no futuro) — nenhum código de pesquisa, filtro ou interface deve depender
de dicionários espalhados; todo produto do catálogo é uma instância desta
classe.

CatalogProduct representa apenas informações permanentes do produto — ele
NÃO possui quantidade de impressão. Quantidade é uma propriedade de uma
*solicitação* de impressão (ver core/print_item.py), não do produto em si:
o mesmo produto pode ser impresso 1 vez hoje e 50 vezes amanhã, sem que
isso altere nada sobre o produto. A quantidade padrão vinda da planilha
(coluna QTD) fica temporariamente em `attributes["default_quantity"]`, só
para ser lida por `CatalogService.create_print_item()` — nunca é um campo
de primeira classe aqui.

Campos futuros não conhecidos hoje podem ser guardados em `attributes`, sem
precisar alterar esta classe nem quebrar código existente que já usa os
campos atuais (exemplos: peso, banho, coleção, marca, linha, fornecedor
original etc.).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.text_normalize import normalize_search_text


@dataclass
class CatalogProduct:
    """Um produto do catálogo, já normalizado a partir da fonte de dados."""

    codigo: str
    descricao: str
    preco: float | None
    categoria: str
    numeracao: str
    fornecedor: str  # origem = nome da aba de onde o produto veio
    attributes: dict[str, Any] = field(default_factory=dict)

    # Pré-computado uma única vez na criação (não a cada pesquisa), para que
    # filtrar milhares de produtos seja apenas comparação de substring.
    search_blob: str = field(init=False, default="", repr=False, compare=False)

    def __post_init__(self) -> None:
        parts = (self.codigo, self.descricao, self.categoria, self.fornecedor, self.numeracao)
        self.search_blob = " ".join(normalize_search_text(part) for part in parts)

    @property
    def display_category(self) -> str:
        """Categoria efetivamente exibida ao usuário.

        Hoje aponta para `categoria`; no futuro pode passar a usar
        subcategoria, linha, coleção etc. — bastando alterar esta
        propriedade. Toda a interface deve usar exclusivamente
        `display_category`, nunca `categoria` diretamente, para não
        precisar mudar em vários lugares quando isso acontecer.
        """
        return self.categoria
