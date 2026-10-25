"""Resolução de nome de categoria/subcategoria da API Jueri.

O recurso "Produto" só traz fk_categoria_id/fk_subcategoria_id (IDs) — o
nome vem de um endpoint separado, carregado e cacheado em memória aqui.
Reaproveita o JueriClient já existente; nenhuma infraestrutura HTTP nova.

Endpoint: GET /api/v1/{cliente_sistema}/produto/categoria — retorna a
lista completa de categorias, cada uma com sua lista de subcategorias
aninhada (também com id + nome).
"""

from __future__ import annotations

from .client import JueriClient

CATEGORIES_PATH = "/api/v1/{cliente_sistema}/produto/categoria"


class CategoriesAPI:
    def __init__(self, client: JueriClient) -> None:
        self.client = client
        self._categoria_por_id: dict[int, str] | None = None
        self._subcategoria_por_id: dict[int, str] | None = None

    def _ensure_loaded(self) -> None:
        """Carrega e cacheia a lista de categorias na primeira chamada.
        Chamadas seguintes reutilizam o cache — nenhuma nova requisição."""
        if self._categoria_por_id is not None:
            return

        path = CATEGORIES_PATH.format(cliente_sistema=self.client.credentials.cliente_sistema)
        raw = self.client.get(path)

        categoria_por_id: dict[int, str] = {}
        subcategoria_por_id: dict[int, str] = {}
        for categoria in raw.get("data") or []:
            categoria_id = categoria.get("id")
            categoria_nome = categoria.get("nome")
            if categoria_id is not None and categoria_nome:
                categoria_por_id[categoria_id] = categoria_nome

            for subcategoria in categoria.get("subcategoria") or []:
                subcategoria_id = subcategoria.get("id")
                subcategoria_nome = subcategoria.get("nome")
                if subcategoria_id is not None and subcategoria_nome:
                    subcategoria_por_id[subcategoria_id] = subcategoria_nome

        self._categoria_por_id = categoria_por_id
        self._subcategoria_por_id = subcategoria_por_id

    @property
    def categoria_por_id(self) -> dict[int, str]:
        self._ensure_loaded()
        return self._categoria_por_id

    @property
    def subcategoria_por_id(self) -> dict[int, str]:
        self._ensure_loaded()
        return self._subcategoria_por_id

    def nome_categoria(self, categoria_id: int | None) -> str | None:
        if categoria_id is None:
            return None
        return self.categoria_por_id.get(categoria_id)

    def nome_subcategoria(self, subcategoria_id: int | None) -> str | None:
        if subcategoria_id is None:
            return None
        return self.subcategoria_por_id.get(subcategoria_id)
