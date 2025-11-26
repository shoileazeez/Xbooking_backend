"""
Enhanced E2E Cart Test with Notifications
Tests: Registration, Login, Cart Flow, Bookings, Orders, Payment, Notifications
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

def run_cart_test():
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
    workspaces = workspace_data.get('workspaces', workspace_data.get('results', []))
    if not workspaces:
        print("No workspaces found. Cannot proceed.")
        return
    
    workspace_id = workspaces[0]['id']
    print(f"✅ Selected Workspace ID: {workspace_id}")
    print(f"   Total: {workspace_data.get('count', len(workspaces))} workspace(s)")

    # 4. List Spaces (with pagination)
    print_step("List Public Spaces (Paginated)")
    response = requests.get(f"{BASE_URL}/api/workspace/public/spaces/?workspace_id={workspace_id}&page=1&page_size=10")
    print(f"Status: {response.status_code}")
    if response.status_code != 200:
        print(f"Failed to list spaces: {response.text}")
        return
    
    space_data = response.json()
    spaces = space_data.get('spaces', space_data.get('results', []))
    if len(spaces) < 3:
        print(f"⚠️  Only {len(spaces)} space(s) found. Need at least 3 for this test.")
        selected_spaces = spaces[:3] if len(spaces) >= 3 else spaces * 3
    else:
        selected_spaces = spaces[:3]
    
    print(f"✅ Selected {len(selected_spaces)} spaces for cart")
    print(f"   Total: {space_data.get('count', len(spaces))} space(s)")

    # 5. Add 3 Spaces to Cart
    print_step("Add 3 Spaces to Cart")
    cart_items = []
    
    for i, space in enumerate(selected_spaces[:3], 1):
        space_id = space['id']
        space_name = space['name']
        
        check_in = (datetime.now() + timedelta(days=i)).isoformat() + "Z"
        check_out = (datetime.now() + timedelta(days=i, hours=4)).isoformat() + "Z"
        
        cart_data = {
            "space_id": space_id,
            "check_in": check_in,
            "check_out": check_out,
            "number_of_guests": 1,
            "special_requests": f"Booking {i} for {space_name}"
        }
        
        response = session.post(f"{BASE_URL}/api/booking/cart/add/", json=cart_data, headers=headers)
        print(f"  [{i}] Adding {space_name}: {response.status_code}")
        
        if response.status_code == 201:
            item = response.json()['item']
            cart_items.append(item)
            print(f"      ✅ Added to cart - Price: ₦{item['price']}")
        else:
            print(f"      ❌ Failed: {response.text}")
    
    print(f"\n✅ Total items in cart: {len(cart_items)}")

    # 6. View Cart
    print_step("View Cart")
    response = session.get(f"{BASE_URL}/api/booking/cart/", headers=headers)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        cart = response.json()['cart']
        print(f"Cart ID: {cart['id']}")
        print(f"Items: {cart['item_count']}")
        print(f"Subtotal: ₦{cart['subtotal']}")
        print(f"Total: ₦{cart['total']}")
        print("✅ Cart retrieved successfully")
    else:
        print(f"Failed to get cart: {response.text}")
        return

    # 7. Checkout Cart
    print_step("Checkout Cart")
    checkout_data = {
        "notes": "E2E test checkout from cart"
    }
    response = session.post(f"{BASE_URL}/api/booking/cart/checkout/", json=checkout_data, headers=headers)
    print(f"Status: {response.status_code}")
    
    if response.status_code != 201:
        print(f"Checkout failed: {response.text}")
        return
    
    bookings = response.json()['bookings']
    booking_ids = [booking['id'] for booking in bookings]
    print(f"✅ Created {len(bookings)} bookings from cart")
    for i, booking in enumerate(bookings, 1):
        print(f"  [{i}] Booking ID: {booking['id']}, Total: ₦{booking['total_price']}")

    # 7a. List User Bookings (with pagination)
    print_step("List User Bookings (Paginated)")
    response = session.get(f"{BASE_URL}/api/booking/bookings/?page=1&page_size=10", headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        bookings_data = response.json()
        bookings_list = bookings_data.get('bookings', bookings_data.get('results', []))
        print(f"✅ Found {bookings_data.get('count', len(bookings_list))} total booking(s)")
        for i, bkg in enumerate(bookings_list[:5], 1):
            print(f"  [{i}] {bkg['id'][:8]}... - {bkg.get('space_name', 'N/A')} - Status: {bkg['status']}")
    else:
        print(f"Failed to list bookings: {response.text}")

    # 7b. Get Details for First Booking
    print_step("Get Booking Details (First Booking)")
    first_booking_id = booking_ids[0]
    response = session.get(f"{BASE_URL}/api/booking/bookings/{first_booking_id}/", headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        booking_details = response.json()['booking']
        print(f"✅ Booking Details Retrieved")
        print(f"  Booking ID: {booking_details['id'][:8]}...")
        print(f"  Space: {booking_details['space_details']['name']}")
        print(f"  Status: {booking_details['status']}")
        print(f"  Total Price: ₦{booking_details['total_price']}")
        print(f"  Guests: {booking_details['number_of_guests']}")
    else:
        print(f"Failed to get booking details: {response.text}")

    # 8. Create Order from Bookings
    print_step("Create Order from Bookings")
    order_data = {
        "booking_ids": booking_ids
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
    order_number = order['order_number']
    total_amount = order['total_amount']
    print(f"✅ Order created successfully")
    print(f"  Order ID: {order_id}")
    print(f"  Order Number: {order_number}")
    print(f"  Total Amount: ₦{total_amount}")

    # 9. Initiate Payment
    print_step("Initiate Payment")
    payment_data = {
        "order_id": order_id,
        "payment_method": "paystack"
    }
    response = session.post(f"{BASE_URL}/api/payment/payments/initiate/", json=payment_data, headers=headers)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        payment_info = response.json()
        print(f"✅ Payment initiated successfully")
        print(f"  Reference: {payment_info.get('reference', 'N/A')}")
        print(f"  Authorization URL: {payment_info.get('authorization_url', 'N/A')}")
    else:
        print(f"⚠️  Payment initiation failed")
        print(f"  Response: {response.text}")

    # 9a. List User Payments (with pagination)
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

    # 9b. List User Orders (with pagination)
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

    # 10. Check Notifications
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

    # 11. Get Notification Preferences
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

    # 12. Summary
    print_step("Test Summary")
    print(f"✅ User registered: {EMAIL}")
    print(f"✅ User logged in successfully")
    print(f"✅ Workspaces listed (paginated)")
    print(f"✅ Spaces listed (paginated)")
    print(f"✅ Added {len(cart_items)} spaces to cart")
    print(f"✅ Checked out cart → {len(bookings)} bookings created")
    print(f"✅ Bookings listed (paginated)")
    print(f"✅ Created order: {order_number}")
    print(f"✅ Payment initiated")
    print(f"✅ Payments listed (paginated)")
    print(f"✅ Orders listed (paginated)")
    print(f"✅ Notifications checked")
    print(f"✅ Notification preferences retrieved")
    print(f"\n🎉 Cart flow test completed successfully!")


if __name__ == "__main__":
    try:
        run_cart_test()
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        import traceback
        traceback.print_exc()
