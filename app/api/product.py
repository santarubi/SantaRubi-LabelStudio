"""Modelo do produto retornado pela API Jueri.

Campos e nomes são exatamente os documentados em
https://jueri.com.br/sis/docs/ para o recurso "Produto" (confirmado no
endpoint "Visualizar Produto", GET /api/v1/{cliente_sistema}/produto/{id}).

A listagem (GET .../produto) é assumida como o mesmo formato de recurso —
mas o exemplo de resposta da listagem na documentação oficial vem truncado,
então todo campo além de `id` é tratado como potencialmente ausente:
`from_api()` nunca lança exceção por causa de um campo faltando.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.catalog_product import CatalogProduct

from .categories import CategoriesAPI


@dataclass
class ProductPrice:
    """Um preço do produto por tipo (ex.: "Varejo"), a partir de tipo_preco[].

    `preco` vem de tipo_preco[].pivot.preco na resposta da API — apenas
    achatado aqui para facilitar o acesso; nenhum dado é inventado.
    """

    id: int | None
    nome: str | None
    preco: float | None

    @classmethod
    def from_api(cls, raw: dict[str, Any]) -> "ProductPrice":
        pivot = raw.get("pivot") or {}
        return cls(
            id=raw.get("id"),
            nome=raw.get("nome"),
            preco=pivot.get("preco"),
        )


@dataclass
class Product:
    id: int | None

    descricao: str | None = None
    descricao_completa: str | None = None
    referencia: str | None = None
    numero_peca: str | None = None
    codigo_barras: str | None = None
    cor: str | None = None
    localizacao: str | None = None
    observacao: str | None = None

    quantidade: int | None = None
    peso: float | None = None
    peso_loja: float | None = None
    largura: float | None = None
    altura: float | None = None
    profundidade: float | None = None
    milesimos_ouro: float | None = None

    custo_compra_bruto: float | None = None
    custo_banho_ouro: float | None = None
    custo_banho_rodio: float | None = None
    custo_banho_prata: float | None = None
    fcp: float | None = None

    numero_ncm: str | None = None
    cfop: str | None = None

    # Somente IDs — a API não retorna o nome da categoria/subcategoria, e
    # nenhum endpoint de resolução foi encontrado na documentação. Mantidos
    # no modelo por completude, mas não devem ser exibidos na interface.
    fk_categoria_id: int | None = None
    fk_subcategoria_id: int | None = None
    fk_status_id: int | None = None

    data_criacao: str | None = None
    data_ultima_alteracao: str | None = None

    tipo_preco: list[ProductPrice] = field(default_factory=list)

    @classmethod
    def from_api(cls, raw: dict[str, Any]) -> "Product":
        return cls(
            id=raw.get("id"),
            descricao=raw.get("descricao"),
            descricao_completa=raw.get("descricao_completa"),
            referencia=raw.get("referencia"),
            numero_peca=raw.get("numero_peca"),
            codigo_barras=raw.get("codigo_barras"),
            cor=raw.get("cor"),
            localizacao=raw.get("localizacao"),
            observacao=raw.get("observacao"),
            quantidade=raw.get("quantidade"),
            peso=raw.get("peso"),
            peso_loja=raw.get("peso_loja"),
            largura=raw.get("largura"),
            altura=raw.get("altura"),
            profundidade=raw.get("profundidade"),
            milesimos_ouro=raw.get("milesimos_ouro"),
            custo_compra_bruto=raw.get("custo_compra_bruto"),
            custo_banho_ouro=raw.get("custo_banho_ouro"),
            custo_banho_rodio=raw.get("custo_banho_rodio"),
            custo_banho_prata=raw.get("custo_banho_prata"),
            fcp=raw.get("fcp"),
            numero_ncm=raw.get("numero_ncm"),
            cfop=raw.get("cfop"),
            fk_categoria_id=raw.get("fk_categoria_id"),
            fk_subcategoria_id=raw.get("fk_subcategoria_id"),
            fk_status_id=raw.get("fk_status_id"),
            data_criacao=raw.get("data_criacao"),
            data_ultima_alteracao=raw.get("data_ultima_alteracao"),
            tipo_preco=[ProductPrice.from_api(item) for item in raw.get("tipo_preco") or []],
        )

    @property
    def preco_principal(self) -> float | None:
        """Preço do tipo "Varejo" (regra de negócio Santa Rubi).

        Não usa outro tipo de preço como alternativa: se não houver um
        ProductPrice com nome exatamente "Varejo", retorna None.
        """
        for price in self.tipo_preco:
            if price.nome == "Varejo":
                return price.preco
        return None

    def to_label_fields(self, categories: CategoriesAPI | None = None) -> dict[str, Any]:
        """Converte para o dict aceito por MainWindow._fill_quick_details()
        e ZplBuilder.build() — mesmo vocabulário do fluxo Excel (codigo,
        categoria, descricao, numero, preco, qtd).

        `codigo` vem de codigo_barras (é o valor que vira o código de
        barras impresso na etiqueta — `referencia` não é usado aqui, pois
        não há evidência de que seja um código de barras válido).

        `numero` vem de numero_peca: confirmado contra produtos reais da
        API — populado com um número pequeno (tamanho de aro) em produtos
        da subcategoria ANEL/ALIANÇA, e sempre null em brincos/pulseiras.

        `categoria` só é resolvida se um CategoriesAPI for passado (resolve
        fk_categoria_id -> nome via seu cache); sem ele, fica None em vez
        de expor o ID cru na interface.

        `qtd` vem de `quantidade` (estoque atual) — mesma chave que o
        fluxo Excel já usa como valor inicial de "Quantidade para
        imprimir"; o usuário pode alterá-la livremente na interface depois.
        """
        categoria = categories.nome_categoria(self.fk_categoria_id) if categories is not None else None
        return {
            "codigo": self.codigo_barras,
            "categoria": categoria,
            "descricao": self.descricao,
            "numero": self.numero_peca,
            "preco": self.preco_principal,
            "qtd": self.quantidade,
        }

    def to_catalog_product(self, categories: CategoriesAPI | None = None) -> CatalogProduct:
        """Converte para CatalogProduct — o mesmo tipo que CatalogService
        usa para alimentar a fila de impressão (PrintQueue/PrintItem) a
        partir do Excel. É assim que um produto vindo da API Jueri entra
        na exata mesma fila, sem nenhuma lógica de impressão nova: depois
        de convertido, ele é indistinguível de um produto do Excel para o
        resto do sistema (PrintQueue, PrintQueueAdapter, ZplBuilder).

        `attributes["default_quantity"]` recebe o estoque atual — é a
        mesma chave que CatalogService.create_print_item() já lê para
        semear PrintItem.quantity a partir da coluna QTD do Excel, então
        a "Quantidade para imprimir" nasce igual ao estoque sem precisar
        de nenhuma lógica de inicialização nova.
        """
        categoria = categories.nome_categoria(self.fk_categoria_id) if categories is not None else None

        return CatalogProduct(
            codigo=self.codigo_barras or "",
            descricao=self.descricao or "",
            preco=self.preco_principal,
            categoria=categoria or "",
            numeracao=self.numero_peca or "",
            fornecedor="Jueri",
            attributes={
                "default_quantity": self.quantidade,
                "quantidade_estoque": self.quantidade,
                "jueri_id": self.id,
                "origem": "jueri",
            },
        )
