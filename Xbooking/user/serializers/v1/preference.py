"""
User Preference Serializers V1
"""
from rest_framework import serializers
from user.models import UserPreference


class UserPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for user preferences"""
    
    class Meta:
        model = UserPreference
        exclude = ['user', 'created_at', 'updated_at']
        read_only_fields = ['id']


class UpdateUserPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for updating user preferences"""
    
    class Meta:
        model = UserPreference
        exclude = ['user', 'id', 'created_at', 'updated_at']
    
    def validate_preferred_capacity_min(self, value):
        """Ensure min capacity is positive"""
        if value < 1:
            raise serializers.ValidationError("Minimum capacity must be at least 1")
        return value
    
    def validate(self, data):
        """Cross-field validation"""
        if 'preferred_capacity_min' in data and 'preferred_capacity_max' in data:
            if data['preferred_capacity_min'] > data['preferred_capacity_max']:
                raise serializers.ValidationError({
                    'preferred_capacity_max': 'Maximum capacity must be greater than or equal to minimum'
                })
        
        if 'budget_min' in data and 'budget_max' in data:
            if data['budget_min'] and data['budget_max'] and data['budget_min'] > data['budget_max']:
                raise serializers.ValidationError({
                    'budget_max': 'Maximum budget must be greater than or equal to minimum'
                })
        
        return data
