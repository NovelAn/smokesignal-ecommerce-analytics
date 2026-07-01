#!/bin/bash
# Cron wrapper for daily AI analysis
# Runs at 2 AM daily to analyze VIC and high-value buyers

# Change to project directory
cd "$(dirname "$0")/.."

# Log file
LOG_FILE="logs/daily_ai_analysis_$(date +\%Y\%m\%d).log"
mkdir -p logs

# Run the analysis script
echo "========================================" >> "$LOG_FILE"
echo "Starting daily AI analysis at $(date)" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

python scripts/daily_ai_analysis.py --max-buyers 500 >> "$LOG_FILE" 2>&1

# Check exit code
EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
    echo "✓ Daily AI analysis completed successfully" >> "$LOG_FILE"

    # 二刷本次（及历史）因 token 不足/接口异常降级到 rule-based 的客户，强制重走 LLM。
    # 跨天补救：某天 token 不足降级，次日 token 恢复后这里自动补回。
    # 依赖后端服务 localhost:8000 运行；未运行则跳过（|| 兜底，不影响 daily）。
    echo "Refreshing rule-based degraded buyers..." >> "$LOG_FILE"
    python scripts/refresh_rule_based.py >> "$LOG_FILE" 2>&1 || \
        echo "⚠ refresh_rule_based skipped/failed (后端未运行或无降级客户)" >> "$LOG_FILE"

    # Refresh keyword analysis cache (Keywords Analysis 面板每日刷新)
    # 之前漏调度，导致缓存停在 6/24 之后不再更新；Bug 1 修复
    echo "Refreshing keyword analysis cache..." >> "$LOG_FILE"
    python scripts/refresh_keyword_analysis_cache.py >> "$LOG_FILE" 2>&1 || \
        echo "⚠ refresh_keyword_analysis_cache skipped/failed" >> "$LOG_FILE"
else
    echo "✗ Daily AI analysis failed with exit code $EXIT_CODE" >> "$LOG_FILE"
fi

echo "========================================" >> "$LOG_FILE"
echo "Finished at $(date)" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# Optional: Send email on failure
# if [ $EXIT_CODE -ne 0 ]; then
#     mail -s "Daily AI Analysis Failed" admin@company.com < "$LOG_FILE"
# fi

exit $EXIT_CODE
