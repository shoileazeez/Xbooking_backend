from rest_framework import serializers
from user.models import User

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "full_name", "email", "phone", "avatar_url", "date_joined", "last_login"]
        read_only_fields = ["id", "email", "date_joined", "last_login"]
    
    def validate_full_name(self, value):
        """Validate full name"""
        if value and len(value.strip()) < 2:
            raise serializers.ValidationError("Full name must be at least 2 characters")
        return value.strip() if value else value
    def validate_phone(self, value):
        if value and len(value) < 10:
            raise serializers.ValidationError("Phone number must be at least 10 digits")
        return value
