"""
Public workspace serializers
"""
from rest_framework import serializers
from workspace.models import Workspace, Branch
from drf_spectacular.utils import extend_schema_field

class WorkspacePublicListSerializer(serializers.ModelSerializer):
    """Serializer for public workspace list"""
    branches_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Workspace
        fields = [
            'id', 'name', 'description', 'logo_url', 'city', 'state', 'country',
            'branches_count', 'created_at'
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.IntegerField())
    def get_branches_count(self, obj):
        """Get count of active branches"""
        return obj.branches.filter(is_active=True).count()


class WorkspacePublicDetailSerializer(serializers.ModelSerializer):
    """Serializer for public workspace detail"""
    branches = serializers.SerializerMethodField()
    
    class Meta:
        model = Workspace
        fields = [
            'id', 'name', 'description', 'logo_url', 'website', 'email', 'phone',
            'address', 'city', 'state', 'country', 'postal_code', 'social_media_links',
            'branches', 'created_at'
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_branches(self, obj):
        """Get active branches with basic info"""
        branches = obj.branches.filter(is_active=True)
        return BranchPublicSerializer(branches, many=True).data


class BranchPublicSerializer(serializers.ModelSerializer):
    """Serializer for public branch info"""
    spaces_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Branch
        fields = [
            'id', 'name', 'description', 'city', 'state', 'country', 
            'latitude', 'longitude', 'operating_hours', 'images', 'spaces_count'
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.IntegerField())
    def get_spaces_count(self, obj):
        """Get count of available spaces"""
        return obj.spaces.filter(is_available=True).count()
