from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
import requests
from django.conf import settings
PAYSTACK_BANKS_URL = "https://api.paystack.co/bank?country=nigeria"
PAYSTACK_RESOLVE_URL = "https://api.paystack.co/bank/resolve"
PAYSTACK_SECRET_KEY = settings.PAYSTACK_SECRET_KEY  # Ensure this is set in your Django settings

class BankListAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
        response = requests.get(PAYSTACK_BANKS_URL, headers=headers)
        if response.status_code == 200:
            banks = response.json().get("data", [])
            return Response([
                {"name": bank["name"], "code": bank["code"]}
                for bank in banks
            ])
        return Response({"error": "Failed to fetch banks"}, status=status.HTTP_502_BAD_GATEWAY)

class BankResolveAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        account_number = request.data.get("account_number")
        bank_code = request.data.get("bank_code")
        if not account_number or not bank_code:
            return Response({"error": "Missing account_number or bank_code"}, status=status.HTTP_400_BAD_REQUEST)
        headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
        params = {"account_number": account_number, "bank_code": bank_code}
        response = requests.get(PAYSTACK_RESOLVE_URL, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json().get("data", {})
            return Response({"account_name": data.get("account_name", "")})
        return Response({"error": "Failed to resolve account"}, status=status.HTTP_502_BAD_GATEWAY)
