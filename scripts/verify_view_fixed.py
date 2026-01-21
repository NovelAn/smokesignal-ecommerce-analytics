"""
验证视图是否修复成功
"""
import pymysql
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

conn = pymysql.connect(
    host='rm-uf68p191h7j2o40s34o.mysql.rds.aliyuncs.com',
    user='novelan',
    password='Anna069832-',
    database='dunhill',
    port=3306,
    charset='utf8mb4'
)

print('验证视图修复状态...')
print('=' * 60)

with conn.cursor(pymysql.cursors.DictCursor) as cursor:
    # 检查视图数据
    cursor.execute('SELECT * FROM dunhill_t01_trade_line LIMIT 5')
    results = cursor.fetchall()

    if results:
        first = results[0]

        # 检查关键字段是否还是 1
        if first.get('买家昵称') == 1:
            print('❌ 视图仍然损坏（字段值还是 1）')
        else:
            print('✅ 视图修复成功！')
            print(f'\n样本数据（前 3 条）:')
            for row in results[:3]:
                nick = row.get('买家昵称', 'N/A')
                order = row.get('订单号', 'N/A')
                gmv = row.get('成交总金额', 0)
                refund = row.get('退款金额', 0)
                print(f'  {nick} | {order} | GMV:{gmv} | 退款:{refund}')

            # 统计总记录数
            cursor.execute('SELECT COUNT(*) as total FROM dunhill_t01_trade_line')
            total = cursor.fetchone()['total']
            print(f'\n视图总记录数: {total}')

            # 检查退款数据
            cursor.execute("""
                SELECT COUNT(*) as cnt,
                       SUM(退款金额) as total_refund
                FROM dunhill_t01_trade_line
                WHERE 退款金额 IS NOT NULL AND 退款金额 > 0
            """)
            refund_info = cursor.fetchone()
            print(f'有退款的记录: {refund_info["cnt"]} 条')
            print(f'总退款金额: {refund_info["total_refund"] or 0:.2f}')
    else:
        print('⚠️  视图返回 0 条记录')

conn.close()
print('\n' + '=' * 60)
