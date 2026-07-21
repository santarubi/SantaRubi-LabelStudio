"""LabelData — uma única etiqueta pronta para o motor de impressão.

Modelo tipado que substitui o list[dict] antes usado entre
PrintQueueAdapter e ZplBuilder.build_row(): dá segurança de tipos e um
único lugar para crescer (código de barras, coleção, peso, fornecedor,
QR code, marca etc.) sem voltar a depender de chaves de dicionário soltas.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LabelData:
    codigo: str
    descricao: str
    categoria: str
    numero: str
    preco: float | None
