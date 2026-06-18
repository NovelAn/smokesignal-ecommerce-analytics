"""Insights API routes — customer insight aggregation endpoints.

v2 routes exposing VIC group persona, period-over-period comparison,
at-risk customer detection, and customer trend data.
"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from backend.analytics.vic_persona_analyzer import VicPersonaAnalyzer
from backend.analytics.period_comparator import PeriodComparator
from backend.analytics.anomaly_detector import AnomalyDetector
from backend.analytics.trend_aggregator import TrendAggregator

router = APIRouter(prefix="/api/v2/insights", tags=["insights"])


@router.get("/vic-persona")
async def get_vic_persona(buyer_type: str = Query("VIC", description="VIC（含BOTH）或 SMOKER（含BOTH）")):
    """聚合高价值客户群体画像：兴趣、痛点、购买动机。

    buyer_type=VIC → VIC + BOTH；buyer_type=SMOKER → SMOKER + BOTH（BOTH 同时属于两者）。
    """
    if buyer_type.upper() not in ("VIC", "SMOKER"):
        raise HTTPException(status_code=400, detail="buyer_type 只支持 VIC 或 SMOKER")
    try:
        return await VicPersonaAnalyzer().analyze_vic_group(buyer_type=buyer_type.upper())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"群体画像查询失败: {str(e)}")


@router.get("/period-comparison")
async def get_period_comparison(
    start_date: date = Query(..., description="当期开始日期"),
    end_date: date = Query(..., description="当期结束日期"),
    comparison_start_date: Optional[date] = Query(None, description="对比期开始日期（可选，留空自动算等长前期）"),
    comparison_end_date: Optional[date] = Query(None, description="对比期结束日期（可选）"),
):
    """对比当期 (T1) 与对比期 (T0) 的关键指标变化。

    未传对比期 → 自动算等长前期（紧邻当期前一天）；
    传了 comparison_start/end → 用自定义对比期（支持同比/不等长）。
    """
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date 不能大于 end_date")
    if comparison_start_date and comparison_end_date and comparison_start_date > comparison_end_date:
        raise HTTPException(status_code=400, detail="comparison_start_date 不能大于 comparison_end_date")
    try:
        return await PeriodComparator().compare_metrics(
            start_date,
            end_date,
            comp_start=comparison_start_date,
            comp_end=comparison_end_date,
        )
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
