"""Exceções específicas da integração com a API do sistema Jueri."""

from __future__ import annotations

import json


class JueriError(Exception):
    """Erro base para qualquer falha relacionada à API Jueri."""

    def describe(self) -> str:
        """Mensagem amigável para exibir ao usuário. Sobrescrita em
        JueriAPIError, que tem corpo de resposta para extrair uma causa
        real em vez de apenas o texto genérico da exceção."""
        return str(self)


class JueriDisabledError(JueriError):
    """A integração com a API Jueri está desabilitada em config.json."""


class JueriAuthenticationError(JueriError):
    """Credenciais (cliente_sistema/token) ausentes ou inválidas."""


class JueriConnectionError(JueriError):
    """Falha de rede ao tentar alcançar a API Jueri."""


class JueriTimeoutError(JueriError):
    """A API Jueri não respondeu dentro do tempo limite configurado."""


class JueriAPIError(JueriError):
    """A API Jueri respondeu com um erro HTTP."""

    # A API roda atrás do Cloudflare. Quando o WAF bloqueia a requisição
    # (ex.: por User-Agent suspeito), a resposta não vem da Jueri — vem do
    # Cloudflare, com esse corpo em texto puro. Confirmado contra a API em
    # produção: ver app/api/client.py (DEFAULT_USER_AGENT).
    CLOUDFLARE_BLOCK_MARKER = "error code: 1010"

    def __init__(
        self,
        status_code: int,
        message: str,
        response_body: str | None = None,
        response_headers: str | None = None,
    ) -> None:
        super().__init__(f"[{status_code}] {message}")
        self.status_code = status_code
        self.message = message
        self.response_body = response_body
        self.response_headers = response_headers

    def describe(self) -> str:
        """Mensagem amigável baseada no corpo real da resposta — nunca
        infere o significado de um status HTTP sem evidência no corpo."""
        body = (self.response_body or "").strip()

        if self.CLOUDFLARE_BLOCK_MARKER in body.lower():
            return (
                "A requisição foi bloqueada pelo Cloudflare antes de chegar "
                "à API Jueri (error code: 1010)."
            )

        api_message = self._extract_api_message(body)
        if api_message:
            return api_message

        if body:
            truncated = body if len(body) <= 200 else body[:200] + "…"
            return f"Erro de comunicação com a API Jueri (HTTP {self.status_code}): {truncated}"

        return f"Erro de comunicação com a API Jueri (HTTP {self.status_code})."

    @staticmethod
    def _extract_api_message(body: str) -> str | None:
        if not body:
            return None
        try:
            parsed = json.loads(body)
        except ValueError:
            return None
        if isinstance(parsed, dict):
            for key in ("message", "error", "erro"):
                value = parsed.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        return None
