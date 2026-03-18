@echo off
REM 每日AI情感/意图分析任务
REM 通过Windows任务计划程序调用

cd /d "D:\Work\ai\projects\smokesignal-ecommerce-analytics"

REM 激活虚拟环境（如果有）
call venv\Scripts\activate.bat 2>nul

REM 运行分析脚本
python scripts\daily_ai_analysis.py --type sentiment --limit 200

echo.
echo [%date% %time%] AI分析完成
