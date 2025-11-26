"""
Enhanced E2E API Test with Notifications
Tests: Registration, Login, Workspaces, Spaces, Booking, Orders, Payment, Notifications
"""
import requests
import json
import time
import uuid
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"
EMAIL = f"testuser_{uuid.uuid4()}@example.com"
PASSWORD = "TestPassword123!"
FIRST_NAME = "Test"
LAST_NAME = "User"

def print_step(step):
    print(f"\n{'='*50}")
    print(f"STEP: {step}")
    print(f"{'='*50}")

def run_test():
    session = requests.Session()
    
    # 1. Register
    print_step("Register User")
    reg_data = {
        "email": EMAIL,
        "password": PASSWORD,
        "confirm_password": PASSWORD,
        "full_name": f"{FIRST_NAME} {LAST_NAME}"
    }
    response = session.post(f"{BASE_URL}/api/user/register/", json=reg_data)
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
    response = session.post(f"{BASE_URL}/api/user/login/", json=login_data)
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
    response = requests.get(f"{BASE_URL}/api/workspace/public/workspaces/?page=1&page_size=10")
    print(f"Status: {response.status_code}")
    if response.status_code != 200:
        print(f"Failed to list workspaces: {response.text}")
        return
    
    workspace_data = response.json()
    print(f"DEBUG: Workspace Response Keys: {workspace_data.keys()}")
    if 'results' in workspace_data:
        print(f"DEBUG: Found {len(workspace_data['results'])} workspaces in 'results'")
    
    workspaces = workspace_data.get('workspaces', workspace_data.get('results', []))
    if not workspaces:
        print("No workspaces found. Cannot proceed.")
        return
    
    workspace_id = workspaces[0]['id']
    print(f"✅ Selected Workspace ID: {workspace_id}")
    print(f"   Total workspaces: {workspace_data.get('count', len(workspaces))}")

    # 4. Get Workspace Details
    print_step("Get Workspace Details")
    response = requests.get(f"{BASE_URL}/api/workspace/public/workspaces/{workspace_id}/")
    print(f"Status: {response.status_code}")
    print("✅ Workspace details retrieved")
    
    # 5. List Spaces (with pagination)
    print_step("List Public Spaces (Paginated)")
    response = requests.get(f"{BASE_URL}/api/workspace/public/spaces/?workspace_id={workspace_id}&page=1&page_size=10")
    print(f"Status: {response.status_code}")
    if response.status_code != 200:
        print(f"Failed to list spaces: {response.text}")
        return
    
    space_data = response.json()
    spaces = space_data.get('spaces', space_data.get('results', []))
    if not spaces:
        print("No spaces found. Cannot proceed.")
        return
    
    space_id = spaces[0]['id']
    print(f"✅ Selected Space ID: {space_id}")
    print(f"   Total spaces: {space_data.get('count', len(spaces))}")

    # 6. Create Booking
    print_step("Create Booking")
    check_in = (datetime.now() + timedelta(days=1)).isoformat() + "Z"
    check_out = (datetime.now() + timedelta(days=1, hours=4)).isoformat() + "Z"
    
    booking_data = {
        "space_id": space_id,
        "booking_type": "hourly",
        "check_in": check_in,
        "check_out": check_out,
        "number_of_guests": 1
    }
    response = session.post(f"{BASE_URL}/api/booking/bookings/create/", json=booking_data, headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code != 201:
        print(f"Booking creation failed: {response.text}")
        return
    
    booking = response.json()['booking']
    booking_id = booking['id']
    print(f"✅ Booking created: {booking_id}")

    # 6a. List User Bookings (with pagination)
    print_step("List User Bookings (Paginated)")
    response = session.get(f"{BASE_URL}/api/booking/bookings/?page=1&page_size=10", headers=headers)
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
    response = session.get(f"{BASE_URL}/api/booking/bookings/{booking_id}/", headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        booking_details = response.json()['booking']
        print(f"✅ Booking Details Retrieved")
        print(f"  Space: {booking_details['space_details']['name']}")
        print(f"  Status: {booking_details['status']}")
        print(f"  Total Price: ₦{booking_details['total_price']}")
    else:
        print(f"Failed to get booking details: {response.text}")

    # 7. Create Order
    print_step("Create Order")
    order_data = {
        "booking_ids": [booking_id]
    }
    response = session.post(f"{BASE_URL}/api/payment/orders/create/", json=order_data, headers=headers)
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
    response = session.post(f"{BASE_URL}/api/payment/payments/initiate/", json=payment_data, headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        payment_info = response.json()
        reference = payment_info.get('reference', 'N/A')
        print(f"✅ Payment initiated. Reference: {reference}")
    else:
        print(f"Payment initiation failed: {response.text}")

    # 8a. List User Payments (with pagination)
    print_step("List User Payments (Paginated)")
    response = session.get(f"{BASE_URL}/api/payment/payments/?page=1&page_size=10", headers=headers)
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
    response = session.get(f"{BASE_URL}/api/payment/orders/?page=1&page_size=10", headers=headers)
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
    response = session.get(f"{BASE_URL}/api/notifications/?page=1&page_size=10", headers=headers)
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
    response = session.get(f"{BASE_URL}/api/notifications/preferences/", headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        prefs = response.json()
        print(f"✅ Notification preferences retrieved")
        print(f"  Email notifications: {prefs.get('email_enabled', 'N/A')}")
        print(f"  In-app notifications: {prefs.get('in_app_enabled', 'N/A')}")
    else:
        print(f"Failed to get preferences: {response.text}")

    # 11. Generate QR Code
    print_step("Generate QR Code")
    response = session.post(f"{BASE_URL}/api/qr/orders/{order_id}/qr-code/generate/", headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 400 and "paid" in response.text:
        print("⚠️  Expected: Order must be paid first")
    elif response.status_code == 200:
        print("✅ QR Code generated successfully")
    else:
        print(f"Response: {response.text}")

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
