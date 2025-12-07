"""
Comprehensive test file for User Authentication, Profile, and Password Change
Tests user registration, login, profile update, and password change endpoints
"""
import requests
import json
import random
import string

# Configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api"

# Generate random email to avoid conflicts
random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))

# Test data
TEST_USER = {
    "full_name": "Test User",
    "email": f"testuser{random_suffix}@example.com",
    "password": "TestPass123!",
    "confirm_password": "TestPass123!"
}

TEST_USER_2 = {
    "full_name": "Jane Doe",
    "email": f"janedoe{random_suffix}@example.com",
    "password": "SecurePass456!",
    "confirm_password": "SecurePass456!"
}


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
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text:^60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")


def print_success(text):
    """Print success message"""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")


def print_error(text):
    """Print error message"""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")


def print_info(text):
    """Print info message"""
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")


def print_json(data):
    """Print formatted JSON"""
    print(f"{Colors.OKBLUE}{json.dumps(data, indent=2)}{Colors.ENDC}")


def test_user_registration():
    """Test user registration"""
    print_header("TEST 1: User Registration")
    
    url = f"{API_BASE}/user/register/"
    print_info(f"POST {url}")
    print_info(f"Payload: {json.dumps(TEST_USER, indent=2)}")
    
    response = requests.post(url, json=TEST_USER)
    
    print_info(f"Status Code: {response.status_code}")
    print_json(response.json())
    
    if response.status_code == 201:
        print_success("User registration successful!")
        return response.json()
    else:
        print_error("User registration failed!")
        return None


def test_user_login(email, password):
    """Test user login"""
    print_header("TEST 2: User Login")
    
    url = f"{API_BASE}/user/login/"
    payload = {
        "email": email,
        "password": password
    }
    
    print_info(f"POST {url}")
    print_info(f"Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.post(url, json=payload)
    
    print_info(f"Status Code: {response.status_code}")
    print_json(response.json())
    
    if response.status_code == 200:
        data = response.json()
        access_token = data.get('token', {}).get('access_token')
        print_success("Login successful!")
        if access_token:
            print_success(f"Access Token: {access_token[:50]}...")
        return access_token
    else:
        print_error("Login failed!")
        return None


def test_get_profile(access_token):
    """Test getting user profile"""
    print_header("TEST 3: Get User Profile")
    
    url = f"{API_BASE}/user/profile/"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    print_info(f"GET {url}")
    print_info(f"Headers: Authorization: Bearer {access_token[:30]}...")
    
    response = requests.get(url, headers=headers)
    
    print_info(f"Status Code: {response.status_code}")
    print_json(response.json())
    
    if response.status_code == 200:
        print_success("Profile retrieved successfully!")
        return response.json()
    else:
        print_error("Failed to retrieve profile!")
        return None


def test_update_profile(access_token):
    """Test updating user profile"""
    print_header("TEST 4: Update User Profile (PATCH)")
    
    url = f"{API_BASE}/user/profile/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "full_name": "Updated Test User",
        "phone": "+1234567890",
        "avatar_url": "https://example.com/avatar.jpg"
    }
    
    print_info(f"PATCH {url}")
    print_info(f"Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.patch(url, json=payload, headers=headers)
    
    print_info(f"Status Code: {response.status_code}")
    print_json(response.json())
    
    if response.status_code == 200:
        print_success("Profile updated successfully!")
        return response.json()
    else:
        print_error("Failed to update profile!")
        return None


def test_update_profile_with_email(access_token):
    """Test updating profile with email (should fail)"""
    print_header("TEST 5: Try to Update Email (Should Fail)")
    
    url = f"{API_BASE}/user/profile/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "email": "newemail@example.com"
    }
    
    print_info(f"PATCH {url}")
    print_info(f"Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.patch(url, json=payload, headers=headers)
    
    print_info(f"Status Code: {response.status_code}")
    print_json(response.json())
    
    if response.status_code == 400:
        print_success("Email update correctly blocked!")
        return True
    else:
        print_error("Email update should have been blocked!")
        return False


def test_change_password_wrong_current(access_token):
    """Test password change with wrong current password"""
    print_header("TEST 6: Change Password (Wrong Current Password)")
    
    url = f"{API_BASE}/users/change-password/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "current_password": "WrongPassword123",
        "new_password": "NewSecurePass456"
    }
    
    print_info(f"POST {url}")
    print_info(f"Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.post(url, json=payload, headers=headers)
    
    print_info(f"Status Code: {response.status_code}")
    print_json(response.json())
    
    if response.status_code == 401:
        print_success("Wrong password correctly rejected!")
        return True
    else:
        print_error("Wrong password should have been rejected!")
        return False


def test_change_password_weak(access_token, current_password):
    """Test password change with weak new password"""
    print_header("TEST 7: Change Password (Weak Password)")
    
    url = f"{API_BASE}/users/change-password/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "current_password": current_password,
        "new_password": "weak"
    }
    
    print_info(f"POST {url}")
    print_info(f"Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.post(url, json=payload, headers=headers)
    
    print_info(f"Status Code: {response.status_code}")
    print_json(response.json())
    
    if response.status_code == 400:
        print_success("Weak password correctly rejected!")
        return True
    else:
        print_error("Weak password should have been rejected!")
        return False


def test_change_password_success(access_token, current_password, new_password):
    """Test successful password change"""
    print_header("TEST 8: Change Password (Success)")
    
    url = f"{API_BASE}/users/change-password/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "current_password": current_password,
        "new_password": new_password
    }
    
    print_info(f"POST {url}")
    print_info(f"Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.post(url, json=payload, headers=headers)
    
    print_info(f"Status Code: {response.status_code}")
    print_json(response.json())
    
    if response.status_code == 200:
        print_success("Password changed successfully!")
        return True
    else:
        print_error("Password change failed!")
        return False


def test_login_with_new_password(email, new_password):
    """Test login with new password"""
    print_header("TEST 9: Login with New Password")
    
    url = f"{API_BASE}/user/login/"
    payload = {
        "email": email,
        "password": new_password
    }
    
    print_info(f"POST {url}")
    print_info(f"Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.post(url, json=payload)
    
    print_info(f"Status Code: {response.status_code}")
    print_json(response.json())
    
    if response.status_code == 200:
        print_success("Login with new password successful!")
        return response.json().get('token', {}).get('access_token')
    else:
        print_error("Login with new password failed!")
        return None


def test_password_change_required(access_token):
    """Test checking if password change is required"""
    print_header("TEST 10: Check Password Change Required")
    
    url = f"{API_BASE}/users/password-change-required/"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    print_info(f"GET {url}")
    
    response = requests.get(url, headers=headers)
    
    print_info(f"Status Code: {response.status_code}")
    print_json(response.json())
    
    if response.status_code == 200:
        print_success("Password change status retrieved!")
        return response.json()
    else:
        print_error("Failed to get password change status!")
        return None


def main():
    """Run all tests"""
    print(f"\n{Colors.BOLD}{Colors.HEADER}")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║   User Profile & Password Change Test Suite               ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"{Colors.ENDC}")
    
    # Test 1: Register user
    registration_result = test_user_registration()
    if not registration_result:
        print_error("Cannot proceed without successful registration")
        return
    
    # Test 2: Login
    access_token = test_user_login(TEST_USER['email'], TEST_USER['password'])
    if not access_token:
        print_error("Cannot proceed without successful login")
        return
    
    # Test 3: Get profile
    test_get_profile(access_token)
    
    # Test 4: Update profile
    test_update_profile(access_token)
    
    # Test 5: Try to update email (should fail)
    test_update_profile_with_email(access_token)
    
    # Test 6: Change password with wrong current password
    test_change_password_wrong_current(access_token)
    
    # Test 7: Change password with weak password
    test_change_password_weak(access_token, TEST_USER['password'])
    
    # Test 8: Change password successfully
    new_password = "NewSecurePass789"
    password_changed = test_change_password_success(
        access_token,
        TEST_USER['password'],
        new_password
    )
    
    if password_changed:
        # Test 9: Login with new password
        new_access_token = test_login_with_new_password(TEST_USER['email'], new_password)
        
        if new_access_token:
            # Test 10: Check password change required status
            test_password_change_required(new_access_token)
    
    print_header("TEST SUITE COMPLETED")
    print_success("All tests executed! Check results above.")


if __name__ == "__main__":
    main()
