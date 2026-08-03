"""core/queue_feedback.py — mensagem de feedback discreto exibida pelo
Toast (ui/toast.py) depois de uma adição à fila de impressão."""

import unittest

from core.queue_feedback import describe_queue_addition


class DescribeQueueAdditionTests(unittest.TestCase):
    def test_single_new_product(self) -> None:
        self.assertEqual(describe_queue_addition(added=1, updated=0), "✓ 1 produto adicionado à fila.")

    def test_multiple_new_products(self) -> None:
        self.assertEqual(describe_queue_addition(added=8, updated=0), "✓ 8 produtos adicionados à fila.")

    def test_single_existing_product_updated(self) -> None:
        self.assertEqual(
            describe_queue_addition(added=0, updated=1),
            "✓ Produto já existia na fila.\nQuantidade atualizada.",
        )

    def test_multiple_existing_products_updated(self) -> None:
        self.assertEqual(
            describe_queue_addition(added=0, updated=3),
            "✓ 3 produtos já existiam na fila.\nQuantidade atualizada.",
        )

    def test_mixed_new_and_updated(self) -> None:
        self.assertEqual(describe_queue_addition(added=5, updated=3), "✓ 5 novo(s) e 3 atualizado(s) na fila.")

    def test_nothing_added_returns_empty_string(self) -> None:
        self.assertEqual(describe_queue_addition(added=0, updated=0), "")


if __name__ == "__main__":
    unittest.main()
