"""Integração com a API do sistema Jueri."""

from .auth import JueriCredentials
from .categories import CategoriesAPI
from .client import JueriClient
from .connection_test import ConnectionTestResult, test_connection
from .date_filters import DateFilterError, DateRangeFilter, build_date_range_filter, today_br, yesterday_br
from .exceptions import (
    JueriAPIError,
    JueriAuthenticationError,
    JueriConnectionError,
    JueriDisabledError,
    JueriError,
    JueriTimeoutError,
)
from .product import Product, ProductPrice
from .products import ProductsAPI, ProductSearchResult

__all__ = [
    "JueriClient",
    "JueriCredentials",
    "ProductsAPI",
    "ProductSearchResult",
    "CategoriesAPI",
    "Product",
    "ProductPrice",
    "ConnectionTestResult",
    "test_connection",
    "DateFilterError",
    "DateRangeFilter",
    "build_date_range_filter",
    "today_br",
    "yesterday_br",
    "JueriError",
    "JueriDisabledError",
    "JueriAuthenticationError",
    "JueriConnectionError",
    "JueriTimeoutError",
    "JueriAPIError",
]
