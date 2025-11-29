from rest_framework import serializers
from workspace.models import Workspace, Branch, WorkspaceUser, Space
from drf_spectacular.utils import extend_schema_field


class UserSimpleSerializer(serializers.Serializer):
    """Simple user serializer for nested data"""
    id = serializers.CharField()
    full_name = serializers.CharField()
    email = serializers.EmailField()


class WorkspaceSerializer(serializers.ModelSerializer):
    """Serializer for Workspace model - List/Create view"""
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
        read_only_fields = ['id', 'created_at', 'updated_at']

    @extend_schema_field(serializers.IntegerField())
    def get_members_count(self, obj):
        """Get count of workspace members"""
        return obj.members.filter(is_active=True).count()

    @extend_schema_field(serializers.IntegerField())
    def get_branches_count(self, obj):
        """Get count of workspace branches"""
        return obj.branches.filter(is_active=True).count()


class WorkspaceDetailSerializer(serializers.ModelSerializer):
    """Detailed workspace serializer with nested data"""
    admin = UserSimpleSerializer(read_only=True)
    branches = serializers.SerializerMethodField()
    members = serializers.SerializerMethodField()
    total_spaces = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = [
            'id', 'name', 'description', 'admin', 'logo_url', 'website',
            'email', 'phone', 'address', 'city', 'state', 'country',
            'postal_code', 'is_active', 'branches', 'members', 'total_spaces',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_branches(self, obj):
        """Get all active branches"""
        branches = obj.branches.filter(is_active=True)
        return BranchSimpleSerializer(branches, many=True).data

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_members(self, obj):
        """Get all active members"""
        members = obj.members.filter(is_active=True)
        return WorkspaceUserDetailSerializer(members, many=True).data

    @extend_schema_field(serializers.IntegerField())
    def get_total_spaces(self, obj):
        """Get total count of spaces in all branches"""
        return Space.objects.filter(
            branch__workspace=obj,
            is_available=True
        ).count()


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
        return obj.spaces.filter(is_available=True).count()


class BranchSerializer(serializers.ModelSerializer):
    """Serializer for Branch model - List/Create view"""
    workspace_name = serializers.CharField(source='workspace.name', read_only=True)
    manager_name = serializers.CharField(source='manager.full_name', read_only=True, allow_null=True)
    manager_email = serializers.CharField(source='manager.email', read_only=True, allow_null=True)
    spaces_count = serializers.SerializerMethodField()

    class Meta:
        model = Branch
        fields = [
            'id', 'workspace', 'workspace_name', 'name', 'description', 'manager',
            'manager_name', 'manager_email', 'email', 'phone', 'address', 'city',
            'state', 'country', 'postal_code', 'latitude', 'longitude', 'operating_hours',
            'images', 'is_active', 'spaces_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    @extend_schema_field(serializers.IntegerField())
    def get_spaces_count(self, obj):
        """Get count of available spaces"""
        return obj.spaces.filter(is_available=True).count()


class BranchDetailSerializer(serializers.ModelSerializer):
    """Detailed branch serializer with nested spaces"""
    workspace = WorkspaceSerializer(read_only=True)
    manager = UserSimpleSerializer(read_only=True, allow_null=True)
    spaces = serializers.SerializerMethodField()

    class Meta:
        model = Branch
        fields = [
            'id', 'workspace', 'name', 'description', 'manager', 'email',
            'phone', 'address', 'city', 'state', 'country', 'postal_code',
            'latitude', 'longitude', 'is_active', 'spaces',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_spaces(self, obj):
        """Get all available spaces"""
        spaces = obj.spaces.filter(is_available=True)
        return SpaceSimpleSerializer(spaces, many=True).data


class SpaceSimpleSerializer(serializers.ModelSerializer):
    """Simple space serializer for nested data"""
    branch_name = serializers.CharField(source='branch.name', read_only=True)

    class Meta:
        model = Space
        fields = [
            'id', 'name', 'branch_name', 'space_type', 'capacity', 'price_per_hour',
            'daily_rate', 'monthly_rate', 'image_url', 'is_available', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class SpaceSerializer(serializers.ModelSerializer):
    """Serializer for Space model - List/Create view"""
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    workspace_name = serializers.CharField(source='branch.workspace.name', read_only=True)

    class Meta:
        model = Space
        fields = [
            'id', 'branch', 'branch_name', 'workspace_name', 'name', 'description',
            'space_type', 'capacity', 'price_per_hour', 'daily_rate', 'monthly_rate',
            'image_url', 'amenities', 'rules', 'cancellation_policy', 
            'is_available', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SpaceDetailSerializer(serializers.ModelSerializer):
    """Detailed space serializer"""
    branch = BranchSimpleSerializer(read_only=True)
    workspace_name = serializers.CharField(source='branch.workspace.name', read_only=True)
    workspace_id = serializers.CharField(source='branch.workspace.id', read_only=True)

    class Meta:
        model = Space
        fields = [
            'id', 'branch', 'workspace_name', 'workspace_id', 'name', 'description',
            'space_type', 'capacity', 'price_per_hour', 'daily_rate', 'monthly_rate',
            'image_url', 'amenities', 'rules', 'cancellation_policy', 
            'is_available', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class WorkspaceUserSerializer(serializers.ModelSerializer):
    """Serializer for WorkspaceUser model"""
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    workspace_name = serializers.CharField(source='workspace.name', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = WorkspaceUser
        fields = [
            'id', 'workspace', 'workspace_name', 'user', 'user_name', 'user_email',
            'role', 'role_display', 'is_active', 'joined_at', 'updated_at'
        ]
        read_only_fields = ['id', 'joined_at', 'updated_at']


class WorkspaceUserDetailSerializer(serializers.ModelSerializer):
    """Detailed workspace user serializer"""
    user = UserSimpleSerializer(read_only=True)
    workspace_name = serializers.CharField(source='workspace.name', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = WorkspaceUser
        fields = [
            'id', 'user', 'workspace_name', 'role', 'role_display', 'is_active',
            'joined_at', 'updated_at'
        ]
        read_only_fields = ['id', 'joined_at', 'updated_at']
