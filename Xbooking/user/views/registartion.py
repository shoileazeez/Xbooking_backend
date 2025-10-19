from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from user.utils import get_tokens_for_user
from user.serializers import UserSerializers
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema


class UserRegistrationView(APIView):
    """ 
    User registration endpoint
    """
    permission_classes = [AllowAny]
    serializer_class = UserSerializers
    
    @extend_schema(
        request=UserSerializers,
        responses={201: UserSerializers},
        description="Register a new user account"
    )
    def post(self, request):
        serializer = UserSerializers(data = request.data)
        try:
            if serializer.is_valid():
                user = serializer.save()
                jwt_tokens = get_tokens_for_user(user)
                return Response({
                    "success": True,
                    "message": "Registration was succesful",
                    "user":{
                        "user_id": user.id,
                        "user_email": user.email,
                        "full_name": user.full_name,
                        "avatar_url": user.avatar_url
                    },
                    "token":jwt_tokens
                    }, status = status.HTTP_201_CREATED
                )
            else:
                return Response({
                    "success": False,
                    "message": "Registration Failed",
                    "error": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            return Response({
                "success": False,
                "message": "An unexpected error occurred",
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
