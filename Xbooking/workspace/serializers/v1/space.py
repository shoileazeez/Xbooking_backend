"""
Space Serializers for v1 API
"""
from rest_framework import serializers
from workspace.models import Space


class SpaceMinimalSerializer(serializers.ModelSerializer):
    """Minimal space serializer for nested representations"""
    
    class Meta:
        model = Space
        fields = ['id', 'name', 'space_type', 'capacity', 'image_url']
        read_only_fields = fields


class SpaceSerializer(serializers.ModelSerializer):
    """Serializer for Space list/create operations"""
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    workspace_name = serializers.CharField(source='branch.workspace.name', read_only=True)

    class Meta:
        model = Space
        fields = [
            'id', 'branch', 'branch_name', 'workspace_name', 'name', 
            'description', 'space_type', 'capacity', 'price_per_hour', 
            'daily_rate', 'monthly_rate', 'rules', 'cancellation_policy', 
            'image_url', 'amenities', 'is_available', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SpaceDetailSerializer(SpaceSerializer):
    """Detailed space serializer with calendar info"""
    calendar = serializers.SerializerMethodField()

    class Meta(SpaceSerializer.Meta):
        fields = SpaceSerializer.Meta.fields + ['calendar']

    def get_calendar(self, obj):
        if hasattr(obj, 'calendar'):
            return {
                'hourly_enabled': obj.calendar.hourly_enabled,
                'daily_enabled': obj.calendar.daily_enabled,
                'monthly_enabled': obj.calendar.monthly_enabled,
                'hourly_price': str(obj.calendar.hourly_price),
                'daily_price': str(obj.calendar.daily_price),
                'monthly_price': str(obj.calendar.monthly_price),
            }
        return None
