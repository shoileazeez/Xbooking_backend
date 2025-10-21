#!/usr/bin/env python
"""
Direct test of UUID JWT authentication logic
Tests the authentication directly without using test client
"""
import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Xbooking.settings')
django.setup()

from user.models import User
from user.authentication import UUIDJWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory
import uuid

print("=" * 80)
print("XBOOKING UUID JWT AUTHENTICATION - DIRECT TEST")
print("=" * 80)

# Get a real user from database
user = User.objects.first()
if not user:
    print("[ERROR] No users found in database!")
    sys.exit(1)

print(f"\n[OK] Using user: {user.email}")
print(f"     User ID: {user.id}")
print(f"     ID Type: {type(user.id).__name__}")

# Generate a real token
print("\n[1] Generating JWT token...")
refresh = RefreshToken.for_user(user)
access_token = str(refresh.access_token)
print(f"[OK] Token generated")

# Decode and inspect token
import jwt as pyjwt
decoded = pyjwt.decode(access_token, options={'verify_signature': False})
print(f"     Token user_id claim: {decoded['user_id']}")
print(f"     Token user_id type: {type(decoded['user_id']).__name__}")

# Test the authentication directly
print("\n[2] Testing authentication logic directly...")
print("    Creating mock request with Bearer token...")

# Create a mock request
factory = APIRequestFactory()
request = factory.get('/api/user/profile/', HTTP_AUTHORIZATION=f'Bearer {access_token}')

# Create authenticator
auth = UUIDJWTAuthentication()

try:
    print("    Calling authenticate()...")
    result = auth.authenticate(request)
    
    if result:
        authenticated_user, validated_token = result
        print(f"[OK] AUTHENTICATION SUCCESSFUL!")
        print(f"     Authenticated user: {authenticated_user.email}")
        print(f"     User ID: {authenticated_user.id}")
        print(f"     Is active: {authenticated_user.is_active}")
    else:
        print(f"[ERROR] Authentication returned None")
        
except Exception as e:
    print(f"[ERROR] Authentication failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("TEST COMPLETED")
print("=" * 80)
