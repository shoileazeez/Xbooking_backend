from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import requests
from django.utils import timezone
from user.serializers import GoogleAuthSerializer
from user.models import User
from user.utils import get_google_tokens, get_google_user_info
from user.utils import get_tokens_for_user
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema

CLIENT_ID = "YOUR_GOOGLE_CLIENT_ID"
CLIENT_SECRET = "YOUR_GOOGLE_CLIENT_SECRET"
REDIRECT_URI = "http://localhost:8000/api/auth/google/callback"

class GoogleAuthView(APIView):
    permission_classes = [AllowAny]
    serializer_class = GoogleAuthSerializer
    
    @extend_schema(
        request=GoogleAuthSerializer,
        description="Google OAuth authentication - returns JWT tokens"
    )
    def post(self, request):
        serializer = GoogleAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        code = serializer.validated_data["code"]

        try:
            tokens = get_google_tokens(code, CLIENT_ID, CLIENT_SECRET, REDIRECT_URI)
            access_token = tokens.get("access_token")
            google_user = get_google_user_info(access_token)

            email = google_user.get("email")
            full_name = google_user.get("name")
            avatar_url = google_user.get("picture")
            google_id = google_user.get("id")

            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "full_name": full_name,
                    "avatar_url": avatar_url,
                    "google_id": google_id,
                },
            )

            if not created:
                user.full_name = full_name
                user.avatar_url = avatar_url
                user.google_id = google_id
                user.last_login = timezone.now()
                user.save()

            jwt_tokens = get_tokens_for_user(user)

            return Response({
                "success": True,
                "message": "Login successful",
                "user": {
                    "user_id": str(user.id),
                    "user_email": user.email,
                    "full_name": user.full_name,
                    "avatar_url": user.avatar_url,
                },
                "token": jwt_tokens
            }, status=status.HTTP_200_OK)

        except requests.HTTPError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
