# Tests Directory

This directory contains all test files for the SmokeSignal Analytics project.

## Directory Structure

```
tests/
├── api/                    # API endpoint tests
│   └── test_api_endpoints.py
├── database/               # Database connection and query tests
│   └── test_db_connection.py
├── integration/            # Integration tests
│   └── test_api_integration.py
└── README.md              # This file
```

## Test Categories

### 1. API Tests (`api/`)
Tests for individual API endpoints:
- Request/response validation
- Status code checks
- Data format verification
- Error handling

**Note**: This directory does not contain `__init__.py` files because tests are run directly as scripts, not imported as packages.

**Run API tests:**
```bash
cd /Users/novel/Documents/trae_projects/smokesignal-ecommerce-analytics
python tests/api/test_api_endpoints.py
```

### 2. Database Tests (`database/`)
Tests for database connectivity and operations:
- Connection verification
- Query execution
- Data integrity checks

**Run database tests:**
```bash
python tests/database/test_db_connection.py
```

### 3. Integration Tests (`integration/`)
End-to-end tests that verify multiple components working together:
- Full API workflow
- Data pipeline validation
- Cross-component integration

**Run integration tests:**
```bash
python tests/integration/test_api_integration.py
```

## Running All Tests

### Run all tests manually:
```bash
# From project root
python tests/api/test_api_endpoints.py
python tests/database/test_db_connection.py
python tests/integration/test_api_integration.py
```

### Run all tests with a script (to be created):
```bash
# TODO: Create run_all_tests.py script
python tests/run_all_tests.py
```

## Test Coverage

Currently, the project has basic tests for:
- ✅ API endpoint connectivity
- ✅ Database connection
- ✅ API integration workflow

### Planned Test Additions:
- [ ] Unit tests for backend analytics modules
- [ ] Unit tests for utility functions
- [ ] Component tests for React frontend
- [ ] E2E tests with Playwright
- [ ] Performance tests
- [ ] Security tests (SQL injection, etc.)

## Writing New Tests

### Naming Convention
- Test files should start with `test_`
- Use descriptive names: `test_<feature>_<scenario>.py`
- Example: `test_buyer_analyzer_churn_calculation.py`

### Test Structure
```python
"""
Test description
"""
import unittest
# or import pytest

class TestFeature(unittest.TestCase):
    def test_scenario(self):
        """Test description"""
        # Arrange
        # Act
        # Assert
        pass

if __name__ == '__main__':
    unittest.main()
```

### Best Practices
1. **Isolation**: Each test should be independent
2. **Clarity**: Use descriptive test names
3. **Setup/Teardown**: Properly manage test data
4. **Assertions**: Be specific in assertions
5. **Documentation**: Comment complex test logic

## Test Environment Setup

### Requirements
Create a `requirements-test.txt` file:
```txt
pytest
pytest-asyncio
pytest-cov
httpx
```

### Environment Variables
Tests may require:
```bash
export TEST_DATABASE_URL="mysql://user:pass@localhost/test_db"
export API_BASE_URL="http://localhost:8000"
```

## Continuous Integration

TODO: Add CI/CD configuration
- [ ] GitHub Actions workflow
- [ ] Automated test runs on push
- [ ] Test coverage reporting

## Test Data

TODO: Create test data fixtures
- [ ] Sample buyer data
- [ ] Mock chat messages
- [ ] Test database schema

## Resources

- [Python unittest documentation](https://docs.python.org/3/library/unittest.html)
- [pytest documentation](https://docs.pytest.org/)
- [FastAPI testing guide](https://fastapi.tiangolo.com/tutorial/testing/)

---

**Note**: This is a basic test structure. As the project grows, consider implementing a more comprehensive testing framework with pytest and coverage reporting.
