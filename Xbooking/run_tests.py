"""
Test runner script for Xbooking API
Run specific test suites or all tests
"""

import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner

if __name__ == "__main__":
    os.environ['DJANGO_SETTINGS_MODULE'] = 'Xbooking.settings'
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    
    # Available test suites
    test_suites = {
        'registration_unit': 'user.tests.registration.test_unit',
        'registration_api': 'user.tests.registration.test_api',
        'registration_integration': 'user.tests.registration.test_integration',
        'login_unit': 'user.tests.login.test_unit',
        'login_api': 'user.tests.login.test_api',
        'login_integration': 'user.tests.login.test_integration',
        'all_registration': 'user.tests.registration',
        'all_login': 'user.tests.login',
        'all': 'user.tests'
    }
    
    if len(sys.argv) > 1:
        test_name = sys.argv[1]
        if test_name in test_suites:
            failures = test_runner.run_tests([test_suites[test_name]])
        else:
            print(f"Available test suites: {list(test_suites.keys())}")
            sys.exit(1)
    else:
        # Run all tests
        failures = test_runner.run_tests(['user.tests'])
    
    if failures:
        sys.exit(1)
