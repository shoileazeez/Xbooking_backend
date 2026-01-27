"""
Branch Serializers for v1 API
"""
from rest_framework import serializers
from workspace.models import Branch
from core.cache import CacheService


class BranchSerializer(serializers.ModelSerializer):
    """Serializer for Branch list/create operations"""
    workspace_name = serializers.CharField(source='workspace.name', read_only=True)
    manager_name = serializers.CharField(source='manager.full_name', read_only=True, allow_null=True)
    spaces_count = serializers.SerializerMethodField()

    class Meta:
        model = Branch
        fields = [
            'id', 'workspace', 'workspace_name', 'name', 'description', 
            'manager', 'manager_name', 'operating_hours', 'images', 
            'email', 'phone', 'address', 'city', 'state', 'country', 
            'postal_code', 'latitude', 'longitude', 'is_active', 
            'spaces_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_spaces_count(self, obj):
        cache_key = f"branch_spaces_count:{obj.id}"
        count = CacheService.get(cache_key)
        if count is None:
            count = obj.spaces.filter(is_available=True).count()
            CacheService.set(cache_key, count, timeout=300)
        return count


class BranchDetailSerializer(BranchSerializer):
    """Detailed branch serializer with spaces"""
    spaces = serializers.SerializerMethodField()

    class Meta(BranchSerializer.Meta):
        fields = BranchSerializer.Meta.fields + ['spaces']

    def get_spaces(self, obj):
        from workspace.serializers.v1.space import SpaceSerializer
        return SpaceSerializer(obj.spaces.filter(is_available=True), many=True).data
