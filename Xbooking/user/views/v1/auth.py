"""
User Authentication Views V1
"""
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.utils import timezone

from core.responses import SuccessResponse, ErrorResponse
from core.throttling import AnonSustainedThrottle, UserSustainedThrottle
from user.serializers.v1 import UserRegistrationSerializer, UserLoginSerializer
from user.models import User


class UserRegistrationView(APIView):
    """
    User registration endpoint.
    - Normal users can register with any email
    - Workspace admins must use business email
    """
    permission_classes = [AllowAny]
    throttle_classes = [AnonSustainedThrottle]
    
    @extend_schema(
        request=UserRegistrationSerializer,
        responses={
            201: OpenApiResponse(description='User registered successfully'),
            400: OpenApiResponse(description='Validation error'),
        },
        description='Register a new user account',
        tags=['Authentication']
    )
    def post(self, request):
        """Register a new user"""
        serializer = UserRegistrationSerializer(data=request.data)
        
        if not serializer.is_valid():
            return ErrorResponse(
                message='Registration failed',
                errors=serializer.errors,
                status_code=400
            )
        
        user = serializer.save()
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        return SuccessResponse(
            message='Registration successful',
            data={
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'full_name': user.full_name,
                    'role': user.role,
                    'avatar_url': user.avatar_url,
                    'onboarding_completed': user.onboarding_completed,
                },
                'tokens': {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                }
            },
            status_code=201
        )


class UserLoginView(APIView):
    """
    User login endpoint with JWT token generation.
    Checks for force_password_change flag.
    """
    permission_classes = [AllowAny]
    throttle_classes = [AnonSustainedThrottle]
    
    @extend_schema(
        request=UserLoginSerializer,
        responses={
            200: OpenApiResponse(description='Login successful'),
            400: OpenApiResponse(description='Invalid credentials'),
        },
        description='User login - returns JWT access and refresh tokens',
        tags=['Authentication']
    )
    def post(self, request):
        """Authenticate user and return JWT tokens"""
        serializer = UserLoginSerializer(data=request.data)
        
        if not serializer.is_valid():
            return ErrorResponse(
                message='Login failed',
                errors=serializer.errors,
                status_code=400
            )
        
        user = serializer.validated_data['user']
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        response_data = {
            'user': {
                'id': str(user.id),
                'email': user.email,
                'full_name': user.full_name,
                'role': user.role,
                'avatar_url': user.avatar_url,
                'onboarding_completed': user.onboarding_completed,
                'force_password_change': user.force_password_change,
            },
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }
        }
        
        # Alert if password change required
        if user.force_password_change:
            response_data['warning'] = 'Password change required before accessing other features'
        
        return SuccessResponse(
            message='Login successful',
            data=response_data,
            status_code=200
        )


class RefreshTokenView(TokenRefreshView):
    """
    JWT token refresh endpoint.
    Uses SimpleJWT's built-in refresh view.
    """
    throttle_classes = [UserSustainedThrottle]
    
    @extend_schema(
        description='Refresh JWT access token using refresh token',
        tags=['Authentication']
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
