from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from rest_framework import serializers


class RefreshTokenSerializer(serializers.Serializer):
    """Serializer for refresh token request"""
    refresh_token = serializers.CharField(
        required=True,
        help_text="The refresh token obtained during login"
    )


class RefreshTokenView(APIView):
    """
    Refresh access token using refresh token.
    
    This endpoint allows clients to obtain a new access token using a valid refresh token.
    The refresh token is obtained during login and should be stored securely by the client.
    """
    permission_classes = [AllowAny]
    serializer_class = RefreshTokenSerializer
    
    @extend_schema(
        request=RefreshTokenSerializer,
        description="Refresh access token using a valid refresh token",
        examples=[
            OpenApiExample(
                'Valid refresh token request',
                value={
                    'refresh_token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...'
                },
                request_only=True
            )
        ],
        responses={
            200: {
                'description': 'New tokens generated successfully',
                'example': {
                    'success': True,
                    'message': 'Token refreshed successfully',
                    'token': {
                        'access_token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                        'refresh_token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...'
                    }
                }
            },
            400: {
                'description': 'Invalid or expired refresh token',
                'example': {
                    'success': False,
                    'message': 'Token refresh failed',
                    'errors': {
                        'refresh_token': ['Token is invalid or expired']
                    }
                }
            }
        }
    )
    def post(self, request):
        """
        Refresh the access token.
        
        Args:
            request: HTTP request containing refresh_token in body
            
        Returns:
            Response with new access_token and refresh_token
        """
        serializer = RefreshTokenSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                "success": False,
                "message": "Invalid request",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        refresh_token = serializer.validated_data['refresh_token']
        
        try:
            # Validate and decode the refresh token
            refresh = RefreshToken(refresh_token)
            
            # Generate new access token
            new_access_token = str(refresh.access_token)
            
            # Get the new refresh token (rotation is handled by SIMPLE_JWT settings)
            new_refresh_token = str(refresh)
            
            return Response({
                "success": True,
                "message": "Token refreshed successfully",
                "token": {
                    "access_token": new_access_token,
                    "refresh_token": new_refresh_token
                }
            }, status=status.HTTP_200_OK)
            
        except TokenError as e:
            return Response({
                "success": False,
                "message": "Token refresh failed",
                "errors": {
                    "refresh_token": [str(e)]
                }
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except InvalidToken as e:
            return Response({
                "success": False,
                "message": "Token refresh failed",
                "errors": {
                    "refresh_token": ["Token is invalid or expired"]
                }
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response({
                "success": False,
                "message": "Token refresh failed",
                "errors": {
                    "detail": [str(e)]
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
