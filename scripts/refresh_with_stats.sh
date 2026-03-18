#!/bin/bash
# 刷新并显示简要统计（Linux/Mac）
# 推荐用于日常使用

DB_HOST="rm-uf68p191h7j2o40s34o.mysql.rds.aliyuncs.com"
DB_USER="novelan"
DB_PASS="Anna069832-"
DB_NAME="dunhill"

echo "========================================"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 目标买家预计算表刷新"
echo "========================================"
echo ""

echo "[1/2] 执行刷新..."
mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" -e "CALL refresh_target_buyers_precomputed();" 2>/dev/null

if [ $? -ne 0 ]; then
    echo "✗ 刷新失败！"
    exit 1
fi

echo ""
echo "[2/2] 获取统计信息..."
echo ""
echo "┌─────────────────────────────────────┐"
echo "│        刷新完成 - 数据统计          │"
echo "└─────────────────────────────────────┘"
echo ""

mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" --default-character-set=utf8mb4 -e "
SELECT
    CONCAT('📊 目标买家总数: ', COUNT(*)) as stat
FROM target_buyers_precomputed
UNION ALL
SELECT CONCAT('⏱️  最后更新: ', MAX(updated_at))
FROM target_buyers_precomputed
UNION ALL
SELECT CONCAT('🔥 Smoker: ', SUM(CASE WHEN buyer_type='SMOKER' THEN 1 ELSE 0 END))
FROM target_buyers_precomputed
UNION ALL
SELECT CONCAT('💎 VIC: ', SUM(CASE WHEN buyer_type='VIC' THEN 1 ELSE 0 END))
FROM target_buyers_precomputed
UNION ALL
SELECT CONCAT('👑 BOTH: ', SUM(CASE WHEN buyer_type='BOTH' THEN 1 ELSE 0 END))
FROM target_buyers_precomputed;
" 2>/dev/null

echo ""
echo "========================================"
echo "✓ 刷新完成！"
echo "========================================"
echo ""
