"""
Workspace Serializers for v1 API
"""
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from workspace.models import Workspace, Branch, Space
from core.cache import CacheService


class UserSimpleSerializer(serializers.Serializer):
    """Simple user serializer for nested data"""
    id = serializers.UUIDField()
    full_name = serializers.CharField()
    email = serializers.EmailField()


class WorkspaceSerializer(serializers.ModelSerializer):
    """
    Serializer for Workspace model - List/Create view
    Optimized with caching support
    """
    admin_name = serializers.CharField(source='admin.full_name', read_only=True)
    admin_email = serializers.CharField(source='admin.email', read_only=True)
    members_count = serializers.SerializerMethodField()
    branches_count = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = [
            'id', 'name', 'description', 'admin', 'admin_name', 'admin_email',
            'logo_url', 'website', 'email', 'phone', 'address', 'city', 'state',
            'country', 'postal_code', 'social_media_links', 'is_active', 
            'members_count', 'branches_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_active']

    @extend_schema_field(serializers.IntegerField())
    def get_members_count(self, obj):
        """Get count of workspace members with caching"""
        cache_key = f"workspace_members_count:{obj.id}"
        count = CacheService.get(cache_key)
        if count is None:
            count = obj.members.filter(is_active=True).count()
            CacheService.set(cache_key, count, timeout=300)
        return count

    @extend_schema_field(serializers.IntegerField())
    def get_branches_count(self, obj):
        """Get count of workspace branches with caching"""
        cache_key = f"workspace_branches_count:{obj.id}"
        count = CacheService.get(cache_key)
        if count is None:
            count = obj.branches.filter(is_active=True).count()
            CacheService.set(cache_key, count, timeout=300)
        return count

    def validate_email(self, value):
        """Validate workspace email uniqueness"""
        if self.instance and self.instance.email == value:
            return value
        
        if Workspace.objects.filter(email=value).exists():
            raise serializers.ValidationError("A workspace with this email already exists.")
        return value

    def validate_name(self, value):
        """Validate workspace name uniqueness"""
        if self.instance and self.instance.name == value:
            return value
        
        if Workspace.objects.filter(name=value).exists():
            raise serializers.ValidationError("A workspace with this name already exists.")
        return value


class BranchSimpleSerializer(serializers.ModelSerializer):
    """Simple branch serializer for nested data"""
    workspace_name = serializers.CharField(source='workspace.name', read_only=True)
    manager_name = serializers.CharField(source='manager.full_name', read_only=True, allow_null=True)
    spaces_count = serializers.SerializerMethodField()

    class Meta:
        model = Branch
        fields = [
            'id', 'name', 'workspace_name', 'manager_name', 'email', 'city',
            'country', 'is_active', 'spaces_count', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    @extend_schema_field(serializers.IntegerField())
    def get_spaces_count(self, obj):
        """Get count of available spaces"""
        cache_key = f"branch_spaces_count:{obj.id}"
        count = CacheService.get(cache_key)
        if count is None:
            count = obj.spaces.filter(is_available=True).count()
            CacheService.set(cache_key, count, timeout=300)
        return count


class WorkspaceUserSimpleSerializer(serializers.Serializer):
    """Simple workspace user serializer"""
    id = serializers.UUIDField()
    user_name = serializers.CharField(source='user.full_name')
    user_email = serializers.EmailField(source='user.email')
    role = serializers.CharField()
    joined_at = serializers.DateTimeField()


class WorkspaceDetailSerializer(serializers.ModelSerializer):
    """
    Detailed workspace serializer with nested data
    Includes branches, members, and statistics (workspace-only data)
    """
    admin = UserSimpleSerializer(read_only=True)
    branches = serializers.SerializerMethodField()
    members = serializers.SerializerMethodField()
    total_spaces = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = [
            'id', 'name', 'description', 'admin', 'logo_url', 'website',
            'email', 'phone', 'address', 'city', 'state', 'country',
            'postal_code', 'social_media_links', 'is_active', 'branches', 
            'members', 'total_spaces', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_branches(self, obj):
        """Get all active branches with caching"""
        cache_key = f"workspace_branches_detail:{obj.id}"
        data = CacheService.get(cache_key)
        if data is None:
            branches = obj.branches.filter(is_active=True)
            data = BranchSimpleSerializer(branches, many=True).data
            CacheService.set(cache_key, data, timeout=300)
        return data

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_members(self, obj):
        """Get all active members with caching"""
        cache_key = f"workspace_members_detail:{obj.id}"
        data = CacheService.get(cache_key)
        if data is None:
            members = obj.members.filter(is_active=True).select_related('user')
            data = WorkspaceUserSimpleSerializer(members, many=True).data
            CacheService.set(cache_key, data, timeout=300)
        return data

    @extend_schema_field(serializers.IntegerField())
    def get_total_spaces(self, obj):
        """Get total count of spaces in all branches"""
        cache_key = f"workspace_total_spaces:{obj.id}"
        count = CacheService.get(cache_key)
        if count is None:
            count = Space.objects.filter(
                branch__workspace=obj,
                is_available=True
            ).count()
            CacheService.set(cache_key, count, timeout=300)
        return count

