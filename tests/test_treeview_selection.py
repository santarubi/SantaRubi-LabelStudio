import tkinter as tk
import unittest
from tkinter import ttk

from ui.treeview_selection import enable_drag_selection


def _tk_available() -> bool:
    try:
        root = tk.Tk()
        root.destroy()
        return True
    except tk.TclError:
        return False


@unittest.skipUnless(_tk_available(), "ambiente de teste sem display Tk disponível")
class EnableDragSelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = tk.Tk()
        self.root.geometry("300x300+0+0")
        self.tree = ttk.Treeview(self.root, columns=("value",), show="headings", selectmode="extended")
        self.tree.heading("value", text="Valor")
        for i in range(6):
            self.tree.insert("", "end", iid=str(i), values=(i,))
        self.tree.pack(fill="both", expand=True)
        enable_drag_selection(self.tree)
        self.root.update_idletasks()
        self.root.update()

    def tearDown(self) -> None:
        self.root.destroy()

    def _row_center(self, iid: str) -> tuple[int, int]:
        bbox = self.tree.bbox(iid)
        if not bbox:
            self.skipTest(f"linha {iid} sem geometria visível neste ambiente")
        x, y, width, height = bbox
        return x + width // 2, y + height // 2

    def _drag(self, from_iid: str, to_iid: str) -> None:
        x0, y0 = self._row_center(from_iid)
        x1, y1 = self._row_center(to_iid)
        self.tree.event_generate("<ButtonPress-1>", x=x0, y=y0)
        self.root.update()
        self.tree.event_generate("<B1-Motion>", x=x1, y=y1)
        self.root.update()
        self.tree.event_generate("<ButtonRelease-1>", x=x1, y=y1)
        self.root.update()

    def test_drag_downwards_selects_the_range(self):
        self._drag("0", "2")
        self.assertEqual(set(self.tree.selection()), {"0", "1", "2"})

    def test_drag_upwards_selects_the_range_regardless_of_direction(self):
        self._drag("3", "1")
        self.assertEqual(set(self.tree.selection()), {"1", "2", "3"})

    def test_plain_click_without_drag_selects_just_that_row(self):
        x, y = self._row_center("2")
        self.tree.event_generate("<ButtonPress-1>", x=x, y=y)
        self.root.update()
        self.tree.event_generate("<ButtonRelease-1>", x=x, y=y)
        self.root.update()
        self.assertEqual(self.tree.selection(), ("2",))

    def test_ctrl_click_adds_to_selection_without_being_broken_by_drag_bindings(self):
        self.tree.selection_set(["0"])
        self.root.update()
        x, y = self._row_center("3")
        self.tree.event_generate("<ButtonPress-1>", x=x, y=y, state=0x0004)  # Control
        self.root.update()
        self.tree.event_generate("<ButtonRelease-1>", x=x, y=y, state=0x0004)
        self.root.update()
        self.assertEqual(set(self.tree.selection()), {"0", "3"})

    def test_shift_click_selects_range_without_being_broken_by_drag_bindings(self):
        # Clique real (não selection_set programático) para estabelecer o
        # "anchor" nativo que o Shift+clique usa — igual ao que um usuário
        # faria de verdade.
        x1, y1 = self._row_center("1")
        self.tree.event_generate("<ButtonPress-1>", x=x1, y=y1)
        self.root.update()
        self.tree.event_generate("<ButtonRelease-1>", x=x1, y=y1)
        self.root.update()

        x4, y4 = self._row_center("4")
        self.tree.event_generate("<ButtonPress-1>", x=x4, y=y4, state=0x0001)  # Shift
        self.root.update()
        self.tree.event_generate("<ButtonRelease-1>", x=x4, y=y4, state=0x0001)
        self.root.update()
        self.assertEqual(set(self.tree.selection()), {"1", "2", "3", "4"})

    def test_new_drag_after_a_previous_one_starts_a_fresh_range(self):
        self._drag("0", "2")
        self._drag("4", "5")
        self.assertEqual(set(self.tree.selection()), {"4", "5"})

    def test_drag_below_viewport_scrolls_and_extends_selection(self):
        for i in range(6, 80):
            self.tree.insert("", "end", iid=str(i), values=(i,))
        self.root.geometry("300x160+0+0")
        self.root.update()

        x, y = self._row_center("0")
        self.tree.event_generate("<ButtonPress-1>", x=x, y=y)
        self.tree.event_generate("<B1-Motion>", x=x, y=self.tree.winfo_height() + 20)
        self.root.update()

        first_after_scroll = self.tree.yview()[0]
        for _ in range(8):
            self.root.after(55, self.root.quit)
            self.root.mainloop()

        self.tree.event_generate("<ButtonRelease-1>", x=x, y=self.tree.winfo_height() + 20)
        self.root.update()

        self.assertGreater(first_after_scroll, 0.0)
        self.assertGreater(len(self.tree.selection()), 6)


if __name__ == "__main__":
    unittest.main()
