"""
Workspace ViewSet for v1 API
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, extend_schema_view
from django.shortcuts import get_object_or_404
from django.db.models import Q

from core.views import CachedModelViewSet
from core.responses import SuccessResponse, ErrorResponse, PaginatedResponse
from core.permissions import IsWorkspaceAdmin
from core.pagination import StandardResultsSetPagination
from core.cache import CacheService
from workspace.models import Workspace
from workspace.serializers.v1 import WorkspaceSerializer, WorkspaceDetailSerializer
from workspace.services import WorkspaceService


@extend_schema_view(
    list=extend_schema(description="List all workspaces for authenticated user"),
    retrieve=extend_schema(description="Retrieve workspace details"),
    create=extend_schema(description="Create a new workspace"),
    update=extend_schema(description="Update workspace"),
    partial_update=extend_schema(description="Partially update workspace"),
    destroy=extend_schema(description="Delete workspace"),
)
class WorkspaceViewSet(CachedModelViewSet):
    """
    ViewSet for managing workspaces with caching support.
    
    Inherits automatic caching from CachedModelViewSet.
    """
    serializer_class = WorkspaceSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    cache_timeout = 300  # 5 minutes
    
    def get_queryset(self):
        """
        Return workspaces owned by or accessible to the user.
        Results are cached per user.
        """
        user = self.request.user
        cache_key = f"user_workspaces:{user.id}"
        
        cached_ids = CacheService.get(cache_key)
        if cached_ids is not None:
            return Workspace.objects.filter(id__in=cached_ids, is_active=True)
        
        workspaces = Workspace.objects.filter(
            Q(admin=user) | Q(members__user=user),
            is_active=True
        ).distinct()
        
        workspace_ids = list(workspaces.values_list('id', flat=True))
        CacheService.set(cache_key, workspace_ids, timeout=self.cache_timeout)
        
        return workspaces
    
    def get_serializer_class(self):
        """Use detailed serializer for retrieve action"""
        if self.action == 'retrieve':
            return WorkspaceDetailSerializer
        return WorkspaceSerializer
    
    def get_permissions(self):
        """
        Admin permission required for update/delete operations
        """
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsWorkspaceAdmin()]
        return super().get_permissions()
    
    def perform_create(self, serializer):
        """Create workspace and publish event"""
        workspace = serializer.save(admin=self.request.user)
        WorkspaceService.create_workspace(workspace, created_by=self.request.user)
    
    def perform_update(self, serializer):
        """Update workspace and publish event"""
        workspace = serializer.save()
        WorkspaceService.update_workspace(workspace, updated_by=self.request.user)
    
    def perform_destroy(self, instance):
        """Soft delete workspace"""
        instance.is_active = False
        instance.save()
        WorkspaceService.delete_workspace(instance, deleted_by=self.request.user)
    
    @extend_schema(
        description="Get workspace statistics",
        responses={200: dict}
    )
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get workspace statistics"""
        workspace = self.get_object()
        stats = WorkspaceService.get_workspace_statistics(workspace)
        return SuccessResponse(
            data=stats,
            message="Statistics retrieved successfully"
        )
    
    @extend_schema(
        description="Clear workspace cache",
        responses={200: dict}
    )
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsWorkspaceAdmin])
    def clear_cache(self, request, pk=None):
        """Clear workspace cache"""
        workspace = self.get_object()
        CacheService.delete(workspace.get_cache_key())
        return SuccessResponse(message="Cache cleared successfully")
