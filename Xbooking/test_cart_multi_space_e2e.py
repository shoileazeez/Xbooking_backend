"""
Cart Multi-Space E2E API Test
Tests: Login, Cart with Multiple Spaces from Same/Different Workspaces, Guests for Each Booking, Payment, QR Codes

Flow:
1. Login User
2. List Multiple Workspaces
3. Select Spaces from Different Workspaces
4. Add Multiple Spaces to Cart
5. View Cart (grouped by workspace)
6. Checkout Cart → Create Multiple Bookings
7. Add Guests to Each Booking
8. Create Single Order for All Bookings
9. Initiate Payment
10. Get QR Codes for All Bookings
11. Verify All Bookings and Guests
"""
import requests
import json
import time
from datetime import datetime, timedelta

BASE_URL = "https://3e9d98bfbd96.ngrok-free.app"
EMAIL = "promptforge.customservice@gmail.com"  # Use existing user
PASSWORD = "TestPassword123!"

# Guest emails for all bookings
GUEST_EMAILS = [
    "cart_guest1@test.com",
    "cart_guest2@test.com"
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
    log_file = 'test_cart_multi_space_output.log'

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
    # 1. REGISTER (if needed) and LOGIN
    # =========================================================================
    print_step("1. Ensure user exists / Register")
    reg_data = {
        "email": EMAIL,
        "password": PASSWORD,
        "confirm_password": PASSWORD,
        "full_name": "Cart Multi Test User"
    }
    print_info(f"Registering (if missing): {EMAIL}")
    reg_resp = do_request("POST", f"{BASE_URL}/api/user/register/", json=reg_data)
    print(f"Status: {reg_resp.status_code}")
    if reg_resp.status_code == 201:
        print_success("Registration successful")
    elif reg_resp.status_code == 400 and 'already' in reg_resp.text.lower():
        print_info("User already exists, proceeding to login")
    else:
        # Non-fatal: proceed to login and let login step handle failures
        print_info(f"Registration response: {reg_resp.status_code} {reg_resp.text}")

    print_step("1. Login")
    login_data = {
        "email": EMAIL,
        "password": PASSWORD
    }
    response = do_request("POST", f"{BASE_URL}/api/user/login/", json=login_data)
    print(f"Status: {response.status_code}")
    
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
    print_success(f"Logged in as: {EMAIL}")

    # Quick check: GET user notifications and preferences after login
    print_step("1.a Check Notifications (post-login)")
    notif_resp = do_request("GET", f"{BASE_URL}/api/notifications/?page=1&page_size=10", headers=headers)
    print(f"Status: {notif_resp.status_code}")
    if notif_resp.status_code == 200:
        notif_data = notif_resp.json()
        notifs = notif_data.get('notifications', notif_data.get('results', []))
        print_info(f"  Found {notif_data.get('count', len(notifs))} notification(s)")
    else:
        print_info(f"  Notifications fetch: {notif_resp.status_code} {notif_resp.text}")

    pref_resp = do_request("GET", f"{BASE_URL}/api/notifications/preferences/", headers=headers)
    print(f"Status: {pref_resp.status_code}")
    if pref_resp.status_code == 200:
        prefs = pref_resp.json()
        print_info(f"  Notification prefs: email={prefs.get('email_enabled')} in_app={prefs.get('in_app_enabled')}")
    else:
        print_info(f"  Preferences fetch: {pref_resp.status_code} {pref_resp.text}")

    # =========================================================================
    # 2. LIST MULTIPLE WORKSPACES
    # =========================================================================
    print_step("2. List Multiple Workspaces")
    response = do_request("GET", f"{BASE_URL}/api/workspace/public/workspaces/?page=1&page_size=10")
    print(f"Status: {response.status_code}")
    
    if response.status_code != 200:
        print_error(f"Failed to list workspaces: {response.text}")
        return
    
    workspaces = _extract_list(response.json())
    if not workspaces:
        print_error("No workspaces found")
        return
    
    print_success(f"Found {len(workspaces)} workspace(s)")
    for i, ws in enumerate(workspaces[:10], 1):
        # show a few for debug; we'll search across them for spaces later
        print_info(f"  [{i}] {ws.get('name', 'Unknown')} ({ws.get('id', ws.get('workspace_id'))})")

    # =========================================================================
    # 3. SELECT SPACES FROM MULTIPLE WORKSPACES
    # =========================================================================
    print_step("3. Select Spaces from Multiple Workspaces")

    # Aim to collect up to `max_spaces` spaces across available workspaces
    max_spaces = 5
    spaces_to_book = []

    for i, workspace in enumerate(workspaces):
        if len(spaces_to_book) >= max_spaces:
            break

        workspace_id = workspace.get('id') or workspace.get('workspace_id')
        workspace_name = workspace.get('name', 'Unknown')
        print_info(f"\n  Scanning Workspace {i+1}: {workspace_name}")

        # Get spaces for this workspace (grab more results per workspace)
        response = do_request("GET", f"{BASE_URL}/api/workspace/public/spaces/?workspace_id={workspace_id}&page=1&page_size=10")
        if response.status_code != 200:
            print_error(f"    Failed to get spaces: {response.text}")
            continue

        space_data = response.json()
        spaces = space_data.get('spaces', space_data.get('results', []))
        if isinstance(spaces, dict):
            spaces = list(spaces.values())

        if not spaces:
            print_info("    No spaces returned for this workspace")
            continue

        # Append up to remaining required spaces from this workspace
        for space in spaces:
            if len(spaces_to_book) >= max_spaces:
                break
            space_id = space.get('id') or space.get('space_id')
            space_name = space.get('name', 'Unknown')
            price = space.get('price_per_hour', 0)
            if not space_id:
                continue

            spaces_to_book.append({
                'space_id': str(space_id),
                'space_name': space_name,
                'workspace_id': str(workspace_id),
                'workspace_name': workspace_name,
                'price_per_hour': price
            })
            print_success(f"    Selected: {space_name} (₦{price}/hr)")

    # If we found fewer than desired, continue with whatever we have
    
    if len(spaces_to_book) < 1:
        print_error("Could not find any spaces to book")
        return
    
    print_success(f"Selected {len(spaces_to_book)} space(s) for cart (target {max_spaces})")

    # =========================================================================
    # 4. CLEAR EXISTING CART
    # =========================================================================
    print_step("4. Clear Existing Cart")
    response = do_request("POST", f"{BASE_URL}/api/booking/cart/clear/", headers=headers)
    print(f"Status: {response.status_code}")
    
    if response.status_code in [200, 204]:
        print_success("Cart cleared")
    else:
        print_info(f"Cart clear response: {response.text}")

    # =========================================================================
    # 5. ADD SPACES TO CART (Different time slots)
    # =========================================================================
    print_step("5. Add Spaces to Cart")
    
    cart_items_info = []
    base_date = datetime.now() + timedelta(days=5)
    
    for i, space_info in enumerate(spaces_to_book):
        # Each booking is 2 hours, staggered by 3 hours
        # For each selected space, try to pick an available hourly slot on base_date
        slot_id = None
        slot_start = None
        slot_end = None
        date_str = base_date.date().isoformat()
        hourly_url = f"{BASE_URL}/api/workspace/spaces/{space_info['space_id']}/calendar/?mode=hourly&date={date_str}"
        print_info(f"\n  Querying slots for Space {i+1}: {space_info['space_name']} on {date_str}")
        cal_resp = do_request("GET", hourly_url)
        if cal_resp.status_code == 200:
            slots = cal_resp.json().get('slots', [])
            for s in slots:
                if s.get('available'):
                    slot_id = s.get('id')
                    slot_start = s.get('start')
                    slot_end = s.get('end')
                    break

        if slot_id:
            # build check_in/check_out datetimes from slot start/end
            try:
                check_in = datetime.fromisoformat(f"{date_str}T{slot_start}")
            except Exception:
                check_in = base_date
            try:
                check_out = datetime.fromisoformat(f"{date_str}T{slot_end}")
            except Exception:
                check_out = check_in + timedelta(hours=2)

            add_to_cart_data = {
                "space_id": space_info['space_id'],
                "booking_type": "hourly",
                "slot_id": slot_id,
                "number_of_guests": 3,
                "special_requests": f"Multi-space cart test #{i+1}"
            }
            print_info(f"  Adding Space {i+1}: {space_info['space_name']} (slot {slot_id} {slot_start}-{slot_end})")
        else:
            # Fallback: choose a datetime window
            check_in = base_date + timedelta(hours=9 + i * 3)
            check_out = check_in + timedelta(hours=2)
            add_to_cart_data = {
                "space_id": space_info['space_id'],
                "booking_type": "hourly",
                "check_in": check_in.isoformat() + "Z",
                "check_out": check_out.isoformat() + "Z",
                "number_of_guests": 3,
                "special_requests": f"Multi-space cart test #{i+1}"
            }
            print_info(f"  No slot found; adding by datetime: {check_in.strftime('%Y-%m-%d %H:%M')} - {check_out.strftime('%H:%M')}")

        # Try add-to-cart with retries for transient slot holds (409)
        add_attempts = 0
        added_ok = False
        while add_attempts < 3 and not added_ok:
            add_attempts += 1
            response = do_request("POST", f"{BASE_URL}/api/booking/cart/add/", json=add_to_cart_data, headers=headers)
            print(f"    Attempt {add_attempts} - Status: {response.status_code}")

            if response.status_code in [200, 201]:
                item_data = response.json()
                item = item_data.get('item', item_data)
                cart_items_info.append({
                    'space_info': space_info,
                    'check_in': check_in,
                    'check_out': check_out,
                    'price': item.get('price', 0)
                })
                print_success(f"    Added - Price: ₦{item.get('price', 'N/A')}")
                added_ok = True
                break

            # If slot is temporarily held, wait and retry a couple times
            if response.status_code == 409:
                print_info("    Slot temporarily held, retrying shortly...")
                time.sleep(3)
                continue

            # For other errors, don't retry
            print_error(f"    Failed: {response.text}")
            break
    
    if not cart_items_info:
        print_error("No items could be added to cart")
        return
    
    print_success(f"Added {len(cart_items_info)} item(s) to cart")

    # =========================================================================
    # 6. VIEW CART (Grouped by Workspace)
    # =========================================================================
    print_step("6. View Cart Contents")
    response = do_request("GET", f"{BASE_URL}/api/booking/cart/", headers=headers)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        cart_data = response.json()
        cart = cart_data.get('cart', cart_data)
        
        items = cart.get('items', [])
        print_success(f"Cart contains {len(items)} item(s)")
        print_info(f"   Subtotal: ₦{cart.get('subtotal', 0)}")
        print_info(f"   Tax: ₦{cart.get('tax_total', 0)}")
        print_info(f"   Discount: ₦{cart.get('discount_total', 0)}")
        print_info(f"   Total: ₦{cart.get('total', 0)}")
        
        # Group by workspace
        workspace_groups = {}
        for item in items:
            space_details = item.get('space_details', {})
            ws_id = space_details.get('workspace_id', 'unknown')
            if ws_id not in workspace_groups:
                workspace_groups[ws_id] = []
            workspace_groups[ws_id].append(item)
        
        print_info(f"\n   Grouped by Workspace:")
        for ws_id, ws_items in workspace_groups.items():
            print_info(f"   Workspace {ws_id}:")
            for item in ws_items:
                space_name = item.get('space_details', {}).get('name', 'Unknown')
                print_info(f"      - {space_name}: ₦{item.get('price', 0)}")
    else:
        print_error(f"Failed to view cart: {response.text}")

    # =========================================================================
    # 7. CHECKOUT CART (Creates Multiple Bookings)
    # =========================================================================
    print_step("7. Checkout Cart")
    checkout_data = {
        "notes": "Multi-space cart checkout test"
    }
    response = do_request("POST", f"{BASE_URL}/api/booking/cart/checkout/", json=checkout_data, headers=headers)
    print(f"Status: {response.status_code}")
    
    if response.status_code not in [200, 201]:
        print_error(f"Checkout failed: {response.text}")
        return
    
    checkout_resp = response.json()
    bookings = checkout_resp.get('bookings', [])
    
    if not bookings:
        print_error("No bookings created from checkout")
        return
    
    booking_ids = [b['id'] for b in bookings]
    print_success(f"Created {len(bookings)} booking(s) from cart checkout")
    
    for i, booking in enumerate(bookings, 1):
        print_info(f"   [{i}] Booking ID: {booking['id'][:8]}...")
        print_info(f"       Space: {booking.get('space_name', 'N/A')}")
        print_info(f"       Total: ₦{booking.get('total_price', 0)}")
        print_info(f"       Status: {booking.get('status', 'N/A')}")

    # =========================================================================
    # 8. ADD GUESTS TO ALL BOOKINGS
    # =========================================================================
    print_step("8. Add Guests to All Bookings")
    
    for booking_id in booking_ids:
        print_info(f"\n  Adding guests to booking {booking_id[:8]}...")
        
        guests_payload = {
            "guests": [
                {
                    "first_name": "Cart",
                    "last_name": "Guest1",
                    "email": GUEST_EMAILS[0],
                    "phone": "+2348012345678"
                },
                {
                    "first_name": "Cart",
                    "last_name": "Guest2",
                    "email": GUEST_EMAILS[1],
                    "phone": "+2348087654321"
                }
            ]
        }
        
        response = do_request("POST", f"{BASE_URL}/api/booking/bookings/{booking_id}/guests/", json=guests_payload, headers=headers)
        
        if response.status_code in [200, 201]:
            guest_resp = response.json()
            guests_added = guest_resp.get('guests', [])
            print_success(f"    Added {len(guests_added)} guest(s)")
        else:
            print_error(f"    Failed to add guests: {response.text}")

    # =========================================================================
    # 9. CREATE SINGLE ORDER FOR ALL BOOKINGS
    # =========================================================================
    print_step("9. Create Order for All Bookings")
    order_data = {
        "booking_ids": booking_ids
    }
    response = do_request("POST", f"{BASE_URL}/api/payment/orders/create/", json=order_data, headers=headers)
    print(f"Status: {response.status_code}")
    
    if response.status_code != 201:
        print_error(f"Order creation failed: {response.text}")
        return
    
    order_resp = response.json()
    if 'orders' in order_resp:
        order = order_resp['orders'][0]
        order_id = order['id']
        order_number = order.get('order_number', 'N/A')
        order_total = order.get('total_amount', 0)
    elif 'order' in order_resp:
        order = order_resp['order']
        order_id = order_resp.get('id', order['id'])
        order_number = order_resp.get('order_number', order.get('order_number', 'N/A'))
        order_total = order_resp.get('total_amount', order.get('total_amount', 0))
    else:
        order = order_resp
        order_id = order_resp.get('id')
        order_number = order_resp.get('order_number', 'N/A')
        order_total = order_resp.get('total_amount', 0)
    
    print_success(f"Order created: {order_number}")
    print_info(f"   Order ID: {order_id}")
    print_info(f"   Total: ₦{order_total}")
    print_info(f"   Bookings: {len(booking_ids)}")

    # =========================================================================
    # 10. INITIATE PAYMENT
    # =========================================================================
    print_step("10. Initiate Payment")
    payment_data = {
        "order_id": str(order_id),
        "payment_method": "paystack"
    }
    response = do_request("POST", f"{BASE_URL}/api/payment/payments/initiate/", json=payment_data, headers=headers)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        payment_info = response.json()
        payment_reference = payment_info.get('reference', 'N/A')
        payment_url = payment_info.get('payment_url')
        
        print_success(f"Payment initiated")
        print_info(f"   Reference: {payment_reference}")
        
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
            # After waiting for manual payment, fetch order detail and notifications
            print_step("10.a Fetch Order Detail & Notifications (post-payment)")
            try:
                # Order detail endpoint
                response = do_request("GET", f"{BASE_URL}/api/payment/orders/{order_id}/", headers=headers)
                print(f"Order detail status: {response.status_code}")
                if response.status_code == 200:
                    od = response.json()
                    order_detail = od.get('order', od)
                    print_info(f"  Order {order_detail.get('order_number', order_detail.get('id'))} - Status: {order_detail.get('status')}")
                else:
                    print_info(f"  Order detail fetch returned: {response.text}")
            except Exception as e:
                print_info(f"  Error fetching order detail: {e}")

            # List orders (paginated) to show recent orders
            resp_orders = do_request("GET", f"{BASE_URL}/api/payment/orders/?page=1&page_size=10", headers=headers)
            print(f"Orders list status: {resp_orders.status_code}")
            if resp_orders.status_code == 200:
                od = resp_orders.json()
                count = od.get('count', len(od.get('results', [])))
                print_info(f"  Orders found: {count}")

            # Re-check notifications after payment
            notif_resp2 = do_request("GET", f"{BASE_URL}/api/notifications/?page=1&page_size=10", headers=headers)
            print(f"Notifications (post-payment) status: {notif_resp2.status_code}")
            if notif_resp2.status_code == 200:
                nd = notif_resp2.json()
                notifs2 = nd.get('notifications', nd.get('results', []))
                print_info(f"  Found {nd.get('count', len(notifs2))} notification(s) after payment")
    else:
        print_error(f"Payment initiation failed: {response.text}")

    # =========================================================================
    # 11. GET QR CODES FOR ALL BOOKINGS
    # =========================================================================
    print_step("11. Get QR Codes for All Bookings")
    
    for booking_id in booking_ids:
        response = do_request("GET", f"{BASE_URL}/api/qr/bookings/{booking_id}/qr-code/", headers=headers)
        
        if response.status_code == 200:
            qr_data = response.json()
            qr_info = qr_data.get('qr_code', qr_data)
            verification_code = qr_info.get('verification_code', 'N/A')
            qr_status = qr_info.get('status', 'N/A')
            
            print_info(f"\n  Booking {booking_id[:8]}...")
            print_success(f"    Verification Code: {verification_code}")
            print_info(f"    Status: {qr_status}")
        else:
            print_error(f"  Failed to get QR for {booking_id[:8]}: {response.text}")

    # =========================================================================
    # 12. VERIFY ALL BOOKINGS AND GUESTS
    # =========================================================================
    print_step("12. Verify All Bookings and Guests")
    
    for booking_id in booking_ids:
        response = do_request("GET", f"{BASE_URL}/api/booking/bookings/{booking_id}/", headers=headers)
        
        if response.status_code == 200:
            booking_data = response.json()
            booking = booking_data.get('booking', booking_data)
            
            print_info(f"\n  Booking {booking_id[:8]}...")
            print_info(f"    Space: {booking.get('space_details', {}).get('name', booking.get('space_name', 'N/A'))}")
            print_info(f"    Status: {booking.get('status', 'N/A')}")
            print_info(f"    Total: ₦{booking.get('total_price', 0)}")
            
            # Get guests for this booking
            guest_response = do_request("GET", f"{BASE_URL}/api/booking/bookings/{booking_id}/guests/list/", headers=headers)
            if guest_response.status_code == 200:
                guests_data = guest_response.json()
                guests = guests_data.get('guests', [])
                print_info(f"    Guests: {len(guests)}")
                for g in guests:
                    qr_sent = g.get('qr_code_sent', False)
                    name = f"{g.get('first_name', '')} {g.get('last_name', '')}"
                    status = "✅" if qr_sent else "⏳"
                    print_info(f"      - {name} {status}")
        else:
            print_error(f"  Failed to get booking {booking_id[:8]}: {response.text}")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print_step("Test Summary")
    print_success(f"Logged in as: {EMAIL}")
    print_success(f"Spaces added to cart: {len(cart_items_info)}")
    print_success(f"Bookings created: {len(booking_ids)}")
    print_success(f"Guests added per booking: 2")
    print_success(f"Order created: {order_number}")
    print_success(f"Total amount: ₦{order_total}")
    
    # Show workspaces involved
    workspace_set = set()
    for info in cart_items_info:
        workspace_set.add(info['space_info']['workspace_name'])
    print_success(f"Workspaces involved: {len(workspace_set)} ({', '.join(workspace_set)})")
    
    print(f"\n🎉 Cart Multi-Space E2E Test Completed!")


if __name__ == "__main__":
    try:
        run_test()
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        import traceback
        traceback.print_exc()
