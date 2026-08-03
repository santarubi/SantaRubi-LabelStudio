"""Validação de conectividade com a API Jueri.

Reaproveita JueriClient/JueriCredentials já existentes — nenhum cliente
HTTP ou mecanismo de autenticação novo é criado aqui.

A documentação oficial (https://jueri.com.br/sis/docs/, coleção Postman em
https://jueri.com.br/sis/docs/collection.json) não lista um endpoint
dedicado a teste de autenticação. Por isso usamos a listagem mais simples
que exige token válido: GET /api/v1/{cliente_sistema}/revendedor/nivel.
"""

from __future__ import annotations

from dataclasses import dataclass

from .auth import JueriCredentials
from .client import DEFAULT_TIMEOUT_SECONDS, JueriClient
from .debug_log import log_jueri_api_error
from .exceptions import (
    JueriAPIError,
    JueriAuthenticationError,
    JueriConnectionError,
    JueriDisabledError,
    JueriTimeoutError,
)

JUERI_BASE_URL = "https://jueri.com.br/sis"
CONNECTION_TEST_PATH = "/api/v1/{cliente_sistema}/revendedor/nivel"


@dataclass
class ConnectionTestResult:
    success: bool
    message: str


def test_connection(
    credentials: JueriCredentials, timeout: float = DEFAULT_TIMEOUT_SECONDS
) -> ConnectionTestResult:
    client = JueriClient(JUERI_BASE_URL, credentials, timeout=timeout)
    path = CONNECTION_TEST_PATH.format(cliente_sistema=credentials.cliente_sistema)
    full_url = f"{client.base_url}/{path.lstrip('/')}"

    try:
        client.get(path)
    except JueriDisabledError:
        return ConnectionTestResult(False, "Habilite a integração antes de testar a conexão.")
    except JueriAuthenticationError:
        return ConnectionTestResult(False, "Preencha Cliente Sistema e Token antes de testar.")
    except JueriTimeoutError:
        return ConnectionTestResult(False, "Tempo de resposta excedido.")
    except JueriConnectionError:
        return ConnectionTestResult(False, "Sem conexão com a internet.")
    except JueriAPIError as exc:
        # Mensagem construída a partir do corpo real da resposta (ver
        # JueriAPIError.describe()) — não infere mais o significado de um
        # status HTTP sem evidência.
        log_jueri_api_error("GET", full_url, exc)
        return ConnectionTestResult(False, exc.describe())

    return ConnectionTestResult(True, "Conectado com sucesso.")
