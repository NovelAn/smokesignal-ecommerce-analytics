"""
Daily AI Analysis - 批量AI分析脚本
每天自动分析VIC和高价值买家，确保数据始终是最新的
"""
import argparse
import sys
import time
from datetime import datetime, date
from typing import List, Dict, Any

# 添加backend到路径
sys.path.insert(0, 'backend')

from backend.config import settings
from backend.monitoring.cost_monitor import get_cost_monitor
from backend.ai.analyzer_orchestrator import get_analyzer_orchestrator
from backend.database.db_config_manager import DBConfigManager
from backend.analytics.target_buyer_analyzer import TargetBuyerAnalyzer
import pymysql


def get_buyers_for_analysis(
    max_buyers: int = 500,
    require_ai_analysis: bool = True
) -> List[Dict[str, Any]]:
    """
    获取需要AI分析的买家列表

    优先级:
    1. VIC客户（V3/V2/V1/V0）- 高价值客户
    2. 高价值买家（L6M > 10K）- 潜在VIC
    3. 最近7天有活动的买家 - 保持数据新鲜

    Args:
        max_buyers: 最大买家数
        require_ai_analysis: 是否只获取没有AI分析的买家

    Returns:
        买家列表
    """
    try:
        db_configs = DBConfigManager.get_db_config_for_pymysql()
        db_name = settings.db_name_to_use
        db_config = None

        for config in db_configs:
            if config["database"] == db_name:
                db_config = config
                break

        if db_config is None:
            print(f"[错误] 未找到数据库配置: {db_name}")
            return []

        conn = pymysql.connect(**db_config)

        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            # 构建查询
            ai_condition = ""
            if require_ai_analysis:
                # 查询没有AI分析或AI分析已过期（>7天）的买家
                ai_condition = """
                AND (
                    buyer_nick NOT IN (
                        SELECT DISTINCT buyer_nick
                        FROM ai_cost_log
                        WHERE DATE(timestamp) >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
                    )
                )
                """

            query = f"""
                SELECT
                    buyer_nick,
                    vip_level,
                    is_vic,
                    is_smoker,
                    l6m_netsales,
                    l6m_orders,
                    last_purchase_date,
                    last_chat_date,
                    channel
                FROM target_buyers_precomputed
                WHERE 1=1
                    {ai_condition}
                ORDER BY
                    is_vic DESC,  -- VIC优先
                    l6m_netsales DESC,  -- 高消费优先
                    last_purchase_date DESC  -- 最近购买优先
                LIMIT %s
            """

            cursor.execute(query, (max_buyers,))
            buyers = cursor.fetchall()

            print(f"[查询] 找到 {len(buyers)} 个买家需要AI分析")
            return buyers

    except Exception as e:
        print(f"[错误] 获取买家列表失败: {e}")
        import traceback
        traceback.print_exc()
        return []


def analyze_buyer(
    buyer_nick: str,
    analyzer,
    orchestrator,
    cost_monitor
) -> Dict[str, Any]:
    """
    分析单个买家

    Args:
        buyer_nick: 买家昵称
        analyzer: TargetBuyerAnalyzer实例
        orchestrator: AnalyzerOrchestrator实例
        cost_monitor: CostMonitor实例

    Returns:
        分析结果
    """
    try:
        # 获取买家档案
        profile = analyzer.get_buyer_profile(buyer_nick)
        if not profile:
            return {
                "buyer_nick": buyer_nick,
                "status": "error",
                "error": "买家不存在"
            }

        # 获取聊天和订单数据
        from backend.database import Database, BuyerQueries
        from backend.config import settings

        db_name = settings.db_name_to_use if settings.db_name_to_use else 'aliyunDB'
        db = Database(db_name=db_name)

        # 获取聊天记录
        query, params = BuyerQueries.get_chat_messages(buyer_nick, limit=30)
        chats = db.execute_query(query, params)

        # 获取订单记录
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
        orders = db.execute_query(orders_query, [buyer_nick])

        # 准备profile数据
        from datetime import datetime
        profile_data = {
            "user_nick": buyer_nick,
            "buyer_nick": profile.get('buyer_nick'),
            "channel": profile.get('channel'),
            "buyer_type": profile.get('buyer_type'),
            "is_smoker": profile.get('is_smoker', 0),
            "is_vic": profile.get('is_vic', 0),
            "vip_level": profile.get('vip_level', 'Non-VIP'),
            "client_monthly_tag": profile.get('client_monthly_tag'),
            "historical_gmv": float(profile.get('historical_gmv', 0)),
            "historical_refund": float(profile.get('historical_refund', 0)),
            "historical_net_sales": float(profile.get('historical_net_sales', 0)),
            "total_orders": int(profile.get('total_orders', 0)),
            "total_net_orders": int(profile.get('total_net_orders', 0)),
            "refund_rate": float(profile.get('refund_rate', 0)),
            "first_purchase_date": profile.get('first_purchase_date', ''),
            "last_purchase_date": profile.get('last_purchase_date', ''),
            "rolling_24m_netsales": float(profile.get('rolling_24m_netsales', 0)),
            "rolling_24m_orders": int(profile.get('rolling_24m_orders', 0)),
            "l6m_gmv": float(profile.get('l6m_gmv', 0)),
            "l6m_netsales": float(profile.get('l6m_netsales', 0)),
            "l6m_orders": int(profile.get('l6m_orders', 0)),
            "l6m_refund_rate": float(profile.get('l6m_refund_rate', 0)),
            "l1y_gmv": float(profile.get('l1y_gmv', 0)),
            "l1y_netsales": float(profile.get('l1y_netsales', 0)),
            "l1y_orders": int(profile.get('l1y_orders', 0)),
            "l1y_refund_rate": float(profile.get('l1y_refund_rate', 0)),
            "discount_ratio": float(profile.get('discount_ratio', 0)),
            "discount_sensitivity": profile.get('discount_sensitivity', '未知'),
            "chat_frequency_days": int(profile.get('chat_frequency_days', 0)),
            "first_chat_date": profile.get('first_chat_date'),
            "last_chat_date": profile.get('last_chat_date'),
            "l30d_chat_frequency_days": int(profile.get('l30d_chat_frequency_days', 0)),
            "l3m_chat_frequency_days": int(profile.get('l3m_chat_frequency_days', 0)),
            "avg_chat_interval_days": float(profile.get('avg_chat_interval_days', 0)),
            "churn_risk": profile.get('churn_risk', '未知'),
            "city": profile.get('city', 'Unknown'),
            "top_category": profile.get('top_category', 'Unknown'),
            "second_category": profile.get('second_category'),
            "third_category": profile.get('third_category'),
            "chat_history": chats,
            "total_refund_count": int(float(profile.get('historical_refund', 0)) / 1000) if float(profile.get('historical_refund', 0)) > 0 else 0
        }

        # 调用AI分析
        analysis = orchestrator.analyze_buyer_persona(
            buyer_nick=buyer_nick,
            profile=profile_data,
            chats=chats,
            orders=orders
        )

        return {
            "buyer_nick": buyer_nick,
            "status": "success",
            "analysis_method": analysis.get("analysis_method", "Unknown"),
            "confidence_level": analysis.get("confidence_level", "Unknown")
        }

    except Exception as e:
        return {
            "buyer_nick": buyer_nick,
            "status": "error",
            "error": str(e)
        }


def run_batch_analysis(
    dry_run: bool = False,
    max_buyers: int = 500
) -> Dict[str, Any]:
    """
    运行批量AI分析

    Args:
        dry_run: 是否为试运行（只打印不执行）
        max_buyers: 最大买家数

    Returns:
        分析结果汇总
    """
    print(f"\n{'='*60}")
    print(f"批量AI分析开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    # 初始化
    analyzer = TargetBuyerAnalyzer()
    orchestrator = get_analyzer_orchestrator()
    cost_monitor = get_cost_monitor()

    # 检查预算
    daily_summary = cost_monitor.get_daily_summary()
    budget_remaining = settings.ai_daily_budget - daily_summary.get("总成本", 0)

    print(f"[预算] 每日预算: ¥{settings.ai_daily_budget:.2f}")
    print(f"[预算] 今日已用: ¥{daily_summary.get('总成本', 0):.2f}")
    print(f"[预算] 剩余预算: ¥{budget_remaining:.2f}\n")

    if budget_remaining < 10:
        print("[警告] 剩余预算不足¥10，建议增加预算或等待明天")
        response = input("是否继续？(y/n): ")
        if response.lower() != 'y':
            return {"status": "cancelled", "reason": "预算不足"}

    # 获取买家列表
    buyers = get_buyers_for_analysis(max_buyers=max_buyers)

    if not buyers:
        print("[完成] 没有需要分析的买家")
        return {"status": "completed", "analyzed": 0, "failed": 0}

    # 试运行模式
    if dry_run:
        print(f"[试运行] 将分析以下 {len(buyers)} 个买家:")
        for i, buyer in enumerate(buyers[:10], 1):
            print(f"  {i}. {buyer['buyer_nick']} (VIP:{buyer['vip_level']}, L6M:¥{buyer['l6m_netsales']:.0f})")
        if len(buyers) > 10:
            print(f"  ... 还有 {len(buyers) - 10} 个买家")
        print(f"\n[估算] 预计成本: ¥{len(buyers) * 7:.2f} (假设每次¥7)")
        return {"status": "dry_run", "will_analyze": len(buyers)}

    # 批量分析
    results = {
        "success": [],
        "failed": [],
        "start_time": datetime.now().isoformat()
    }

    print(f"\n[分析] 开始批量分析 {len(buyers)} 个买家...\n")

    for i, buyer in enumerate(buyers, 1):
        buyer_nick = buyer["buyer_nick"]
        print(f"[{i}/{len(buyers)}] 分析 {buyer_nick} (VIP:{buyer['vip_level']})...", end=" ")

        result = analyze_buyer(buyer_nick, analyzer, orchestrator, cost_monitor)

        if result["status"] == "success":
            print(f"✓ ({result['analysis_method']}, 置信度:{result['confidence_level']})")
            results["success"].append(result)
        else:
            print(f"✗ ({result.get('error', 'Unknown error')})")
            results["failed"].append(result)

        # 避免API限流
        if i < len(buyers):
            time.sleep(1)

    # 汇总结果
    results["end_time"] = datetime.now().isoformat()
    results["total_analyzed"] = len(buyers)
    results["success_count"] = len(results["success"])
    results["failed_count"] = len(results["failed"])
    results["success_rate"] = round(len(results["success"]) / len(buyers) * 100, 2) if buyers else 0

    # 最终成本统计
    final_summary = cost_monitor.get_daily_summary()

    print(f"\n{'='*60}")
    print(f"批量分析完成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    print(f"总计: {len(buyers)} 个买家")
    print(f"成功: {len(results['success'])} 个 ({results['success_rate']}%)")
    print(f"失败: {len(results['failed'])} 个")
    print(f"\n今日成本统计:")
    print(f"  调用次数: {final_summary.get('调用次数', 0)}")
    print(f"  总成本: ¥{final_summary.get('总成本', 0):.2f}")
    print(f"  预算使用: {final_summary.get('预算使用率', 0):.1f}%")
    print(f"  预算余额: ¥{final_summary.get('预算余额', 0):.2f}")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="批量AI分析脚本")
    parser.add_argument("--dry-run", action="store_true", help="试运行（只打印不执行）")
    parser.add_argument("--max-buyers", type=int, default=500, help="最大买家数（默认500）")

    args = parser.parse_args()

    # 运行批量分析
    results = run_batch_analysis(
        dry_run=args.dry_run,
        max_buyers=args.max_buyers
    )

    # 退出码
    if results.get("status") == "cancelled":
        sys.exit(1)
    elif results.get("failed_count", 0) > 10:
        print(f"\n[警告] 失败数量过多: {results['failed_count']}")
        sys.exit(2)
    else:
        sys.exit(0)
