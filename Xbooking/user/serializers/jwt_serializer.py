"""
Custom JWT Serializers to handle UUID user IDs
"""
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
import uuid


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom serializer to properly handle UUID user IDs in JWT tokens
    """
    @classmethod
    def get_token(cls, user):
        """
        Override to ensure UUID is properly serialized
        """
        token = super().get_token(user)
        
        # Ensure user_id is a string representation of UUID
        if isinstance(user.id, uuid.UUID):
            token['user_id'] = str(user.id)
        else:
            token['user_id'] = user.id
            
        # Add additional user info if needed
        token['email'] = user.email
        
        return token


class CustomTokenRefreshSerializer:
    """
    Helper to ensure refresh tokens also handle UUIDs properly
    """
    @staticmethod
    def get_token(user):
        """Generate token with proper UUID handling"""
        token = RefreshToken.for_user(user)
        
        # Ensure user_id is properly formatted
        if isinstance(user.id, uuid.UUID):
            token['user_id'] = str(user.id)
        else:
            token['user_id'] = user.id
            
        return token
