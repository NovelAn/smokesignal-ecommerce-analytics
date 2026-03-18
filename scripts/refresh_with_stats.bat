@echo off
REM 刷新并显示简要统计（推荐用于日常使用）
REM 快速刷新 + 关键指标展示

echo ========================================
echo [%date% %time%] 目标买家预计算表刷新
echo ========================================
echo.

echo [1/2] 执行刷新...
mysql -h rm-uf68p191h7j2o40s34o.mysql.rds.aliyuncs.com -u novelan -pAnna069832- dunhill -e "CALL refresh_target_buyers_precomputed();" 2>nul

if %errorlevel% neq 0 (
    echo ✗ 刷新失败！
    pause
    exit /b 1
)

echo.
echo [2/2] 获取统计信息...
echo.
echo ┌─────────────────────────────────────┐
echo │        刷新完成 - 数据统计          │
echo └─────────────────────────────────────┘
echo.

mysql -h rm-uf68p191h7j2o40s34o.mysql.rds.aliyuncs.com -u novelan -pAnna069832- dunhill --default-character-set=utf8mb4 -e "
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
" 2>nul

echo.
echo ========================================
echo ✓ 刷新完成！
echo ========================================
echo.
