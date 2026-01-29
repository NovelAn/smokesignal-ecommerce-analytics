"""
优化版FastAPI路由 - 使用预计算表实现超快速查询
性能提升: 10-50倍

AI分析: 使用DeepSeek-R1 + 多级降级策略
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from backend.analytics.target_buyer_analyzer import TargetBuyerAnalyzer
from backend.ai.analyzer_orchestrator import get_analyzer_orchestrator
from backend.database import BuyerQueries

router = APIRouter(prefix="/api/v2", tags=["target_buyers"])
analyzer = TargetBuyerAnalyzer()
ai_orchestrator = get_analyzer_orchestrator()


@router.get("/")
async def root():
    """API health check"""
    return {
        "status": "ok",
        "service": "SmokeSignal Analytics API v2 (Optimized)",
        "version": "2.0.0",
        "performance": "Using precomputed table - 10-50x faster"
    }


@router.get("/buyers")
async def get_all_buyers(
    search: Optional[str] = Query(None, description="昵称模糊搜索"),
    buyer_type: Optional[List[str]] = Query(None, description="买家类型: SMOKER/VIC/BOTH"),
    vip_level: Optional[List[str]] = Query(None, description="VIP等级: V3/V2/V1/V0/Non-VIP"),
    channel: Optional[List[str]] = Query(None, description="渠道: DTC/PFS"),
    last_purchase_after: Optional[str] = Query(None, description="最后购买日期筛选 (YYYY-MM-DD)"),
    chat_status: Optional[str] = Query(None, description="聊天状态: chatted/no_chat"),
    sort_by: str = Query('last_purchase', description="排序字段: last_purchase/l6m_netsales/vip_level"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量"),
    offset: int = Query(0, ge=0, description="偏移量")
) -> Dict[str, Any]:
    """
    获取所有目标买家列表(超快!)

    性能: < 0.5秒 (优化前: 10-30秒)

    支持的筛选条件:
    - search: 昵称模糊搜索
    - buyer_type: 买家类型 (SMOKER/VIC/BOTH)
    - vip_level: VIP等级 (V3/V2/V1/V0/Non-VIP)
    - channel: 渠道 (DTC/PFS)
    - last_purchase_after: 最后购买日期筛选
    - chat_status: 聊天状态 (chatted/no_chat)
    - sort_by: 排序字段 (last_purchase/l6m_netsales/vip_level)
    """
    try:
        result = analyzer.get_all_buyers(
            search=search,
            buyer_type=buyer_type,
            vip_level=vip_level,
            channel=channel,
            last_purchase_after=last_purchase_after,
            chat_status=chat_status,
            sort_by=sort_by,
            limit=limit,
            offset=offset
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/buyers/{user_nick}")
async def get_buyer_profile(
    user_nick: str,
    include_ai: bool = Query(False, description="是否包含AI分析")
) -> Dict[str, Any]:
    """
    获取买家360°详情(超快!)

    性能: < 0.1秒 (优化前: 2-5秒)

    Args:
        user_nick: 买家昵称
        include_ai: 是否包含AI分析(会慢一些)
    """
    try:
        # 从预计算表获取基本信息(超快)
        profile = analyzer.get_buyer_profile(user_nick)

        if not profile:
            raise HTTPException(status_code=404, detail=f"买家 {user_nick} 不存在")

        # 如果需要AI分析,添加AI生成的洞察
        if include_ai:
            profile = await _add_ai_analysis(profile)

        return profile

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/metrics")
async def get_dashboard_metrics() -> Dict[str, Any]:
    """
    获取Dashboard汇总指标(超快!)

    性能: < 0.1秒 (优化前: 5-15秒)
    """
    try:
        metrics = analyzer.get_dashboard_metrics()
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/buyers/type/{buyer_type}")
async def get_buyers_by_type(
    buyer_type: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
) -> List[Dict[str, Any]]:
    """
    按买家类型筛选

    性能: < 0.1秒 (使用索引)

    Args:
        buyer_type: 买家类型 (SMOKER/VIC/BOTH)
    """
    try:
        if buyer_type not in ['SMOKER', 'VIC', 'BOTH']:
            raise HTTPException(
                status_code=400,
                detail=f"无效的buyer_type: {buyer_type}. 必须是 SMOKER, VIC 或 BOTH"
            )

        buyers = analyzer.get_buyers_by_type(buyer_type, limit, offset)
        return buyers
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/buyers/vic")
async def get_vic_buyers(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
) -> List[Dict[str, Any]]:
    """
    获取VIC买家列表(按VIP等级排序)

    性能: < 0.1秒 (使用vip_level索引)
    """
    try:
        buyers = analyzer.get_vic_buyers(limit, offset)
        return buyers
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/buyers/smoker")
async def get_smoker_buyers(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
) -> List[Dict[str, Any]]:
    """
    获取Smoker买家列表(按消费金额排序)

    性能: < 0.1秒 (使用l6m_netsales索引)
    """
    try:
        buyers = analyzer.get_smoker_buyers(limit, offset)
        return buyers
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/buyers/churn-risk/{risk_level}")
async def get_churn_risk_buyers(
    risk_level: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
) -> List[Dict[str, Any]]:
    """
    获取流失风险买家

    性能: < 0.1秒 (使用churn_risk索引)

    Args:
        risk_level: 风险等级 (高/中/低)
    """
    try:
        if risk_level not in ['高', '中', '低']:
            raise HTTPException(
                status_code=400,
                detail=f"无效的risk_level: {risk_level}. 必须是 高, 中 或 低"
            )

        buyers = analyzer.get_churn_risk_buyers(risk_level, limit, offset)
        return buyers
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/buyers/high-value")
async def get_high_value_buyers(
    min_l6m_netsales: float = Query(5000, ge=0, description="最小近6个月消费金额"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
) -> List[Dict[str, Any]]:
    """
    获取高价值买家(L6M消费 >= 阈值)

    性能: < 0.1秒 (使用l6m_netsales索引)
    """
    try:
        buyers = analyzer.get_high_value_buyers(min_l6m_netsales, limit, offset)
        return buyers
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/buyers/vip-level/{vip_level}")
async def get_buyers_by_vip_level(
    vip_level: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
) -> List[Dict[str, Any]]:
    """
    按VIP等级筛选买家

    性能: < 0.1秒 (使用vip_level索引)

    Args:
        vip_level: VIP等级 (V3/V2/V1/V0/Non-VIP)
    """
    try:
        if vip_level not in ['V3', 'V2', 'V1', 'V0', 'Non-VIP']:
            raise HTTPException(
                status_code=400,
                detail=f"无效的vip_level: {vip_level}. 必须是 V3, V2, V1, V0 或 Non-VIP"
            )

        buyers = analyzer.get_buyers_by_vip_level(vip_level, limit, offset)
        return buyers
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/channel")
async def get_channel_stats() -> List[Dict[str, Any]]:
    """
    按渠道统计(DTC/PFS)

    性能: < 0.1秒 (使用channel索引)
    """
    try:
        stats = analyzer.get_channel_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ai/status")
async def get_ai_system_status() -> Dict[str, Any]:
    """
    获取AI分析系统状态

    返回:
    - 可用的AI模型
    - 成本统计
    - 缓存状态
    """
    try:
        from backend.monitoring.cost_monitor import get_cost_monitor
        from backend.utils.cache_manager import get_cache_manager
        from backend.config import settings

        cost_monitor = get_cost_monitor()
        cache_manager = get_cache_manager()

        # 获取成本统计
        cost_summary = cost_monitor.get_daily_summary()

        # 获取缓存统计
        cache_stats = cache_manager.get_stats()

        # 检查模型可用性
        models = {
            "deepseek_available": bool(settings.deepseek_api_key),
            "zhipu_available": bool(settings.zhipu_api_key)
        }

        return {
            "status": "ok",
            "models": models,
            "cost": cost_summary,
            "cache": cache_stats,
            "config": {
                "cache_ttl_days": settings.ai_cache_ttl_days,
                "cache_enabled": settings.ai_enable_cache
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/actionable-customers")
async def get_actionable_customers(
    limit: int = Query(50, ge=1, le=500, description="每个类别返回数量")
) -> Dict[str, List[Dict[str, Any]]]:
    """
    获取需要优先处理的客户(可操作客户列表)

    整合流失风险、高价值等需要关注的客户

    性能: < 0.5秒 (多次索引查询)
    """
    try:
        customers = analyzer.get_actionable_customers(limit)
        return customers
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/buyers/{user_nick}/orders")
async def get_buyer_orders(
    user_nick: str,
    time_range: str = Query('1y', description="时间范围: 7d/15d/30d/90d/1y/all"),
    limit: int = Query(50, ge=1, le=1000)
) -> List[Dict[str, Any]]:
    """
    获取买家订单历史(使用订单明细预计算表 - 超快!)

    性能: < 0.5秒 (使用索引查询)

    支持的时间范围:
    - 7d: 近7天
    - 15d: 近15天
    - 30d: 近30天
    - 90d: 近90天
    - 1y: 近1年(默认)
    - all: 全部历史
    """
    try:
        from backend.database import Database
        from backend.config import settings
        import pymysql

        # 默认使用aliyunDB数据库
        db_name = settings.db_name_to_use if settings.db_name_to_use else 'aliyunDB'
        db = Database(db_name=db_name)

        # 构建时间范围条件
        time_conditions = {
            '7d': "AND 最后付款时间 >= DATE_SUB(NOW(), INTERVAL 7 DAY)",
            '15d': "AND 最后付款时间 >= DATE_SUB(NOW(), INTERVAL 15 DAY)",
            '30d': "AND 最后付款时间 >= DATE_SUB(NOW(), INTERVAL 30 DAY)",
            '90d': "AND 最后付款时间 >= DATE_SUB(NOW(), INTERVAL 90 DAY)",
            '1y': "AND 最后付款时间 >= DATE_SUB(NOW(), INTERVAL 1 YEAR)",
            'all': ""
        }

        time_condition = time_conditions.get(time_range, time_conditions['1y'])

        # 使用订单明细预计算表查询
        query = f"""
            SELECT
                订单号, 子订单号, 商品名称, category as category,
                成交总金额, 退款金额, 退款类型,
                FP_MD, 图片地址, 最后付款时间, 件数,
                (成交总金额 - IFNULL(退款金额, 0)) as netsales
            FROM target_buyer_orders
            WHERE 买家昵称 = %s
              {time_condition}
            ORDER BY 最后付款时间 DESC
            LIMIT %s
        """

        params = [user_nick, limit]
        orders = db.execute_query(query, params)

        return orders
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/buyers/{user_nick}/chats")
async def get_buyer_chats(
    user_nick: str,
    limit: int = Query(100, ge=1, le=1000)
) -> List[Dict[str, Any]]:
    """
    获取买家聊天记录

    注意: 这个查询会比较多,建议限制返回数量
    """
    try:
        from backend.database import Database
        from backend.config import settings

        # 默认使用aliyunDB数据库
        db_name = settings.db_name_to_use if settings.db_name_to_use else 'aliyunDB'
        db = Database(db_name=db_name)

        query, params = BuyerQueries.get_chat_messages(user_nick, limit)
        chats = db.execute_query(query, params)

        return chats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _add_ai_analysis(profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    添加AI生成的买家洞察（使用增强版AI分析系统）

    特性:
    - 两阶段推理: 证据提取 → 画像推理
    - 多级降级: DeepSeek-R1 → DeepSeek-Chat → Zhipu GLM-4 → 规则引擎
    - 成本监控: 实时记录API调用和成本
    - 智能缓存: 30天缓存，减少重复调用

    性能: 3-10秒 (取决于模型和数据复杂度)
    """
    try:
        user_nick = profile.get("user_nick")

        # 1. 获取聊天记录(最近30条，增强分析需要更多数据)
        from backend.database import Database
        from backend.config import settings
        from backend.database import BuyerQueries

        # 默认使用aliyunDB数据库
        db_name = settings.db_name_to_use if settings.db_name_to_use else 'aliyunDB'
        db = Database(db_name=db_name)

        # 获取聊天记录
        query, params = BuyerQueries.get_chat_messages(user_nick, limit=30)
        chats = db.execute_query(query, params)

        # 2. 获取订单记录（用于行为分析）
        orders_query = """
            SELECT
                订单号, 商品名称 as commodity_name, category,
                成交总金额 as payment, 退款金额, 退款类型 as refund_status,
                最后付款时间 as pay_time
            FROM target_buyer_orders
            WHERE 买家昵称 = %s
            ORDER BY 最后付款时间 DESC
            LIMIT 50
        """
        orders = db.execute_query(orders_query, [user_nick])

        # 3. 准备profile数据（传递所有预计算表字段，除了updated_at）
        # 确保AI能够基于完整的真实数据进行分析
        profile_data = {
            # 基本信息（直接从profile传递所有字段）
            "user_nick": user_nick,
            "buyer_nick": profile.get('buyer_nick'),
            "channel": profile.get('channel'),
            "buyer_type": profile.get('buyer_type'),
            "is_smoker": profile.get('is_smoker', 0),
            "is_vic": profile.get('is_vic', 0),
            "vip_level": profile.get('vip_level', 'Non-VIP'),
            "client_monthly_tag": profile.get('client_monthly_tag'),

            # 历史消费指标
            "historical_gmv": float(profile.get('historical_gmv', 0)),
            "historical_refund": float(profile.get('historical_refund', 0)),
            "historical_net_sales": float(profile.get('historical_net_sales', 0)),
            "total_orders": int(profile.get('total_orders', 0)),
            "total_net_orders": int(profile.get('total_net_orders', 0)),
            "refund_rate": float(profile.get('refund_rate', 0)),

            # 时间维度指标
            "first_purchase_date": profile.get('first_purchase_date', ''),
            "last_purchase_date": profile.get('last_purchase_date', ''),

            # 滚动24个月指标
            "rolling_24m_netsales": float(profile.get('rolling_24m_netsales', 0)),
            "rolling_24m_orders": int(profile.get('rolling_24m_orders', 0)),

            # L6M指标
            "l6m_gmv": float(profile.get('l6m_gmv', 0)),
            "l6m_netsales": float(profile.get('l6m_netsales', 0)),
            "l6m_orders": int(profile.get('l6m_orders', 0)),
            "l6m_refund_rate": float(profile.get('l6m_refund_rate', 0)),

            # L1Y指标
            "l1y_gmv": float(profile.get('l1y_gmv', 0)),
            "l1y_netsales": float(profile.get('l1y_netsales', 0)),
            "l1y_orders": int(profile.get('l1y_orders', 0)),
            "l1y_refund_rate": float(profile.get('l1y_refund_rate', 0)),

            # 折扣和敏感度
            "discount_ratio": float(profile.get('discount_ratio', 0)),
            "discount_sensitivity": profile.get('discount_sensitivity', '未知'),

            # 聊天行为指标
            "chat_frequency_days": int(profile.get('chat_frequency_days', 0)),
            "first_chat_date": profile.get('first_chat_date'),
            "last_chat_date": profile.get('last_chat_date'),
            "l30d_chat_frequency_days": int(profile.get('l30d_chat_frequency_days', 0)),
            "l3m_chat_frequency_days": int(profile.get('l3m_chat_frequency_days', 0)),
            "avg_chat_interval_days": float(profile.get('avg_chat_interval_days', 0)),

            # 风险和偏好
            "churn_risk": profile.get('churn_risk', '未知'),
            "city": profile.get('city', 'Unknown'),
            "top_category": profile.get('top_category', 'Unknown'),
            "second_category": profile.get('second_category'),
            "third_category": profile.get('third_category'),

            # AI分析专用字段
            "chat_history": chats,  # 传递聊天记录用于文本分析
            "total_refund_count": int(float(profile.get('historical_refund', 0)) / 1000) if float(profile.get('historical_refund', 0)) > 0 else 0  # 估算退款次数
        }

        # 4. 调用增强版AI分析器（自动选择最优模型和降级策略）
        import logging
        logging.info(f"[AI] 开始分析客户 {user_nick}, VIP等级: {profile_data['vip_level']}")

        ai_analysis = ai_orchestrator.analyze_buyer_persona(
            buyer_nick=user_nick,
            profile=profile_data,
            chats=chats,
            orders=orders
        )

        # 5. 添加AI分析结果到profile
        profile["ai_analysis"] = ai_analysis

        # 记录使用的分析方法
        method = ai_analysis.get('analysis_method', 'Unknown')
        confidence = ai_analysis.get('confidence_level', 'Unknown')
        logging.info(f"[AI] 分析完成 {user_nick}, 方法: {method}, 置信度: {confidence}")

        return profile

    except Exception as e:
        import logging
        logging.error(f"AI分析失败 for user {user_nick}: {e}", exc_info=True)
        # AI分析失败不影响基本信息返回
        profile["ai_analysis"] = {
            "summary": f"AI分析暂时不可用: {str(e)[:100]}",
            "key_interests": [],
            "pain_points": [],
            "recommended_action": "建议根据买家历史购买情况制定个性化跟进方案",
            "analysis_method": "Error",
            "error": str(e)
        }
        return profile
