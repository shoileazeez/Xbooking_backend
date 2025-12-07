"""
Public branch views that don't require authentication
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
from workspace.models import Branch, Workspace, Space
from workspace.serializers.public_space import SpacePublicListSerializer


class PublicBranchListView(APIView):
    """List all public branches without authentication"""
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'public_list'

    @extend_schema(
        responses={200},
        description="Get all public branches"
    )
    @method_decorator(cache_page(60 * 5))  # Cache for 5 minutes
    def get(self, request):
        """Get all branches that are active"""
        branches = Branch.objects.filter(
            is_active=True,
            workspace__is_active=True
        ).select_related('workspace').prefetch_related('spaces')

        # Apply filters if provided
        workspace_id = request.query_params.get('workspace_id')
        city = request.query_params.get('city')
        country = request.query_params.get('country')

        if workspace_id:
            branches = branches.filter(workspace_id=workspace_id)
        if city:
            branches = branches.filter(city__icontains=city)
        if country:
            branches = branches.filter(country__icontains=country)

        # Build response with branch details and their spaces
        branches_data = []
        for branch in branches:
            branch_data = {
                'id': str(branch.id),
                'name': branch.name,
                'workspace': {
                    'id': str(branch.workspace.id),
                    'name': branch.workspace.name,
                },
                'address': branch.address,
                'city': branch.city,
                'state': branch.state,
                'country': branch.country,
                'phone': branch.phone,
                'email': branch.email,
                'operating_hours': branch.operating_hours,
                'latitude': branch.latitude,
                'longitude': branch.longitude,
                'spaces_count': branch.spaces.filter(is_available=True).count(),
                'created_at': branch.created_at.isoformat() if branch.created_at else None,
            }
            branches_data.append(branch_data)

        return Response({
            'success': True,
            'count': len(branches_data),
            'branches': branches_data
        }, status=status.HTTP_200_OK)


class PublicBranchDetailView(APIView):
    """Get public branch details with all spaces without authentication"""
    permission_classes = [AllowAny]
    serializer_class = SpacePublicListSerializer

    @extend_schema(
        responses={200},
        description="Get public branch details and all spaces in the branch by ID"
    )
    def get(self, request, branch_id):
        """Get branch details with all available spaces"""
        try:
            branch = Branch.objects.select_related('workspace').prefetch_related('spaces').get(
                id=branch_id,
                is_active=True,
                workspace__is_active=True
            )
        except Branch.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Branch not found or not active'
            }, status=status.HTTP_404_NOT_FOUND)

        # Get all available spaces in this branch
        spaces = Space.objects.filter(
            branch=branch,
            is_available=True
        ).select_related('branch', 'branch__workspace')

        # Serialize spaces
        spaces_serializer = SpacePublicListSerializer(spaces, many=True)

        branch_data = {
            'id': str(branch.id),
            'name': branch.name,
            'workspace': {
                'id': str(branch.workspace.id),
                'name': branch.workspace.name,
                'logo_url': branch.workspace.logo_url,
            },
            'description': branch.description,
            'address': branch.address,
            'city': branch.city,
            'state': branch.state,
            'country': branch.country,
            'postal_code': branch.postal_code,
            'phone': branch.phone,
            'email': branch.email,
            'operating_hours': branch.operating_hours,
            'images': branch.images,
            'latitude': branch.latitude,
            'longitude': branch.longitude,
            'manager': {
                'id': str(branch.manager.id),
                'name': branch.manager.full_name
            } if branch.manager else None,
            'created_at': branch.created_at.isoformat() if branch.created_at else None,
            'spaces': spaces_serializer.data,
            'spaces_count': spaces.count(),
        }

        return Response({
            'success': True,
            'branch': branch_data
        }, status=status.HTTP_200_OK)
