"""
Admin Check-in/Check-out E2E API Test
Tests: Admin Login, QR Code Verification, Check-in, Check-out, Dashboard, Check-in List

This test simulates the admin/staff workflow for verifying QR codes and managing check-ins.

Flow:
1. Create User Booking (setup)
2. Complete Payment (setup)
3. Get Booking QR Code
4. Admin Login (workspace staff/manager/admin)
5. Admin Check-in via verification_code + booking_id
6. View Check-in Dashboard
7. List Today's Check-ins
8. Admin Check-out
9. Verify Duration Calculation

IMPORTANT: 
- Admin needs workspace membership with role: staff, manager, or admin
- Check-in only works at or after scheduled check_in time
- Check-out creates CheckIn record with duration
"""
import requests
import json
import time
from datetime import datetime, timedelta

BASE_URL = "https://6a63f43d1a91.ngrok-free.app"

# User credentials (the person making the booking)
USER_EMAIL = f"checkin_user_{int(time.time())}@test.com"
USER_PASSWORD = "TestPassword123!"

# Admin credentials (workspace staff who verifies QR codes)
# In production, this would be a separate workspace admin account
ADMIN_EMAIL = "promptforge.customservice@gmail.com"  # Assume this is workspace admin
ADMIN_PASSWORD = "TestPassword123!"


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

def print_warning(msg):
    print(f"⚠️  {msg}")


def run_test():
    session = requests.Session()
    log_file = 'test_admin_checkin_output.log'

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
    # SETUP: Create User Booking
    # =========================================================================
    print_step("SETUP: Create User and Booking")
    
    # Register user
    print_info("Registering test user...")
    reg_data = {
        "email": USER_EMAIL,
        "password": USER_PASSWORD,
        "confirm_password": USER_PASSWORD,
        "full_name": "Check-in Test User"
    }
    response = do_request("POST", f"{BASE_URL}/api/user/register/", json=reg_data)
    
    if response.status_code == 201:
        print_success("User registered")
    else:
        print_info("Using existing user")
    
    # Login as user
    login_data = {"email": USER_EMAIL, "password": USER_PASSWORD}
    response = do_request("POST", f"{BASE_URL}/api/user/login/", json=login_data)
    
    if response.status_code != 200:
        # Fallback to admin user
        login_data = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        response = do_request("POST", f"{BASE_URL}/api/user/login/", json=login_data)
        if response.status_code != 200:
            print_error(f"Login failed: {response.text}")
            return
    
    tokens = response.json()
    if 'token' in tokens:
        user_access_token = tokens['token']['access_token']
    else:
        user_access_token = tokens['access']
    
    user_headers = {'Authorization': f'Bearer {user_access_token}'}
    print_success("User logged in")

    # Get workspace and space
    response = do_request("GET", f"{BASE_URL}/api/workspace/public/workspaces/?page=1&page_size=5")
    workspaces = _extract_list(response.json())
    if not workspaces:
        print_error("No workspaces found")
        return
    
    workspace = workspaces[0]
    workspace_id = workspace.get('id') or workspace.get('workspace_id')
    print_success(f"Selected workspace: {workspace.get('name', 'Unknown')}")
    
    response = do_request("GET", f"{BASE_URL}/api/workspace/public/spaces/?workspace_id={workspace_id}&page=1&page_size=5")
    space_data = response.json()
    spaces = space_data.get('spaces', space_data.get('results', []))
    if isinstance(spaces, dict):
        spaces = list(spaces.values())
    
    if not spaces:
        print_error("No spaces found")
        return
    
    space = spaces[0]
    space_id = space.get('id') or space.get('space_id')
    print_success(f"Selected space: {space.get('name', 'Unknown')}")

    # Create booking using an available hourly slot (so booking times are server-resolved)
    # Try to pick a slot for today so admin can check-in immediately
    target_date = datetime.now().date()
    date_str = target_date.isoformat()
    hourly_url = f"{BASE_URL}/api/workspace/spaces/{space_id}/calendar/?mode=hourly&date={date_str}"
    print_info(f"Querying hourly slots for today: {date_str}")
    response = do_request("GET", hourly_url)

    slot_id = None
    booking_type = 'hourly'
    if response.status_code == 200:
        slots_data = response.json().get('slots', [])
        available_slot = None
        for s in slots_data:
            if s.get('available'):
                available_slot = s
                break

        if available_slot:
            slot_id = available_slot.get('id')
            booking_type = available_slot.get('booking_type', 'hourly')
            print_success(f"Selected slot: {slot_id} ({available_slot.get('start')} - {available_slot.get('end')})")

    if slot_id:
        booking_data = {
            "space_id": str(space_id),
            "booking_type": booking_type,
            "slot_id": slot_id,
            "number_of_guests": 2
        }
        print_info(f"Creating booking using slot_id: {slot_id}")
        response = do_request("POST", f"{BASE_URL}/api/booking/bookings/create/", json=booking_data, headers=user_headers)
    else:
        # Fallback: create a booking using a near-future datetime window (legacy behavior)
        check_in_time = datetime.now() - timedelta(minutes=5)  # 5 min ago (already checkable)
        check_out_time = check_in_time + timedelta(hours=2)
        booking_data = {
            "space_id": str(space_id),
            "booking_type": "hourly",
            "check_in": check_in_time.isoformat() + "Z",
            "check_out": check_out_time.isoformat() + "Z",
            "number_of_guests": 2
        }
        print_info(f"No available slot found; creating booking by datetimes: {check_in_time.strftime('%H:%M')} - {check_out_time.strftime('%H:%M')}")
        response = do_request("POST", f"{BASE_URL}/api/booking/bookings/create/", json=booking_data, headers=user_headers)
    
    if response.status_code != 201:
        print_error(f"Booking failed: {response.text}")
        return
    
    resp_json = response.json()
    booking = resp_json.get('booking') or resp_json.get('data') or resp_json
    if isinstance(booking, dict) and 'booking' in booking:
        booking = booking['booking']
    
    booking_id = booking['id']
    print_success(f"Booking created: {booking_id}")

    # Create order and initiate payment
    order_data = {"booking_ids": [booking_id]}
    response = do_request("POST", f"{BASE_URL}/api/payment/orders/create/", json=order_data, headers=user_headers)
    
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
    print_success(f"Order created: {order.get('order_number', order_id)}")

    # Initiate payment (optional - may need manual completion)
    payment_data = {"order_id": str(order_id), "payment_method": "paystack"}
    response = do_request("POST", f"{BASE_URL}/api/payment/payments/initiate/", json=payment_data, headers=user_headers)
    
    if response.status_code == 200:
        payment_info = response.json()
        payment_url = payment_info.get('payment_url')
        
        if payment_url:
            print_warning("Payment needs to be completed manually for QR code generation")
            print_info(f"Payment URL: {payment_url}")
            print("\n" + "="*60)
            print("🔔 COMPLETE PAYMENT TO CONTINUE")
            print("="*60)
            print("Waiting 60 seconds for payment completion...")
            print("="*60 + "\n")
            
            for remaining in range(60, 0, -10):
                print(f"  ⏳ {remaining} seconds remaining...")
                time.sleep(10)

    # =========================================================================
    # 1. GET BOOKING QR CODE
    # =========================================================================
    print_step("1. Get Booking QR Code")
    response = do_request("GET", f"{BASE_URL}/api/qr-code/bookings/{booking_id}/qr-code/", headers=user_headers)
    print(f"Status: {response.status_code}")
    
    verification_code = None
    if response.status_code == 200:
        qr_data = response.json()
        qr_info = qr_data.get('qr_code', qr_data)
        verification_code = qr_info.get('verification_code')
        qr_status = qr_info.get('status', 'N/A')
        
        print_success("QR Code retrieved")
        print_info(f"Verification Code: {verification_code}")
        print_info(f"Status: {qr_status}")
        print_info(f"Total Check-ins: {qr_info.get('total_check_ins', 0)}")
        print_info(f"Max Check-ins: {qr_info.get('max_check_ins', 1)}")
    else:
        print_error(f"Failed to get QR code: {response.text}")
        print_warning("QR code might not be generated yet (payment pending)")
        # For testing, we'll create a mock verification code
        verification_code = "BKG-TEST12345"
        print_info(f"Using mock verification code: {verification_code}")

    # =========================================================================
    # 2. ADMIN LOGIN
    # =========================================================================
    print_step("2. Admin Login (Workspace Staff)")
    
    admin_login_data = {
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    }
    response = do_request("POST", f"{BASE_URL}/api/user/login/", json=admin_login_data)
    print(f"Status: {response.status_code}")
    
    if response.status_code != 200:
        print_error(f"Admin login failed: {response.text}")
        return
    
    tokens = response.json()
    if 'token' in tokens:
        admin_access_token = tokens['token']['access_token']
    else:
        admin_access_token = tokens['access']
    
    admin_headers = {'Authorization': f'Bearer {admin_access_token}'}
    print_success(f"Admin logged in: {ADMIN_EMAIL}")

    # =========================================================================
    # 3. VIEW CHECK-IN DASHBOARD (Before Check-in)
    # =========================================================================
    print_step("3. View Check-in Dashboard (Before)")
    
    dashboard_url = f"{BASE_URL}/api/qr-code/workspaces/{workspace_id}/admin/check-in-dashboard/"
    response = do_request("GET", dashboard_url, headers=admin_headers)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        dashboard = response.json()
        print_success("Dashboard retrieved")
        print_info(f"Pending Check-ins: {dashboard.get('pending_check_ins', 0)}")
        print_info(f"Checked In Today: {dashboard.get('checked_in_today', 0)}")
        print_info(f"Checked Out Today: {dashboard.get('checked_out_today', 0)}")
        print_info(f"Active Bookings: {dashboard.get('active_bookings', 0)}")
    elif response.status_code == 403:
        print_warning("Admin does not have permission for this workspace")
        print_info("Admin needs 'staff', 'manager', or 'admin' role in this workspace")
    else:
        print_error(f"Failed to get dashboard: {response.text}")

    # =========================================================================
    # 4. ADMIN CHECK-IN
    # =========================================================================
    print_step("4. Admin Check-in (Verify QR Code)")
    
    if verification_code:
        check_in_url = f"{BASE_URL}/api/qr-code/workspaces/{workspace_id}/admin/check-in/"
        check_in_data = {
            "verification_code": verification_code,
            "booking_id": booking_id,
            "notes": "Check-in via E2E test"
        }
        
        print_info(f"Sending check-in request...")
        print_info(f"  verification_code: {verification_code}")
        print_info(f"  booking_id: {booking_id}")
        
        response = do_request("POST", check_in_url, json=check_in_data, headers=admin_headers)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            check_in_resp = response.json()
            print_success("Guest checked in successfully!")
            print_info(f"Message: {check_in_resp.get('message', 'N/A')}")
            
            # Check-in details
            check_in_info = check_in_resp.get('check_in', {})
            print_info(f"Check-in ID: {check_in_info.get('id', 'N/A')}")
            print_info(f"Check-in Time: {check_in_info.get('check_in_time', 'N/A')}")
            
            # Booking update
            booking_info = check_in_resp.get('booking', {})
            print_info(f"Booking Status: {booking_info.get('status', 'N/A')}")
            
            # QR Code stats
            qr_stats = check_in_resp.get('qr_code_stats', {})
            print_info(f"Scan Count: {qr_stats.get('scan_count', 0)}")
            print_info(f"Total Check-ins: {qr_stats.get('total_check_ins', 0)}")
            print_info(f"Max Check-ins: {qr_stats.get('max_check_ins', 1)}")
        elif response.status_code == 400:
            resp_data = response.json()
            detail = resp_data.get('detail', '')
            if 'already checked in' in detail.lower():
                print_warning("Guest is already checked in")
            elif 'not available yet' in detail.lower():
                print_warning(f"Check-in not available yet: {detail}")
                print_info(f"Scheduled check-in time: {resp_data.get('check_in_time', 'N/A')}")
            elif 'expired' in detail.lower():
                print_warning(f"Booking period has expired: {detail}")
            else:
                print_error(f"Check-in failed: {response.text}")
        elif response.status_code == 403:
            print_error("Admin does not have permission to verify QR codes in this workspace")
        elif response.status_code == 404:
            print_error("QR code not found - verification code or booking ID is invalid")
        else:
            print_error(f"Check-in failed: {response.text}")
    else:
        print_warning("Skipping check-in - no verification code available")

    # =========================================================================
    # 5. LIST TODAY'S CHECK-INS
    # =========================================================================
    print_step("5. List Today's Check-ins")
    
    check_ins_url = f"{BASE_URL}/api/qr-code/workspaces/{workspace_id}/admin/check-ins/"
    response = do_request("GET", check_ins_url, headers=admin_headers)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        check_ins_data = response.json()
        print_success(f"Date: {check_ins_data.get('date', 'N/A')}")
        print_info(f"Total Check-ins Today: {check_ins_data.get('total_check_ins', 0)}")
        
        check_ins = check_ins_data.get('check_ins', [])
        for i, ci in enumerate(check_ins[:5], 1):
            print_info(f"\n  [{i}] {ci.get('guest_name', 'N/A')}")
            print_info(f"      Space: {ci.get('space', 'N/A')}")
            print_info(f"      Check-in: {ci.get('check_in_time', 'N/A')}")
            print_info(f"      Status: {ci.get('status', 'N/A')}")
            print_info(f"      Verified by: {ci.get('verified_by', 'N/A')}")
    elif response.status_code == 403:
        print_warning("Admin does not have permission for this workspace")
    else:
        print_error(f"Failed to list check-ins: {response.text}")

    # =========================================================================
    # 6. WAIT AND CHECK-OUT (Simulate time passing)
    # =========================================================================
    print_step("6. Admin Check-out")
    
    if verification_code:
        print_info("Simulating guest checkout after some time...")
        time.sleep(2)  # Small delay to simulate time passing
        
        check_out_url = f"{BASE_URL}/api/qr-code/workspaces/{workspace_id}/admin/check-out/"
        check_out_data = {
            "verification_code": verification_code,
            "booking_id": booking_id,
            "notes": "Check-out via E2E test"
        }
        
        response = do_request("POST", check_out_url, json=check_out_data, headers=admin_headers)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            check_out_resp = response.json()
            print_success("Guest checked out successfully!")
            print_info(f"Message: {check_out_resp.get('message', 'N/A')}")
            
            # Duration
            duration = check_out_resp.get('duration', 'N/A')
            print_info(f"Duration of stay: {duration}")
            
            # Check-out details
            check_in_info = check_out_resp.get('check_in', {})
            print_info(f"Check-in Time: {check_in_info.get('check_in_time', 'N/A')}")
            print_info(f"Check-out Time: {check_in_info.get('check_out_time', 'N/A')}")
            
            # Booking update
            booking_info = check_out_resp.get('booking', {})
            print_info(f"Booking Status: {booking_info.get('status', 'N/A')}")
            
            # QR Code stats
            qr_stats = check_out_resp.get('qr_code_stats', {})
            print_info(f"Final Scan Count: {qr_stats.get('scan_count', 0)}")
        elif response.status_code == 403:
            print_error("Admin does not have permission for this workspace")
        else:
            print_error(f"Check-out failed: {response.text}")
    else:
        print_warning("Skipping check-out - no verification code available")

    # =========================================================================
    # 7. VIEW DASHBOARD AFTER CHECK-OUT
    # =========================================================================
    print_step("7. View Dashboard (After Check-out)")
    
    response = do_request("GET", dashboard_url, headers=admin_headers)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        dashboard = response.json()
        print_success("Dashboard updated")
        print_info(f"Pending Check-ins: {dashboard.get('pending_check_ins', 0)}")
        print_info(f"Checked In Today: {dashboard.get('checked_in_today', 0)}")
        print_info(f"Checked Out Today: {dashboard.get('checked_out_today', 0)}")
        print_info(f"Active Bookings: {dashboard.get('active_bookings', 0)}")
    else:
        print_error(f"Failed to get dashboard: {response.text}")

    # =========================================================================
    # 8. VERIFY FINAL BOOKING STATE
    # =========================================================================
    print_step("8. Verify Final Booking State")
    
    response = do_request("GET", f"{BASE_URL}/api/booking/bookings/{booking_id}/", headers=user_headers)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        booking_data = response.json()
        booking_info = booking_data.get('booking', booking_data)
        
        print_success("Booking state retrieved")
        print_info(f"Status: {booking_info.get('status', 'N/A')}")
        print_info(f"Is Checked In: {booking_info.get('is_checked_in', False)}")
        print_info(f"Is Checked Out: {booking_info.get('is_checked_out', False)}")
        
        # QR Code stats
        qr_stats = booking_info.get('qr_code_stats', {})
        if qr_stats:
            print_info(f"QR Scan Count: {qr_stats.get('scan_count', 0)}")
            print_info(f"Total Check-ins: {qr_stats.get('total_check_ins', 0)}")
    else:
        print_error(f"Failed to get booking: {response.text}")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print_step("Admin Check-in Test Summary")
    print_success(f"User: {USER_EMAIL}")
    print_success(f"Admin: {ADMIN_EMAIL}")
    print_success(f"Workspace: {workspace.get('name', 'Unknown')}")
    print_success(f"Space: {space.get('name', 'Unknown')}")
    print_success(f"Booking ID: {booking_id}")
    if verification_code:
        print_success(f"Verification Code: {verification_code}")
    
    print_info("\n=== ADMIN CHECK-IN FLOW ===")
    print_info("1. User creates booking and completes payment")
    print_info("2. System generates BookingQRCode with verification_code")
    print_info("3. Admin scans QR code → extracts verification_code + booking_id")
    print_info("4. Admin POSTs to /admin/check-in/ with verification_code + booking_id")
    print_info("5. System validates time window and creates CheckIn record")
    print_info("6. System increments total_check_ins and scan_count")
    print_info("7. For monthly: QR remains valid until max_check_ins reached")
    print_info("8. Admin POSTs to /admin/check-out/ when guest leaves")
    print_info("9. System calculates duration and updates status")
    
    print(f"\n🎉 Admin Check-in E2E Test Completed!")


if __name__ == "__main__":
    try:
        run_test()
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        import traceback
        traceback.print_exc()
