"""Log opcional de diagnóstico HTTP bruto para a integração com a API Jueri.

Desabilitado por padrão. Para reativar (ex.: suporte técnico investigando
um novo erro de comunicação), defina a variável de ambiente
JUERI_DEBUG_LOG=1 antes de abrir o aplicativo. Quando habilitado, grava em
%LOCALAPPDATA%/Santa Rubi Label Studio/jueri_debug.log a URL chamada (sem
token — o token nunca aparece na URL, só no header Authorization, que não é
logado), status HTTP, headers e corpo da resposta, e a exceção original.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from core.config import APP_DATA_DIR
from .exceptions import JueriAPIError

DEFAULT_DEBUG_LOG_FILE = APP_DATA_DIR / "jueri_debug.log"
DEBUG_LOG_ENV_VAR = "JUERI_DEBUG_LOG"


def is_debug_logging_enabled() -> bool:
    return os.environ.get(DEBUG_LOG_ENV_VAR, "").strip() == "1"


def log_jueri_api_error(
    method: str,
    url: str,
    exc: JueriAPIError,
    log_file: Path = DEFAULT_DEBUG_LOG_FILE,
) -> None:
    """Grava a resposta HTTP bruta de um JueriAPIError. Não faz nada se
    JUERI_DEBUG_LOG não estiver habilitado."""
    if not is_debug_logging_enabled():
        return

    log_file.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"===== {timestamp} =====",
        f"method={method}",
        f"url={url}",
        f"status_code={exc.status_code}",
        f"exception={exc.__class__.__name__}: {exc}",
        "response_headers:",
        exc.response_headers or "(indisponível)",
        "response_body:",
        exc.response_body or "(indisponível)",
        "",
    ]
    with log_file.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
