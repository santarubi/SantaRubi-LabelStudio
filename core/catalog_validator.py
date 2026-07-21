"""Validador da configuração do Catálogo Integrado.

Responsabilidade única: validar arquivo, abas e colunas mapeadas, e contar
quantos produtos seriam carregados. Não fornece nem carrega dados — isso é
responsabilidade exclusiva de CatalogRepository.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.catalog_datasource import DataSource
from core.catalog_excel_source import normalize_header
from core.catalog_settings import CATALOG_FIELD_LABELS, CATALOG_FIELDS, CatalogSettings


@dataclass
class ValidationIssue:
    """Um problema encontrado ao validar a configuração — aba e/ou campo
    relacionado, quando aplicável, e a mensagem já pronta para exibição."""

    sheet: str | None
    field: str | None
    message: str


@dataclass
class ValidationReport:
    """Resultado de `CatalogConfigurationValidator.validate()`."""

    file_found: bool = False
    sheets_found: list[str] = field(default_factory=list)
    all_columns_found: bool = False
    total_products: int = 0
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return self.file_found and self.all_columns_found and not self.issues


class CatalogConfigurationValidator:
    """Valida uma CatalogSettings contra uma DataSource concreta."""

    def __init__(self, data_source: DataSource):
        self.data_source = data_source

    def validate(self, settings: CatalogSettings) -> ValidationReport:
        """Valida a configuração: arquivo, abas e mapeamento de colunas.

        Em caso de erro, cada `ValidationIssue` informa exatamente a aba
        e/ou o campo relacionado, para uma mensagem precisa na interface.
        """
        report = ValidationReport()

        try:
            available_sheets = self.data_source.list_sheets()
        except FileNotFoundError:
            report.issues.append(ValidationIssue(None, None, "Arquivo não encontrado."))
            return report
        except Exception as exc:  # pragma: no cover - erro de leitura do Excel
            report.issues.append(ValidationIssue(None, None, f"Não foi possível abrir o arquivo: {exc}"))
            return report

        report.file_found = True

        for name in settings.selected_sheets:
            if name not in available_sheets:
                report.issues.append(ValidationIssue(name, None, f"Aba '{name}' não encontrada no arquivo."))

        valid_sheets = [name for name in settings.selected_sheets if name in available_sheets]
        report.sheets_found = valid_sheets

        if not valid_sheets:
            report.issues.append(ValidationIssue(None, None, "Nenhuma aba selecionada é válida."))
            return report

        unmapped_fields = [
            internal_field for internal_field in CATALOG_FIELDS if not settings.column_map.get(internal_field)
        ]
        for internal_field in unmapped_fields:
            label = CATALOG_FIELD_LABELS[internal_field]
            report.issues.append(ValidationIssue(None, internal_field, f"Campo '{label}' não foi mapeado."))

        mapped_fields = [
            internal_field for internal_field in CATALOG_FIELDS if settings.column_map.get(internal_field)
        ]
        headers_by_sheet = self.data_source.get_headers(valid_sheets)
        for sheet_name, headers in headers_by_sheet.items():
            normalized_headers = {normalize_header(header) for header in headers}
            for internal_field in mapped_fields:
                mapped_header = settings.column_map[internal_field]
                if normalize_header(mapped_header) not in normalized_headers:
                    label = CATALOG_FIELD_LABELS[internal_field]
                    report.issues.append(
                        ValidationIssue(
                            sheet_name,
                            internal_field,
                            f"Coluna '{mapped_header}' (campo '{label}') não localizada na aba '{sheet_name}'.",
                        )
                    )

        column_issues = [issue for issue in report.issues if issue.field is not None]
        report.all_columns_found = not column_issues

        if report.all_columns_found:
            counts = self.data_source.count_rows(valid_sheets)
            report.total_products = sum(counts.values())

        return report
