"""
Public workspace views
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from workspace.models import Workspace
from workspace.serializers.public_workspace import WorkspacePublicListSerializer, WorkspacePublicDetailSerializer

from rest_framework.throttling import ScopedRateThrottle

from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

class PublicWorkspaceListView(APIView):
    """List all public workspaces"""
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'public_list'
    serializer_class = WorkspacePublicListSerializer

    @extend_schema(
        responses={200: WorkspacePublicListSerializer(many=True)},
        description="Get all active workspaces"
    )
    @method_decorator(cache_page(60 * 15))  # Cache for 15 minutes
    def get(self, request):
        """Get all active workspaces"""
        workspaces = Workspace.objects.filter(is_active=True).order_by('name')
        
        # Optional filtering
        city = request.query_params.get('city')
        country = request.query_params.get('country')
        
        if city:
            workspaces = workspaces.filter(city__icontains=city)
        if country:
            workspaces = workspaces.filter(country__icontains=country)
        
        # Pagination
        paginator = PageNumberPagination()
        paginator.page_size = 20
        paginated_workspaces = paginator.paginate_queryset(workspaces, request)
        
        serializer = WorkspacePublicListSerializer(paginated_workspaces, many=True)
        return paginator.get_paginated_response({
            'success': True,
            'workspaces': serializer.data
        })


class PublicWorkspaceDetailView(APIView):
    """Get public workspace details"""
    permission_classes = [AllowAny]
    serializer_class = WorkspacePublicDetailSerializer

    @extend_schema(
        responses={200: WorkspacePublicDetailSerializer},
        description="Get public workspace details by ID"
    )
    def get(self, request, workspace_id):
        """Get workspace details"""
        try:
            workspace = Workspace.objects.get(id=workspace_id, is_active=True)
        except Workspace.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Workspace not found or inactive'
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = WorkspacePublicDetailSerializer(workspace)
        return Response({
            'success': True,
            'workspace': serializer.data
        }, status=status.HTTP_200_OK)
