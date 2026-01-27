"""
Workspace Members ViewSet for v1 API
"""
from rest_framework import viewsets, status, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema_view, extend_schema
from django.db import transaction

from core.views import CachedModelViewSet
from core.responses import SuccessResponse, ErrorResponse
from core.permissions import IsWorkspaceAdmin
from core.pagination import StandardResultsSetPagination
from workspace.models import WorkspaceUser, Workspace
from workspace.serializers.v1 import WorkspaceMemberSerializer
from workspace.services import WorkspaceService
from user.services.user_service import UserService


@extend_schema_view(
    list=extend_schema(description="List workspace members"),
    retrieve=extend_schema(description="Retrieve member details"),
    create=extend_schema(description="Add member to workspace"),
    destroy=extend_schema(description="Remove member from workspace"),
)
class WorkspaceMemberViewSet(CachedModelViewSet):
    """ViewSet for managing workspace members"""
    serializer_class = WorkspaceMemberSerializer
    permission_classes = [IsAuthenticated, IsWorkspaceAdmin]
    pagination_class = StandardResultsSetPagination
    cache_timeout = 300
    http_method_names = ['get', 'post', 'delete']  # No PUT/PATCH

    def get_queryset(self):
        user = self.request.user
        return WorkspaceUser.objects.filter(
            workspace__admin=user,
            is_active=True
        ).select_related('workspace', 'user')

    @transaction.atomic
    def perform_create(self, serializer):
        """
        Create workspace member.
        If user doesn't exist, create account with random password.
        """
        workspace = serializer.validated_data['workspace']
        user_id = serializer.validated_data.get('user')
        
        # If user ID provided, use existing user
        if user_id:
            member = serializer.save()
            WorkspaceService.add_member(
                workspace=member.workspace,
                user=member.user,
                role=member.role,
                added_by=self.request.user
            )
        else:
            # Create user from email and name if provided
            email = self.request.data.get('email')
            full_name = self.request.data.get('full_name')
            
            if not email or not full_name:
                raise serializers.ValidationError({
                    'email': 'Email and full_name are required when user is not provided'
                })
            
            # Create or get user
            user, password, is_new = UserService.create_or_get_user_for_workspace_invite(
                email=email,
                full_name=full_name,
                created_by=self.request.user
            )
            
            # Create workspace membership
            serializer.validated_data['user'] = user
            member = serializer.save()
            
            WorkspaceService.add_member(
                workspace=member.workspace,
                user=member.user,
                role=member.role,
                added_by=self.request.user
            )

    def perform_destroy(self, instance):
        WorkspaceService.remove_member(
            workspace=instance.workspace,
            user=instance.user,
            removed_by=self.request.user
        )
        instance.is_active = False
        instance.save()
