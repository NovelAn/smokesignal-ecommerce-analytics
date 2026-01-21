@echo off
REM 快速刷新目标买家预计算表（仅执行，无验证查询）
REM 这是最快的方式，直接调用存储过程

echo [%date% %time%] 开始刷新目标买家预计算表...

mysql -h rm-uf68p191h7j2o40s34o.mysql.rds.aliyuncs.com -u novelan -pAnna069832- dunhill -e "CALL refresh_target_buyers_precomputed();" 2>nul

if %errorlevel% equ 0 (
    echo [%date% %time%] ✓ 刷新成功！
) else (
    echo [%date% %time%] ✗ 刷新失败，错误代码: %errorlevel%
)

echo.
