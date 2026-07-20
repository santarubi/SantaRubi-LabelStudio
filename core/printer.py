"""Impressão da etiqueta para a impressora Windows.

Este módulo recebe a imagem já preparada pelo renderer e a envia para a
impressora selecionada pelo usuário. A lógica de layout da etiqueta continua
no renderer e não é redesenhada aqui.
"""

from __future__ import annotations

from typing import Any

try:
    import win32print
    import win32ui
    from PIL import Image, ImageWin
except ImportError:  # pragma: no cover - ambiente sem dependências Windows
    win32print = None
    win32ui = None
    Image = None
    ImageWin = None


class PrinterService:
    """Responsável por enviar uma imagem para a impressora Windows."""

    def __init__(self, printer_name: str | None = None):
        self.printer_name = printer_name

    def list_printers(self) -> list[str]:
        """Retorna a lista de impressoras instaladas no Windows."""
        if win32print is None:
            return []

        printers = []
        try:
            printers = [
                info[2]
                for info in win32print.EnumPrinters(
                    win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
                )
            ]
        except Exception:
            printers = []
        return printers

    def print_image(self, image: Any, copies: int = 1) -> None:
        """Envia uma imagem para a impressora selecionada."""
        if win32print is None or win32ui is None or Image is None or ImageWin is None:
            raise RuntimeError("Bibliotecas de impressão do Windows não estão disponíveis.")

        if not self.printer_name:
            raise RuntimeError("Nenhuma impressora foi selecionada.")

        if copies < 1:
            copies = 1

        image = image.convert("RGBA")
        image = image.resize((300, 220), Image.LANCZOS)

        hdc = win32ui.CreateDC()
        hdc.CreatePrinterDC(self.printer_name)
        hdc.StartDoc("Santa Rubi Label Studio")

        try:
            dib = ImageWin.Dib(image)
            for _ in range(copies):
                hdc.StartPage()
                dib.draw(hdc.GetHandleOutput(), (0, 0, image.width, image.height))
                hdc.EndPage()
        finally:
            hdc.EndDoc()
            hdc.DeleteDC()
