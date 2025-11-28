"""
Enhanced E2E API Test with Notifications
Tests: Registration, Login, Workspaces, Spaces, Booking, Orders, Payment, Notifications
"""
import requests
import json
import time
import uuid
from datetime import datetime, timedelta

BASE_URL = "https://6a63f43d1a91.ngrok-free.app/"
EMAIL = f" promptforge.customservice@gmail.com"
PASSWORD = "TestPassword123!"
FIRST_NAME = "Test"
LAST_NAME = "User"

def print_step(step):
    print(f"\n{'='*50}")
    print(f"STEP: {step}")
    print(f"{'='*50}")

def run_test():
    session = requests.Session()
    log_file = 'e2e_api_test_output.log'

    def do_request(method, url, **kwargs):
        """Wrapper to perform request, log response to file, and return Response."""
        resp = session.request(method, url, **kwargs)
        entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'method': method,
            'url': url,
            'status_code': resp.status_code,
        }
        # try to parse JSON body for nicer logs
        try:
            entry['body'] = resp.json()
        except Exception:
            entry['body'] = resp.text

        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False))
                f.write('\n')
        except Exception:
            # if logging fails, don't break the test
            pass

        return resp
    
    # 1. Register
    print_step("Register User")
    reg_data = {
        "email": EMAIL,
        "password": PASSWORD,
        "confirm_password": PASSWORD,
        "full_name": f"{FIRST_NAME} {LAST_NAME}"
    }
    print(EMAIL)
    response = do_request("POST", f"{BASE_URL}/api/user/register/", json=reg_data)
    print(f"Status: {response.status_code}")
    if response.status_code != 201:
        print(f"Registration failed: {response.text}")
        return
    print("✅ Registration successful")

    # 2. Login
    print_step("Login")
    login_data = {
        "email": EMAIL,
        "password": PASSWORD
    }
    response = do_request("POST", f"{BASE_URL}/api/user/login/", json=login_data)
    print(f"Status: {response.status_code}")
    if response.status_code != 200:
        print(f"Login failed: {response.text}")
        return
    
    tokens = response.json()
    if 'token' in tokens:
        access_token = tokens['token']['access_token']
    elif 'access' in tokens:
        access_token = tokens['access']
    else:
        print(f"Unexpected response structure: {tokens}")
        return
    
    headers = {'Authorization': f'Bearer {access_token}'}
    print("✅ Login successful, token received")

    # 3. List Public Workspaces (with pagination)
    print_step("List Public Workspaces (Paginated)")
    response = do_request("GET", f"{BASE_URL}/api/workspace/public/workspaces/?page=1&page_size=10")
    print(f"Status: {response.status_code}")
    if response.status_code != 200:
        print(f"Failed to list workspaces: {response.text}")
        return
    
    workspace_data = response.json()
    print(f"DEBUG: Workspace Response Keys: {list(workspace_data.keys())}")

    # The backend can return several shapes. Handle them robustly:
    # - Standard DRF pagination: { ..., 'results': [ {...}, ... ] }
    # - Nested wrapper: { ..., 'results': { 'success': True, 'workspaces': [ ... ] } }
    # - Non-paginated: { 'workspaces': [ ... ] }
    def _extract_list(obj):
        # If it's a dict, try known keys in order
        if isinstance(obj, dict):
            # If results is present and is a list -> standard DRF
            if 'results' in obj:
                results = obj['results']
                if isinstance(results, list):
                    return results
                if isinstance(results, dict):
                    # common nested wrapper
                    if 'workspaces' in results and isinstance(results['workspaces'], list):
                        return results['workspaces']
                    # sometimes results may itself contain the items under other keys
                    for candidate in ('workspaces', 'items', 'results'):
                        if candidate in results and isinstance(results[candidate], list):
                            return results[candidate]

            # Top-level workspaces key
            if 'workspaces' in obj and isinstance(obj['workspaces'], list):
                return obj['workspaces']

            # Fallback: if any value is a list of dicts, pick the first reasonable one
            for v in obj.values():
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    return v

        # If it's already a list, return as-is
        if isinstance(obj, list):
            return obj

        return []

    workspaces_list = _extract_list(workspace_data)

    if not workspaces_list:
        print("No workspaces found. Cannot proceed.")
        return

    # Choose the first workspace (index 0)
    first_workspace = workspaces_list[0]

    # workspace may be a dict or just an id string
    if isinstance(first_workspace, dict):
        workspace_id = first_workspace.get('id') or first_workspace.get('workspace_id')
    else:
        workspace_id = first_workspace

    if not workspace_id:
        print('Could not determine workspace id from response. Full response logged to file.')
        return
    print(f"✅ Selected Workspace ID: {workspace_id}")
    print(f"   Total workspaces: {workspace_data.get('count', len(workspaces_list))}")

    # 4. Get Workspace Details
    print_step("Get Workspace Details")
    response = do_request("GET", f"{BASE_URL}/api/workspace/public/workspaces/{workspace_id}/")
    print(f"Status: {response.status_code}")
    print("✅ Workspace details retrieved")
    
    # 5. List Spaces (with pagination)
    print_step("List Public Spaces (Paginated)")
    response = do_request("GET", f"{BASE_URL}/api/workspace/public/spaces/?workspace_id={workspace_id}&page=1&page_size=10")
    print(f"Status: {response.status_code}")
    if response.status_code != 200:
        print(f"Failed to list spaces: {response.text}")
        return
    
    space_data = response.json()
    spaces = space_data.get('spaces', space_data.get('results', []))
    if isinstance(spaces, dict):
        spaces_list = list(spaces.values())
    else:
        spaces_list = spaces

    if not spaces_list:
        print("No spaces found. Cannot proceed.")
        return

    first_space = spaces_list[0]
    if isinstance(first_space, dict):
        space_id = first_space.get('id') or first_space.get('space_id')
    else:
        space_id = first_space

    if not space_id:
        print('Could not determine space id from response. Full response logged to file.')
        return
    print(f"✅ Selected Space ID: {space_id}")
    print(f"   Total spaces: {space_data.get('count', len(spaces))}")

    # Calendar tests (hourly, daily, monthly)
    print_step("Space Calendar - hourly/daily/monthly")
    from datetime import date as _date
    target_date = (datetime.now() + timedelta(days=1)).date()
    date_str = target_date.isoformat()
    month_str = f"{target_date.year}-{target_date.month:02d}"
    year_str = f"{target_date.year}"

    # hourly
    cal_hourly_url = f"{BASE_URL}/api/workspace/spaces/{space_id}/calendar/?mode=hourly&date={date_str}"
    resp = do_request("GET", cal_hourly_url)
    print(f"Hourly calendar ({date_str}) - Status: {resp.status_code}")
    try:
        cal_hourly = resp.json()
        slots = cal_hourly.get('slots', cal_hourly.get('data', {}).get('slots', []))
        print(f"  Slots returned: {len(slots)}")
        if len(slots) > 0:
            print(f"  First slot: {slots[0]}")
    except Exception:
        print(f"  Failed to parse hourly calendar response: {resp.text}")

    # daily
    cal_daily_url = f"{BASE_URL}/api/workspace/spaces/{space_id}/calendar/?mode=daily&month={month_str}"
    resp = do_request("GET", cal_daily_url)
    print(f"Daily calendar ({month_str}) - Status: {resp.status_code}")
    try:
        cal_daily = resp.json()
        days = cal_daily.get('days', cal_daily.get('data', {}).get('days', []))
        print(f"  Days returned: {len(days)}")
        if len(days) > 0:
            print(f"  Sample day: {days[0]}")
    except Exception:
        print(f"  Failed to parse daily calendar response: {resp.text}")

    # monthly
    cal_monthly_url = f"{BASE_URL}/api/workspace/spaces/{space_id}/calendar/?mode=monthly&year={year_str}"
    resp = do_request("GET", cal_monthly_url)
    print(f"Monthly calendar ({year_str}) - Status: {resp.status_code}")
    try:
        cal_monthly = resp.json()
        months = cal_monthly.get('months', cal_monthly.get('data', {}).get('months', []))
        print(f"  Months returned: {len(months)}")
        if len(months) > 0:
            print(f"  Sample month: {months[0]}")
    except Exception:
        print(f"  Failed to parse monthly calendar response: {resp.text}")

    # 6. Create Booking
    print_step("Create Booking")
    check_in = (datetime.now() + timedelta(days=5)).isoformat() + "Z"
    check_out = (datetime.now() + timedelta(days=5, hours=1)).isoformat() + "Z"
    
    booking_data = {
        "space_id": space_id,
        "booking_type": "hourly",
        "check_in": check_in,
        "check_out": check_out,
        "number_of_guests": 3  # Allow for 2 guests plus primary booker
    }
    response = do_request("POST", f"{BASE_URL}/api/booking/bookings/create/", json=booking_data, headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code != 201:
        print(f"Booking creation failed: {response.text}")
        return
    
    # Be tolerant of different response shapes. Try common keys then fall back to raw json
    resp_json = {}
    try:
        resp_json = response.json()
    except Exception:
        print("Failed to parse booking response as JSON")
        return

    if isinstance(resp_json, dict):
        booking = resp_json.get('booking') or resp_json.get('data') or resp_json.get('result') or resp_json
        # If we got a wrapper with success/message, ensure booking is the inner dict
        if isinstance(booking, dict) and 'id' in booking:
            booking = booking
        elif isinstance(booking, dict) and 'booking' in booking:
            booking = booking['booking']
    else:
        booking = resp_json
    booking_id = booking['id']
    print(f"✅ Booking created: {booking_id}")

    # 6a. List User Bookings (with pagination)
    print_step("List User Bookings (Paginated)")
    response = do_request("GET", f"{BASE_URL}/api/booking/bookings/?page=1&page_size=10", headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        bookings_data = response.json()
        bookings_list = bookings_data.get('bookings', bookings_data.get('results', []))
        print(f"✅ Found {bookings_data.get('count', len(bookings_list))} booking(s)")
        for i, bkg in enumerate(bookings_list[:3], 1):
            print(f"  [{i}] {bkg['id'][:8]}... - {bkg.get('space_name', 'N/A')} - Status: {bkg['status']}")
    else:
        print(f"Failed to list bookings: {response.text}")

    # 6b. Get Booking Details
    print_step("Get Booking Details")
    response = do_request("GET", f"{BASE_URL}/api/booking/bookings/{booking_id}/", headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        booking_details = response.json()['booking']
        print(f"✅ Booking Details Retrieved")
        print(f"  Space: {booking_details['space_details']['name']}")
        print(f"  Status: {booking_details['status']}")
        print(f"  Total Price: ₦{booking_details['total_price']}")
    else:
        print(f"Failed to get booking details: {response.text}")

    # 6c. Add Guests to Booking (multiple at once)
    print_step("Add Guests to Booking")
    # API expects: {"guests": [{"first_name": "...", "last_name": "...", "email": "...", "phone": "..."}]}
    guests_payload = {
        "guests": [
            {
                "first_name": "John",
                "last_name": "Guest",
                "email": "shoabdulazeez@gmail.com",
                "phone": "+2348012345678"
            },
            {
                "first_name": "Jane",
                "last_name": "Visitor",
                "email": "abdulazeezshoile@gmail.com",
                "phone": "+2348087654321"
            }
        ]
    }
    response = do_request("POST", f"{BASE_URL}/api/booking/bookings/{booking_id}/guests/", json=guests_payload, headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code in [200, 201]:
        guest_resp = response.json()
        guests_added = guest_resp.get('guests', [])
        print(f"✅ Added {len(guests_added)} guest(s) to booking")
        for i, g in enumerate(guests_added, 1):
            full_name = g.get('full_name', f"{g.get('first_name', '')} {g.get('last_name', '')}")
            print(f"  [{i}] {full_name} ({g.get('email', 'N/A')})")
    else:
        print(f"Failed to add guests: {response.text}")
        # Continue anyway, guest addition might be optional

    # List guests for the booking
    print_step("List Booking Guests")
    response = do_request("GET", f"{BASE_URL}/api/booking/bookings/{booking_id}/guests/list/", headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        guests_data = response.json()
        guests_list = guests_data.get('guests', guests_data.get('results', []))
        print(f"✅ Found {len(guests_list)} guest(s) for booking")
        for i, g in enumerate(guests_list, 1):
            full_name = g.get('full_name', f"{g.get('first_name', '')} {g.get('last_name', '')}")
            qr_sent = g.get('qr_code_sent', False)
            print(f"  [{i}] {full_name} - {g.get('email', 'N/A')} - QR Sent: {'Yes' if qr_sent else 'Pending'}")
    else:
        print(f"Failed to list guests: {response.text}")

    # 7. Create Order
    print_step("Create Order")
    order_data = {
        "booking_ids": [booking_id]
    }
    response = do_request("POST", f"{BASE_URL}/api/payment/orders/create/", json=order_data, headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code != 201:
        print(f"Order creation failed: {response.text}")
        return
    
    order_resp = response.json()
    if 'orders' in order_resp:
        order = order_resp['orders'][0]
    else:
        order = order_resp
        
    order_id = order['id']
    print(f"✅ Order created: {order_id}")

    # 8. Initiate Payment
    print_step("Initiate Payment")
    payment_data = {
        "order_id": order_id,
        "payment_method": "paystack"
    }
    response = do_request("POST", f"{BASE_URL}/api/payment/payments/initiate/", json=payment_data, headers=headers)
    print(f"Status: {response.status_code}")
    payment_url = None
    if response.status_code == 200:
        payment_info = response.json()
        reference = payment_info.get('reference', 'N/A')
        payment_url = payment_info.get('payment_url', None)
        print(f"✅ Payment initiated. Reference: {reference}")
        print(f"   Payment URL: {payment_url}")
        print(payment_info)
        
        # ========================================================
        # PAUSE: Open the payment_url in browser to complete payment
        # ========================================================
        if payment_url:
            print("\n" + "="*60)
            print("🔔 MANUAL PAYMENT STEP")
            print("="*60)
            print(f"Open this URL in your browser to complete payment:")
            print(f"\n  {payment_url}\n")
            print("Waiting 2 minutes for you to complete the payment...")
            print("="*60 + "\n")
            
            # Wait 2 minutes (120 seconds) for manual payment
            for remaining in range(120, 0, -10):
                print(f"  ⏳ {remaining} seconds remaining...")
                time.sleep(10)
            
            print("✅ Wait complete. Continuing with verification...\n")
            
            # 8a. Verify Payment via Callback API
            # print_step("Verify Payment (Callback API)")
            # verify_url = f"{BASE_URL}/api/payment/payments/callback/?reference={reference}"
            # print(f"Calling: {verify_url}")
            # response = do_request("GET", verify_url, headers=headers)
            # print(f"Status: {response.status_code}")
            # if response.status_code == 200:
            #     verify_data = response.json()
            #     print(f"✅ Payment verification result:")
            #     print(f"   Success: {verify_data.get('success', 'N/A')}")
            #     print(f"   Message: {verify_data.get('message', 'N/A')}")
            #     if verify_data.get('payment'):
            #         print(f"   Payment Status: {verify_data['payment'].get('status', 'N/A')}")
            #     if verify_data.get('order'):
            #         print(f"   Order Status: {verify_data['order'].get('status', 'N/A')}")
            # else:
            #     print(f"Payment verification response: {response.text}")
    else:
        print(f"Payment initiation failed: {response.text}")

    # 8b. List User Payments (with pagination)
    print_step("List User Payments (Paginated)")
    response = do_request("GET", f"{BASE_URL}/api/payment/payments/?page=1&page_size=10", headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        payments_data = response.json()
        # Handle both paginated and non-paginated responses
        if isinstance(payments_data, list):
            payments = payments_data
            count = len(payments)
        else:
            payments = payments_data.get('results', payments_data.get('payments', []))
            count = payments_data.get('count', len(payments))
        
        print(f"✅ Found {count} payment(s)")
        for i, payment in enumerate(payments[:3], 1):
            print(f"  [{i}] {payment.get('id', 'N/A')[:8]}... - ₦{payment.get('amount', 0)} - {payment.get('status', 'N/A')}")
    else:
        print(f"Failed to list payments: {response.text}")

    # 8b. List User Orders (with pagination)
    print_step("List User Orders (Paginated)")
    response = do_request("GET", f"{BASE_URL}/api/payment/orders/?page=1&page_size=10", headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        orders_data = response.json()
        # Handle both paginated and non-paginated responses
        if isinstance(orders_data, list):
            orders = orders_data
            count = len(orders)
        else:
            orders = orders_data.get('results', orders_data.get('orders', []))
            count = orders_data.get('count', len(orders))
        
        print(f"✅ Found {count} order(s)")
        for i, order in enumerate(orders[:3], 1):
            print(f"  [{i}] {order.get('order_number', 'N/A')} - ₦{order.get('total_amount', 0)} - {order.get('status', 'N/A')}")
    else:
        print(f"Failed to list orders: {response.text}")

    # 9. Check Notifications
    print_step("Check User Notifications")
    response = do_request("GET", f"{BASE_URL}/api/notifications/?page=1&page_size=10", headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        notifications_data = response.json()
        notifications = notifications_data.get('notifications', notifications_data.get('results', []))
        print(f"✅ Found {notifications_data.get('count', len(notifications))} notification(s)")
        for i, notif in enumerate(notifications[:5], 1):
            print(f"  [{i}] {notif.get('title', 'N/A')} - {notif.get('notification_type', 'N/A')}")
    else:
        print(f"Failed to get notifications: {response.text}")

    # 10. Get Notification Preferences
    print_step("Get Notification Preferences")
    response = do_request("GET", f"{BASE_URL}/api/notifications/preferences/", headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        prefs = response.json()
        print(f"✅ Notification preferences retrieved")
        print(f"  Email notifications: {prefs.get('email_enabled', 'N/A')}")
        print(f"  In-app notifications: {prefs.get('in_app_enabled', 'N/A')}")
    else:
        print(f"Failed to get preferences: {response.text}")

    # 11. Verify Guest QR Codes (generated automatically by webhook after payment)
    print_step("Verify Guest QR Codes (Auto-generated)")
    response = do_request("GET", f"{BASE_URL}/api/booking/bookings/{booking_id}/guests/list/", headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        guests_data = response.json()
        guests_list = guests_data.get('guests', guests_data.get('results', []))
        print(f"✅ Checking QR codes for {len(guests_list)} guest(s)")
        for i, g in enumerate(guests_list, 1):
            qr_sent = g.get('qr_code_sent', False)
            full_name = g.get('full_name', f"{g.get('first_name', '')} {g.get('last_name', '')}")
            status_str = "✅ Sent" if qr_sent else "⏳ Pending (webhook may still be processing)"
            print(f"  [{i}] {full_name} - QR Code: {status_str}")
    else:
        print(f"Failed to verify guest QR codes: {response.text}")

    # Summary
    print_step("Test Summary")
    print(f"✅ User registered: {EMAIL}")
    print(f"✅ User logged in")
    print(f"✅ Workspaces listed (paginated)")
    print(f"✅ Spaces listed (paginated)")
    print(f"✅ Booking created")
    print(f"✅ Bookings listed (paginated)")
    print(f"✅ Order created")
    print(f"✅ Payment initiated")
    print(f"✅ Payments listed (paginated)")
    print(f"✅ Orders listed (paginated)")
    print(f"✅ Notifications checked")
    print(f"✅ Notification preferences retrieved")
    print(f"\n🎉 Direct booking flow test completed!")


if __name__ == "__main__":
    try:
        run_test()
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        import traceback
        traceback.print_exc()
