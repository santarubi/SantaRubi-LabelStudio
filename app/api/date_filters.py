"""Conversão e validação de datas para os filtros data_criacao_inicial /
data_criacao_final da API Jueri.

Confirmado contra a API real (não é suposição):
- só aceita ISO (YYYY-MM-DD) — enviar DD/MM/YYYY resulta em HTTP 422;
- data_criacao_inicial sozinho já funciona como "a partir de";
- filtra no servidor, sem limite de resultados além da paginação normal.

A interface sempre trabalha em DD/MM/AAAA (o que o usuário digita) — este
módulo é o único lugar que converte para o formato que a API exige.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta


class DateFilterError(Exception):
    """Erro de validação num filtro de data — mensagem já pronta para
    mostrar ao usuário na interface."""


def br_date_to_iso(text: str) -> str:
    """Converte "23/07/2026" (formato brasileiro, como o usuário digita)
    para "2026-07-23" (único formato aceito pela API Jueri)."""
    text = text.strip()
    try:
        parsed = datetime.strptime(text, "%d/%m/%Y").date()
    except ValueError:
        raise DateFilterError(f'Data inválida: "{text}". Use o formato DD/MM/AAAA.') from None
    return parsed.isoformat()


@dataclass
class DateRangeFilter:
    """Filtro de data já validado e convertido — pronto para virar
    data_criacao_inicial/data_criacao_final na chamada à API."""

    data_criacao_inicial: str | None = None
    data_criacao_final: str | None = None

    @property
    def is_active(self) -> bool:
        return self.data_criacao_inicial is not None or self.data_criacao_final is not None

    def to_params(self) -> dict[str, str]:
        params: dict[str, str] = {}
        if self.data_criacao_inicial:
            params["data_criacao_inicial"] = self.data_criacao_inicial
        if self.data_criacao_final:
            params["data_criacao_final"] = self.data_criacao_final
        return params


def build_date_range_filter(data_inicial_br: str, data_final_br: str) -> DateRangeFilter:
    """Valida e converte os dois campos de data (formato brasileiro, como
    vêm da interface) para um DateRangeFilter pronto para a API.

    Campos vazios são ignorados (sem filtro — comportamento igual ao
    atual). Se só um dos dois vier preenchido, usa só esse. Se os dois
    vierem, valida que a final não seja anterior à inicial.
    """
    data_inicial_br = (data_inicial_br or "").strip()
    data_final_br = (data_final_br or "").strip()

    if not data_inicial_br and not data_final_br:
        return DateRangeFilter()

    iso_inicial = br_date_to_iso(data_inicial_br) if data_inicial_br else None
    iso_final = br_date_to_iso(data_final_br) if data_final_br else None

    if iso_inicial and iso_final and iso_final < iso_inicial:
        raise DateFilterError("A Data Final não pode ser anterior à Data Inicial.")

    return DateRangeFilter(data_criacao_inicial=iso_inicial, data_criacao_final=iso_final)


def today_br() -> str:
    return date.today().strftime("%d/%m/%Y")


def yesterday_br() -> str:
    return (date.today() - timedelta(days=1)).strftime("%d/%m/%Y")
