# Xbooking API Test Suite

This directory contains comprehensive test suites for the Xbooking API authentication endpoints.

## Test Structure

```
user/tests/
├── __init__.py
├── registration/
│   ├── __init__.py
│   ├── test_unit.py          # Unit tests for registration
│   ├── test_api.py           # API tests for registration endpoint
│   └── test_integration.py   # Integration tests for registration
└── login/
    ├── __init__.py
    ├── test_unit.py          # Unit tests for login
    ├── test_api.py           # API tests for login endpoint
    └── test_integration.py   # Integration tests for login
```

## Test Types

### 1. Unit Tests (`test_unit.py`)
- Test individual components in isolation
- Model methods, serializer validation, helper functions
- Fast execution, no external dependencies

### 2. API Tests (`test_api.py`)
- Test HTTP endpoints directly
- Request/response validation
- Status codes and response formats

### 3. Integration Tests (`test_integration.py`)
- Test complete flows end-to-end
- Database transactions, token generation
- Component interaction testing

## Running Tests

### Run All Tests
```bash
python manage.py test user.tests
```

### Run Specific Test Suites

#### Registration Tests
```bash
# All registration tests
python manage.py test user.tests.registration

# Registration unit tests only
python manage.py test user.tests.registration.test_unit

# Registration API tests only
python manage.py test user.tests.registration.test_api

# Registration integration tests only
python manage.py test user.tests.registration.test_integration
```

#### Login Tests
```bash
# All login tests
python manage.py test user.tests.login

# Login unit tests only
python manage.py test user.tests.login.test_unit

# Login API tests only
python manage.py test user.tests.login.test_api

# Login integration tests only
python manage.py test user.tests.login.test_integration
```

### Using the Test Runner Script
```bash
# Run all tests
python run_tests.py

# Run specific test suite
python run_tests.py registration_unit
python run_tests.py login_api
python run_tests.py all_registration
```

## Test Coverage

### Registration Endpoint Tests
- ✅ User model creation and validation
- ✅ Password hashing and verification
- ✅ Email uniqueness validation
- ✅ Avatar URL generation
- ✅ Serializer field validation
- ✅ API endpoint responses
- ✅ JWT token generation
- ✅ Error handling
- ✅ Database transactions

### Login Endpoint Tests
- ✅ User authentication
- ✅ Password verification
- ✅ Inactive user handling
- ✅ Last login update
- ✅ JWT token generation
- ✅ API endpoint responses
- ✅ Error handling
- ✅ Multiple login attempts

## Test Data

### Valid Registration Data
```json
{
  "full_name": "John Doe",
  "email": "john.doe@example.com",
  "password": "SecurePass123!",
  "confirm_password": "SecurePass123!"
}
```

### Valid Login Data
```json
{
  "email": "test@example.com",
  "password": "TestPassword123!"
}
```

## Test Scenarios Covered

### Registration Tests
1. **Successful Registration**
   - Valid data creates user
   - Password is hashed
   - JWT tokens generated
   - Avatar URL created

2. **Validation Failures**
   - Invalid email format
   - Duplicate email
   - Password mismatch
   - Weak passwords
   - Missing fields

3. **Error Handling**
   - Server errors
   - Database constraints
   - External service failures

### Login Tests
1. **Successful Login**
   - Valid credentials authenticate
   - JWT tokens generated
   - Last login updated
   - User data returned

2. **Authentication Failures**
   - Invalid email
   - Wrong password
   - Inactive users
   - Missing fields

3. **Security Tests**
   - Password not in response
   - Token validation
   - Multiple login attempts

## Assertions and Validations

### Response Structure Validation
- Status codes
- Response format consistency
- Required fields presence
- Data types and values

### Database State Validation
- User creation/updates
- Password hashing
- Constraint enforcement
- Transaction integrity

### Security Validation
- Password not exposed
- JWT token validity
- Authentication flows
- Error message safety

## Mock Testing

Tests include mocking for:
- External API calls (DiceBear avatar generation)
- Database errors
- Authentication failures
- Network timeouts

## Performance Considerations

- Tests use `TransactionTestCase` for integration tests
- Database rollback between tests
- Minimal test data creation
- Fast assertion methods

## Best Practices

1. **Test Independence**: Each test can run independently
2. **Clear Naming**: Test names describe what they test
3. **Setup/Teardown**: Proper test data management
4. **Assertions**: Specific and meaningful assertions
5. **Coverage**: Test both success and failure cases
6. **Documentation**: Clear test descriptions and comments

## Continuous Integration

These tests are designed to run in CI environments:
- No external dependencies
- Consistent test data
- Proper database handling
- Clear pass/fail criteria

## Adding New Tests

When adding new tests:
1. Follow the existing structure
2. Use appropriate test type (unit/api/integration)
3. Include both positive and negative test cases
4. Update this README if needed
5. Ensure tests are independent and repeatable
