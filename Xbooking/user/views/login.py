from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from user.serializers import LoginSerializers
from rest_framework.permissions import AllowAny
from user.models import User
import datetime
from user.utils import get_tokens_for_user
from drf_spectacular.utils import extend_schema

class UserLoginView(APIView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializers
    
    @extend_schema(
        request=LoginSerializers,
        description="User login - returns JWT access and refresh tokens"
    )
    def post(self, request):
        serializer = LoginSerializers(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            user.last_login = datetime.datetime.now()
            user.save()
            jwt_tokens = get_tokens_for_user(user)
            return Response({
                "success": True,
                "message":"Login was succesful",
                "user":{
                    "user_id": user.id,
                    "user_email": user.email,
                    "full_name": user.full_name,
                    "avatar_url": user.avatar_url
                },
                "token": jwt_tokens
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "success":False,
                "message": "Login failed",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
