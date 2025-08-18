from user.models import User
from rest_framework import serializers
from rest_framework.serializers import ValidationError
from user.validators import password_validation
import urllib.parse

class UserSerializers(serializers.ModelSerializer):
    """
    User serializer with validation logic for registration
    """
    confirm_password = serializers.CharField(write_only=True)
    class Meta():
        model = User
        fields = ["id", "full_name", "email", "password", "confirm_password", "is_active", "avatar_url"]
        extra_kwargs = {
            "id": {"read_only": True},
            "is_active": {"read_only": True},
            "password": {"write_only": True},
            "avatar_url": {"read_only": True},
        }
    # Email validation
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise ValidationError("Email already exists")
        return value
    
    # Avatar url generation
    def generate_avatar_url(self, email):
        """
        Generate avatar URL using DiceBear API
        """
        try:
            if not email:
                return self.get_default_avatar_url()
            
            style = "personas"
            seed = urllib.parse.quote(email.lower())
            
            url = f"https://api.dicebear.com/9.x/{style}/svg?seed={seed}&size=200&radius=20"
            return url
            
        except Exception:
            return self.get_default_avatar_url()

    # Fallback for avatar url
    def get_default_avatar_url(self):
        """Fallback avatar URL"""
        return "https://api.dicebear.com/9.x/initials/svg?seed=User&backgroundColor=6366f1&color=white"
    
    def to_representation(self, instance):
        """Add avatar_url to the response data"""
        data = super().to_representation(instance)
        data['avatar_url'] = instance.avatar_url if instance.avatar_url else self.generate_avatar_url(instance.email)
        return data

    # password validation
    
    def validate(self, attrs):
        password = attrs.get("password")
        confirm_password = attrs.get("confirm_password")
        
        password_validation(password, confirm_password)
        return attrs
    
    def create(self, validated_data):
        validated_data.pop("confirm_password")
        email = validated_data['email']
        avatar_url = self.generate_avatar_url(email)
        
        # Create user instance
        user = User.objects.create(
            email=validated_data["email"],
            full_name=validated_data["full_name"],
            is_active=True,
        )
        # Set password using the model's set_password method
        user.set_password(validated_data["password"])
        user.avatar_url = avatar_url
        user.save()
        return user