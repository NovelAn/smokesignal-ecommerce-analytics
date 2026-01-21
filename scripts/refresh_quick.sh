#!/bin/bash
# 快速刷新目标买家预计算表（Linux/Mac）
# 这是最快的方式，直接调用存储过程

DB_HOST="rm-uf68p191h7j2o40s34o.mysql.rds.aliyuncs.com"
DB_USER="novelan"
DB_PASS="Anna069832-"
DB_NAME="dunhill"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始刷新..."

mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" -e "CALL refresh_target_buyers_precomputed();" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✓ 刷新成功！"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✗ 刷新失败！"
    exit 1
fi
