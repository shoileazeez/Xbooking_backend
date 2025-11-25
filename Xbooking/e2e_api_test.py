import requests
import json
import time
import uuid

BASE_URL = "http://localhost:8000"
EMAIL = f"testuser_{uuid.uuid4()}@example.com"
PASSWORD = "TestPassword123!"
FIRST_NAME = "Abdulazeez"
LAST_NAME = "Shoile"

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
    print(f"Response: {response.text}")
    if response.status_code != 201:
        print("Registration failed")
        return

    # 2. Login
    print_step("Login")
    login_data = {
        "email": EMAIL,
        "password": PASSWORD
    }
    response = session.post(f"{BASE_URL}/api/user/login/", json=login_data)
    print(f"Status: {response.status_code}")
    if response.status_code != 200:
        print("Login failed")
        return
    
    
    tokens = response.json()
    # Handle both possible response structures
    if 'token' in tokens:
        access_token = tokens['token']['access_token']
    elif 'access' in tokens:
        access_token = tokens['access']
    else:
        print(f"Unexpected response structure: {tokens}")
        return
    
    headers = {'Authorization': f'Bearer {access_token}'}
    print("Login successful, token received")

    # 3. List Public Workspaces
    print_step("List Public Workspaces")
    response = requests.get(f"{BASE_URL}/api/workspace/public/workspaces/")
    print(f"Status: {response.status_code}")
    if response.status_code != 200:
        print("Failed to list workspaces")
        return
    
    workspaces = response.json()['workspaces']
    if not workspaces:
        print("No workspaces found. Cannot proceed.")
        return
    
    workspace_id = workspaces[0]['id']
    print(f"Selected Workspace ID: {workspace_id}")

    # 4. Get Workspace Details
    print_step("Get Workspace Details")
    response = requests.get(f"{BASE_URL}/api/workspace/public/workspaces/{workspace_id}/")
    print(f"Status: {response.status_code}")
    
    # 5. List Spaces in Workspace
    print_step("List Public Spaces")
    response = requests.get(f"{BASE_URL}/api/workspace/public/spaces/?workspace_id={workspace_id}")
    print(f"Status: {response.status_code}")
    spaces = response.json()['spaces']
    if not spaces:
        print("No spaces found in workspace. Cannot proceed.")
        return
    
    space_id = spaces[0]['id']
    print(f"Selected Space ID: {space_id}")

    # 6. Create Booking (Direct)
    print_step("Create Booking")
    # Calculate future dates
    # Assuming format YYYY-MM-DDTHH:MM:SSZ
    from datetime import datetime, timedelta
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
    print(f"Response: {response.text}")
    if response.status_code != 201:
        print("Booking creation failed")
        return
    
    
    booking = response.json()['booking']
    booking_id = booking['id']
    print(f"Booking created: {booking_id}")

    # 6a. List User Bookings
    print_step("List User Bookings")
    response = session.get(f"{BASE_URL}/api/booking/bookings/", headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        bookings_list = response.json()['bookings']
        print(f"✅ Found {len(bookings_list)} booking(s)")
        for i, bkg in enumerate(bookings_list[:3], 1):  # Show first 3
            print(f"  [{i}] {bkg['id'][:8]}... - {bkg['space_name']} - Status: {bkg['status']}")
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
        print(f"  Check-in: {booking_details['check_in']}")
    else:
        print(f"Failed to get booking details: {response.text}")


    # 7. Create Order
    print_step("Create Order")
    order_data = {
        "booking_ids": [booking_id]
    }
    response = session.post(f"{BASE_URL}/api/payment/orders/create/", json=order_data, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    if response.status_code != 201:
        print("Order creation failed")
        return
    
    # Handle response structure (might be list or object wrapper)
    order_resp = response.json()
    if 'orders' in order_resp:
        order = order_resp['orders'][0]
    else:
        order = order_resp # Fallback if changed
        
    order_id = order['id']
    print(f"Order created: {order_id}")

    # 8. Initiate Payment
    print_step("Initiate Payment")
    payment_data = {
        "order_id": order_id,
        "payment_method": "paystack"
    }
    response = session.post(f"{BASE_URL}/api/payment/payments/initiate/", json=payment_data, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    if response.status_code != 200:
        print("Payment initiation failed")
        return
    
    payment_info = response.json()
    reference = payment_info['reference']
    print(f"Payment initiated. Reference: {reference}")

    # 9. Simulate Webhook (Payment Success)
    print_step("Simulate Payment Webhook")
    # This requires knowing the secret to sign, or we can just check if we can mock it or manually update DB if we were running tests.
    # Since we can't easily sign without the secret key from env (which we have access to, but it's complex to replicate the signature logic here),
    # We might skip this or try to hit the callback if we can generate a valid signature.
    # Alternatively, we can use the 'verify' endpoint if one exists, but usually it's a callback.
    # For this script, we might stop here or try to verify status.
    
    print("Skipping webhook simulation (requires valid signature).")
    print("To fully test, you would need to manually update the payment status to 'success' in the DB or send a valid webhook.")

    # 10. Add Guest
    print_step("Add Guest")
    guest_data = {
        "booking_id": booking_id,
        "name": "Guest User",
        "email": "guest@example.com"
    }
    response = session.post(f"{BASE_URL}/api/booking/bookings/{booking_id}/guests/", json=guest_data, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    # 11. Generate QR Code (might fail if order not paid)
    print_step("Generate QR Code")
    response = session.post(f"{BASE_URL}/api/qr/generate/{order_id}/", headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    if response.status_code == 400 and "paid" in response.text:
        print("Expected failure: Order is not paid yet.")
    else:
        print("QR Code generation response received.")

if __name__ == "__main__":
    try:
        run_test()
    except Exception as e:
        print(f"An error occurred: {e}")
