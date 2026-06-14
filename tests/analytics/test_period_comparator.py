import pytest
from datetime import date
from backend.analytics.period_comparator import PeriodComparator


def test_calculate_comparison_period():
    """测试计算等长对比期"""
    comparator = PeriodComparator()
    current_start = date(2026, 5, 1)
    current_end = date(2026, 5, 31)
    comp_start, comp_end = comparator.calculate_comparison_period(current_start, current_end)
    # 当期 31 天 (5/1~5/31)；对比期 = 前 31 天 = 3/31~4/30
    assert comp_start == date(2026, 3, 31)
    assert comp_end == date(2026, 4, 30)


def test_comparison_period_same_length():
    """对比期与当期等长"""
    comparator = PeriodComparator()
    cs, ce = date(2026, 5, 1), date(2026, 5, 31)
    comp_start, comp_end = comparator.calculate_comparison_period(cs, ce)
    current_len = (ce - cs).days + 1
    comp_len = (comp_end - comp_start).days + 1
    assert current_len == comp_len


def test_single_day_period():
    """单天当期"""
    comparator = PeriodComparator()
    comp_start, comp_end = comparator.calculate_comparison_period(
        date(2026, 6, 10), date(2026, 6, 10)
    )
    assert comp_start == date(2026, 6, 9)
    assert comp_end == date(2026, 6, 9)


def test_compare_metrics_structure():
    """compare_metrics 返回正确结构（DB 方法用占位实现）"""
    comparator = PeriodComparator()
    import asyncio

    result = asyncio.run(
        comparator.compare_metrics(date(2026, 5, 1), date(2026, 5, 31))
    )
    assert "current_period" in result
    assert "comparison_period" in result
    assert "metrics" in result
    assert result["current_period"]["start_date"] == "2026-05-01"
    for m in ["new_vic", "churn_warning", "vip_upgrades", "sentiment_negative"]:
        assert set(result["metrics"][m].keys()) == {
            "current",
            "previous",
            "change",
            "change_pct",
        }
