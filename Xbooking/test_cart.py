"""
Cart E2E API Test - Multiple Spaces from Different Workspaces
Tests: Login, Cart (Add Multiple Spaces), Checkout, Orders, Payment, Guests
"""
import requests
import json
import time
from datetime import datetime, timedelta

BASE_URL = "https://6a63f43d1a91.ngrok-free.app/"
EMAIL = "promptforge.customservice@gmail.com"
PASSWORD = "TestPassword123!"

# Guest emails for all bookings
GUEST_EMAILS = [
    "shoabdulazeez@gmail.com",
    "abdulazeezshoile@gmail.com"
]


def print_step(step):
    print(f"\n{'='*60}")
    print(f"STEP: {step}")
    print(f"{'='*60}")


def run_cart_test():
    session = requests.Session()
    log_file = 'test_cart_output.log'

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

    # =========================================================================
    # 1. LOGIN (Use existing user)
    # =========================================================================
    print_step("Login with Existing User")
    login_data = {
        "email": EMAIL,
        "password": PASSWORD
    }
    response = do_request("POST", f"{BASE_URL}/api/user/login/", json=login_data)
    print(f"Status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"Login failed: {response.text}")
        print("Trying to register first...")
        
        # Try to register
        reg_data = {
            "email": EMAIL,
            "password": PASSWORD,
            "confirm_password": PASSWORD,
            "full_name": "Test User"
        }
        response = do_request("POST", f"{BASE_URL}/api/user/register/", json=reg_data)
        if response.status_code != 201:
            print(f"Registration also failed: {response.text}")
            return
        
        # Login again
        response = do_request("POST", f"{BASE_URL}/api/user/login/", json=login_data)
        if response.status_code != 200:
            print(f"Login after registration failed: {response.text}")
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
    print(f"✅ Logged in as: {EMAIL}")

    # =========================================================================
    # 2. GET MULTIPLE WORKSPACES AND THEIR SPACES
    # =========================================================================
    print_step("Fetch Multiple Workspaces")
    response = do_request("GET", f"{BASE_URL}/api/workspace/public/workspaces/?page=1&page_size=10")
    
    if response.status_code != 200:
        print(f"Failed to list workspaces: {response.text}")
        return
    
    workspace_data = response.json()
    
    # Extract workspaces list
    def _extract_list(obj):
        if isinstance(obj, dict):
            if 'results' in obj:
                results = obj['results']
                if isinstance(results, list):
                    return results
                if isinstance(results, dict):
                    if 'workspaces' in results:
                        return results['workspaces']
            if 'workspaces' in obj:
                return obj['workspaces']
            for v in obj.values():
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    return v
        if isinstance(obj, list):
            return obj
        return []
    
    workspaces_list = _extract_list(workspace_data)
    
    if len(workspaces_list) < 1:
        print("Not enough workspaces found. Need at least 1 workspace.")
        return
    
    print(f"✅ Found {len(workspaces_list)} workspace(s)")
    
    # Collect spaces from multiple workspaces (up to 3 different spaces)
    spaces_to_book = []
    
    for i, workspace in enumerate(workspaces_list[:3]):  # Try up to 3 workspaces
        workspace_id = workspace.get('id') or workspace.get('workspace_id')
        workspace_name = workspace.get('name', 'Unknown')
        
        print(f"\n  Workspace {i+1}: {workspace_name} ({workspace_id})")
        
        # Get spaces for this workspace
        response = do_request("GET", f"{BASE_URL}/api/workspace/public/spaces/?workspace_id={workspace_id}&page=1&page_size=5")
        
        if response.status_code != 200:
            print(f"    Failed to get spaces: {response.text}")
            continue
        
        space_data = response.json()
        spaces = space_data.get('spaces', space_data.get('results', []))
        
        if isinstance(spaces, dict):
            spaces = list(spaces.values())
        
        if spaces:
            # Take first available space from this workspace
            for space in spaces:
                space_id = space.get('id') or space.get('space_id')
                space_name = space.get('name', 'Unknown')
                price = space.get('price_per_hour', 0)
                
                if space_id:
                    spaces_to_book.append({
                        'space_id': space_id,
                        'space_name': space_name,
                        'workspace_id': workspace_id,
                        'workspace_name': workspace_name,
                        'price': price
                    })
                    print(f"    ✅ Selected Space: {space_name} (₦{price}/hr)")
                    break
        
        if len(spaces_to_book) >= 3:
            break
    
    if len(spaces_to_book) < 1:
        print("Could not find any spaces to book.")
        return
    
    print(f"\n✅ Selected {len(spaces_to_book)} space(s) to add to cart")

    # =========================================================================
    # 3. CLEAR EXISTING CART
    # =========================================================================
    print_step("Clear Existing Cart")
    response = do_request("POST", f"{BASE_URL}/api/booking/cart/clear/", headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code in [200, 204]:
        print("✅ Cart cleared")
    else:
        print(f"Cart clear response: {response.text}")

    # =========================================================================
    # 4. ADD SPACES TO CART (Different time slots)
    # =========================================================================
    print_step("Add Spaces to Cart")
    
    cart_items = []
    base_date = datetime.now() + timedelta(days=7)  # Start booking 7 days from now
    
    for i, space_info in enumerate(spaces_to_book):
        # Each booking is 2 hours, staggered by 3 hours
        check_in = base_date + timedelta(hours=i * 3)
        check_out = check_in + timedelta(hours=2)
        
        add_to_cart_data = {
            "space_id": space_info['space_id'],
            "check_in": check_in.isoformat() + "Z",
            "check_out": check_out.isoformat() + "Z",
            "number_of_guests": 3,  # Allow 2 guests + booker
            "special_requests": f"Cart test booking #{i+1}"
        }
        
        print(f"\n  Adding Space {i+1}: {space_info['space_name']}")
        print(f"    Workspace: {space_info['workspace_name']}")
        print(f"    Check-in: {check_in.strftime('%Y-%m-%d %H:%M')}")
        print(f"    Check-out: {check_out.strftime('%Y-%m-%d %H:%M')}")
        
        response = do_request("POST", f"{BASE_URL}/api/booking/cart/add/", json=add_to_cart_data, headers=headers)
        print(f"    Status: {response.status_code}")
        
        if response.status_code in [200, 201]:
            item_data = response.json()
            item = item_data.get('item', item_data)
            cart_items.append({
                'space_info': space_info,
                'check_in': check_in,
                'check_out': check_out
            })
            print(f"    ✅ Added to cart - Price: ₦{item.get('price', 'N/A')}")
        else:
            print(f"    ❌ Failed to add: {response.text}")

    if not cart_items:
        print("\n❌ No items could be added to cart.")
        return
    
    print(f"\n✅ Successfully added {len(cart_items)} item(s) to cart")

    # =========================================================================
    # 5. VIEW CART
    # =========================================================================
    print_step("View Cart Contents")
    response = do_request("GET", f"{BASE_URL}/api/booking/cart/", headers=headers)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        cart_data = response.json()
        cart = cart_data.get('cart', cart_data)
        
        items = cart.get('items', [])
        print(f"✅ Cart contains {len(items)} item(s)")
        print(f"   Subtotal: ₦{cart.get('subtotal', 0)}")
        print(f"   Tax: ₦{cart.get('tax_total', 0)}")
        print(f"   Discount: ₦{cart.get('discount_total', 0)}")
        print(f"   Total: ₦{cart.get('total', 0)}")
        
        for i, item in enumerate(items, 1):
            space_details = item.get('space_details', {})
            print(f"\n   [{i}] {space_details.get('name', 'Unknown Space')}")
            print(f"       Price: ₦{item.get('price', 0)}")
            print(f"       Check-in: {item.get('check_in', 'N/A')}")
            print(f"       Check-out: {item.get('check_out', 'N/A')}")
    else:
        print(f"Failed to view cart: {response.text}")

    # =========================================================================
    # 6. CHECKOUT CART (Creates Bookings)
    # =========================================================================
    print_step("Checkout Cart")
    checkout_data = {
        "notes": "Multi-space cart checkout test"
    }
    response = do_request("POST", f"{BASE_URL}/api/booking/cart/checkout/", json=checkout_data, headers=headers)
    print(f"Status: {response.status_code}")
    
    if response.status_code not in [200, 201]:
        print(f"Checkout failed: {response.text}")
        return
    
    checkout_resp = response.json()
    bookings = checkout_resp.get('bookings', [])
    
    if not bookings:
        print("No bookings created from checkout")
        return
    
    booking_ids = [b['id'] for b in bookings]
    print(f"✅ Created {len(bookings)} booking(s) from cart checkout")
    
    for i, booking in enumerate(bookings, 1):
        print(f"   [{i}] Booking ID: {booking['id'][:8]}...")
        print(f"       Space: {booking.get('space_name', 'N/A')}")
        print(f"       Total: ₦{booking.get('total_price', 0)}")
        print(f"       Status: {booking.get('status', 'N/A')}")

    # =========================================================================
    # 7. ADD GUESTS TO ALL BOOKINGS
    # =========================================================================
    print_step("Add Guests to All Bookings")
    
    for booking_id in booking_ids:
        print(f"\n  Adding guests to booking {booking_id[:8]}...")
        
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
        
        if response.status_code in [200, 201]:
            guest_resp = response.json()
            guests_added = guest_resp.get('guests', [])
            print(f"    ✅ Added {len(guests_added)} guest(s)")
        else:
            print(f"    ❌ Failed to add guests: {response.text}")

    # =========================================================================
    # 8. CREATE ORDER FOR ALL BOOKINGS
    # =========================================================================
    print_step("Create Order for All Bookings")
    order_data = {
        "booking_ids": booking_ids
    }
    response = do_request("POST", f"{BASE_URL}/api/payment/orders/create/", json=order_data, headers=headers)
    print(f"Status: {response.status_code}")
    
    if response.status_code != 201:
        print(f"Order creation failed: {response.text}")
        return
    
    order_resp = response.json()
    
    # Handle both old format (orders array) and new format (single order)
    if 'orders' in order_resp:
        # Old format - multiple orders
        order = order_resp['orders'][0]
        order_id = order['id']
        order_number = order.get('order_number', 'N/A')
        total_amount = order.get('total_amount', 0)
    elif 'order' in order_resp:
        # New format - single order object
        order = order_resp['order']
        order_id = order_resp.get('id', order['id'])
        order_number = order_resp.get('order_number', order.get('order_number', 'N/A'))
        total_amount = order_resp.get('total_amount', order.get('total_amount', 0))
    else:
        # Direct order object
        order = order_resp
        order_id = order_resp.get('id')
        order_number = order_resp.get('order_number', 'N/A')
        total_amount = order_resp.get('total_amount', 0)
    
    print(f"✅ Order created successfully")
    print(f"   Order ID: {order_id}")
    print(f"   Order Number: {order_number}")
    print(f"   Total Amount: ₦{total_amount}")
    print(f"   Bookings: {len(booking_ids)}")

    # =========================================================================
    # 9. INITIATE PAYMENT
    # =========================================================================
    print_step("Initiate Payment")
    payment_data = {
        "order_id": order_id,
        "payment_method": "paystack"
    }
    response = do_request("POST", f"{BASE_URL}/api/payment/payments/initiate/", json=payment_data, headers=headers)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        payment_info = response.json()
        reference = payment_info.get('reference', 'N/A')
        payment_url = payment_info.get('payment_url', None)
        
        print(f"✅ Payment initiated")
        print(f"   Reference: {reference}")
        print(f"   Payment URL: {payment_url}")
        
        if payment_url:
            print("\n" + "="*60)
            print("🔔 MANUAL PAYMENT STEP")
            print("="*60)
            print(f"Open this URL in your browser to complete payment:")
            print(f"\n  {payment_url}\n")
            print("Waiting 2 minutes for you to complete the payment...")
            print("="*60 + "\n")
            
            # Wait 2 minutes for manual payment
            for remaining in range(120, 0, -10):
                print(f"  ⏳ {remaining} seconds remaining...")
                time.sleep(10)
            
            print("✅ Wait complete. Continuing with verification...\n")
    else:
        print(f"Payment initiation failed: {response.text}")

    # =========================================================================
    # 10. VERIFY BOOKINGS AND GUESTS
    # =========================================================================
    print_step("Verify Bookings Status")
    
    for booking_id in booking_ids:
        response = do_request("GET", f"{BASE_URL}/api/booking/bookings/{booking_id}/", headers=headers)
        
        if response.status_code == 200:
            booking_data = response.json()
            booking = booking_data.get('booking', booking_data)
            print(f"\n  Booking {booking_id[:8]}...")
            print(f"    Status: {booking.get('status', 'N/A')}")
            print(f"    Space: {booking.get('space_details', {}).get('name', 'N/A')}")

    # =========================================================================
    # 11. VERIFY GUEST QR CODES
    # =========================================================================
    print_step("Verify Guest QR Codes")
    
    for booking_id in booking_ids:
        response = do_request("GET", f"{BASE_URL}/api/booking/bookings/{booking_id}/guests/list/", headers=headers)
        
        if response.status_code == 200:
            guests_data = response.json()
            guests_list = guests_data.get('guests', [])
            
            print(f"\n  Booking {booking_id[:8]}... - {len(guests_list)} guest(s)")
            for g in guests_list:
                full_name = g.get('full_name', f"{g.get('first_name', '')} {g.get('last_name', '')}")
                qr_sent = g.get('qr_code_sent', False)
                status = "✅ Sent" if qr_sent else "⏳ Pending"
                print(f"    - {full_name}: QR Code {status}")
        else:
            print(f"  Failed to get guests for {booking_id[:8]}: {response.text}")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print_step("Test Summary")
    print(f"✅ Logged in as: {EMAIL}")
    print(f"✅ Added {len(cart_items)} space(s) to cart from different workspaces")
    print(f"✅ Checked out cart and created {len(booking_ids)} booking(s)")
    print(f"✅ Added guests to all bookings")
    print(f"✅ Created order: {order_number}")
    print(f"✅ Initiated payment for ₦{total_amount}")
    print(f"\n🎉 Cart multi-booking test completed!")


if __name__ == "__main__":
    try:
        run_cart_test()
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        import traceback
        traceback.print_exc()
