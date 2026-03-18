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
