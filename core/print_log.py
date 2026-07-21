"""Log de trabalhos de impressão da Fila de Impressão (Catálogo Integrado).

Uma linha por trabalho concluído (sucesso ou falha) em data/print_log.txt:
horário, quantidade de produtos, quantidade total de etiquetas, tempo total
e resultado.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

DEFAULT_LOG_FILE = Path(__file__).resolve().parents[1] / "data" / "print_log.txt"


def log_print_job(
    product_count: int,
    total_labels: int,
    elapsed_seconds: float,
    result: str,
    log_file: Path = DEFAULT_LOG_FILE,
) -> None:
    """Acrescenta uma linha ao log. `log_file` é parametrizável para que os
    testes nunca escrevam no arquivo real do projeto."""
    log_file.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = (
        f"{timestamp} | produtos={product_count} | etiquetas={total_labels} | "
        f"tempo={elapsed_seconds:.2f}s | resultado={result}"
    )
    with log_file.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
