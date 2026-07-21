"""Impressão da etiqueta para a impressora Windows.

Este módulo envia o comando ZPL já montado pelo ZplBuilder direto para a
impressora ("RAW"), sem passar pelo driver GDI do Windows.
"""

from __future__ import annotations

try:
    import win32print
except ImportError:  # pragma: no cover - ambiente sem dependências Windows
    win32print = None


class PrinterService:
    """Responsável por enviar dados para a impressora Windows."""

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

    def get_default_printer(self) -> str | None:
        """Retorna o nome da impressora padrão configurada no Windows, se houver."""
        if win32print is None:
            return None

        try:
            return win32print.GetDefaultPrinter()
        except Exception:
            return None

    def print_raw(self, data: str, copies: int = 1) -> None:
        """Envia dados brutos (ex.: ZPL) direto para a impressora, sem GDI/DEVMODE."""
        if win32print is None:
            raise RuntimeError("Bibliotecas de impressão do Windows não estão disponíveis.")

        if not self.printer_name:
            raise RuntimeError("Nenhuma impressora foi selecionada.")

        if copies < 1:
            copies = 1

        payload = data.encode("utf-8")

        hprinter = win32print.OpenPrinter(self.printer_name)
        try:
            job_info = ("Santa Rubi Label Studio (RAW)", None, "RAW")
            win32print.StartDocPrinter(hprinter, 1, job_info)
            try:
                for _ in range(copies):
                    win32print.StartPagePrinter(hprinter)
                    win32print.WritePrinter(hprinter, payload)
                    win32print.EndPagePrinter(hprinter)
            finally:
                win32print.EndDocPrinter(hprinter)
        finally:
            win32print.ClosePrinter(hprinter)
