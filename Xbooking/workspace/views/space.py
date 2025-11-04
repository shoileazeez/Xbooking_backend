from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from workspace.models import Space, Branch
from workspace.serializers.workspace import SpaceSerializer, SpaceDetailSerializer, SpaceSimpleSerializer
from workspace.permissions import (
    check_workspace_admin, check_workspace_member, check_branch_manager
)


class CreateSpaceView(APIView):
    """Create a new space in a branch"""
    permission_classes = [IsAuthenticated]
    serializer_class = SpaceSerializer

    @extend_schema(
        request=SpaceSerializer,
        responses={201: SpaceSerializer},
        description="Create a new space in branch"
    )
    def post(self, request, branch_id):
        """Create space"""
        branch = get_object_or_404(Branch, id=branch_id)
        workspace = branch.workspace

        # Check if user is workspace admin or branch manager using permission helper
        if not (check_workspace_admin(request.user, workspace) or check_branch_manager(request.user, branch)):
            return Response({
                'success': False,
                'message': 'Only workspace admin or branch manager can create spaces'
            }, status=status.HTTP_403_FORBIDDEN)

        data = request.data.copy()
        data['branch'] = branch.id

        serializer = SpaceSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Space created successfully',
                'space': serializer.data
            }, status=status.HTTP_201_CREATED)

        return Response({
            'success': False,
            'message': 'Space creation failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class ListSpacesView(APIView):
    """List spaces in a branch"""
    permission_classes = [IsAuthenticated]
    serializer_class = SpaceSimpleSerializer

    @extend_schema(
        responses={200: SpaceSimpleSerializer(many=True)},
        description="Get all spaces in a branch"
    )
    def get(self, request, branch_id):
        """Get all spaces"""
        branch = get_object_or_404(Branch, id=branch_id)
        workspace = branch.workspace

        # Check if user has access using permission helper
        if not check_workspace_member(request.user, workspace):
            return Response({
                'success': False,
                'message': 'You do not have permission to access this branch'
            }, status=status.HTTP_403_FORBIDDEN)

        spaces = branch.spaces.all()
        serializer = SpaceSimpleSerializer(spaces, many=True)

        return Response({
            'success': True,
            'count': len(spaces),
            'spaces': serializer.data
        }, status=status.HTTP_200_OK)


class SpaceDetailView(APIView):
    """Get, update, delete space"""
    permission_classes = [IsAuthenticated]
    serializer_class = SpaceDetailSerializer

    def get_space(self, space_id, user):
        """Helper to get space and check permissions"""
        space = get_object_or_404(Space, id=space_id)
        branch = space.branch
        workspace = branch.workspace

        # Check if user has access to workspace using permission helper
        if not check_workspace_member(user, workspace):
            return None, Response({
                'success': False,
                'message': 'You do not have permission to access this space'
            }, status=status.HTTP_403_FORBIDDEN)

        return space, None

    @extend_schema(
        responses={200: SpaceDetailSerializer},
        description="Get space details"
    )
    def get(self, request, space_id):
        """Get space details"""
        space, error = self.get_space(space_id, request.user)
        if error:
            return error

        serializer = SpaceDetailSerializer(space)
        return Response({
            'success': True,
            'space': serializer.data
        }, status=status.HTTP_200_OK)

    @extend_schema(
        request=SpaceSerializer,
        responses={200: SpaceSerializer},
        description="Update space"
    )
    def put(self, request, space_id):
        """Update space"""
        space, error = self.get_space(space_id, request.user)
        if error:
            return error

        # Check if user is admin or manager using permission helper
        branch = space.branch
        workspace = branch.workspace
        if not (check_workspace_admin(request.user, workspace) or check_branch_manager(request.user, branch)):
            return Response({
                'success': False,
                'message': 'Only workspace admin or branch manager can update spaces'
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = SpaceSerializer(space, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Space updated successfully',
                'space': serializer.data
            }, status=status.HTTP_200_OK)

        return Response({
            'success': False,
            'message': 'Update failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        description="Delete space"
    )
    def delete(self, request, space_id):
        """Delete space"""
        space, error = self.get_space(space_id, request.user)
        if error:
            return error

        # Check if user is admin using permission helper
        if not check_workspace_admin(request.user, space.branch.workspace):
            return Response({
                'success': False,
                'message': 'Only workspace admin can delete spaces'
            }, status=status.HTTP_403_FORBIDDEN)

        space.delete()
        return Response({
            'success': True,
            'message': 'Space deleted successfully'
        }, status=status.HTTP_200_OK)

