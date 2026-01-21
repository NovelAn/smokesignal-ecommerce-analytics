#!/bin/bash
# 部署目标买家预计算表 - 使用mysql命令行
# 这样可以正确执行DELIMITER和多语句的SQL

echo "🚀 开始部署目标买家预计算表"
echo "========================================"

# 数据库配置
DB_HOST="rm-uf68p191h7j2o40s34o.mysql.rds.aliyuncs.com"
DB_USER="novelan"
DB_PASS="Anna069832-"
DB_NAME="dunhill"
SQL_FILE="/Users/novel/Documents/trae_projects/smokesignal-ecommerce-analytics/backend/database/sql/create_target_buyers_precomputed.sql"

echo ""
echo "📄 执行SQL文件: $SQL_FILE"
echo "📍 目标数据库: $DB_NAME@$DB_HOST"
echo ""

# 执行SQL脚本
mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" < "$SQL_FILE"

echo ""
echo "========================================"
echo "🔍 验证部署结果"
echo "========================================"

# 检查表是否创建
mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" -e "SHOW TABLES LIKE 'target_buyers_precomputed';"

# 检查数据量
mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" -e "SELECT COUNT(*) as total FROM target_buyers_precomputed;"

# 按类型统计
mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" -e "SELECT buyer_type, COUNT(*) as count FROM target_buyers_precomputed GROUP BY buyer_type;"

# 检查前5条数据
mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" -e "SELECT buyer_nick, buyer_type, vip_level, client_monthly_tag, historical_net_sales FROM target_buyers_precomputed LIMIT 5;"

echo ""
echo "✅ 部署完成!"
echo ""
echo "📝 下一步:"
echo "1. 如果数据为0，请手动执行: CALL refresh_target_buyers_precomputed();"
echo "2. 启动后端服务: cd backend && python -m uvicorn main:app --reload"
echo "3. 测试新API: curl http://localhost:8000/api/v2/buyers?limit=10"
