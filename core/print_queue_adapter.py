"""PrintQueueAdapter — converte PrintQueue/PrintItem para o modelo tipado
(LabelData) que ZplBuilder.build_row() espera.

Responsabilidade única: adaptar o modelo de dados do Catálogo Integrado ao
formato de entrada do motor de impressão existente. Nenhuma regra de
impressão (agrupamento em colunas, largura do rolo, envio para a
impressora) vive aqui — isso é responsabilidade de quem monta o job de
impressão, usando build_row()/PrinterService diretamente.
"""

from __future__ import annotations

from core.label_data import LabelData
from core.print_queue import PrintQueue


class PrintQueueAdapter:
    """Converte PrintQueue -> lista de LabelData compatível com build_row()."""

    @staticmethod
    def to_label_data(queue: PrintQueue) -> list[LabelData]:
        """Expande cada PrintItem em N LabelData (um por etiqueta, N =
        item.quantity) no formato esperado por ZplBuilder.build_row()."""
        labels: list[LabelData] = []
        for item in queue.to_list():
            product = item.product
            label = LabelData(
                codigo=product.codigo,
                descricao=product.descricao,
                categoria=product.display_category,
                numero=product.numeracao,
                preco=product.preco,
            )
            labels.extend([label] * item.quantity)
        return labels
