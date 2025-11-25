from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from workspace.models import Workspace, Branch
from workspace.serializers.workspace import (
    WorkspaceSerializer, WorkspaceDetailSerializer,
)
from workspace.permissions import (
    check_workspace_admin, check_workspace_member, get_user_role
)


class CreateWorkspaceView(APIView):
    """Create a new workspace"""
    permission_classes = [IsAuthenticated]
    serializer_class = WorkspaceSerializer

    @extend_schema(
        request=WorkspaceSerializer,
        responses={201: WorkspaceSerializer},
        description="Create a new workspace"
    )
    def post(self, request):
        """Create workspace"""
        data = request.data.copy()
        data['admin'] = request.user.id

        serializer = WorkspaceSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Workspace created successfully',
                'workspace': serializer.data
            }, status=status.HTTP_201_CREATED)

        return Response({
            'success': False,
            'message': 'Workspace creation failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class ListWorkspacesView(APIView):
    """List workspaces for authenticated user"""
    permission_classes = [IsAuthenticated]
    serializer_class = WorkspaceSerializer

    @extend_schema(
        responses={200: WorkspaceSerializer(many=True)},
        description="Get all workspaces owned by or user is member of"
    )
    def get(self, request):
        """Get all workspaces owned by user or member"""
        # Get workspaces owned by user
        owned = Workspace.objects.filter(admin=request.user)
        
        # Get workspaces where user is a member
        member_workspaces = Workspace.objects.filter(members__user=request.user).distinct()
        
        # Combine both
        workspaces = (owned | member_workspaces).distinct()

        serializer = WorkspaceSerializer(workspaces, many=True)
        return Response({
            'success': True,
            'count': len(workspaces),
            'workspaces': serializer.data
        }, status=status.HTTP_200_OK)


class WorkspaceDetailView(APIView):
    """Get, update, delete workspace"""
    permission_classes = [IsAuthenticated]
    serializer_class = WorkspaceDetailSerializer

    def get_workspace(self, workspace_id, user):
        """Helper to get workspace and check permissions"""
        workspace = get_object_or_404(Workspace, id=workspace_id)
        
        # Check if user is admin or member using permission helper
        # Relaxed permission: Any authenticated user can view workspace details
        # if not check_workspace_member(user, workspace):
        #     return None, Response({
        #         'success': False,
        #         'message': 'You do not have permission to access this workspace'
        #     }, status=status.HTTP_403_FORBIDDEN)
        
        return workspace, None

    @extend_schema(
        responses={200: WorkspaceDetailSerializer},
        description="Get workspace details"
    )
    def get(self, request, workspace_id):
        """Get workspace details"""
        workspace, error = self.get_workspace(workspace_id, request.user)
        if error:
            return error

        serializer = WorkspaceDetailSerializer(workspace)
        return Response({
            'success': True,
            'workspace': serializer.data
        }, status=status.HTTP_200_OK)

    @extend_schema(
        request=WorkspaceSerializer,
        responses={200: WorkspaceSerializer},
        description="Update workspace"
    )
    def put(self, request, workspace_id):
        """Update workspace"""
        workspace, error = self.get_workspace(workspace_id, request.user)
        if error:
            return error

        # Check if user is admin using permission helper
        if not check_workspace_admin(request.user, workspace):
            return Response({
                'success': False,
                'message': 'Only workspace admin can update workspace'
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = WorkspaceSerializer(workspace, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Workspace updated successfully',
                'workspace': serializer.data
            }, status=status.HTTP_200_OK)

        return Response({
            'success': False,
            'message': 'Update failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        description="Delete workspace"
    )
    def delete(self, request, workspace_id):
        """Delete workspace"""
        workspace, error = self.get_workspace(workspace_id, request.user)
        if error:
            return error

        # Check if user is admin using permission helper
        if not check_workspace_admin(request.user, workspace):
            return Response({
                'success': False,
                'message': 'Only workspace admin can delete workspace'
            }, status=status.HTTP_403_FORBIDDEN)

        workspace.delete()
        return Response({
            'success': True,
            'message': 'Workspace deleted successfully'
        }, status=status.HTTP_200_OK)
