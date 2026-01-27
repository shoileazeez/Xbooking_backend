"""
Public API Views for v1 - Read-only workspace/branch/space data
"""
from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema_view, extend_schema

from core.views import CachedModelViewSet
from core.pagination import StandardResultsSetPagination
from workspace.models import Workspace, Branch, Space
from workspace.serializers.v1 import WorkspaceSerializer, BranchSerializer, SpaceSerializer


@extend_schema_view(
    list=extend_schema(description="List all active workspaces (public)"),
    retrieve=extend_schema(description="Retrieve workspace details (public)"),
)
class PublicWorkspaceViewSet(CachedModelViewSet):
    """Public read-only workspace listing"""
    serializer_class = WorkspaceSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination
    http_method_names = ['get']
    cache_timeout = 600

    def get_queryset(self):
        return Workspace.objects.filter(is_active=True)


@extend_schema_view(
    list=extend_schema(description="List all active branches (public)"),
    retrieve=extend_schema(description="Retrieve branch details (public)"),
)
class PublicBranchViewSet(CachedModelViewSet):
    """Public read-only branch listing"""
    serializer_class = BranchSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination
    http_method_names = ['get']
    cache_timeout = 600

    def get_queryset(self):
        return Branch.objects.filter(
            is_active=True,
            workspace__is_active=True
        ).select_related('workspace')


@extend_schema_view(
    list=extend_schema(description="List all available spaces (public)"),
    retrieve=extend_schema(description="Retrieve space details (public)"),
)
class PublicSpaceViewSet(CachedModelViewSet):
    """Public read-only space listing"""
    serializer_class = SpaceSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination
    http_method_names = ['get']
    cache_timeout = 600

    def get_queryset(self):
        return Space.objects.filter(
            is_available=True,
            branch__is_active=True,
            branch__workspace__is_active=True
        ).select_related('branch', 'branch__workspace')
