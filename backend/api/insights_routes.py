"""Insights API routes — customer insight aggregation endpoints.

v2 routes exposing VIC group persona, period-over-period comparison,
at-risk customer detection, and customer trend data.
"""
from datetime import date

from fastapi import APIRouter, HTTPException, Query

from backend.analytics.vic_persona_analyzer import VicPersonaAnalyzer
from backend.analytics.period_comparator import PeriodComparator
from backend.analytics.anomaly_detector import AnomalyDetector
from backend.analytics.trend_aggregator import TrendAggregator

router = APIRouter(prefix="/api/v2/insights", tags=["insights"])


@router.get("/vic-persona")
async def get_vic_persona():
    """聚合 VIC 群体画像：兴趣、痛点、购买动机。"""
    try:
        return await VicPersonaAnalyzer().analyze_vic_group()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"VIC 群体画像查询失败: {str(e)}")


@router.get("/period-comparison")
async def get_period_comparison(
    start_date: date = Query(..., description="当期开始日期"),
    end_date: date = Query(..., description="当期结束日期"),
):
    """对比当期 (T1) 与等长对比期 (T0) 的关键指标变化。"""
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date 不能大于 end_date")
    try:
        return await PeriodComparator().compare_metrics(start_date, end_date)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"时间对比查询失败: {str(e)}")


@router.get("/anomaly-alerts", deprecated=True)
async def get_anomaly_alerts():
    """检测高价值客户中的异常信号（情感负向 / 购买间隔 / 沟通频次）。"""
    try:
        return await AnomalyDetector().get_all_anomalies()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"异常客户检测失败: {str(e)}")


@router.get("/customer-trends")
async def get_customer_trends(months: int = Query(6, ge=1, le=24)):
    """聚合 VIC 池规模、活跃率、高风险趋势。"""
    try:
        return await TrendAggregator().get_customer_trends(months)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"趋势数据查询失败: {str(e)}")
