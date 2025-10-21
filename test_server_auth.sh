#!/bin/bash
# Test script to verify UUID JWT authentication against running server

echo "================================================================================"
echo "XBOOKING JWT AUTHENTICATION TEST - AGAINST RUNNING SERVER"
echo "================================================================================"

# Make sure server is running
echo ""
echo "[1] Checking if server is running on localhost:8000..."
if ! curl -s http://localhost:8000/api/schema/ > /dev/null 2>&1; then
    echo "[ERROR] Server is not running on localhost:8000"
    echo "Start the server with: python manage.py runserver"
    exit 1
fi
echo "[OK] Server is running"

# Get a token
echo ""
echo "[2] Getting JWT token for user..."

# Use Python to generate a token
TOKEN=$(cd /c/Users/Admin/Xbooking_backend/Xbooking && python manage.py shell -c "
from user.models import User
from rest_framework_simplejwt.tokens import RefreshToken

user = User.objects.first()
refresh = RefreshToken.for_user(user)
access_token = str(refresh.access_token)
print(access_token)
" 2>/dev/null | tail -1)

if [ -z "$TOKEN" ]; then
    echo "[ERROR] Failed to generate token"
    exit 1
fi

echo "[OK] Token generated"
echo "     User: $(cd /c/Users/Admin/Xbooking_backend/Xbooking && python manage.py shell -c "from user.models import User; print(User.objects.first().email)" 2>/dev/null | tail -1)"
echo "     Token (first 50 chars): ${TOKEN:0:50}..."

# Test the profile endpoint
echo ""
echo "[3] Testing /api/user/profile/ endpoint..."
echo "    Command: curl -H 'Authorization: Bearer <TOKEN>' http://localhost:8000/api/user/profile/"

RESPONSE=$(curl -s -X GET http://localhost:8000/api/user/profile/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json")

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X GET http://localhost:8000/api/user/profile/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json")

echo ""
if [ "$HTTP_CODE" = "200" ]; then
    echo "[OK] SUCCESS! Status: $HTTP_CODE"
    echo ""
    echo "Response:"
    echo "$RESPONSE" | python -m json.tool 2>/dev/null || echo "$RESPONSE"
else
    echo "[ERROR] FAILED! Status: $HTTP_CODE"
    echo ""
    echo "Response:"
    echo "$RESPONSE" | python -m json.tool 2>/dev/null || echo "$RESPONSE"
fi

echo ""
echo "================================================================================"
echo "TEST COMPLETED"
echo "================================================================================"
