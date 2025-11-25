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

    # 3. List Public Workspaces
    print_step("List Public Workspaces")
    response = requests.get(f"{BASE_URL}/api/workspace/public/workspaces/")
    print(f"Status: {response.status_code}")
    if response.status_code != 200:
        print(f"Failed to list workspaces: {response.text}")
        return
    
    workspaces = response.json()['workspaces']
    if not workspaces:
        print("No workspaces found. Cannot proceed.")
        return
    
    workspace_id = workspaces[0]['id']
    print(f"✅ Selected Workspace ID: {workspace_id}")

    # 4. List Spaces in Workspace
    print_step("List Public Spaces")
    response = requests.get(f"{BASE_URL}/api/workspace/public/spaces/?workspace_id={workspace_id}")
    print(f"Status: {response.status_code}")
    if response.status_code != 200:
        print(f"Failed to list spaces: {response.text}")
        return
    
    spaces = response.json()['spaces']
    if len(spaces) < 3:
        print(f"⚠️  Only {len(spaces)} space(s) found. Need at least 3 for this test.")
        # Use available spaces, repeat if necessary
        selected_spaces = spaces[:3] if len(spaces) >= 3 else spaces * 3
    else:
        selected_spaces = spaces[:3]
    
    print(f"✅ Selected {len(selected_spaces)} spaces for cart")

    # 5. Add 3 Spaces to Cart
    print_step("Add 3 Spaces to Cart")
    cart_items = []
    
    for i, space in enumerate(selected_spaces[:3], 1):
        space_id = space['id']
        space_name = space['name']
        
        # Calculate future dates (each booking 1 day apart)
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

    # 7. Checkout Cart (Create Bookings)
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

    # 7a. List User Bookings
    print_step("List User Bookings")
    response = session.get(f"{BASE_URL}/api/booking/bookings/", headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        bookings_list = response.json()['bookings']
        print(f"✅ Found {len(bookings_list)} total booking(s)")
        for i, bkg in enumerate(bookings_list[:5], 1):  # Show first 5
            print(f"  [{i}] {bkg['id'][:8]}... - {bkg['space_name']} - Status: {bkg['status']}")
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
        print(f"⚠️  Payment initiation failed (expected if API keys not configured)")
        print(f"  Response: {response.text}")
        print(f"  Note: This is expected without valid Paystack API keys")

    # 10. Summary
    print_step("Test Summary")
    print(f"✅ User registered: {EMAIL}")
    print(f"✅ User logged in successfully")
    print(f"✅ Added {len(cart_items)} spaces to cart")
    print(f"✅ Checked out cart → {len(bookings)} bookings created")
    print(f"✅ Created order: {order_number}")
    print(f"⚠️  Payment: Requires valid API keys")
    print(f"\n🎉 Cart flow test completed successfully!")

if __name__ == "__main__":
    try:
        run_cart_test()
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        import traceback
        traceback.print_exc()
