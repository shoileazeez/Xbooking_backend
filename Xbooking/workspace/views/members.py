"""
Workspace Member Management Views
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.contrib.auth.hashers import make_password
from drf_spectacular.utils import extend_schema
from workspace.models import WorkspaceUser, Workspace
from workspace.serializers.members import (
    WorkspaceMemberSerializer, WorkspaceMemberDetailSerializer,
    InviteTokenSerializer, AdminRegisterSerializer, AdminProfileSerializer,
    AdminLoginSerializer, AdminOnboardingSerializer, MemberSignUpSerializer, OnboardingStatusSerializer
)
from workspace.permissions import check_workspace_admin, check_workspace_member
from user.models import User
from user.utils import get_tokens_for_user
import uuid
import datetime


class AdminRegisterView(APIView):
    """Register a new admin account - requires business email"""
    permission_classes = [AllowAny]
    serializer_class = AdminRegisterSerializer
    
    @extend_schema(
        request=AdminRegisterSerializer,
        responses={201: AdminProfileSerializer},
        description="Register a new admin with business email validation"
    )
    def post(self, request):
        """Register new admin user"""
        serializer = AdminRegisterSerializer(data=request.data)
        if serializer.is_valid():
            # Create user
            user = User.objects.create(
                full_name=serializer.validated_data['full_name'],
                email=serializer.validated_data['email']
            )
            user.set_password(serializer.validated_data['password'])
            user.save()
            
            # Generate JWT tokens
            jwt_tokens = get_tokens_for_user(user)
            
            return Response({
                'success': True,
                'message': 'Admin registration successful',
                'user': {
                    'user_id': str(user.id),
                    'email': user.email,
                    'full_name': user.full_name,
                    'avatar_url': user.avatar_url
                },
                'token': jwt_tokens
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'message': 'Admin registration failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class AdminProfileView(APIView):
    """Get admin/user profile"""
    permission_classes = [IsAuthenticated]
    serializer_class = AdminProfileSerializer
    
    @extend_schema(
        responses={200: AdminProfileSerializer},
        description="Get authenticated user profile"
    )
    def get(self, request):
        """Get user profile"""
        serializer = AdminProfileSerializer(request.user)
        return Response({
            'success': True,
            'message': 'Profile retrieved successfully',
            'user': serializer.data
        }, status=status.HTTP_200_OK)
    
    @extend_schema(
        request=AdminProfileSerializer,
        responses={200: AdminProfileSerializer},
        description="Update authenticated user profile"
    )
    def put(self, request):
        """Update user profile"""
        user = request.user
        data = request.data.copy()
        
        # Don't allow email change for now
        if 'email' in data and data['email'] != user.email:
            return Response({
                'success': False,
                'message': 'Email cannot be changed'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = AdminProfileSerializer(user, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Profile updated successfully',
                'user': serializer.data
            }, status=status.HTTP_200_OK)
        
        return Response({
            'success': False,
            'message': 'Update failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class AdminLoginView(APIView):
    """Login for admin users"""
    permission_classes = [AllowAny]
    serializer_class = AdminLoginSerializer
    
    @extend_schema(
        request=AdminLoginSerializer,
        responses={200: AdminProfileSerializer},
        description="Admin login - returns JWT access and refresh tokens"
    )
    def post(self, request):
        """Admin login"""
        serializer = AdminLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Generate JWT tokens
            jwt_tokens = get_tokens_for_user(user)
            
            # Update last login
            from django.utils import timezone
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            
            return Response({
                'success': True,
                'message': 'Admin login successful',
                'user': {
                    'user_id': str(user.id),
                    'email': user.email,
                    'full_name': user.full_name,
                    'avatar_url': user.avatar_url
                },
                'token': jwt_tokens
            }, status=status.HTTP_200_OK)
        
        return Response({
            'success': False,
            'message': 'Login failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class AdminOnboardingView(APIView):
    """Admin onboarding - creates initial workspace"""
    permission_classes = [IsAuthenticated]
    serializer_class = AdminOnboardingSerializer
    
    @extend_schema(
        request=AdminOnboardingSerializer,
        description="Create workspace during admin onboarding"
    )
    def post(self, request):
        """Create workspace during onboarding"""
        serializer = AdminOnboardingSerializer(data=request.data)
        if serializer.is_valid():
            # Check if user already has a workspace
            if request.user.owned_workspaces.exists():
                return Response({
                    'success': False,
                    'message': 'Admin can create workspace only once during onboarding. Use workspace creation endpoint for additional workspaces.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Create workspace
            workspace = Workspace.objects.create(
                name=serializer.validated_data['workspace_name'],
                description=serializer.validated_data.get('workspace_description', ''),
                admin=request.user,
                email=serializer.validated_data['company_email'],
                phone=serializer.validated_data.get('company_phone', ''),
                address=serializer.validated_data.get('company_address', ''),
                city=serializer.validated_data.get('company_city', ''),
                country=serializer.validated_data.get('company_country', '')
            )
            
            from workspace.serializers.workspace import WorkspaceDetailSerializer
            workspace_serializer = WorkspaceDetailSerializer(workspace)
            
            return Response({
                'success': True,
                'message': 'Onboarding successful. Workspace created!',
                'workspace': workspace_serializer.data,
                'next_steps': [
                    'Create branches for your workspace',
                    'Add spaces/rooms within branches',
                    'Invite team members to manage the workspace',
                    'Set up pricing and availability'
                ]
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'message': 'Onboarding failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class AdminOnboardingStatusView(APIView):
    """Check admin onboarding status"""
    permission_classes = [IsAuthenticated]
    serializer_class = OnboardingStatusSerializer
    
    @extend_schema(
        responses={200: OnboardingStatusSerializer},
        description="Get admin onboarding progress and completion status"
    )
    def get(self, request):
        """Get onboarding status"""
        workspace = request.user.owned_workspaces.first()
        
        onboarding_data = {
            'is_registered': True,
            'has_workspace': bool(workspace),
            'completed_steps': [],
            'pending_steps': [
                'Create workspace',
                'Create branches',
                'Create spaces',
                'Invite team members'
            ]
        }
        
        if workspace:
            onboarding_data['workspace'] = {
                'workspace_id': str(workspace.id),
                'name': workspace.name,
                'branch_count': workspace.branches.count(),
                'member_count': workspace.members.count() + 1  # +1 for admin
            }
            onboarding_data['completed_steps'].append('Create workspace')
            onboarding_data['pending_steps'].remove('Create workspace')
            
            if workspace.branches.exists():
                onboarding_data['completed_steps'].append('Create branches')
                onboarding_data['pending_steps'].remove('Create branches')
            
            if workspace.branches.filter(spaces__isnull=False).exists():
                onboarding_data['completed_steps'].append('Create spaces')
                onboarding_data['pending_steps'].remove('Create spaces')
            
            if workspace.members.exists():
                onboarding_data['completed_steps'].append('Invite team members')
                onboarding_data['pending_steps'].remove('Invite team members')
        
        progress_percentage = (len(onboarding_data['completed_steps']) / 4) * 100
        
        return Response({
            'success': True,
            'message': 'Onboarding status retrieved',
            'onboarding': onboarding_data,
            'progress_percentage': progress_percentage
        }, status=status.HTTP_200_OK)


class InviteMemberView(APIView):
    """Invite a member to workspace"""
    permission_classes = [IsAuthenticated]
    serializer_class = InviteTokenSerializer
    
    @extend_schema(
        request=InviteTokenSerializer,
        description="Invite an existing user to join workspace"
    )
    def post(self, request, workspace_id):
        """Invite member to workspace"""
        workspace = get_object_or_404(Workspace, id=workspace_id)
        
        # Check if user is workspace admin
        if not check_workspace_admin(request.user, workspace):
            return Response({
                'success': False,
                'message': 'Only workspace admin can invite members'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = InviteTokenSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            role = serializer.validated_data['role']
            
            # Check if user exists
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'User with this email does not exist. They need to register first.'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Check if already a member
            if WorkspaceUser.objects.filter(workspace=workspace, user=user).exists():
                return Response({
                    'success': False,
                    'message': 'User is already a member of this workspace'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Add user to workspace
            member = WorkspaceUser.objects.create(
                workspace=workspace,
                user=user,
                role=role,
                is_active=True
            )
            
            return Response({
                'success': True,
                'message': f'User invited as {role} successfully',
                'member': WorkspaceMemberSerializer(member).data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'message': 'Invitation failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class ListWorkspaceMembersView(APIView):
    """List members of a workspace"""
    permission_classes = [IsAuthenticated]
    serializer_class = WorkspaceMemberSerializer
    
    @extend_schema(
        responses={200: WorkspaceMemberSerializer(many=True)},
        description="Get all active members of a workspace"
    )
    def get(self, request, workspace_id):
        """Get workspace members"""
        workspace = get_object_or_404(Workspace, id=workspace_id)
        
        # Check if user has access
        if not check_workspace_member(request.user, workspace):
            return Response({
                'success': False,
                'message': 'You do not have permission to view workspace members'
            }, status=status.HTTP_403_FORBIDDEN)
        
        members = workspace.members.filter(is_active=True)
        serializer = WorkspaceMemberSerializer(members, many=True)
        
        # Add admin info
        admin_info = {
            'id': str(workspace.admin.id),
            'email': workspace.admin.email,
            'full_name': workspace.admin.full_name,
            'role': 'admin',
            'joined_at': workspace.created_at
        }
        
        return Response({
            'success': True,
            'count': members.count() + 1,  # +1 for admin
            'admin': admin_info,
            'members': serializer.data
        }, status=status.HTTP_200_OK)


class WorkspaceMemberDetailView(APIView):
    """Get, update, remove workspace member"""
    permission_classes = [IsAuthenticated]
    serializer_class = WorkspaceMemberDetailSerializer
    
    @extend_schema(
        responses={200: WorkspaceMemberDetailSerializer},
        description="Get details of a specific workspace member"
    )
    def get(self, request, workspace_id, member_id):
        """Get member details"""
        workspace = get_object_or_404(Workspace, id=workspace_id)
        
        # Check if user has access
        if not check_workspace_member(request.user, workspace):
            return Response({
                'success': False,
                'message': 'You do not have permission to view workspace members'
            }, status=status.HTTP_403_FORBIDDEN)
        
        member = get_object_or_404(WorkspaceUser, id=member_id, workspace=workspace)
        serializer = WorkspaceMemberDetailSerializer(member)
        
        return Response({
            'success': True,
            'member': serializer.data
        }, status=status.HTTP_200_OK)
    
    @extend_schema(
        request=WorkspaceMemberDetailSerializer,
        responses={200: WorkspaceMemberDetailSerializer},
        description="Update member role or status"
    )
    def put(self, request, workspace_id, member_id):
        """Update member role"""
        workspace = get_object_or_404(Workspace, id=workspace_id)
        
        # Check if user is workspace admin
        if not check_workspace_admin(request.user, workspace):
            return Response({
                'success': False,
                'message': 'Only workspace admin can update member roles'
            }, status=status.HTTP_403_FORBIDDEN)
        
        member = get_object_or_404(WorkspaceUser, id=member_id, workspace=workspace)
        
        # Don't allow changing admin
        if member.user == workspace.admin:
            return Response({
                'success': False,
                'message': 'Cannot change admin role'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Update role if provided
        if 'role' in request.data:
            role = request.data['role']
            valid_roles = ['manager', 'staff', 'user']
            if role not in valid_roles:
                return Response({
                    'success': False,
                    'message': f'Invalid role. Must be one of: {", ".join(valid_roles)}'
                }, status=status.HTTP_400_BAD_REQUEST)
            member.role = role
        
        # Update is_active if provided
        if 'is_active' in request.data:
            member.is_active = request.data['is_active']
        
        member.save()
        serializer = WorkspaceMemberDetailSerializer(member)
        
        return Response({
            'success': True,
            'message': 'Member updated successfully',
            'member': serializer.data
        }, status=status.HTTP_200_OK)
    
    @extend_schema(
        description="Remove member from workspace"
    )
    def delete(self, request, workspace_id, member_id):
        """Remove member from workspace"""
        workspace = get_object_or_404(Workspace, id=workspace_id)
        
        # Check if user is workspace admin
        if not check_workspace_admin(request.user, workspace):
            return Response({
                'success': False,
                'message': 'Only workspace admin can remove members'
            }, status=status.HTTP_403_FORBIDDEN)
        
        member = get_object_or_404(WorkspaceUser, id=member_id, workspace=workspace)
        
        # Don't allow removing admin
        if member.user == workspace.admin:
            return Response({
                'success': False,
                'message': 'Cannot remove workspace admin'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        member.delete()
        
        return Response({
            'success': True,
            'message': 'Member removed from workspace'
        }, status=status.HTTP_200_OK)


class SelfSignUpInviteView(APIView):
    """Allow user to sign up and join workspace via invite link"""
    permission_classes = [AllowAny]
    serializer_class = MemberSignUpSerializer
    
    @extend_schema(
        request=MemberSignUpSerializer,
        description="Register as a new user and join workspace via invite link"
    )
    def post(self, request, invite_token):
        """Register and join workspace"""
        # For now, invite_token is workspace_id
        # In production, use proper token generation/validation
        
        try:
            workspace = Workspace.objects.get(id=invite_token)
        except Workspace.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Invalid invite link'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = MemberSignUpSerializer(data=request.data)
        if serializer.is_valid():
            # Check if email already invited
            email = serializer.validated_data['email']
            try:
                user = User.objects.get(email=email)
                # User exists, add to workspace if not already member
                if WorkspaceUser.objects.filter(workspace=workspace, user=user).exists():
                    return Response({
                        'success': False,
                        'message': 'User is already a member of this workspace'
                    }, status=status.HTTP_400_BAD_REQUEST)
            except User.DoesNotExist:
                # Create new user
                user = User.objects.create(
                    full_name=serializer.validated_data['full_name'],
                    email=email
                )
                user.set_password(serializer.validated_data['password'])
                user.save()
            
            # Add user to workspace
            member = WorkspaceUser.objects.create(
                workspace=workspace,
                user=user,
                role='user',
                is_active=True
            )
            
            # Generate JWT tokens
            jwt_tokens = get_tokens_for_user(user)
            
            return Response({
                'success': True,
                'message': 'Sign up and workspace join successful',
                'user': {
                    'user_id': str(user.id),
                    'email': user.email,
                    'full_name': user.full_name,
                    'avatar_url': user.avatar_url
                },
                'workspace': {
                    'workspace_id': str(workspace.id),
                    'name': workspace.name
                },
                'token': jwt_tokens
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'message': 'Sign up failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
