"""
Admin User Management ViewSet for v1 API
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view
import secrets
import string

from core.responses import SuccessResponse, ErrorResponse
from core.permissions import IsWorkspaceAdmin
from core.services import EventBus, Event, EventTypes
from workspace.models import Workspace, WorkspaceUser
from user.models import User
from workspace.serializers.v1.admin import (
    AdminResetPasswordSerializer,
    AdminUserActionSerializer,
    AdminUserDetailSerializer
)


@extend_schema_view(
    list=extend_schema(description="List workspace users for admin management"),
    retrieve=extend_schema(description="Get user details"),
)
class AdminUserManagementViewSet(viewsets.ReadOnlyModelViewSet):
    """Admin user management for workspace"""
    serializer_class = AdminUserDetailSerializer
    permission_classes = [IsAuthenticated, IsWorkspaceAdmin]
    
    def get_queryset(self):
        workspace_id = self.kwargs.get('workspace_id')
        return WorkspaceUser.objects.filter(
            workspace_id=workspace_id,
            is_active=True
        ).select_related('user', 'workspace')
    
    @extend_schema(
        request=AdminResetPasswordSerializer,
        responses={200: dict},
        description="Reset user password and send temporary password via email"
    )
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def reset_password(self, request, workspace_id=None, pk=None):
        """Reset staff/manager password"""
        workspace_user = self.get_object()
        
        if workspace_user.role not in ['manager', 'staff']:
            return ErrorResponse(
                message="Can only reset passwords for staff and managers",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Generate temporary password
        alphabet = string.ascii_letters + string.digits + '!@#$%^&*'
        temporary_password = ''.join(secrets.choice(alphabet) for _ in range(12))
        
        target_user = workspace_user.user
        target_user.set_password(temporary_password)
        target_user.force_password_change = True
        target_user.save()
        
        send_email = request.data.get('send_email', True)
        
        if send_email:
            # Publish event for notification service to handle
            event = Event(
                event_type=EventTypes.EMAIL_SENT,
                data={
                    'user_id': str(target_user.id),
                    'notification_type': 'password_reset',
                    'title': 'Password Reset by Administrator',
                    'message': 'Your password has been reset. Use the temporary password to login.',
                    'channels': ['email'],
                    'workspace_id': str(workspace_user.workspace_id),
                    'temporary_password': temporary_password,
                    'admin_name': request.user.full_name
                },
                source_module='workspace'
            )
            EventBus.publish(event)
            
            return SuccessResponse(
                message="Password reset successfully. Email will be sent to user.",
                data={'email_sent': True}
            )
        
        return SuccessResponse(
            message="Password reset successfully",
            data={'temporary_password': temporary_password, 'email_sent': False}
        )
    
    @extend_schema(
        request=AdminUserActionSerializer,
        responses={200: dict},
        description="Force user to change password on next login"
    )
    @action(detail=True, methods=['post'])
    def force_password_change(self, request, workspace_id=None, pk=None):
        """Force password change on next login"""
        workspace_user = self.get_object()
        
        if workspace_user.role not in ['manager', 'staff']:
            return ErrorResponse(
                message="Can only force password change for staff and managers",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        target_user = workspace_user.user
        target_user.force_password_change = True
        target_user.save()
        
        # Publish event for notification service
        event = Event(
            event_type=EventTypes.EMAIL_SENT,
            data={
                'user_id': str(target_user.id),
                'notification_type': 'force_password_change',
                'title': 'Password Change Required',
                'message': 'Your administrator requires you to change your password.',
                'workspace_id': str(workspace_user.workspace_id),
                'channels': ['email']
            },
            source_module='workspace'
        )
        EventBus.publish(event)
        
        return SuccessResponse(message="User will be required to change password on next login")
    
    @extend_schema(
        request=AdminUserActionSerializer,
        responses={200: dict},
        description="Revoke user access to workspace"
    )
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def revoke_access(self, request, workspace_id=None, pk=None):
        """Revoke user access"""
        workspace_user = self.get_object()
        
        if workspace_user.role == 'admin':
            return ErrorResponse(
                message="Cannot revoke admin access",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        workspace_user.is_active = False
        workspace_user.save()
        
        return SuccessResponse(message="User access revoked successfully")
    
    @extend_schema(
        request=AdminUserActionSerializer,
        responses={200: dict},
        description="Restore user access to workspace"
    )
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def restore_access(self, request, workspace_id=None, pk=None):
        """Restore user access"""
        workspace_user = WorkspaceUser.objects.filter(
            workspace_id=workspace_id,
            id=pk
        ).first()
        
        if not workspace_user:
            return ErrorResponse(message="User not found", status_code=status.HTTP_404_NOT_FOUND)
        
        workspace_user.is_active = True
        workspace_user.save()
        
        return SuccessResponse(message="User access restored successfully")
