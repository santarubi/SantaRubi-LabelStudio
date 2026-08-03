"""Cliente HTTP reutilizável para chamadas à API do sistema Jueri.

Usa apenas a biblioteca padrão (urllib) para evitar adicionar novas
dependências ao projeto sem aprovação prévia.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlencode

from .auth import JueriCredentials
from .exceptions import (
    JueriAPIError,
    JueriConnectionError,
    JueriDisabledError,
    JueriTimeoutError,
)

DEFAULT_TIMEOUT_SECONDS = 10.0

# A API Jueri roda atrás do Cloudflare, que bloqueia (HTTP 403, corpo
# "error code: 1010") o User-Agent padrão do urllib. Confirmado contra o
# ambiente de produção em 2026-07-23: a mesma requisição, só trocando o
# User-Agent, passa a responder 200 normalmente.
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
DEFAULT_ACCEPT = "application/json"


class JueriClient:
    def __init__(
        self,
        base_url: str,
        credentials: JueriCredentials,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.credentials = credentials
        self.timeout = timeout

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        query = f"?{urlencode(params)}" if params else ""
        return self._request("GET", f"{path}{query}")

    def post(self, path: str, payload: dict[str, Any] | None = None) -> Any:
        return self._request("POST", path, payload)

    def _build_headers(self) -> dict[str, str]:
        """Único local que monta os headers padrão de toda requisição."""
        headers = self.credentials.build_headers()
        headers["Content-Type"] = "application/json"
        headers["Accept"] = DEFAULT_ACCEPT
        headers["User-Agent"] = DEFAULT_USER_AGENT
        return headers

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        if not self.credentials.enabled:
            raise JueriDisabledError("A integração com a API Jueri está desabilitada.")

        url = f"{self.base_url}/{path.lstrip('/')}"
        headers = self._build_headers()
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(url, data=body, headers=headers, method=method)

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            response_body = exc.read().decode("utf-8", errors="replace")
            response_headers = str(exc.headers)
            raise JueriAPIError(
                exc.code, exc.reason, response_body=response_body, response_headers=response_headers
            ) from exc
        except TimeoutError as exc:
            raise JueriTimeoutError("Tempo limite excedido ao acessar a API Jueri.") from exc
        except urllib.error.URLError as exc:
            raise JueriConnectionError(f"Falha de conexão com a API Jueri: {exc.reason}") from exc
