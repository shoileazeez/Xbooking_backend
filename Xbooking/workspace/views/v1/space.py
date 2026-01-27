"""
Space ViewSet for v1 API
"""
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema_view, extend_schema

from core.views import CachedModelViewSet
from core.permissions import IsWorkspaceAdmin
from core.pagination import StandardResultsSetPagination
from workspace.models import Space
from workspace.serializers.v1 import SpaceSerializer, SpaceDetailSerializer
from workspace.services import SpaceService


@extend_schema_view(
    list=extend_schema(description="List all spaces in user's workspaces"),
    retrieve=extend_schema(description="Retrieve space details"),
    create=extend_schema(description="Create a new space"),
    update=extend_schema(description="Update space"),
    partial_update=extend_schema(description="Partially update space"),
    destroy=extend_schema(description="Delete space"),
)
class SpaceViewSet(CachedModelViewSet):
    """ViewSet for managing workspace spaces"""
    serializer_class = SpaceSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    cache_timeout = 300

    def get_queryset(self):
        user = self.request.user
        return Space.objects.filter(
            branch__workspace__admin=user,
            is_available=True
        ).select_related('branch', 'branch__workspace')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return SpaceDetailSerializer
        return SpaceSerializer

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsWorkspaceAdmin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        space = serializer.save()
        SpaceService.create_space(space, created_by=self.request.user)

    def perform_update(self, serializer):
        space = serializer.save()
        SpaceService.update_space(space, updated_by=self.request.user)

    def perform_destroy(self, instance):
        instance.is_available = False
        instance.save()
