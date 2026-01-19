#!/usr/bin/env python3
"""
Run all tests for SmokeSignal Analytics

Usage:
    python run_all_tests.py
"""
import subprocess
import sys
from pathlib import Path

# Colors for terminal output
class Colors:
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    YELLOW = '\033[0;33m'
    NC = '\033[0m'  # No Color

def run_test(test_file: str, test_name: str) -> bool:
    """Run a single test file and return True if passed"""
    print(f"Running: {test_name}")

    try:
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            print(f"{Colors.GREEN}✓ PASSED{Colors.NC}: {test_name}")
            return True
        else:
            print(f"{Colors.RED}✗ FAILED{Colors.NC}: {test_name}")
            if result.stdout:
                print(f"Output: {result.stdout}")
            if result.stderr:
                print(f"Error: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print(f"{Colors.YELLOW}⏱ TIMEOUT{Colors.NC}: {test_name}")
        return False
    except Exception as e:
        print(f"{Colors.RED}✗ ERROR{Colors.NC}: {test_name} - {e}")
        return False

def main():
    """Run all tests and display summary"""
    print("🧪 Running SmokeSignal Analytics Test Suite")
    print("=" * 50)
    print()

    # Get project root
    project_root = Path(__file__).parent.parent
    tests_dir = project_root / "tests"

    # Define tests to run
    tests = [
        ("tests/database/test_db_connection.py", "Database Connection Test"),
        ("tests/api/test_api_endpoints.py", "API Endpoints Test"),
        ("tests/integration/test_api_integration.py", "API Integration Test"),
    ]

    total = len(tests)
    passed = 0
    failed = 0

    # Run all tests
    for test_file, test_name in tests:
        test_path = project_root / test_file
        if test_path.exists():
            if run_test(str(test_path), test_name):
                passed += 1
            else:
                failed += 1
        else:
            print(f"{Colors.YELLOW}⚠ SKIPPED{Colors.NC}: {test_name} (file not found)")
            total -= 1
        print()

    # Summary
    print("=" * 50)
    print("Test Summary:")
    print(f"  Total:   {total}")
    print(f"  {Colors.GREEN}Passed:  {passed}{Colors.NC}")
    print(f"  {Colors.RED}Failed:  {failed}{Colors.NC}")

    if failed == 0:
        print(f"\n{Colors.GREEN}All tests passed!{Colors.NC}")
        return 0
    else:
        print(f"\n{Colors.RED}Some tests failed!{Colors.NC}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
