"""Mensagem de feedback discreto ao adicionar produtos à fila de impressão.

Pura formatação de texto — não depende de PrintQueue nem de nenhum widget:
quem chama já sabe quantos itens eram novos e quantos já existiam (a
diferenciação é feita com PrintQueue.contains() antes de cada adição).
"""

from __future__ import annotations


def describe_queue_addition(added: int, updated: int) -> str:
    """Monta a mensagem exibida pelo Toast (ui/toast.py) depois de uma
    adição à fila. Nunca lançada como MessageBox — só texto para um
    rótulo temporário."""
    if added and not updated:
        plural = "s" if added != 1 else ""
        return f"✓ {added} produto{plural} adicionado{plural} à fila."

    if updated and not added:
        if updated == 1:
            return "✓ Produto já existia na fila.\nQuantidade atualizada."
        return f"✓ {updated} produtos já existiam na fila.\nQuantidade atualizada."

    if added and updated:
        return f"✓ {added} novo(s) e {updated} atualizado(s) na fila."

    return ""
