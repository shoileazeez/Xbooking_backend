from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from user.serializers import LoginSerializers
from rest_framework.permissions import AllowAny
from user.models import User
import datetime

class UserLoginView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = LoginSerializers(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            user.last_login = datetime.datetime.now()
            user.save()
            refresh_token = RefreshToken.for_user(user)
            return Response({
                "success": True,
                "message":"Login was succesful",
                "user":{
                    "user_id": user.id,
                    "user_email": user.email,
                    "full_name": user.full_name,
                    "avatar_url": user.avatar_url
                },
                "token":{
                    "access_token": str(refresh_token.access_token),
                    "refresh_token": str(refresh_token)
                }
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "success":False,
                "message": "Login failed",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
