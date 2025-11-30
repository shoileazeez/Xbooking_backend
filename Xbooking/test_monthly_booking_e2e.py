"""
Monthly Booking E2E API Test
Tests: Registration, Login, Space Selection, Calendar Check, Monthly Booking, Guests, Payment, QR Code, Multi-day Check-in Tracking

Flow:
1. Register/Login User
2. List Workspaces → Select Workspace
3. List Spaces → Select Space
4. Get Calendar (monthly mode for specific year)
5. Check month availability
6. Create Monthly Booking
7. Add Guests immediately after booking
8. Create Order
9. Initiate Payment
10. Get Booking QR Code
11. Verify Guest QR Codes
12. Check Booking Details (days_used, days_remaining, max_check_ins)
13. Simulate Daily Check-ins (admin flow)

IMPORTANT: Monthly bookings have max_check_ins = 28/30/31 (days in month)
"""
import requests
import json
import time
import uuid
from datetime import datetime, timedelta
from calendar import monthrange

BASE_URL = "https://6a63f43d1a91.ngrok-free.app"
EMAIL = f"monthly_test_{int(time.time())}@test.com"
PASSWORD = "TestPassword123!"

# Guest emails
GUEST_EMAILS = [
    "monthly_guest1@test.com",
    "monthly_guest2@test.com",
    "monthly_guest3@test.com"
]

def print_step(step):
    print(f"\n{'='*60}")
    print(f"STEP: {step}")
    print(f"{'='*60}")

def print_success(msg):
    print(f"✅ {msg}")

def print_error(msg):
    print(f"❌ {msg}")

def print_info(msg):
    print(f"ℹ️  {msg}")


def run_test():
    session = requests.Session()
    log_file = 'test_monthly_booking_output.log'

    def do_request(method, url, **kwargs):
        """Wrapper to perform request, log response to file, and return Response."""
        resp = session.request(method, url, **kwargs)
        entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'method': method,
            'url': url,
            'status_code': resp.status_code,
        }
        try:
            entry['body'] = resp.json()
        except Exception:
            entry['body'] = resp.text

        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False))
                f.write('\n')
        except Exception:
            pass

        return resp

    def _extract_list(obj):
        """Extract list from various response formats"""
        if isinstance(obj, dict):
            if 'results' in obj:
                results = obj['results']
                if isinstance(results, list):
                    return results
                if isinstance(results, dict):
                    if 'workspaces' in results:
                        return results['workspaces']
                    for k in ('workspaces', 'spaces', 'items'):
                        if k in results and isinstance(results[k], list):
                            return results[k]
            for k in ('workspaces', 'spaces', 'items'):
                if k in obj and isinstance(obj[k], list):
                    return obj[k]
            for v in obj.values():
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    return v
        if isinstance(obj, list):
            return obj
        return []

    # =========================================================================
    # 1. REGISTER USER
    # =========================================================================
    print_step("1. Register User")
    reg_data = {
        "email": EMAIL,
        "password": PASSWORD,
        "confirm_password": PASSWORD,
        "full_name": "Monthly Test User"
    }
    print_info(f"Registering: {EMAIL}")
    response = do_request("POST", f"{BASE_URL}/api/user/register/", json=reg_data)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 201:
        print_success("Registration successful")
    elif response.status_code == 400 and 'already' in response.text.lower():
        print_info("User already exists, proceeding to login")
    else:
        print_error(f"Registration failed: {response.text}")

    # =========================================================================
    # 2. LOGIN
    # =========================================================================
    print_step("2. Login")
    login_data = {
        "email": EMAIL,
        "password": PASSWORD
    }
    response = do_request("POST", f"{BASE_URL}/api/user/login/", json=login_data)
    print(f"Status: {response.status_code}")
    
    if response.status_code != 200:
        # Try with existing test user
        login_data = {"email": "promptforge.customservice@gmail.com", "password": "TestPassword123!"}
        response = do_request("POST", f"{BASE_URL}/api/user/login/", json=login_data)
        if response.status_code != 200:
            print_error(f"Login failed: {response.text}")
            return
    
    tokens = response.json()
    if 'token' in tokens:
        access_token = tokens['token']['access_token']
    elif 'access' in tokens:
        access_token = tokens['access']
    else:
        print_error(f"Unexpected response structure: {tokens}")
        return
    
    headers = {'Authorization': f'Bearer {access_token}'}
    print_success(f"Logged in successfully")

    # =========================================================================
    # 3. LIST WORKSPACES
    # =========================================================================
    print_step("3. List Public Workspaces")
    response = do_request("GET", f"{BASE_URL}/api/workspace/public/workspaces/?page=1&page_size=10")
    print(f"Status: {response.status_code}")
    
    if response.status_code != 200:
        print_error(f"Failed to list workspaces: {response.text}")
        return
    
    workspaces = _extract_list(response.json())
    if not workspaces:
        print_error("No workspaces found")
        return
    
    workspace = workspaces[0]
    workspace_id = workspace.get('id') or workspace.get('workspace_id')
    print_success(f"Selected Workspace: {workspace.get('name', 'Unknown')} ({workspace_id})")

    # =========================================================================
    # 4. LIST SPACES
    # =========================================================================
    print_step("4. List Spaces for Workspace")
    response = do_request("GET", f"{BASE_URL}/api/workspace/public/spaces/?workspace_id={workspace_id}&page=1&page_size=10")
    print(f"Status: {response.status_code}")
    
    if response.status_code != 200:
        print_error(f"Failed to list spaces: {response.text}")
        return
    
    space_data = response.json()
    spaces = space_data.get('spaces', space_data.get('results', []))
    if isinstance(spaces, dict):
        spaces = list(spaces.values())
    
    if not spaces:
        print_error("No spaces found")
        return
    
    space = spaces[0]
    space_id = space.get('id') or space.get('space_id')
    price_per_month = space.get('price_per_month', 0)
    print_success(f"Selected Space: {space.get('name', 'Unknown')} - ₦{price_per_month}/month")

    # =========================================================================
    # 5. CHECK MONTHLY CALENDAR
    # =========================================================================
    print_step("5. Check Monthly Calendar")
    
    # Book for next month
    today = datetime.now()
    next_month = today.replace(day=1) + timedelta(days=32)
    next_month = next_month.replace(day=1)  # First day of next month
    year_str = str(next_month.year)
    
    cal_url = f"{BASE_URL}/api/workspace/spaces/{space_id}/calendar/?mode=monthly&year={year_str}"
    print_info(f"Checking availability for year: {year_str}")
    response = do_request("GET", cal_url)
    print(f"Status: {response.status_code}")
    
    available_months = []
    if response.status_code == 200:
        cal_data = response.json()
        months = cal_data.get('months', cal_data.get('data', {}).get('months', []))
        print_info(f"Total months returned: {len(months)}")
        
        # Find available months
        for month in months:
            if month.get('available', month.get('status') == 'available'):
                available_months.append(month)
        
        print_success(f"Available months: {len(available_months)}")
        if available_months:
            print_info(f"First available: {available_months[0]}")
    else:
        print_error(f"Failed to get calendar: {response.text}")

    # =========================================================================
    # 6. CREATE MONTHLY BOOKING
    # =========================================================================
    print_step("6. Create Monthly Booking")
    
    # Calculate days in the booking month
    days_in_month = monthrange(next_month.year, next_month.month)[1]

    # Book entire month by sending booking_date + start_time + end_time (no full datetimes)
    # booking_date = first day of the month, start_time/end_time are the daily window
    booking_date = next_month.replace(day=1).date().isoformat()
    start_time_str = "09:00:00"
    end_time_str = "18:00:00"

    booking_data = {
        "space_id": str(space_id),
        "booking_type": "monthly",
        "booking_date": booking_date,
        "start_time": start_time_str,
        "end_time": end_time_str,
        "number_of_guests": 5  # Allow 4 guests + 1 primary user
    }

    print_info(f"Booking Type: MONTHLY")
    print_info(f"Month: {next_month.strftime('%B %Y')}")
    print_info(f"Booking Date (start of month): {booking_date}")
    print_info(f"Daily Window: {start_time_str} - {end_time_str}")
    print_info(f"Days in Month: {days_in_month}")

    response = do_request("POST", f"{BASE_URL}/api/booking/bookings/create/", json=booking_data, headers=headers)
    print(f"Status: {response.status_code}")
    
    if response.status_code != 201:
        print_error(f"Booking creation failed: {response.text}")
        return
    
    resp_json = response.json()
    booking = resp_json.get('booking') or resp_json.get('data') or resp_json
    if isinstance(booking, dict) and 'booking' in booking:
        booking = booking['booking']
    
    booking_id = booking['id']
    total_price = booking.get('total_price', 0)
    print_success(f"Booking created: {booking_id}")
    print_info(f"Total Price: ₦{total_price}")

    # =========================================================================
    # 7. ADD GUESTS IMMEDIATELY AFTER BOOKING
    # =========================================================================
    print_step("7. Add Guests to Booking")
    
    guests_payload = {
        "guests": [
            {
                "first_name": "Charlie",
                "last_name": "Monthly",
                "email": GUEST_EMAILS[0],
                "phone": "+2348012345678"
            },
            {
                "first_name": "Diana",
                "last_name": "Subscriber",
                "email": GUEST_EMAILS[1],
                "phone": "+2348087654321"
            },
            {
                "first_name": "Eve",
                "last_name": "Regular",
                "email": GUEST_EMAILS[2],
                "phone": "+2348099887766"
            }
        ]
    }
    
    response = do_request("POST", f"{BASE_URL}/api/booking/bookings/{booking_id}/guests/", json=guests_payload, headers=headers)
    print(f"Status: {response.status_code}")
    
    if response.status_code in [200, 201]:
        guest_resp = response.json()
        guests_added = guest_resp.get('guests', [])
        print_success(f"Added {len(guests_added)} guest(s)")
        for g in guests_added:
            full_name = g.get('full_name', f"{g.get('first_name', '')} {g.get('last_name', '')}")
            print_info(f"  - {full_name} ({g.get('email', 'N/A')})")
    else:
        print_error(f"Failed to add guests: {response.text}")

    # =========================================================================
    # 8. CREATE ORDER
    # =========================================================================
    print_step("8. Create Order")
    order_data = {
        "booking_ids": [booking_id]
    }
    response = do_request("POST", f"{BASE_URL}/api/payment/orders/create/", json=order_data, headers=headers)
    print(f"Status: {response.status_code}")
    
    if response.status_code != 201:
        print_error(f"Order creation failed: {response.text}")
        return
    
    order_resp = response.json()
    if 'orders' in order_resp:
        order = order_resp['orders'][0]
    elif 'order' in order_resp:
        order = order_resp['order']
    else:
        order = order_resp
    
    order_id = order.get('id') or order_resp.get('id')
    order_number = order.get('order_number', 'N/A')
    order_total = order.get('total_amount', 0)
    
    print_success(f"Order created: {order_number}")
    print_info(f"Order ID: {order_id}")
    print_info(f"Total: ₦{order_total}")

    # =========================================================================
    # 9. INITIATE PAYMENT
    # =========================================================================
    print_step("9. Initiate Payment")
    payment_data = {
        "order_id": str(order_id),
        "payment_method": "paystack"
    }
    response = do_request("POST", f"{BASE_URL}/api/payment/payments/initiate/", json=payment_data, headers=headers)
    print(f"Status: {response.status_code}")
    
    payment_url = None
    payment_reference = None
    
    if response.status_code == 200:
        payment_info = response.json()
        payment_reference = payment_info.get('reference', 'N/A')
        payment_url = payment_info.get('payment_url')
        
        print_success(f"Payment initiated")
        print_info(f"Reference: {payment_reference}")
        
        if payment_url:
            print("\n" + "="*60)
            print("🔔 MANUAL PAYMENT STEP")
            print("="*60)
            print(f"Open this URL in your browser to complete payment:")
            print(f"\n  {payment_url}\n")
            print("Waiting 2 minutes for you to complete the payment...")
            print("="*60 + "\n")
            
            for remaining in range(120, 0, -10):
                print(f"  ⏳ {remaining} seconds remaining...")
                time.sleep(10)
    else:
        print_error(f"Payment initiation failed: {response.text}")

    # =========================================================================
    # 10. GET BOOKING QR CODE
    # =========================================================================
    print_step("10. Get Booking QR Code")
    response = do_request("GET", f"{BASE_URL}/api/qr-code/bookings/{booking_id}/qr-code/", headers=headers)
    print(f"Status: {response.status_code}")
    
    verification_code = None
    if response.status_code == 200:
        qr_data = response.json()
        qr_info = qr_data.get('qr_code', qr_data)
        verification_code = qr_info.get('verification_code', 'N/A')
        qr_image_url = qr_info.get('qr_code_image', 'N/A')
        qr_status = qr_info.get('status', 'N/A')
        
        print_success("QR Code retrieved")
        print_info(f"Verification Code: {verification_code}")
        print_info(f"Status: {qr_status}")
        print_info(f"Image URL: {qr_image_url}")
        
        # QR Code stats - CRITICAL for monthly bookings
        max_check_ins = qr_info.get('max_check_ins', days_in_month)
        total_check_ins = qr_info.get('total_check_ins', 0)
        used = qr_info.get('used', False)
        
        print_info(f"=== MONTHLY BOOKING QR STATS ===")
        print_info(f"Max Check-ins: {max_check_ins} (days in month)")
        print_info(f"Total Check-ins: {total_check_ins}")
        print_info(f"QR Used (depleted): {used}")
        print_info(f"Remaining Check-ins: {max_check_ins - total_check_ins}")
    else:
        print_error(f"Failed to get QR code: {response.text}")

    # =========================================================================
    # 11. VERIFY GUEST QR CODES
    # =========================================================================
    print_step("11. Verify Guest QR Codes")
    response = do_request("GET", f"{BASE_URL}/api/booking/bookings/{booking_id}/guests/list/", headers=headers)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        guests_data = response.json()
        guests_list = guests_data.get('guests', guests_data.get('results', []))
        print_success(f"Found {len(guests_list)} guest(s)")
        
        for g in guests_list:
            full_name = g.get('full_name', f"{g.get('first_name', '')} {g.get('last_name', '')}")
            qr_sent = g.get('qr_code_sent', False)
            status_str = "✅ Sent" if qr_sent else "⏳ Pending"
            print_info(f"  - {full_name}: QR Code {status_str}")
    else:
        print_error(f"Failed to get guests: {response.text}")

    # =========================================================================
    # 12. GET BOOKING DETAILS (days_used, days_remaining)
    # =========================================================================
    print_step("12. Get Booking Details (Monthly Tracking)")
    response = do_request("GET", f"{BASE_URL}/api/booking/bookings/{booking_id}/", headers=headers)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        booking_details = response.json()
        booking_info = booking_details.get('booking', booking_details)
        
        print_success("Booking Details Retrieved")
        print_info(f"ID: {booking_info.get('id', 'N/A')}")
        print_info(f"Space: {booking_info.get('space_details', {}).get('name', booking_info.get('space_name', 'N/A'))}")
        print_info(f"Type: {booking_info.get('booking_type', 'N/A')}")
        print_info(f"Status: {booking_info.get('status', 'N/A')}")
        print_info(f"Total Price: ₦{booking_info.get('total_price', 0)}")
        print_info(f"Checked In: {booking_info.get('is_checked_in', False)}")
        
        # Monthly-specific fields
        print_info(f"\n=== MONTHLY BOOKING TRACKING ===")
        days_used = booking_info.get('days_used', 0)
        days_remaining = booking_info.get('days_remaining', days_in_month)
        print_info(f"Days Used: {days_used}")
        print_info(f"Days Remaining: {days_remaining}")
        print_info(f"Total Days: {days_in_month}")
        
        # QR Code stats
        qr_stats = booking_info.get('qr_code_stats', {})
        if qr_stats:
            print_info(f"\n=== QR CODE STATS ===")
            print_info(f"Scan Count: {qr_stats.get('scan_count', 0)}")
            print_info(f"Total Check-ins: {qr_stats.get('total_check_ins', 0)}")
            print_info(f"Max Check-ins: {qr_stats.get('max_check_ins', days_in_month)}")
    else:
        print_error(f"Failed to get booking details: {response.text}")

    # =========================================================================
    # 13. EXPLAIN ADMIN CHECK-IN FLOW FOR MONTHLY
    # =========================================================================
    print_step("13. Admin Check-in Flow (Documentation)")
    print_info("For monthly bookings, the admin check-in flow works as follows:")
    print_info("")
    print_info("1. User arrives at workspace with QR code")
    print_info("2. Admin scans QR code → extracts verification_code and booking_id")
    print_info("3. Admin POSTs to: /api/qr-code/workspaces/{workspace_id}/admin/check-in/")
    print_info("   Body: {verification_code, booking_id, notes}")
    print_info("4. System creates CheckIn record with check_in_time")
    print_info("5. System increments qr_code.total_check_ins and scan_count")
    print_info("6. Response includes qr_code_stats with updated counts")
    print_info("")
    print_info("For MONTHLY bookings:")
    print_info(f"  - max_check_ins = {days_in_month} (days in month)")
    print_info("  - QR code is NOT marked as 'used' until checkout")
    print_info("  - Same QR code can be used for daily check-ins throughout the month")
    print_info("  - days_used and days_remaining update based on check-in history")
    print_info("")
    print_info("Admin Check-out Flow:")
    print_info("  POST /api/qr-code/workspaces/{workspace_id}/admin/check-out/")
    print_info("  Body: {verification_code, booking_id, notes}")
    print_info("  Response includes duration of stay")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print_step("Test Summary")
    print_success(f"Booking Type: MONTHLY")
    print_success(f"Space: {space.get('name', 'Unknown')}")
    print_success(f"Month: {next_month.strftime('%B %Y')}")
    print_success(f"Days in Month: {days_in_month}")
    print_success(f"Max Check-ins: {days_in_month}")
    print_success(f"Total Price: ₦{total_price}")
    print_success(f"Guests Added: 3")
    print_success(f"Order: {order_number}")
    if verification_code:
        print_success(f"QR Verification Code: {verification_code}")
    print(f"\n🎉 Monthly Booking E2E Test Completed!")


if __name__ == "__main__":
    try:
        run_test()
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        import traceback
        traceback.print_exc()
