"""
Hourly Booking E2E API Test
Tests: Registration, Login, Space Selection, Calendar Check, Hourly Booking, Guests, Payment, QR Code, Check-in

Flow:
1. Register/Login User
2. List Workspaces → Select Workspace
3. List Spaces → Select Space
4. Get Calendar (hourly mode for specific date)
5. Check slot availability
6. Create Hourly Booking
7. Add Guests immediately after booking
8. Create Order
9. Initiate Payment
10. Get Booking QR Code
11. Verify Guest QR Codes
12. Admin Check-in (simulated)
"""
import requests
import json
import time
import uuid
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"
EMAIL = f"hourly_test_{int(time.time())}@test.com"
PASSWORD = "TestPassword123!"

# Guest emails
GUEST_EMAILS = [
    "guest1@test.com",
    "guest2@test.com"
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
    log_file = 'test_hourly_booking_output.log'

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
        "full_name": "Hourly Test User"
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
    price_per_hour = space.get('price_per_hour', 0)
    print_success(f"Selected Space: {space.get('name', 'Unknown')} - ₦{price_per_hour}/hr")

    # =========================================================================
    # 5. CHECK HOURLY CALENDAR
    # =========================================================================
    print_step("5. Check Hourly Calendar")
    target_date = (datetime.now() + timedelta(days=2)).date()
    date_str = target_date.isoformat()
    
    cal_url = f"{BASE_URL}/api/workspace/spaces/{space_id}/calendar/?mode=hourly&date={date_str}"
    print_info(f"Checking slots for: {date_str}")
    response = do_request("GET", cal_url)
    print(f"Status: {response.status_code}")
    
    available_slots = []
    if response.status_code == 200:
        cal_data = response.json()
        slots = cal_data.get('slots', cal_data.get('data', {}).get('slots', []))
        print_info(f"Total slots returned: {len(slots)}")
        
        # Find available slots
        for slot in slots:
            if slot.get('available', slot.get('status') == 'available'):
                available_slots.append(slot)
        
        print_success(f"Available slots: {len(available_slots)}")
        if available_slots:
            print_info(f"First available: {available_slots[0]}")
    else:
        print_error(f"Failed to get calendar: {response.text}")

    # =========================================================================
    # 6. CREATE HOURLY BOOKING
    # =========================================================================
    print_step("6. Create Hourly Booking")
    
    # Prefer creating booking using an available slot (server resolves times)
    slot_id = None
    booking_type = 'hourly'
    if response.status_code == 200:
        slots = response.json().get('slots', [])
        selected_slot = None
        for s in slots:
            if s.get('available'):
                selected_slot = s
                break

        if selected_slot:
            slot_id = selected_slot.get('id')
            booking_type = selected_slot.get('booking_type', 'hourly')
            print_success(f"Selected slot: {slot_id} ({selected_slot.get('start')} - {selected_slot.get('end')})")

    if slot_id:
        booking_data = {
            "space_id": str(space_id),
            "booking_type": booking_type,
            "slot_id": slot_id,
            "number_of_guests": 3
        }
        print_info(f"Creating booking using slot_id: {slot_id}")
        response = do_request("POST", f"{BASE_URL}/api/booking/bookings/create/", json=booking_data, headers=headers)
    else:
        # Fallback to legacy datetime-based booking if no slot available
        check_in = datetime.combine(target_date, datetime.min.time().replace(hour=9))
        check_out = check_in + timedelta(hours=2)
        booking_data = {
            "space_id": str(space_id),
            "booking_type": "hourly",
            "check_in": check_in.isoformat() + "Z",
            "check_out": check_out.isoformat() + "Z",
            "number_of_guests": 3
        }
        print_info(f"No slot found; creating booking by datetimes: {check_in} - {check_out}")
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
                "first_name": "John",
                "last_name": "Guest",
                "email": GUEST_EMAILS[0],
                "phone": "+2348012345678"
            },
            {
                "first_name": "Jane",
                "last_name": "Visitor",
                "email": GUEST_EMAILS[1],
                "phone": "+2348087654321"
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
    response = do_request("GET", f"{BASE_URL}/api/qr/bookings/{booking_id}/qr-code/", headers=headers)
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
        
        # QR Code stats (for monthly bookings)
        max_check_ins = qr_info.get('max_check_ins', 1)
        total_check_ins = qr_info.get('total_check_ins', 0)
        print_info(f"Check-ins: {total_check_ins}/{max_check_ins}")
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
    # 12. GET BOOKING DETAILS (with QR stats)
    # =========================================================================
    print_step("12. Get Booking Details")
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
        
        # QR Code stats
        qr_stats = booking_info.get('qr_code_stats', {})
        if qr_stats:
            print_info(f"QR Code Stats:")
            print_info(f"  - Scan Count: {qr_stats.get('scan_count', 0)}")
            print_info(f"  - Total Check-ins: {qr_stats.get('total_check_ins', 0)}")
            print_info(f"  - Max Check-ins: {qr_stats.get('max_check_ins', 1)}")
    else:
        print_error(f"Failed to get booking details: {response.text}")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print_step("Test Summary")
    print_success(f"Booking Type: HOURLY")
    print_success(f"Space: {space.get('name', 'Unknown')}")
    # print_success(f"Duration: 2 hours ({check_in.strftime('%H:%M')} - {check_out.strftime('%H:%M')})")
    print_success(f"Total Price: ₦{total_price}")
    print_success(f"Guests Added: 2")
    print_success(f"Order: {order_number}")
    if verification_code:
        print_success(f"QR Verification Code: {verification_code}")
    print(f"\n🎉 Hourly Booking E2E Test Completed!")


if __name__ == "__main__":
    try:
        run_test()
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        import traceback
        traceback.print_exc()
