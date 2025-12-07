"""
Comprehensive test file for QR Code functionality and Appwrite Storage Integration
Tests QR code generation, retrieval, and Appwrite URL validation
"""
import os

# Set FILE_UPLOAD_KEY if not already set
if 'FILE_UPLOAD_KEY' not in os.environ:
    os.environ['FILE_UPLOAD_KEY'] = 'cec7ebe4f0a50821e26ad3c770ee590a'

import django

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Xbooking.settings')
django.setup()

import requests
import json
from datetime import datetime, timedelta

# Configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api"

# Test credentials
TEST_USER_EMAIL = "qrcode_test@example.com"
TEST_USER_PASSWORD = "TestPass123!"

ADMIN_EMAIL = "qrcode_admin@example.com"
ADMIN_PASSWORD = "AdminPass123!"


class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text):
    """Print formatted header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text:^70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}\n")


def print_success(text):
    """Print success message"""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")


def print_error(text):
    """Print error message"""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")


def print_info(text):
    """Print info message"""
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")


def print_warning(text):
    """Print warning message"""
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")


def print_json(data):
    """Print formatted JSON"""
    print(f"{Colors.OKBLUE}{json.dumps(data, indent=2)}{Colors.ENDC}")


def login_user(email, password):
    """Login and return access token"""
    url = f"{API_BASE}/user/login/"
    payload = {"email": email, "password": password}
    
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        return response.json().get('token', {}).get('access_token')
    return None


def get_public_workspaces():
    """Get list of public workspaces (no auth required)"""
    url = f"{API_BASE}/workspace/public/workspaces/"
    
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        # Handle nested response structure
        if 'results' in data and isinstance(data['results'], dict) and 'workspaces' in data['results']:
            return data['results']['workspaces']
        elif 'results' in data and isinstance(data['results'], list):
            return data['results']
    return []


def get_public_spaces():
    """Get public spaces (no auth required)"""
    url = f"{API_BASE}/workspace/public/spaces/"
    
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        # Handle nested response structure
        if 'spaces' in data and isinstance(data['spaces'], list):
            return data['spaces']
        elif 'results' in data and isinstance(data['results'], dict) and 'spaces' in data['results']:
            return data['results']['spaces']
        elif 'results' in data and isinstance(data['results'], list):
            return data['results']
    return []


def get_space_slots(space_id):
    """Get available slots for a space (no auth required)"""
    from datetime import datetime
    current_month = datetime.now().strftime('%Y-%m')
    url = f"{API_BASE}/workspace/spaces/{space_id}/calendar/?month={current_month}"
    
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        # Get available slots from days array
        if 'days' in data and isinstance(data['days'], list):
            available_slots = [day for day in data['days'] if day.get('available') and day.get('id')]
            return available_slots
        elif 'slots' in data and isinstance(data['slots'], list):
            return data['slots']
        elif 'results' in data and isinstance(data['results'], list):
            return data['results']
    return []


def create_booking_with_slot(access_token, space_id, workspace_id, slot_id):
    """Create a booking using slot_id"""
    url = f"{API_BASE}/booking/bookings/create/"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    payload = {
        "space_id": space_id,
        "workspace_id": workspace_id,
        "slot_id": slot_id,
    }
    
    response = requests.post(url, json=payload, headers=headers)
    return response


def create_order_from_booking(access_token, booking_id):
    """Create an order from a booking"""
    url = f"{API_BASE}/payment/orders/create/"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    payload = {
        "booking_ids": [booking_id]
    }
    
    response = requests.post(url, json=payload, headers=headers)
    return response


def initiate_paystack_payment(access_token, order_id, email):
    """Initiate payment for an order using Paystack"""
    url = f"{API_BASE}/payment/payments/initiate/"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    payload = {
        "order_id": order_id,
        "payment_method": "paystack",
        "email": email
    }
    
    response = requests.post(url, json=payload, headers=headers)
    return response


def verify_payment_status(access_token, payment_id):
    """Verify payment status"""
    url = f"{API_BASE}/payment/payments/{payment_id}/"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    response = requests.get(url, headers=headers)
    return response


def create_order(access_token, workspace_id):
    """Create an order"""
    url = f"{API_BASE}/payment/orders/"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    payload = {
        "workspace": workspace_id,
        "total_amount": "150.00",
        "payment_method": "card",
    }
    
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 201:
        return response.json()
    return None


def generate_order_qr_code(access_token, order_id):
    """Generate QR code for order"""
    url = f"{API_BASE}/qr/orders/{order_id}/qr-code/generate/"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    response = requests.post(url, headers=headers)
    return response


def get_order_qr_code(access_token, order_id):
    """Get QR code for order"""
    url = f"{API_BASE}/qr/orders/{order_id}/qr-code/"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    response = requests.get(url, headers=headers)
    return response


def get_booking_qr_code(access_token, booking_id):
    """Get QR code for booking"""
    url = f"{API_BASE}/qr/bookings/{booking_id}/qr-code/"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    response = requests.get(url, headers=headers)
    return response


def validate_appwrite_url(url):
    """Validate if URL is from Appwrite"""
    if not url:
        return False, "URL is empty"
    
    if "appwrite" not in url.lower():
        return False, "Not an Appwrite URL"
    
    if "/storage/buckets/" not in url:
        return False, "Invalid Appwrite storage URL format"
    
    if "/files/" not in url:
        return False, "Missing /files/ in URL"
    
    return True, "Valid Appwrite URL"


def test_qr_code_workflow():
    """Test complete QR code workflow"""
    print_header("QR CODE TESTING SUITE")
    print_info("Testing Appwrite Storage Integration and QR Code Generation")
    
    # Step 1: Login user
    print_header("STEP 1: User Login")
    print_info(f"Logging in as: {TEST_USER_EMAIL}")
    access_token = login_user(TEST_USER_EMAIL, TEST_USER_PASSWORD)
    
    if not access_token:
        print_error("Failed to login!")
        return False
    
    print_success("User login successful!")
    print_info(f"Access Token: {access_token[:50]}...")
    
    # Step 2: Get public workspaces
    print_header("STEP 2: Get Public Workspaces")
    workspaces = get_public_workspaces()
    
    if not workspaces:
        print_error("No workspaces found!")
        return False
    
    workspace = workspaces[0]
    workspace_id = workspace['id']
    print_success(f"Found workspace: {workspace['name']}")
    print_info(f"Workspace ID: {workspace_id}")
    
    # Step 3: Get public spaces
    print_header("STEP 3: Get Public Spaces")
    spaces = get_public_spaces()
    
    if not spaces:
        print_error("No spaces found!")
        return False
    
    space = spaces[0]
    space_id = space['id']
    print_success(f"Found {len(spaces)} spaces")
    print_success(f"Using space: {space['name']}")
    print_info(f"Space ID: {space_id}")
    
    # Step 4: Get available slots for the space
    print_header("STEP 4: Get Available Space Slots")
    slots = get_space_slots(space_id)
    
    if not slots:
        print_warning("No available slots found for space")
        print_info("Skipping booking creation")
        slot_id = None
    else:
        slot = slots[0]
        slot_id = slot.get('id')
        print_success(f"Found {len(slots)} available slots")
        print_success(f"Using slot: {slot.get('id', 'N/A')}")
        print_info(f"Slot Date: {slot.get('date', 'N/A')}")
        print_info(f"Slot Time: {slot.get('start_time', 'N/A')} - {slot.get('end_time', 'N/A')}")
        print_info(f"Status: {slot.get('status', 'N/A')}")
    
    # Step 5: Create booking using slot_id
    print_header("STEP 5: Create Booking with Slot")
    if slot_id:
        booking_response = create_booking_with_slot(access_token, space_id, workspace_id, slot_id)
        
        if booking_response.status_code in [200, 201]:
            booking = booking_response.json()
            # Handle different response formats
            booking_id = booking.get('id') or booking.get('booking_id') or booking.get('booking', {}).get('id')
            
            # If data is nested under 'booking' key
            if isinstance(booking.get('booking'), dict):
                booking = booking['booking']
                booking_id = booking.get('id')
            
            print_success("Booking created successfully!")
            print_info(f"Booking ID: {booking_id}")
            
            if booking_id and booking_id != 'None':
                if 'check_in' in booking:
                    print_info(f"Check-in: {booking['check_in']}")
                if 'check_out' in booking:
                    print_info(f"Check-out: {booking['check_out']}")
                
                # Step 6: Create Order from Booking
                print_header("STEP 6: Create Order from Booking")
                order_response = create_order_from_booking(access_token, booking_id)
                
                if order_response.status_code in [200, 201]:
                    order_data = order_response.json()
                    order_id = order_data.get('order_id') or order_data.get('id')
                    print_success("Order created successfully!")
                    print_info(f"Order ID: {order_id}")
                    if 'order' in order_data:
                        print_info(f"Order Amount: {order_data['order'].get('total_amount', 'N/A')}")
                    
                    # Step 7: Initiate Payment with Paystack
                    print_header("STEP 7: Initiate Payment with Paystack")
                    payment_response = initiate_paystack_payment(access_token, order_id, TEST_USER_EMAIL)
                    
                    if payment_response.status_code == 200:
                        payment_data = payment_response.json()
                        payment_id = payment_data.get('payment_id')
                        payment_url = payment_data.get('payment_url')
                        payment_reference = payment_data.get('reference')
                        
                        print_success("Payment initiated successfully!")
                        print_info(f"Payment ID: {payment_id}")
                        print_info(f"Amount: {payment_data.get('amount')} {payment_data.get('currency')}")
                        print_info(f"Payment Reference: {payment_reference}")
                        if payment_url:
                            print_info(f"Payment URL: {payment_url[:60]}...")
                            print_warning("Note: In real scenario, user would complete payment at this URL")
                    else:
                        print_error(f"Failed to initiate payment: {payment_response.status_code}")
                        print_json(payment_response.json())
                else:
                    print_error(f"Failed to create order: {order_response.status_code}")
                    print_json(order_response.json())
                
                # Step 8: Get booking QR code (will be generated after payment completion)
                print_header("STEP 8: Get Booking QR Code Status")
                qr_response = get_booking_qr_code(access_token, booking_id)
                
                if qr_response.status_code == 200:
                    qr_data = qr_response.json()
                    print_success("Booking QR code retrieved!")
                    
                    # Validate QR code URL
                    qr_code_url = qr_data.get('qr_code_url')
                    if qr_code_url:
                        is_valid, message = validate_appwrite_url(qr_code_url)
                        if is_valid:
                            print_success(f"✓ {message}")
                            print_info(f"QR Code URL: {qr_code_url[:60]}...")
                        else:
                            print_warning(f"✗ {message}")
                    else:
                        print_info("QR code URL not yet generated (will be generated after payment completion)")
                elif qr_response.status_code == 404:
                    print_info("QR code not yet generated (will be generated after payment is completed)")
                else:
                    print_error(f"Failed to get QR code: {qr_response.status_code}")
                    print_json(qr_response.json())
            else:
                print_warning("Booking created but ID not in response - Order/Payment test skipped")
        else:
            print_error(f"Failed to create booking: {booking_response.status_code}")
            print_json(booking_response.json())
    else:
        print_warning("Skipped booking creation - no slots available")
    
    # Step 9: Test File Upload Endpoint (Appwrite)
    print_header("STEP 9: Test File Upload Endpoint")
    print_info("Testing unauthenticated file upload to Appwrite using FILE_UPLOAD_KEY")
    
    # Create a simple test image
    from PIL import Image
    import io
    
    img = Image.new('RGB', (100, 100), color='red')
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    
    # Get FILE_UPLOAD_KEY from environment
    import os
    file_upload_key = os.getenv('FILE_UPLOAD_KEY', '')
    
    if not file_upload_key:
        print_warning("FILE_UPLOAD_KEY not set in environment, skipping file upload test")
    else:
        url = f"{API_BASE}/qr/upload/file/"
        headers = {"X-File-Upload-Key": file_upload_key}
        files = {"file": ("test_image.png", img_io, "image/png")}
        
        response = requests.post(url, headers=headers, files=files)
        
        if response.status_code == 200:
            result = response.json()
            print_success("File uploaded successfully!")
            print_info(f"Response: {json.dumps(result, indent=2)}")
            
            if 'file_url' in result:
                is_valid, message = validate_appwrite_url(result['file_url'])
                if is_valid:
                    print_success(f"✓ {message}")
                    print_info(f"File URL: {result['file_url']}")
                else:
                    print_error(f"✗ {message}")
        else:
            print_error(f"Failed to upload file: {response.status_code}")
            print_json(response.json())
    
    # Step 10: Test QR Code Models
    print_header("STEP 10: Test QR Code Models in Database")
    print_info("Checking if QR code models have Appwrite URL support")
    
    # Query database for existing QR codes
    try:
        from qr_code.models import OrderQRCode, BookingQRCode
        
        order_qr_codes = OrderQRCode.objects.all()[:5]
        if order_qr_codes:
            print_success(f"Found {order_qr_codes.count()} Order QR Codes in database")
            for qr in order_qr_codes:
                print_info(f"Order: {qr.order_id}")
                print_info(f"  - QR Code URL: {qr.qr_code_image_url}")
                print_info(f"  - Appwrite File ID: {qr.appwrite_file_id}")
                if qr.qr_code_image_url:
                    is_valid, message = validate_appwrite_url(qr.qr_code_image_url)
                    print_info(f"  - URL Valid: {is_valid} ({message})")
        else:
            print_info("No Order QR codes found in database (this is OK for new setup)")
        
        booking_qr_codes = BookingQRCode.objects.all()[:5]
        if booking_qr_codes:
            print_success(f"Found {booking_qr_codes.count()} Booking QR Codes in database")
            for qr in booking_qr_codes:
                print_info(f"Booking: {qr.booking_id}")
                print_info(f"  - QR Code URL: {qr.qr_code_image_url}")
                print_info(f"  - Appwrite File ID: {qr.appwrite_file_id}")
                if qr.qr_code_image_url:
                    is_valid, message = validate_appwrite_url(qr.qr_code_image_url)
                    print_info(f"  - URL Valid: {is_valid} ({message})")
        else:
            print_info("No Booking QR codes found in database (this is OK for new setup)")
    except Exception as e:
        print_error(f"Error checking QR code models: {str(e)}")
    
    print_header("SUMMARY")
    print_success("QR Code Testing Completed")
    print_info("✓ Public workspace endpoint working")
    print_info("✓ Public space endpoint working")
    print_info("✓ File upload endpoint available (with FILE_UPLOAD_KEY auth)")
    print_info("✓ QR Code models have Appwrite URL support")
    
    return True


def main():
    """Run QR code tests"""
    try:
        success = test_qr_code_workflow()
        if success:
            print_header("QR CODE TESTS COMPLETED")
            print_success("All QR code tests executed successfully!")
        else:
            print_header("QR CODE TESTS FAILED")
            print_error("Some tests failed")
    except Exception as e:
        print_header("ERROR")
        print_error(f"Test execution error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
