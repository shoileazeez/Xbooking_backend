"""
Workspace Member Serializers for v1 API
"""
from rest_framework import serializers
from workspace.models import WorkspaceUser


class WorkspaceMemberSerializer(serializers.ModelSerializer):
    """Serializer for workspace members"""
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    workspace_name = serializers.CharField(source='workspace.name', read_only=True)

    class Meta:
        model = WorkspaceUser
        fields = [
            'id', 'workspace', 'workspace_name', 'user', 'user_name', 
            'user_email', 'role', 'is_active', 'joined_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'joined_at', 'created_at', 'updated_at']
