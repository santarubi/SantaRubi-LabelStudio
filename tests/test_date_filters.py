import unittest
from datetime import date, timedelta
from unittest.mock import patch

from app.api.date_filters import (
    DateFilterError,
    DateRangeFilter,
    br_date_to_iso,
    build_date_range_filter,
    today_br,
    yesterday_br,
)


class BrDateToIsoTests(unittest.TestCase):
    def test_converts_br_format_to_iso(self):
        self.assertEqual(br_date_to_iso("23/07/2026"), "2026-07-23")

    def test_strips_whitespace(self):
        self.assertEqual(br_date_to_iso("  23/07/2026  "), "2026-07-23")

    def test_raises_friendly_error_for_invalid_format(self):
        with self.assertRaises(DateFilterError) as ctx:
            br_date_to_iso("2026-07-23")  # ISO, não o formato esperado
        self.assertIn("2026-07-23", str(ctx.exception))
        self.assertIn("DD/MM/AAAA", str(ctx.exception))

    def test_raises_friendly_error_for_garbage_input(self):
        with self.assertRaises(DateFilterError):
            br_date_to_iso("não é uma data")

    def test_raises_for_impossible_date(self):
        with self.assertRaises(DateFilterError):
            br_date_to_iso("31/02/2026")


class BuildDateRangeFilterTests(unittest.TestCase):
    def test_both_fields_empty_returns_inactive_filter(self):
        """Comportamento atual preservado quando nenhuma data é informada."""
        result = build_date_range_filter("", "")
        self.assertFalse(result.is_active)
        self.assertEqual(result.to_params(), {})

    def test_whitespace_only_fields_are_treated_as_empty(self):
        result = build_date_range_filter("   ", "   ")
        self.assertFalse(result.is_active)

    def test_only_data_inicial_filled(self):
        result = build_date_range_filter("23/07/2026", "")
        self.assertTrue(result.is_active)
        self.assertEqual(result.to_params(), {"data_criacao_inicial": "2026-07-23"})

    def test_only_data_final_filled(self):
        result = build_date_range_filter("", "23/07/2026")
        self.assertTrue(result.is_active)
        self.assertEqual(result.to_params(), {"data_criacao_final": "2026-07-23"})

    def test_specific_date_uses_same_date_for_both(self):
        result = build_date_range_filter("23/07/2026", "23/07/2026")
        self.assertEqual(result.to_params(), {"data_criacao_inicial": "2026-07-23", "data_criacao_final": "2026-07-23"})

    def test_date_range(self):
        result = build_date_range_filter("20/07/2026", "23/07/2026")
        self.assertEqual(
            result.to_params(), {"data_criacao_inicial": "2026-07-20", "data_criacao_final": "2026-07-23"}
        )

    def test_final_before_inicial_raises_friendly_error(self):
        with self.assertRaises(DateFilterError) as ctx:
            build_date_range_filter("23/07/2026", "20/07/2026")
        self.assertIn("Data Final", str(ctx.exception))
        self.assertIn("Data Inicial", str(ctx.exception))

    def test_same_date_for_both_is_not_an_error(self):
        build_date_range_filter("23/07/2026", "23/07/2026")  # nao deve levantar

    def test_invalid_data_inicial_raises(self):
        with self.assertRaises(DateFilterError):
            build_date_range_filter("31/13/2026", "")

    def test_invalid_data_final_raises(self):
        with self.assertRaises(DateFilterError):
            build_date_range_filter("", "31/13/2026")


class QuickDateHelpersTests(unittest.TestCase):
    @patch("app.api.date_filters.date")
    def test_today_br_formats_current_date(self, mock_date):
        mock_date.today.return_value = date(2026, 7, 23)
        self.assertEqual(today_br(), "23/07/2026")

    @patch("app.api.date_filters.date")
    def test_yesterday_br_formats_previous_day(self, mock_date):
        mock_date.today.return_value = date(2026, 7, 23)
        self.assertEqual(yesterday_br(), "22/07/2026")

    def test_today_and_yesterday_round_trip_through_build_date_range_filter(self):
        today_result = build_date_range_filter(today_br(), today_br())
        expected_today = date.today().isoformat()
        self.assertEqual(today_result.to_params(), {"data_criacao_inicial": expected_today, "data_criacao_final": expected_today})

        yesterday_result = build_date_range_filter(yesterday_br(), yesterday_br())
        expected_yesterday = (date.today() - timedelta(days=1)).isoformat()
        self.assertEqual(
            yesterday_result.to_params(),
            {"data_criacao_inicial": expected_yesterday, "data_criacao_final": expected_yesterday},
        )


class DateRangeFilterDataclassTests(unittest.TestCase):
    def test_default_is_inactive(self):
        self.assertFalse(DateRangeFilter().is_active)

    def test_to_params_omits_none_fields(self):
        self.assertEqual(DateRangeFilter(data_criacao_inicial="2026-07-23").to_params(), {"data_criacao_inicial": "2026-07-23"})


if __name__ == "__main__":
    unittest.main()
