"""Ponto de entrada do Santa Rubi Label Studio.

Este arquivo apenas inicializa a interface gráfica. Nenhuma lógica de
negócio deve ser adicionada aqui.
"""

import time
import tkinter as tk

from ui.branding import SplashScreen
from ui.main_window import MainWindow


def main():
    root = tk.Tk()
    root.withdraw()
    splash = SplashScreen(root)
    root.update()
    started_at = time.perf_counter()
    MainWindow(root)

    def show_main_window() -> None:
        splash.destroy()
        root.deiconify()

    remaining_ms = max(0, int(1600 - (time.perf_counter() - started_at) * 1000))
    root.after(remaining_ms, show_main_window)
    root.mainloop()


if __name__ == "__main__":
    main()
