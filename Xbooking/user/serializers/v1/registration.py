"""
User Registration Serializer V1
"""
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
import urllib.parse

from user.models import User, UserRole
from user.validators.business_email import is_business_email, get_email_domain, validate_business_email


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    User registration serializer.
    - Normal users can register with any email
    - Workspace admins must use business email
    """
    password = serializers.CharField(write_only=True, required=True)
    confirm_password = serializers.CharField(write_only=True, required=True)
    role = serializers.ChoiceField(
        choices=UserRole.choices,
        default=UserRole.USER,
        required=False
    )
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'full_name', 'password', 'confirm_password',
            'phone', 'role', 'avatar_url', 'created_at'
        ]
        read_only_fields = ['id', 'avatar_url', 'created_at']
    
    def validate_email(self, value):
        """Validate email uniqueness"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()
    
    def validate(self, attrs):
        """Validate passwords and business email for workspace admins"""
        password = attrs.get('password')
        confirm_password = attrs.pop('confirm_password', None)
        role = attrs.get('role', UserRole.USER)
        email = attrs.get('email')
        
        # Validate password match
        if password != confirm_password:
            raise serializers.ValidationError({
                'confirm_password': 'Passwords do not match.'
            })
        
        # Validate password strength
        try:
            validate_password(password)
        except DjangoValidationError as e:
            raise serializers.ValidationError({
                'password': list(e.messages)
            })
        
        # Validate business email for workspace admins
        if role == UserRole.WORKSPACE_ADMIN:
            try:
                is_business, domain = validate_business_email(email)
                attrs['is_business_email'] = True
                attrs['business_domain'] = domain
            except DjangoValidationError as e:
                raise serializers.ValidationError({
                    'email': str(e)
                })
        else:
            # For regular users, just check if business email (informational)
            attrs['is_business_email'] = is_business_email(email)
            attrs['business_domain'] = get_email_domain(email) if attrs['is_business_email'] else None
        
        return attrs
    
    def create(self, validated_data):
        """Create user with service layer"""
        from user.services.user_service import UserService
        # from user.models import UserPreference
        
        password = validated_data.pop('password')
        email = validated_data['email']
        
        # Generate avatar URL
        avatar_url = self._generate_avatar_url(email)
        validated_data['avatar_url'] = avatar_url
        
        # Create user
        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        
        # Create default preferences for user (lazy - created on first GET)
        # UserPreference.objects.create(user=user)
        
        # Publish event via service
        UserService.create_user(user)
        
        return user
    
    def _generate_avatar_url(self, email):
        """Generate avatar URL using DiceBear API"""
        try:
            if not email:
                return self._get_default_avatar_url()
            
            style = "personas"
            seed = urllib.parse.quote(email.lower())
            url = f"https://api.dicebear.com/9.x/{style}/svg?seed={seed}&size=200&radius=20"
            return url
        except Exception:
            return self._get_default_avatar_url()
    
    def _get_default_avatar_url(self):
        """Fallback avatar URL"""
        return "https://api.dicebear.com/9.x/initials/svg?seed=User&backgroundColor=6366f1&color=white"
