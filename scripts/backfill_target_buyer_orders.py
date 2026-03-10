"""
补充target_buyer_orders表缺失的历史订单
用于修复部分客户订单数据不完整的问题

执行方式: python scripts/backfill_target_buyer_orders.py
"""
import sys
import os
import io

# 设置UTF-8编码输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import Database
from backend.config import settings


def backfill_missing_orders():
    """补充缺失的历史订单"""

    db_name = settings.db_name_to_use if settings.db_name_to_use else 'aliyun'
    db = Database(db_name=db_name)

    print("=" * 60)
    print("补充 target_buyer_orders 缺失的历史订单")
    print("=" * 60)

    # 1. 查找所有缺失订单的目标买家
    print("\n[1] 查找缺失订单的客户...")

    find_missing_query = """
    SELECT
        p.buyer_nick,
        p.total_orders as expected_orders,
        COALESCE(COUNT(o.订单号), 0) as current_orders,
        p.total_orders - COALESCE(COUNT(o.订单号), 0) as missing_orders
    FROM target_buyers_precomputed p
    LEFT JOIN target_buyer_orders o ON p.buyer_nick = o.买家昵称
    GROUP BY p.buyer_nick, p.total_orders
    HAVING missing_orders > 0
    ORDER BY missing_orders DESC
    """

    missing_buyers = db.execute_query(find_missing_query)

    if not missing_buyers:
        print("  [OK] 所有客户的订单数据都是完整的!")
        return

    print(f"  发现 {len(missing_buyers)} 个客户缺失订单:")
    for b in missing_buyers[:10]:  # 只显示前10个
        print(f"    - {b.get('buyer_nick')}: 缺失 {b.get('missing_orders')} 条")
    if len(missing_buyers) > 10:
        print(f"    ... 还有 {len(missing_buyers) - 10} 个客户")

    # 2. 为每个缺失的客户补充订单
    print("\n[2] 开始补充缺失的订单...")

    total_inserted = 0
    errors = []

    for buyer in missing_buyers:
        buyer_nick = buyer.get('buyer_nick')

        try:
            # 插入缺失的订单
            insert_query = """
            INSERT INTO target_buyer_orders (
                channel, 店铺名称, 订单号, 子订单号, 买家昵称, 买家openid, client_monthly_tag,
                平台创建时间, 付款时间, 付款日期, 最后付款时间, 子订单状态, 图片地址,
                是否聚划算, 预售单状态, 天猫ID, 天猫商品编码, 天猫款号, 天猫外部编码,
                条形码, 商品名称, 宝尊商品编码, 件数, 商品划线价, 划线价总金额,
                优惠金额, 应付总金额, 成交单价, 成交总金额, 省份, 城市,
                退款类型, 退款金额, 退款完结时间, 退款完结日期, 退款原因,
                商品sku属性, skc, product_name, rsp, oms_category, category,
                main_category, division, season_by_arrival, season_by_code,
                commercial_line, FP_MD, 是否分期, 分期数, 是否免息,
                livestream_flag, 直播场次ID, 直播场次标题, 直播开播时间,
                直播确认收货时间, 直播确认收货金额, ff_flag, sc_flag,
                sc来源, sc推广日期, pay_year, pay_season, pay_month, pay_week
            )
            SELECT
                channel, 店铺名称, 订单号, 子订单号, 买家昵称, 买家openid, client_monthly_tag,
                平台创建时间, 付款时间, 付款日期, 最后付款时间, 子订单状态, 图片地址,
                是否聚划算, 预售单状态, 天猫ID, 天猫商品编码, 天猫款号, 天猫外部编码,
                条形码, 商品名称, 宝尊商品编码, 件数, 商品划线价, 划线价总金额,
                优惠金额, 应付总金额, 成交单价, 成交总金额, 省份, 城市,
                退款类型, 退款金额, 退款完结时间, 退款完结日期, 退款原因,
                商品sku属性, skc, product_name, rsp, oms_category, category,
                main_category, division, season_by_arrival, season_by_code,
                commercial_line, FP_MD, 是否分期, 分期数, 是否免息,
                livestream_flag, 直播场次ID, 直播场次标题, 直播开播时间,
                直播确认收货时间, 直播确认收货金额, ff_flag, sc_flag,
                sc来源, sc推广日期, pay_year, pay_season, pay_month, pay_week
            FROM dunhill_t01_trade_line
            WHERE 买家昵称 = %s
              AND 订单号 NOT IN (
                  SELECT 订单号 FROM target_buyer_orders WHERE 买家昵称 = %s
              )
            """

            db.execute_update(insert_query, [buyer_nick, buyer_nick])

            # 获取插入的行数
            count_query = """
            SELECT COUNT(*) as cnt FROM target_buyer_orders WHERE 买家昵称 = %s
            """
            result = db.execute_query(count_query, [buyer_nick])
            new_count = result[0].get('cnt') if result else 0

            inserted = new_count - buyer.get('current_orders', 0)
            if inserted > 0:
                total_inserted += inserted
                print(f"  [OK] {buyer_nick}: 补充了 {inserted} 条订单")

        except Exception as e:
            errors.append(f"{buyer_nick}: {str(e)}")
            print(f"  [FAIL] {buyer_nick}: 失败 - {str(e)[:50]}")

    # 3. 输出统计
    print("\n" + "=" * 60)
    print("补充完成!")
    print("=" * 60)
    print(f"  处理客户数: {len(missing_buyers)}")
    print(f"  补充订单总数: {total_inserted}")
    print(f"  失败数: {len(errors)}")

    if errors:
        print("\n失败详情:")
        for e in errors[:5]:
            print(f"  - {e}")

    # 4. 验证特定客户
    print("\n[验证] zhaixiangming888 订单数:")
    verify_query = """
    SELECT COUNT(*) as cnt FROM target_buyer_orders WHERE 买家昵称 = %s
    """
    result = db.execute_query(verify_query, ['zhaixiangming888'])
    if result:
        print(f"  当前订单数: {result[0].get('cnt')}")


if __name__ == "__main__":
    backfill_missing_orders()
