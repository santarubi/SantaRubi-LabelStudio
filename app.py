"""Ponto de entrada do Santa Rubi Label Studio.

Este arquivo apenas inicializa a interface gráfica. Nenhuma lógica de
negócio deve ser adicionada aqui.
"""

import tkinter as tk

from ui.main_window import MainWindow


def main():
    root = tk.Tk()
    MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
