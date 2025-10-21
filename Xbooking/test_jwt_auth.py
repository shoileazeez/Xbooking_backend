#!/usr/bin/env python
"""
Test script to verify the UUID JWT authentication fix
"""
import os
import django
import sys
import logging

# Fix Windows encoding
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# Enable debug logging
logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Xbooking.settings')

# Add testserver to ALLOWED_HOSTS for testing
from django.conf import settings
if 'testserver' not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + ['testserver']

django.setup()

from user.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.test import APIClient
import json

print("=" * 80)
print("XBOOKING JWT AUTHENTICATION TEST")
print("=" * 80)

# Get a user
user = User.objects.first()
if not user:
    print("[ERROR] No users found in database!")
    sys.exit(1)

print(f"\n[OK] Using user: {user.email}")
print(f"     User ID: {user.id}")
print(f"     ID Type: {type(user.id).__name__}")

# Generate token
print("\n[1] Generating JWT token...")
refresh = RefreshToken.for_user(user)
access_token = str(refresh.access_token)

print(f"[OK] Token generated")
print(f"     Access Token (first 50 chars): {access_token[:50]}...")

# Test the profile endpoint
print("\n[2] Testing /api/user/profile/ endpoint...")
client = APIClient()
client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

try:
    response = client.get('/api/user/profile/')
    
    if response.status_code == 200:
        print(f"[OK] SUCCESS! Status: {response.status_code}")
        data = response.json()
        print(f"\nProfile Data:")
        print(json.dumps(data, indent=2))
    else:
        print(f"[ERROR] FAILED! Status: {response.status_code}")
        try:
            print(f"Response: {response.json()}")
        except:
            print(f"Response: {response.content[:500]}")
        
except Exception as e:
    print(f"[ERROR] Exception: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("TEST COMPLETED")
print("=" * 80)
