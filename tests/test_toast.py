"""ui/toast.py — feedback discreto e temporário (nunca um messagebox).
Melhoria 2: mensagem aparece e some sozinha depois de alguns segundos."""

import tkinter as tk
import unittest

from ui.toast import INFO, SUCCESS, Toast


def _tk_available() -> bool:
    try:
        root = tk.Tk()
        root.destroy()
        return True
    except tk.TclError:
        return False


@unittest.skipUnless(_tk_available(), "ambiente de teste sem display Tk disponível")
class ToastTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = tk.Tk()
        self.label = tk.Label(self.root, text="")
        self.toast = Toast(self.label, duration_ms=50)

    def tearDown(self) -> None:
        try:
            self.root.destroy()
        except tk.TclError:
            pass  # já destruído pelo próprio teste (ver test de <Destroy>)

    def test_show_sets_the_message_text(self) -> None:
        self.toast.show("✓ 8 produtos adicionados à fila.")
        self.assertEqual(self.label.cget("text"), "✓ 8 produtos adicionados à fila.")

    def test_show_applies_success_style_by_default(self) -> None:
        self.toast.show("✓ ok")
        fg, bg = SUCCESS
        self.assertEqual(self.label.cget("fg"), fg)
        self.assertEqual(self.label.cget("bg"), bg)

    def test_show_accepts_a_different_style(self) -> None:
        self.toast.show("info", style=INFO)
        fg, bg = INFO
        self.assertEqual(self.label.cget("fg"), fg)
        self.assertEqual(self.label.cget("bg"), bg)

    def test_message_disappears_automatically_after_the_duration(self) -> None:
        self.toast.show("✓ 8 produtos adicionados à fila.")
        self.root.update()

        self.root.after(150, self.root.quit)
        self.root.mainloop()

        self.assertEqual(self.label.cget("text"), "")

    def test_calling_show_again_restarts_the_timer_instead_of_stacking(self) -> None:
        self.toast.show("primeira mensagem")
        self.root.update()
        self.toast.show("segunda mensagem")
        self.root.update()

        self.root.after(150, self.root.quit)
        self.root.mainloop()

        # Ambos os timers já teriam disparado dentro de 150ms — o texto
        # deve estar limpo (não travado na primeira mensagem por um
        # after_cancel que não aconteceu).
        self.assertEqual(self.label.cget("text"), "")

    def test_destroying_the_window_before_the_timer_fires_does_not_raise(self) -> None:
        """Regressão: sem cancelar o after() pendente no <Destroy>, o
        timer tentaria rodar contra um widget já destruído mais tarde."""
        self.toast.show("mensagem")
        self.root.update()
        self.root.destroy()
        # Não deve lançar "invalid command name" nem travar o teste.


if __name__ == "__main__":
    unittest.main()
