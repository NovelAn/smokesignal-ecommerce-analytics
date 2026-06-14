"""TrendAggregator unit tests.

Tests cover pure formatting and rate-calculation logic only.
Database-dependent get_customer_trends() is excluded (integration-level).
"""

import pytest

from backend.analytics.trend_aggregator import TrendAggregator


class TestFormatVicPoolTrend:
    def test_passes_through_raw_data(self):
        aggregator = TrendAggregator()
        mock = [{"month": "2026-01", "SMOKER": 45, "VIC": 82, "BOTH": 38}]
        result = aggregator.format_vic_pool_trend(mock)
        assert len(result) == 1
        assert result[0]["VIC"] == 82
        assert result[0]["SMOKER"] == 45
        assert result[0]["BOTH"] == 38

    def test_preserves_multiple_months(self):
        aggregator = TrendAggregator()
        mock = [
            {"month": "2026-01", "SMOKER": 10, "VIC": 20, "BOTH": 5},
            {"month": "2026-02", "SMOKER": 12, "VIC": 22, "BOTH": 7},
        ]
        result = aggregator.format_vic_pool_trend(mock)
        assert len(result) == 2
        assert result[1]["VIC"] == 22

    def test_empty_input(self):
        aggregator = TrendAggregator()
        result = aggregator.format_vic_pool_trend([])
        assert result == []


class TestCalculateActiveRate:
    def test_standard_calculation(self):
        aggregator = TrendAggregator()
        assert aggregator.calculate_active_rate(100, 65) == 65.0

    def test_zero_total(self):
        aggregator = TrendAggregator()
        assert aggregator.calculate_active_rate(0, 0) == 0.0

    def test_zero_total_nonzero_active(self):
        aggregator = TrendAggregator()
        assert aggregator.calculate_active_rate(0, 5) == 0.0

    def test_rounding_to_one_decimal(self):
        aggregator = TrendAggregator()
        assert aggregator.calculate_active_rate(3, 1) == 33.3

    def test_full_rate(self):
        aggregator = TrendAggregator()
        assert aggregator.calculate_active_rate(50, 50) == 100.0

    def test_zero_rate(self):
        aggregator = TrendAggregator()
        assert aggregator.calculate_active_rate(50, 0) == 0.0


class TestFormatActiveRateTrend:
    def test_single_month(self):
        aggregator = TrendAggregator()
        raw = [{"month": "2026-01", "total_vic": 100, "active_vic": 60}]
        result = aggregator.format_active_rate_trend(raw)
        assert len(result) == 1
        assert result[0]["active_rate"] == 60.0
        assert result[0]["total_vic"] == 100
        assert result[0]["active_vic"] == 60
        assert result[0]["month"] == "2026-01"

    def test_rate_with_rounding(self):
        aggregator = TrendAggregator()
        raw = [{"month": "2026-01", "total_vic": 7, "active_vic": 2}]
        result = aggregator.format_active_rate_trend(raw)
        assert result[0]["active_rate"] == 28.6

    def test_empty_input(self):
        aggregator = TrendAggregator()
        result = aggregator.format_active_rate_trend([])
        assert result == []

    def test_preserves_month_order(self):
        aggregator = TrendAggregator()
        raw = [
            {"month": "2026-01", "total_vic": 100, "active_vic": 60},
            {"month": "2026-02", "total_vic": 110, "active_vic": 70},
            {"month": "2026-03", "total_vic": 105, "active_vic": 55},
        ]
        result = aggregator.format_active_rate_trend(raw)
        assert [r["month"] for r in result] == ["2026-01", "2026-02", "2026-03"]
