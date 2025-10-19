from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from workspace.models import Branch, Workspace, WorkspaceUser
from workspace.serializers.workspace import BranchSerializer, BranchDetailSerializer, BranchSimpleSerializer
from workspace.permissions import (
    check_workspace_admin, check_workspace_member, check_workspace_manager, check_branch_manager
)


class CreateBranchView(APIView):
    """Create a new branch for a workspace"""
    permission_classes = [IsAuthenticated]
    serializer_class = BranchSerializer

    @extend_schema(
        request=BranchSerializer,
        responses={201: BranchSerializer},
        description="Create a new branch in workspace"
    )
    def post(self, request, workspace_id):
        """Create branch"""
        workspace = get_object_or_404(Workspace, id=workspace_id)

        # Check if user is workspace admin using permission helper
        if not check_workspace_admin(request.user, workspace):
            return Response({
                'success': False,
                'message': 'Only workspace admin can create branches'
            }, status=status.HTTP_403_FORBIDDEN)

        data = request.data.copy()
        data['workspace'] = workspace.id

        serializer = BranchSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Branch created successfully',
                'branch': serializer.data
            }, status=status.HTTP_201_CREATED)

        return Response({
            'success': False,
            'message': 'Branch creation failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class ListBranchesView(APIView):
    """List branches for a workspace"""
    permission_classes = [IsAuthenticated]
    serializer_class = BranchSimpleSerializer

    @extend_schema(
        responses={200: BranchSimpleSerializer(many=True)},
        description="Get all branches in a workspace"
    )
    def get(self, request, workspace_id):
        """Get all branches"""
        workspace = get_object_or_404(Workspace, id=workspace_id)

        # Check if user has access using permission helper
        if not check_workspace_member(request.user, workspace):
            return Response({
                'success': False,
                'message': 'You do not have permission to access this workspace'
            }, status=status.HTTP_403_FORBIDDEN)

        branches = workspace.branches.all()
        serializer = BranchSimpleSerializer(branches, many=True)

        return Response({
            'success': True,
            'count': len(branches),
            'branches': serializer.data
        }, status=status.HTTP_200_OK)


class BranchDetailView(APIView):
    """Get, update, delete branch"""
    permission_classes = [IsAuthenticated]
    serializer_class = BranchDetailSerializer

    def get_branch(self, branch_id, user):
        """Helper to get branch and check permissions"""
        branch = get_object_or_404(Branch, id=branch_id)
        workspace = branch.workspace

        # Check if user has access to workspace using permission helper
        if not check_workspace_member(user, workspace):
            return None, Response({
                'success': False,
                'message': 'You do not have permission to access this branch'
            }, status=status.HTTP_403_FORBIDDEN)

        return branch, None

    @extend_schema(
        responses={200: BranchDetailSerializer},
        description="Get branch details"
    )
    def get(self, request, branch_id):
        """Get branch details"""
        branch, error = self.get_branch(branch_id, request.user)
        if error:
            return error

        serializer = BranchDetailSerializer(branch)
        return Response({
            'success': True,
            'branch': serializer.data
        }, status=status.HTTP_200_OK)

    @extend_schema(
        request=BranchSerializer,
        responses={200: BranchSerializer},
        description="Update branch"
    )
    def put(self, request, branch_id):
        """Update branch"""
        branch, error = self.get_branch(branch_id, request.user)
        if error:
            return error

        # Check if user is admin or manager using permission helper
        workspace = branch.workspace
        if not (check_workspace_admin(request.user, workspace) or check_branch_manager(request.user, branch)):
            return Response({
                'success': False,
                'message': 'Only workspace admin or branch manager can update branch'
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = BranchSerializer(branch, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Branch updated successfully',
                'branch': serializer.data
            }, status=status.HTTP_200_OK)

        return Response({
            'success': False,
            'message': 'Update failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        description="Delete branch"
    )
    def delete(self, request, branch_id):
        """Delete branch"""
        branch, error = self.get_branch(branch_id, request.user)
        if error:
            return error

        # Check if user is admin using permission helper
        if not check_workspace_admin(request.user, branch.workspace):
            return Response({
                'success': False,
                'message': 'Only workspace admin can delete branches'
            }, status=status.HTTP_403_FORBIDDEN)

        branch.delete()
        return Response({
            'success': True,
            'message': 'Branch deleted successfully'
        }, status=status.HTTP_200_OK)
