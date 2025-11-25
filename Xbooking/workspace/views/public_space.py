"""
Public space views that don't require authentication
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.throttling import ScopedRateThrottle
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from drf_spectacular.utils import extend_schema
from workspace.models import Space, Branch, Workspace
from workspace.serializers.public_space import SpacePublicListSerializer, SpacePublicDetailSerializer


class PublicSpaceListView(APIView):
    """List all public spaces without authentication"""
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'public_list'
    serializer_class = SpacePublicListSerializer

    @extend_schema(
        responses={200: SpacePublicListSerializer(many=True)},
        description="Get all public spaces"
    )
    @method_decorator(cache_page(60 * 5))  # Cache for 5 minutes
    def get(self, request):
        """Get all spaces that are available for booking"""
        # Filter active spaces from active branches in active workspaces
        spaces = Space.objects.filter(
            is_available=True,
            branch__is_active=True,
            branch__workspace__is_active=True
        ).select_related('branch', 'branch__workspace')

        # Apply filters if provided
        workspace_id = request.query_params.get('workspace_id')
        branch_id = request.query_params.get('branch_id')
        min_price = request.query_params.get('min_price')
        max_price = request.query_params.get('max_price')
        capacity = request.query_params.get('capacity')
        space_type = request.query_params.get('type')

        if workspace_id:
            spaces = spaces.filter(branch__workspace_id=workspace_id)
        if branch_id:
            spaces = spaces.filter(branch_id=branch_id)
        if min_price:
            spaces = spaces.filter(price_per_hour__gte=min_price)
        if max_price:
            spaces = spaces.filter(price_per_hour__lte=max_price)
        if capacity:
            spaces = spaces.filter(capacity__gte=capacity)
        if space_type:
            spaces = spaces.filter(space_type=space_type)

        serializer = SpacePublicListSerializer(spaces, many=True)
        return Response({
            'success': True,
            'count': spaces.count(),
            'spaces': serializer.data
        }, status=status.HTTP_200_OK)


class PublicSpaceDetailView(APIView):
    """Get public space details without authentication"""
    permission_classes = [AllowAny]
    serializer_class = SpacePublicDetailSerializer

    @extend_schema(
        responses={200: SpacePublicDetailSerializer},
        description="Get public space details by ID"
    )
    def get(self, request, space_id):
        """Get space details for a specific space"""
        try:
            # Get active space from active branch in active workspace
            space = Space.objects.select_related(
                'branch', 'branch__workspace'
            ).get(
                id=space_id,
                is_available=True,
                branch__is_active=True,
                branch__workspace__is_active=True
            )
        except Space.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Space not found or not available'
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = SpacePublicDetailSerializer(space)
        return Response({
            'success': True,
            'space': serializer.data
        }, status=status.HTTP_200_OK)