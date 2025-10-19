"""
Workspace Member Management Serializers
"""
from rest_framework import serializers
from workspace.models import WorkspaceUser, Workspace
from user.models import User
from drf_spectacular.utils import extend_schema_field
import re


class OnboardingStatusSerializer(serializers.Serializer):
    """Serializer for onboarding status"""
    is_registered = serializers.BooleanField()
    has_workspace = serializers.BooleanField()
    completed_steps = serializers.ListField(child=serializers.CharField())
    progress_percentage = serializers.IntegerField(min_value=0, max_value=100)


def is_business_email(email):
    """Check if email is a business email (not free email provider)"""
    free_email_domains = [
        'gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com',
        'aol.com', 'mail.com', 'protonmail.com', 'icloud.com',
        'yandex.com', 'mail.ru', 'qq.com', '163.com'
    ]
    domain = email.split('@')[1].lower() if '@' in email else ''
    return domain not in free_email_domains


class InviteTokenSerializer(serializers.Serializer):
    """Serializer for generating invite tokens"""
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=['manager', 'staff', 'user'])
    
    def validate_role(self, value):
        valid_roles = ['manager', 'staff', 'user']
        if value not in valid_roles:
            raise serializers.ValidationError(f"Role must be one of: {', '.join(valid_roles)}")
        return value


class AdminRegisterSerializer(serializers.Serializer):
    """Serializer for admin registration - requires business email"""
    full_name = serializers.CharField(max_length=200, required=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, required=True)
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        
        # Validate business email for admin registration
        if not is_business_email(value):
            raise serializers.ValidationError(
                "Admin registration requires a business email address. "
                "Free email providers (Gmail, Yahoo, etc.) are not allowed."
            )
        
        return value
    
    def validate(self, data):
        if data.get('password') != data.get('confirm_password'):
            raise serializers.ValidationError({"password": "Passwords do not match"})
        
        password = data.get('password')
        if not self._validate_password_strength(password):
            raise serializers.ValidationError({
                "password": "Password must contain uppercase, lowercase, digit, and special character"
            })
        
        return data
    
    @staticmethod
    def _validate_password_strength(password):
        """Validate password strength"""
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password)
        
        return has_upper and has_lower and has_digit and has_special


class MemberSignUpSerializer(serializers.Serializer):
    """Serializer for member/staff/manager signup - allows any email"""
    full_name = serializers.CharField(max_length=200, required=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, required=True)
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value
    
    def validate(self, data):
        if data.get('password') != data.get('confirm_password'):
            raise serializers.ValidationError({"password": "Passwords do not match"})
        
        password = data.get('password')
        if not self._validate_password_strength(password):
            raise serializers.ValidationError({
                "password": "Password must contain uppercase, lowercase, digit, and special character"
            })
        
        return data
    
    @staticmethod
    def _validate_password_strength(password):
        """Validate password strength"""
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password)
        
        return has_upper and has_lower and has_digit and has_special


class WorkspaceMemberSerializer(serializers.ModelSerializer):
    """Serializer for workspace members"""
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_id = serializers.CharField(source='user.id', read_only=True)
    
    class Meta:
        model = WorkspaceUser
        fields = ['id', 'user_id', 'user_email', 'user_name', 'role', 'is_active', 'joined_at']
        read_only_fields = ['id', 'joined_at']


class WorkspaceMemberDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for workspace members"""
    user = serializers.SerializerMethodField()
    
    class Meta:
        model = WorkspaceUser
        fields = ['id', 'user', 'role', 'is_active', 'joined_at', 'updated_at']
        read_only_fields = ['id', 'joined_at', 'updated_at']
    
    @extend_schema_field(serializers.DictField())
    def get_user(self, obj):
        return {
            'id': str(obj.user.id),
            'email': obj.user.email,
            'full_name': obj.user.full_name,
            'avatar_url': obj.user.avatar_url,
            'date_joined': obj.user.date_joined
        }


class AdminProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile"""
    workspace_count = serializers.SerializerMethodField()
    membership_count = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'full_name', 'email', 'avatar_url', 'date_joined', 'last_login', 'workspace_count', 'membership_count']
        read_only_fields = ['id', 'date_joined', 'last_login']
    
    @extend_schema_field(serializers.IntegerField())
    def get_workspace_count(self, obj):
        """Count workspaces where user is admin"""
        return obj.owned_workspaces.count()
    
    @extend_schema_field(serializers.IntegerField())
    def get_membership_count(self, obj):
        """Count workspace memberships"""
        return obj.workspace_memberships.filter(is_active=True).count()


class AdminLoginSerializer(serializers.Serializer):
    """Serializer for admin login"""
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)
    
    def validate(self, data):
        email = data.get('email')
        password = data.get('password')
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({"email": "User with this email does not exist"})
        
        if not user.check_password(password):
            raise serializers.ValidationError({"password": "Invalid password"})
        
        if not user.is_active:
            raise serializers.ValidationError({"email": "User account is inactive"})
        
        data['user'] = user
        return data


class AdminOnboardingSerializer(serializers.Serializer):
    """Serializer for admin onboarding - creates workspace with initial setup"""
    workspace_name = serializers.CharField(max_length=255, required=True)
    workspace_description = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    company_email = serializers.EmailField(required=True)
    company_phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    company_address = serializers.CharField(max_length=255, required=False, allow_blank=True)
    company_city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    company_country = serializers.CharField(max_length=100, required=False, allow_blank=True)
    
    def validate_workspace_name(self, value):
        """Check if workspace name is unique"""
        if Workspace.objects.filter(name=value).exists():
            raise serializers.ValidationError("Workspace name already exists")
        return value
    
    def validate_company_email(self, value):
        """Check if email is unique"""
        if Workspace.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already used for another workspace")
        return value

