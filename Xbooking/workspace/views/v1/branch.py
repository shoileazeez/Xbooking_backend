"""
Branch ViewSet for v1 API
"""
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema_view, extend_schema

from core.views import CachedModelViewSet
from core.permissions import IsWorkspaceAdmin
from core.pagination import StandardResultsSetPagination
from workspace.models import Branch
from workspace.serializers.v1 import BranchSerializer, BranchDetailSerializer
from workspace.services import BranchService


@extend_schema_view(
    list=extend_schema(description="List all branches in user's workspaces"),
    retrieve=extend_schema(description="Retrieve branch details"),
    create=extend_schema(description="Create a new branch"),
    update=extend_schema(description="Update branch"),
    partial_update=extend_schema(description="Partially update branch"),
    destroy=extend_schema(description="Delete branch"),
)
class BranchViewSet(CachedModelViewSet):
    """ViewSet for managing workspace branches"""
    serializer_class = BranchSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    cache_timeout = 300

    def get_queryset(self):
        user = self.request.user
        return Branch.objects.filter(
            workspace__admin=user,
            is_active=True
        ).select_related('workspace', 'manager')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return BranchDetailSerializer
        return BranchSerializer

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsWorkspaceAdmin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        branch = serializer.save()
        BranchService.create_branch(branch, created_by=self.request.user)

    def perform_update(self, serializer):
        branch = serializer.save()
        BranchService.update_branch(branch, updated_by=self.request.user)

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()
