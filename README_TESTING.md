# Testing Guide

## Overview
Sentrix sử dụng pytest framework cho testing với 3 loại tests:
- **Unit Tests**: Test business logic và utility functions
- **Integration Tests**: Test API endpoints
- **E2E Tests**: Test complete user flows với Selenium

## Setup

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Run Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_models.py

# Run with verbose output
pytest -v
```

## Test Structure

```
tests/
├── __init__.py
├── conftest.py          # Pytest fixtures
├── test_models.py       # Unit tests for models
├── test_security_utils.py  # Unit tests for security utilities
├── test_auth.py         # Integration tests for authentication
├── test_integration.py  # Integration tests for API
└── test_e2e.py          # End-to-end tests (requires running app)
```

## Fixtures

### `client`
Test client without authentication

### `auth_client`
Test client with authenticated user (testadmin/testpass)

### `sample_camera`
Sample camera object for testing

## Writing Tests

### Unit Test Example
```python
def test_password_validation():
    is_valid, error = validate_password('Test123!')
    assert is_valid is True
    assert error is None
```

### Integration Test Example
```python
def test_login_success(client):
    response = client.post('/login', data={
        'username': 'testadmin',
        'password': 'testpass'
    })
    assert response.status_code == 200
```

## E2E Tests

E2E tests require:
1. Running Flask application
2. Selenium WebDriver (Chrome)
3. ChromeDriver installed

To run E2E tests:
```bash
# Start Flask app in one terminal
python app.py

# Run E2E tests in another terminal
pytest tests/test_e2e.py
```

## Coverage

Coverage reports are generated in `htmlcov/` directory. Open `htmlcov/index.html` in browser to view detailed coverage.
