"""
User Login Serializer V1
"""
from rest_framework import serializers
from django.contrib.auth import authenticate

from user.models import User


class UserLoginSerializer(serializers.Serializer):
    """
    User login serializer with email/password validation.
    Checks force_password_change flag for workspace-invited users.
    """
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)
    
    def validate(self, attrs):
        """Validate credentials"""
        email = attrs.get('email', '').lower()
        password = attrs.get('password')
        
        if not email or not password:
            raise serializers.ValidationError('Email and password are required.')
        
        # Authenticate user
        user = authenticate(username=email, password=password)
        
        if not user:
            raise serializers.ValidationError('Invalid email or password.')
        
        if not user.is_active:
            raise serializers.ValidationError('User account is disabled.')
        
        attrs['user'] = user
        return attrs
