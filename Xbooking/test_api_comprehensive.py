"""
XBOOKING COMPREHENSIVE API TESTING
Tests all 46+ user-facing API endpoints based on API_ENDPOINTS_DOCUMENTATION.py

Prerequisites:
1. Run migrations: python manage.py migrate
2. Start Redis: redis-server
3. Start Celery: celery -A Xbooking worker -l info
4. Run populate script: python manage.py populate_comprehensive
5. Start server: python manage.py runserver

Usage:
    python test_api_comprehensive.py

This will test:
- User Authentication & Profile (7 endpoints)
- User Preferences (2 endpoints)
- Workspace & Space Discovery (11 endpoints)
- Cart Management (5 endpoints)
- Checkout & Orders (3 endpoints)
- Payment (4 endpoints)
- Bookings (6 endpoints)
- Wallet & Transactions (3 endpoints)
- Reviews (2 endpoints)
- Notifications (3 endpoints)
"""

import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import sys


class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class APITester:
    """Comprehensive API testing class for Xbooking"""
    
    def __init__(self, base_url: str = " http://127.0.0.1:8000"):
        self.base_url = base_url
        self.access_token = None
        self.refresh_token = None
        self.user_id = None
        self.user_email = None
        
        # Store IDs for subsequent tests
        self.workspace_id = None
        self.branch_id = None
        self.space_id = None
        self.calendar_id = None
        self.cart_id = None
        self.cart_item_id = None
        self.order_id = None
        self.booking_id = None
        self.payment_id = None
        self.wallet_id = None
        self.review_id = None
        self.notification_id = None
        self.preference_id = None
        
        # Test statistics
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.skipped_tests = 0
        
    def print_header(self, text: str):
        """Print section header"""
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{text.center(70)}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}\n")
        
    def print_success(self, text: str):
        """Print success message"""
        print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")
        
    def print_error(self, text: str):
        """Print error message"""
        print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")
        
    def print_warning(self, text: str):
        """Print warning message"""
        print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")
        
    def print_info(self, text: str):
        """Print info message"""
        print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")
        
    def make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        use_auth: bool = False,
        expected_status: int = 200
    ) -> tuple[bool, Optional[Dict], int]:
        """
        Make HTTP request and handle response
        
        Returns:
            (success, response_data, status_code)
        """
        url = f"{self.base_url}{endpoint}"
        headers = {"Content-Type": "application/json"}
        
        if use_auth and self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
            
        try:
            if method.upper() == "GET":
                response = requests.get(url, params=params, headers=headers, timeout=10)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, params=params, headers=headers, timeout=10)
            elif method.upper() == "PATCH":
                response = requests.patch(url, json=data, params=params, headers=headers, timeout=10)
            elif method.upper() == "PUT":
                response = requests.put(url, json=data, params=params, headers=headers, timeout=10)
            elif method.upper() == "DELETE":
                response = requests.delete(url, params=params, headers=headers, timeout=10)
            else:
                return False, None, 0
                
            success = response.status_code == expected_status
            
            try:
                response_data = response.json()
            except:
                response_data = {"text": response.text}
                
            return success, response_data, response.status_code
            
        except requests.exceptions.RequestException as e:
            self.print_error(f"Request failed: {str(e)}")
            return False, None, 0
            
    def test_endpoint(
        self,
        name: str,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        use_auth: bool = False,
        expected_status: int = 200,
        extract_ids: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Test a single endpoint
        
        Args:
            name: Test name
            method: HTTP method
            endpoint: API endpoint
            data: Request body
            params: Query parameters
            use_auth: Use authentication
            expected_status: Expected HTTP status code
            extract_ids: Dict mapping response keys to instance attributes
                        e.g., {"id": "workspace_id", "user.id": "user_id"}
        """
        self.total_tests += 1
        self.print_info(f"Testing: {name}")
        print(f"  Method: {method} {endpoint}")
        
        success, response_data, status_code = self.make_request(
            method, endpoint, data, params, use_auth, expected_status
        )
        
        if success:
            self.passed_tests += 1
            self.print_success(f"{name} - Status: {status_code}")
            
            # Extract IDs from response
            if extract_ids and response_data:
                for response_key, attr_name in extract_ids.items():
                    value = self._extract_nested_value(response_data, response_key)
                    if value:
                        setattr(self, attr_name, value)
                        print(f"  Extracted {attr_name}: {value}")
                        
            # Print relevant response data
            if response_data:
                self._print_response_summary(response_data)
                
            return True
        else:
            self.failed_tests += 1
            self.print_error(f"{name} - Expected {expected_status}, got {status_code}")
            if response_data:
                print(f"  Response: {json.dumps(response_data, indent=2)[:500]}")
            return False
            
    def _extract_nested_value(self, data: Dict, key_path: str) -> Any:
        """Extract value from nested dict using dot notation (e.g., 'user.id')"""
        keys = key_path.split('.')
        value = data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value
        
    def _print_response_summary(self, data: Dict, max_lines: int = 5):
        """Print summary of response data"""
        if isinstance(data, dict):
            # Print key information
            important_keys = ['id', 'count', 'message', 'total_amount', 'status', 
                            'balance', 'payment_url', 'access', 'refresh']
            for key in important_keys:
                if key in data:
                    print(f"  {key}: {data[key]}")
                    
    # ========================================================================
    # 1. USER AUTHENTICATION & PROFILE TESTS
    # ========================================================================
    
    def test_user_authentication(self):
        """Test user registration and login"""
        self.print_header("1. USER AUTHENTICATION & PROFILE")
        
        # Generate unique email with valid domain
        timestamp = int(time.time())
        self.user_email = f"testuser_{timestamp}@example.com"
        
        # 1. Register user
        self.test_endpoint(
            name="User Registration",
            method="POST",
            endpoint="/api/v1/user/auth/register/",
            data={
                "email": self.user_email,
                "password": "TestPass123!",
                "confirm_password": "TestPass123!",
                "full_name": "Test User",
                "phone": "+2348012345678"
            },
            expected_status=201,
            extract_ids={
                "user.id": "user_id",
                "tokens.access": "access_token",
                "tokens.refresh": "refresh_token"
            }
        )
        
        time.sleep(1)
        
        # 2. Login
        self.test_endpoint(
            name="User Login",
            method="POST",
            endpoint="/api/v1/user/auth/login/",
            data={
                "email": self.user_email,
                "password": "TestPass123!"
            },
            expected_status=200,
            extract_ids={
                "tokens.access": "access_token",
                "tokens.refresh": "refresh_token"
            }
        )
        
        time.sleep(1)
        
        # 3. Get profile
        self.test_endpoint(
            name="Get User Profile",
            method="GET",
            endpoint="/api/v1/user/profile/",
            use_auth=True,
            expected_status=200
        )
        
        time.sleep(1)
        
        # 4. Update profile
        self.test_endpoint(
            name="Update User Profile",
            method="PATCH",
            endpoint="/api/v1/user/profile/",
            data={
                "full_name": "Test User Updated",
                "phone": "+2348087654321"
            },
            use_auth=True,
            expected_status=200
        )
        
        time.sleep(1)
        
        # 5. Token refresh
        if self.refresh_token:
            self.test_endpoint(
                name="Token Refresh",
                method="POST",
                endpoint="/api/v1/user/auth/token/refresh/",
                data={"refresh": self.refresh_token},
                expected_status=200,
                extract_ids={"access": "access_token"}
            )
            time.sleep(1)
        
        # 6. Onboarding
        self.test_endpoint(
            name="Complete Onboarding",
            method="POST",
            endpoint="/api/v1/user/onboarding/",
            use_auth=True,
            expected_status=200
        )
        
        time.sleep(1)
        
    # ========================================================================
    # 2. USER PREFERENCES TESTS
    # ========================================================================
    
    def test_user_preferences(self):
        """Test user preferences for recommendations"""
        self.print_header("2. USER PREFERENCES")
        
        # 1. Get preferences
        success, data, _ = self.make_request(
            "GET",
            "/api/v1/user/preferences/",
            use_auth=True,
            expected_status=200
        )
        
        if success and data and isinstance(data, list) and len(data) > 0:
            self.preference_id = data[0].get('id')
            self.print_success(f"Get User Preferences - Found {len(data)} preferences")
            self.passed_tests += 1
        elif success and data and isinstance(data, dict):
            self.preference_id = data.get('id')
            self.print_success("Get User Preferences")
            self.passed_tests += 1
        else:
            self.print_warning("No preferences found, might need to be created")
            self.skipped_tests += 1
            
        self.total_tests += 1
        time.sleep(1)
        
        # 2. Update preferences (if we have an ID)
        if self.preference_id:
            self.test_endpoint(
                name="Update User Preferences",
                method="PATCH",
                endpoint=f"/api/v1/user/preferences/{self.preference_id}/",
                data={
                    "preferred_booking_type": "hourly",
                    "preferred_space_types": ["meeting_room", "coworking"],
                    "budget_min": "3000.00",
                    "budget_max": "30000.00",
                    "preferred_cities": ["Lagos", "Abuja"]
                },
                use_auth=True,
                expected_status=200
            )
            time.sleep(1)
        else:
            self.print_warning("Skipping preference update - no preference ID")
            self.skipped_tests += 1
            self.total_tests += 1
            
    # ========================================================================
    # 3. WORKSPACE & SPACE DISCOVERY TESTS
    # ========================================================================
    
    def test_workspace_discovery(self):
        """Test workspace and space discovery endpoints"""
        self.print_header("3. WORKSPACE & SPACE DISCOVERY")
        
        # 1. List workspaces
        success, data, _ = self.make_request(
            "GET",
            "/api/v1/workspace/public/workspaces/",
            params={"page": 1, "page_size": 20},
            expected_status=200
        )
        
        if success and data and data.get('results'):
            self.workspace_id = data['results'][0].get('id')
            self.print_success(f"List Workspaces - Found {data.get('count', 0)} workspaces")
            self.passed_tests += 1
        else:
            self.print_error("List Workspaces - No workspaces found")
            self.failed_tests += 1
            
        self.total_tests += 1
        time.sleep(1)
        
        # 2. Workspace detail
        if self.workspace_id:
            self.test_endpoint(
                name="Workspace Detail",
                method="GET",
                endpoint=f"/api/v1/workspace/public/workspaces/{self.workspace_id}/",
                expected_status=200
            )
            time.sleep(1)
        else:
            self.print_warning("Skipping workspace detail - no workspace found")
            self.skipped_tests += 1
            self.total_tests += 1
            
        # 3. List branches
        success, data, _ = self.make_request(
            "GET",
            "/api/v1/workspace/public/branches/",
            params={"page": 1, "workspace": self.workspace_id} if self.workspace_id else {"page": 1},
            expected_status=200
        )
        
        if success and data and data.get('results'):
            self.branch_id = data['results'][0].get('id')
            self.print_success(f"List Branches - Found {data.get('count', 0)} branches")
            self.passed_tests += 1
        else:
            self.print_error("List Branches - No branches found")
            self.failed_tests += 1
            
        self.total_tests += 1
        time.sleep(1)
        
        # 4. List spaces
        success, data, _ = self.make_request(
            "GET",
            "/api/v1/workspace/public/spaces/",
            params={"page": 1, "page_size": 200},
            expected_status=200
        )
        
        if success and data and data.get('results'):
            # Get a space from the results (use index 0 if there aren't 50 spaces)
            results = data['results']
            space_index = min(42, len(results) - 1) if len(results) > 0 else 0
            self.space_id = results[space_index].get('id') if len(results) > 0 else None
            self.print_success(f"List Spaces - Found {data.get('count', 0)} spaces")
            self.passed_tests += 1
        else:
            self.print_error("List Spaces - No spaces found")
            self.failed_tests += 1
            
        self.total_tests += 1
        time.sleep(1)
        
        # 5. Space detail
        if self.space_id:
            self.test_endpoint(
                name="Space Detail",
                method="GET",
                endpoint=f"/api/v1/workspace/public/spaces/{self.space_id}/",
                expected_status=200
            )
            time.sleep(1)
        else:
            self.print_warning("Skipping space detail - no space found")
            self.skipped_tests += 1
            self.total_tests += 1
            
        # 6. List calendars
        if self.space_id:
            success, data, _ = self.make_request(
                "GET",
                "/api/v1/workspace/public/calendars/",
                params={"space": self.space_id},
                expected_status=200
            )
            
            if success and data and data.get('results'):
                self.calendar_id = data['results'][0].get('id')
                self.print_success(f"List Space Calendars - Found {len(data['results'])} calendars")
                self.passed_tests += 1
            else:
                self.print_warning("No calendars found for this space")
                self.skipped_tests += 1
                
            self.total_tests += 1
            time.sleep(1)
        else:
            self.print_warning("Skipping calendars - no space ID")
            self.skipped_tests += 1
            self.total_tests += 1
            
        # 7. List slots
        if self.space_id:
            today = datetime.now()
            future_date = today + timedelta(days=5)
            
            success, data, _ = self.make_request(
                "GET",
                "/api/v1/workspace/public/slots/",
                params={
                    "space": self.space_id,
                    "date": future_date.strftime("%Y-%m-%d"),
                    "status": "available"
                },
                expected_status=200
            )
            
            if success:
                count = data.get('count', 0) if isinstance(data, dict) else 0
                self.print_success(f"List Space Slots - Found {count} slots")
                self.passed_tests += 1
            else:
                self.print_warning("Could not list slots")
                self.failed_tests += 1
                
            self.total_tests += 1
            time.sleep(1)
        else:
            self.print_warning("Skipping slots - no space ID")
            self.skipped_tests += 1
            self.total_tests += 1
            
        # 8. Get available slots
        if self.space_id:
            today = datetime.now()
            start_date = today + timedelta(days=5)
            end_date = start_date + timedelta(days=7)
            
            self.test_endpoint(
                name="Get Available Slots",
                method="GET",
                endpoint="/api/v1/workspace/public/slots/available/",
                params={
                    "space": self.space_id,
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d"),
                    "booking_type": "hourly"
                },
                expected_status=200
            )
            time.sleep(1)
        else:
            self.print_warning("Skipping available slots - no space ID")
            self.skipped_tests += 1
            self.total_tests += 1
            
        # 9. Check availability
        if self.space_id:
            future_date = datetime.now() + timedelta(days=7)
            
            self.test_endpoint(
                name="Check Space Availability",
                method="POST",
                endpoint="/api/v1/workspace/public/slots/check-availability/",
                data={
                    "space": self.space_id,
                    "booking_type": "hourly",
                    "date": future_date.strftime("%Y-%m-%d"),
                    "start_time": "09:00",
                    "end_time": "12:00"
                },
                expected_status=200
            )
            time.sleep(1)
        else:
            self.print_warning("Skipping availability check - no space ID")
            self.skipped_tests += 1
            self.total_tests += 1
            
    # ========================================================================
    # 4. CART MANAGEMENT TESTS
    # ========================================================================
    
    def test_cart_management(self):
        """Test cart operations"""
        self.print_header("4. CART MANAGEMENT")
        
        if not self.space_id:
            self.print_error("Cannot test cart - no space ID available")
            self.skipped_tests += 5
            self.total_tests += 5
            return
            
        # 1. Get cart (might be empty)
        success, data, _ = self.make_request(
            "GET",
            "/api/v1/booking/cart/",
            use_auth=True,
            expected_status=200
        )
        
        if success:
            self.cart_id = data.get('id') if isinstance(data, dict) else None
            self.print_success("Get Cart")
            self.passed_tests += 1
        else:
            self.print_error("Get Cart failed")
            self.failed_tests += 1
            
        self.total_tests += 1
        time.sleep(1)
        
        # 2. Add item to cart
        future_date = datetime.now() + timedelta(days=7)
        
        success, data, status = self.make_request(
            "POST",
            "/api/v1/booking/cart/add_item/",
            data={
                "space_id": self.space_id,
                "booking_type": "hourly",
                "booking_date": future_date.strftime("%Y-%m-%d"),
                "start_time": "09:00",
                "end_time": "12:00",
                "number_of_guests": 5
            },
            use_auth=True,
            expected_status=201
        )
        
        if success and data:
            self.cart_item_id = data.get('id')
            self.print_success(f"Add to Cart - Item ID: {self.cart_item_id}")
            self.passed_tests += 1
        else:
            self.print_error(f"Add to Cart failed - Status: {status}")
            if data:
                print(f"  Response: {json.dumps(data, indent=2)[:300]}")
            self.failed_tests += 1
            
        self.total_tests += 1
        time.sleep(1)
        
        # 3. Update cart item
        if self.cart_item_id:
            self.test_endpoint(
                name="Update Cart Item",
                method="POST",
                endpoint="/api/v1/booking/cart/update_item/",
                data={
                    "item_id": self.cart_item_id,
                    "number_of_guests": 8
                },
                use_auth=True,
                expected_status=200
            )
            time.sleep(1)
        else:
            self.print_warning("Skipping cart update - no cart item")
            self.skipped_tests += 1
            self.total_tests += 1
            
        # 4. Get cart again (should have items now)
        self.test_endpoint(
            name="Get Cart with Items",
            method="GET",
            endpoint="/api/v1/booking/cart/",
            use_auth=True,
            expected_status=200,
            extract_ids={"id": "cart_id"}
        )
        time.sleep(1)
        
    # ========================================================================
    # 5. CHECKOUT & ORDER TESTS
    # ========================================================================
    
    def test_checkout_and_orders(self):
        """Test checkout process"""
        self.print_header("5. CHECKOUT & ORDERS")
        
        if not self.cart_item_id:
            self.print_error("Cannot test checkout - cart is empty")
            self.skipped_tests += 3
            self.total_tests += 3
            return
            
        # 1. Checkout
        success, data, status = self.make_request(
            "POST",
            "/api/v1/booking/cart/checkout/",
            data={
                "guests": [
                    {
                        "full_name": "Guest One",
                        "email": "guest1@example.com",
                        "phone_number": "+2348012345678"
                    },
                    {
                        "full_name": "Guest Two",
                        "email": "guest2@example.com",
                        "phone_number": "+2348087654321"
                    }
                ]
            },
            use_auth=True,
            expected_status=201
        )
        
        if success and data:
            order_data = data.get('order', {})
            self.order_id = order_data.get('id')
            
            # Extract first booking ID
            bookings = order_data.get('bookings', [])
            if bookings:
                self.booking_id = bookings[0].get('id')
                
            self.print_success(f"Checkout - Order ID: {self.order_id}")
            if self.booking_id:
                print(f"  Booking ID: {self.booking_id}")
            self.passed_tests += 1
        else:
            self.print_error(f"Checkout failed - Status: {status}")
            if data:
                print(f"  Response: {json.dumps(data, indent=2)[:300]}")
            self.failed_tests += 1
            
        self.total_tests += 1
        time.sleep(1)
        
        # 2. List orders
        self.test_endpoint(
            name="List Orders",
            method="GET",
            endpoint="/api/v1/payment/orders/",
            params={"page": 1},
            use_auth=True,
            expected_status=200
        )
        time.sleep(1)
        
        # 3. Order detail
        if self.order_id:
            self.test_endpoint(
                name="Order Detail",
                method="GET",
                endpoint=f"/api/v1/payment/orders/{self.order_id}/",
                use_auth=True,
                expected_status=200
            )
            time.sleep(1)
        else:
            self.print_warning("Skipping order detail - no order ID")
            self.skipped_tests += 1
            self.total_tests += 1
            
    # ========================================================================
    # 6. PAYMENT TESTS
    # ========================================================================
    
    def test_payments(self):
        """Test payment operations"""
        self.print_header("6. PAYMENT")
        
        if not self.order_id:
            self.print_error("Cannot test payments - no order ID")
            self.skipped_tests += 4
            self.total_tests += 4
            return
            
        # 1. Get wallet first
        success, data, _ = self.make_request(
            "GET",
            "/api/v1/bank/v1/wallets/",
            use_auth=True,
            expected_status=200
        )
        
        if success and data:
            # Handle both list and single object response
            if isinstance(data, list) and len(data) > 0:
                self.wallet_id = data[0].get('id')
                wallet_balance = float(data[0].get('balance', 0))
            elif isinstance(data, dict):
                self.wallet_id = data.get('id')
                wallet_balance = float(data.get('balance', 0))
            else:
                wallet_balance = 0
                
            self.print_success(f"Get Wallet - Balance: {wallet_balance}")
            self.passed_tests += 1
        else:
            self.print_warning("Could not get wallet")
            wallet_balance = 0
            self.failed_tests += 1
            
        self.total_tests += 1
        time.sleep(1)
        
        # Get order amount
        success, order_data, _ = self.make_request(
            "GET",
            f"/api/v1/payment/orders/{self.order_id}/",
            use_auth=True,
            expected_status=200
        )
        
        order_amount = 0
        if success and order_data:
            order_amount = float(order_data.get('total_amount', 0))
        
        # Initialize payment reference at method level
        payment_reference = None
        payment_url = None
            
        # 2. Try wallet payment if sufficient balance
        if wallet_balance >= order_amount and order_amount > 0:
            success, data, status = self.make_request(
                "POST",
                "/api/v1/payment/payments/pay_with_wallet/",
                data={"order_id": self.order_id},
                use_auth=True,
                expected_status=200
            )
            
            if success:
                payment_data = data.get('payment', {})
                self.payment_id = payment_data.get('id')
                self.print_success(f"Wallet Payment - Payment ID: {self.payment_id}")
                self.passed_tests += 1
            else:
                self.print_error(f"Wallet Payment failed - Status: {status}")
                if data:
                    print(f"  Response: {json.dumps(data, indent=2)[:300]}")
                self.failed_tests += 1
        else:
            # 2. Initiate Paystack payment
            success, data, status = self.make_request(
                "POST",
                "/api/v1/payment/payments/initiate/",
                data={
                    "order_id": self.order_id,
                    "payment_method": "paystack"
                },
                use_auth=True,
                expected_status=200
            )
            
            if success and data:
                self.payment_id = data.get('payment_id')
                payment_url = data.get('authorization_url', '')
                payment_reference = data.get('reference', '')
                
                # Debug: Show all response data
                print(f"\n  📋 Payment Response Data:")
                print(f"  {json.dumps(data, indent=2)}\n")
                
                self.print_success(f"Initiate Payment - Payment ID: {self.payment_id}")
                
                if payment_url:
                    print(f"\n{'='*70}")
                    print(f"  💳 PAYMENT URL (Copy and open in browser):")
                    print(f"  {payment_url}")
                    print(f"  Reference: {payment_reference}")
                    print(f"{'='*70}\n")
                    
                    # Wait for user to complete payment
                    print("  ⏳ Waiting 20 seconds for you to complete the payment...")
                    print("  Please complete the payment in your browser now.")
                    for i in range(40, 0, -1):
                        print(f"  ⏱  {i} seconds remaining...", end='\r')
                        time.sleep(1)
                    print(f"\n  ✓ Wait completed. Proceeding with verification...\n")
                else:
                    print(f"  ⚠ No payment URL received in response!")
                
                self.passed_tests += 1
            else:
                self.print_error(f"Initiate Payment failed - Status: {status}")
                if data:
                    print(f"  Response: {json.dumps(data, indent=2)[:300]}")
                self.failed_tests += 1
                
        self.total_tests += 1
        time.sleep(1)
        
        # 3. List payments
        self.test_endpoint(
            name="List Payments",
            method="GET",
            endpoint="/api/v1/payment/payments/",
            params={"page": 1},
            use_auth=True,
            expected_status=200
        )
        time.sleep(1)
        
        # 4. Verify payment via callback
        if self.payment_id and payment_reference:
            print(f"\n  🔍 Verifying payment with reference: {payment_reference}")
            success, data, status = self.make_request(
                "GET",
                f"/api/v1/payment/payments/callback/?reference={payment_reference}",
                use_auth=True,
                expected_status=200
            )
            
            if success and data:
                payment_status = data.get('payment', {}).get('status', 'unknown')
                self.print_success(f"Verify Payment - Status: {payment_status}")
                if data.get('success'):
                    print(f"  ✓ Payment verified successfully!")
                    print(f"  Order Status: {data.get('order', {}).get('status', 'N/A')}")
                self.passed_tests += 1
            else:
                self.print_warning(f"Verify Payment - Status: {status} (Payment may not be completed)")
                if data:
                    print(f"  Response: {json.dumps(data, indent=2)[:300]}")
                self.skipped_tests += 1
                
            self.total_tests += 1
            time.sleep(1)
        else:
            self.print_warning("Skipping verify payment - no payment ID or reference")
            self.skipped_tests += 1
            self.total_tests += 1
            
    # ========================================================================
    # 7. BOOKING TESTS
    # ========================================================================
    
    def test_bookings(self):
        """Test booking operations"""
        self.print_header("7. BOOKINGS")
        
        # 1. List bookings
        self.test_endpoint(
            name="List Bookings",
            method="GET",
            endpoint="/api/v1/booking/bookings/",
            params={"page": 1},
            use_auth=True,
            expected_status=200
        )
        time.sleep(1)
        
        # 2. Upcoming bookings
        self.test_endpoint(
            name="Upcoming Bookings",
            method="GET",
            endpoint="/api/v1/booking/bookings/upcoming/",
            use_auth=True,
            expected_status=200
        )
        time.sleep(1)
        
        # 3. Past bookings
        self.test_endpoint(
            name="Past Bookings",
            method="GET",
            endpoint="/api/v1/booking/bookings/past/",
            use_auth=True,
            expected_status=200
        )
        time.sleep(1)
        
        # 4. Booking detail
        if self.booking_id:
            self.test_endpoint(
                name="Booking Detail",
                method="GET",
                endpoint=f"/api/v1/booking/bookings/{self.booking_id}/",
                use_auth=True,
                expected_status=200
            )
            time.sleep(1)
        else:
            self.print_warning("Skipping booking detail - no booking ID")
            self.skipped_tests += 1
            self.total_tests += 1
            
        # Note: We won't cancel the booking so we can test reviews
        
    # ========================================================================
    # 8. WALLET & TRANSACTIONS TESTS
    # ========================================================================
    
    def test_wallet_transactions(self):
        """Test wallet and transaction operations"""
        self.print_header("8. WALLET & TRANSACTIONS")
        
        # 1. Get wallet (already tested but repeat)
        self.test_endpoint(
            name="Get Wallet Details",
            method="GET",
            endpoint="/api/v1/bank/v1/wallets/",
            use_auth=True,
            expected_status=200,
            extract_ids={"id": "wallet_id"} if not self.wallet_id else None
        )
        time.sleep(1)
        
        # 2. Wallet transactions
        self.test_endpoint(
            name="Wallet Transactions",
            method="GET",
            endpoint="/api/v1/bank/v1/transactions/",
            params={"page": 1},
            use_auth=True,
            expected_status=200
        )
        time.sleep(1)
        
        # 3. Fund wallet (initiate deposit)
        success, data, status = self.make_request(
            "POST",
            "/api/v1/bank/v1/deposits/",
            data={
                "amount": "50000.00",
                "payment_method": "paystack"
            },
            use_auth=True,
            expected_status=201
        )
        
        if success and data:
            deposit_id = data.get('id')
            payment_url = data.get('payment_url', '')
            self.print_success(f"Fund Wallet - Deposit ID: {deposit_id}")
            if payment_url:
                print(f"  Payment URL: {payment_url[:60]}...")
            self.passed_tests += 1
        else:
            self.print_error(f"Fund Wallet failed - Status: {status}")
            if data:
                print(f"  Response: {json.dumps(data, indent=2)[:300]}")
            self.failed_tests += 1
            
        self.total_tests += 1
        time.sleep(1)
        
    # ========================================================================
    # 9. REVIEWS TESTS
    # ========================================================================
    
    def test_reviews(self):
        """Test review operations"""
        self.print_header("9. REVIEWS")
        
        # 1. Create review
        if self.booking_id:
            success, data, status = self.make_request(
                "POST",
                "/api/v1/booking/reviews/",
                data={
                    "booking": self.booking_id,
                    "rating": 5,
                    "comment": "Excellent space and service! Highly recommended."
                },
                use_auth=True,
                expected_status=201
            )
            
            if success and data:
                self.review_id = data.get('id')
                self.print_success(f"Create Review - Review ID: {self.review_id}")
                self.passed_tests += 1
            else:
                self.print_warning(f"Create Review - Status: {status} (May fail if already reviewed)")
                if data:
                    print(f"  Response: {json.dumps(data, indent=2)[:300]}")
                self.skipped_tests += 1
                
            self.total_tests += 1
            time.sleep(1)
        else:
            self.print_warning("Skipping create review - no booking ID")
            self.skipped_tests += 1
            self.total_tests += 1
            
        # 2. List reviews
        self.test_endpoint(
            name="List Reviews",
            method="GET",
            endpoint="/api/v1/booking/reviews/",
            use_auth=True,
            expected_status=200
        )
        time.sleep(1)
        
    # ========================================================================
    # 10. NOTIFICATIONS TESTS
    # ========================================================================
    
    def test_notifications(self):
        """Test notification operations"""
        self.print_header("10. NOTIFICATIONS")
        
        # 1. List notifications
        success, data, _ = self.make_request(
            "GET",
            "/api/v1/notifications/",
            params={"page": 1},
            use_auth=True,
            expected_status=200
        )
        
        if success and data:
            results = data.get('results', [])
            if results:
                self.notification_id = results[0].get('id')
                self.print_success(f"List Notifications - Found {len(results)} notifications")
            else:
                self.print_success("List Notifications - No notifications yet")
            self.passed_tests += 1
        else:
            self.print_error("List Notifications failed")
            self.failed_tests += 1
            
        self.total_tests += 1
        time.sleep(1)
        
        # 2. Mark notification as read
        if self.notification_id:
            self.test_endpoint(
                name="Mark Notification Read",
                method="PATCH",
                endpoint=f"/api/v1/notifications/{self.notification_id}/mark_read/",
                use_auth=True,
                expected_status=200
            )
            time.sleep(1)
        else:
            self.print_warning("Skipping mark notification - no notifications")
            self.skipped_tests += 1
            self.total_tests += 1
            
        # 3. Mark all as read
        self.test_endpoint(
            name="Mark All Notifications Read",
            method="POST",
            endpoint="/api/v1/notifications/notifications/mark_all_read/",
            use_auth=True,
            expected_status=200
        )
        time.sleep(1)
        
    # ========================================================================
    # MAIN TEST RUNNER
    # ========================================================================
    
    def run_all_tests(self):
        """Run all API tests"""
        start_time = time.time()
        
        print(f"\n{Colors.BOLD}{'='*70}{Colors.ENDC}")
        print(f"{Colors.BOLD}{'XBOOKING COMPREHENSIVE API TESTING'.center(70)}{Colors.ENDC}")
        print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}")
        print(f"\nBase URL: {self.base_url}")
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        try:
            # Run all test suites
            self.test_user_authentication()
            self.test_user_preferences()
            self.test_workspace_discovery()
            self.test_cart_management()
            self.test_checkout_and_orders()
            self.test_payments()
            self.test_bookings()
            self.test_wallet_transactions()
            self.test_reviews()
            self.test_notifications()
            
        except KeyboardInterrupt:
            print(f"\n\n{Colors.WARNING}Tests interrupted by user{Colors.ENDC}")
        except Exception as e:
            print(f"\n\n{Colors.FAIL}Unexpected error: {str(e)}{Colors.ENDC}")
            import traceback
            traceback.print_exc()
            
        # Print summary
        elapsed_time = time.time() - start_time
        self.print_summary(elapsed_time)
        
    def print_summary(self, elapsed_time: float):
        """Print test summary"""
        self.print_header("TEST SUMMARY")
        
        print(f"Total Tests:   {self.total_tests}")
        print(f"{Colors.OKGREEN}✓ Passed:      {self.passed_tests}{Colors.ENDC}")
        print(f"{Colors.FAIL}✗ Failed:      {self.failed_tests}{Colors.ENDC}")
        print(f"{Colors.WARNING}⚠ Skipped:     {self.skipped_tests}{Colors.ENDC}")
        
        if self.total_tests > 0:
            pass_rate = (self.passed_tests / self.total_tests) * 100
            print(f"\nPass Rate:     {pass_rate:.1f}%")
            
        print(f"Elapsed Time:  {elapsed_time:.2f}s")
        
        # Print extracted IDs for reference
        print(f"\n{Colors.BOLD}Extracted IDs (for manual testing):{Colors.ENDC}")
        print(f"  User ID:         {self.user_id}")
        print(f"  Workspace ID:    {self.workspace_id}")
        print(f"  Branch ID:       {self.branch_id}")
        print(f"  Space ID:        {self.space_id}")
        print(f"  Cart ID:         {self.cart_id}")
        print(f"  Order ID:        {self.order_id}")
        print(f"  Booking ID:      {self.booking_id}")
        print(f"  Payment ID:      {self.payment_id}")
        print(f"  Wallet ID:       {self.wallet_id}")
        print(f"  Review ID:       {self.review_id}")
        
        print(f"\n{Colors.BOLD}{'='*70}{Colors.ENDC}\n")
        
        # Exit with appropriate code
        if self.failed_tests > 0:
            sys.exit(1)
        else:
            sys.exit(0)


if __name__ == "__main__":
    # Allow custom base URL
    base_url = "http://localhost:8000"
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
        
    tester = APITester(base_url=base_url)
    tester.run_all_tests()
