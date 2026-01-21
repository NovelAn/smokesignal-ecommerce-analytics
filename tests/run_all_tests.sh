#!/bin/bash
# Run all tests for SmokeSignal Analytics

echo "🧪 Running SmokeSignal Analytics Test Suite"
echo "==========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Test counter
TOTAL=0
PASSED=0
FAILED=0

# Function to run a test
run_test() {
    local test_file=$1
    local test_name=$2

    echo "Running: $test_name"
    TOTAL=$((TOTAL + 1))

    if python "$test_file"; then
        echo -e "${GREEN}✓ PASSED${NC}: $test_name"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}✗ FAILED${NC}: $test_name"
        FAILED=$((FAILED + 1))
    fi
    echo ""
}

# Run all tests
run_test "tests/database/test_db_connection.py" "Database Connection Test"
run_test "tests/api/test_api_endpoints.py" "API Endpoints Test"
run_test "tests/integration/test_api_integration.py" "API Integration Test"

# Summary
echo "==========================================="
echo "Test Summary:"
echo "  Total:   $TOTAL"
echo -e "  ${GREEN}Passed:  $PASSED${NC}"
if [ $FAILED -gt 0 ]; then
    echo -e "  ${RED}Failed:  $FAILED${NC}"
    exit 1
else
    echo "  Failed:  $FAILED"
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
fi
