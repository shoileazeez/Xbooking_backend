"""
XBooking E2E Test Suite Runner
Runs all E2E tests and generates a summary report

Tests included:
1. test_hourly_booking_e2e.py - Hourly booking flow
2. test_daily_booking_e2e.py - Daily booking flow  
3. test_monthly_booking_e2e.py - Monthly booking with multi-day check-ins
4. test_cart_multi_space_e2e.py - Cart with multiple spaces
5. test_admin_checkin_e2e.py - Admin check-in/check-out flow

Usage:
    python run_all_e2e_tests.py [--test <test_name>] [--skip-payment]

Options:
    --test <name>     Run only a specific test (hourly, daily, monthly, cart, admin)
    --skip-payment    Skip payment wait steps
    --dry-run         Just list tests without running
"""
import subprocess
import sys
import os
import time
from datetime import datetime

# Define all test files
TESTS = {
    'hourly': 'test_hourly_booking_e2e.py',
    'daily': 'test_daily_booking_e2e.py',
    'monthly': 'test_monthly_booking_e2e.py',
    'cart': 'test_cart_multi_space_e2e.py',
    'admin': 'test_admin_checkin_e2e.py',
    'e2e': 'e2e_api_test.py',
    'cart_original': 'test_cart.py',
}

TEST_DESCRIPTIONS = {
    'hourly': 'Hourly Booking Flow (2-hour slot)',
    'daily': 'Daily Booking Flow (full day)',
    'monthly': 'Monthly Booking Flow (28/30/31 check-ins)',
    'cart': 'Cart Multi-Space Flow (multiple workspaces)',
    'admin': 'Admin Check-in/Check-out Flow',
    'e2e': 'Original E2E Test (full flow)',
    'cart_original': 'Original Cart Test',
}


def print_header(text):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_subheader(text):
    print("\n" + "-" * 50)
    print(f"  {text}")
    print("-" * 50)


def run_test(test_name, test_file, skip_payment=False):
    """Run a single test and return result"""
    print_subheader(f"Running: {TEST_DESCRIPTIONS.get(test_name, test_name)}")
    print(f"File: {test_file}")
    
    start_time = time.time()
    
    # Check if file exists
    if not os.path.exists(test_file):
        print(f"❌ Test file not found: {test_file}")
        return {
            'name': test_name,
            'file': test_file,
            'success': False,
            'error': 'File not found',
            'duration': 0
        }
    
    try:
        # Run the test
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        duration = time.time() - start_time
        success = result.returncode == 0
        
        # Print output
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return {
            'name': test_name,
            'file': test_file,
            'success': success,
            'error': result.stderr if not success else None,
            'duration': duration
        }
        
    except subprocess.TimeoutExpired:
        print(f"❌ Test timed out after 5 minutes")
        return {
            'name': test_name,
            'file': test_file,
            'success': False,
            'error': 'Timeout',
            'duration': 300
        }
    except Exception as e:
        print(f"❌ Error running test: {e}")
        return {
            'name': test_name,
            'file': test_file,
            'success': False,
            'error': str(e),
            'duration': time.time() - start_time
        }


def run_all_tests(selected_tests=None, skip_payment=False, dry_run=False):
    """Run all tests and generate report"""
    print_header("XBooking E2E Test Suite")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Determine which tests to run
    if selected_tests:
        tests_to_run = {k: v for k, v in TESTS.items() if k in selected_tests}
    else:
        # Default: run new tests only (not original e2e and cart)
        tests_to_run = {k: v for k, v in TESTS.items() if k not in ['e2e', 'cart_original']}
    
    print(f"\nTests to run: {len(tests_to_run)}")
    for name, file in tests_to_run.items():
        print(f"  - {name}: {TEST_DESCRIPTIONS.get(name, file)}")
    
    if dry_run:
        print("\n[DRY RUN] Would run the above tests")
        return
    
    results = []
    
    for test_name, test_file in tests_to_run.items():
        result = run_test(test_name, test_file, skip_payment)
        results.append(result)
        
        # Small delay between tests
        if len(tests_to_run) > 1:
            print("\n⏳ Waiting 5 seconds before next test...")
            time.sleep(5)
    
    # Generate report
    print_header("Test Results Summary")
    
    passed = sum(1 for r in results if r['success'])
    failed = sum(1 for r in results if not r['success'])
    total_duration = sum(r['duration'] for r in results)
    
    print(f"\n📊 Overall Results:")
    print(f"   Total Tests: {len(results)}")
    print(f"   ✅ Passed: {passed}")
    print(f"   ❌ Failed: {failed}")
    print(f"   ⏱️  Total Duration: {total_duration:.1f}s")
    
    print(f"\n📋 Individual Results:")
    for r in results:
        status = "✅" if r['success'] else "❌"
        print(f"   {status} {r['name']}: {r['duration']:.1f}s")
        if r['error'] and not r['success']:
            print(f"      Error: {r['error'][:100]}...")
    
    # Generate log file
    report_file = f"e2e_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_file, 'w') as f:
        f.write("XBooking E2E Test Report\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Total: {len(results)}, Passed: {passed}, Failed: {failed}\n\n")
        for r in results:
            status = "PASS" if r['success'] else "FAIL"
            f.write(f"{status} - {r['name']} ({r['file']}) - {r['duration']:.1f}s\n")
            if r['error']:
                f.write(f"   Error: {r['error']}\n")
        f.write("\n")
    
    print(f"\n📄 Report saved to: {report_file}")
    
    return passed == len(results)


def print_usage():
    print(__doc__)
    print("\nAvailable tests:")
    for name, desc in TEST_DESCRIPTIONS.items():
        print(f"  {name}: {desc}")


if __name__ == "__main__":
    args = sys.argv[1:]
    
    if '--help' in args or '-h' in args:
        print_usage()
        sys.exit(0)
    
    selected_tests = []
    skip_payment = '--skip-payment' in args
    dry_run = '--dry-run' in args
    
    if '--test' in args:
        idx = args.index('--test')
        if idx + 1 < len(args):
            test_name = args[idx + 1]
            if test_name in TESTS:
                selected_tests.append(test_name)
            else:
                print(f"Unknown test: {test_name}")
                print_usage()
                sys.exit(1)
    
    try:
        success = run_all_tests(
            selected_tests=selected_tests if selected_tests else None,
            skip_payment=skip_payment,
            dry_run=dry_run
        )
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Test suite interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
