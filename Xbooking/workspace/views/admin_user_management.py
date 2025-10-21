"""
Admin User Management Views for Workspace Managers/Staff
Allows admins to:
- Reset staff/manager passwords (send temporary password via email)
- Revoke user account access
- Delete user account
- Force password change on next login
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db import transaction
import secrets
import string

from workspace.models import Workspace, WorkspaceUser
from user.models import User
from notifications.tasks import send_notification
from workspace.serializers.admin_user_management import (
    AdminResetPasswordSerializer,
    AdminForcePasswordChangeSerializer,
    AdminRevokeAccessSerializer,
    AdminRestoreAccessSerializer,
    AdminDeleteAccountSerializer,
    AdminUserStatusResponseSerializer
)


class AdminResetStaffPasswordView(APIView):
    """
    Admin endpoint to reset staff/manager password
    Generates temporary password and sends via email
    Forces user to change password on next login
    """
    
    permission_classes = [IsAuthenticated]
    serializer_class = AdminResetPasswordSerializer
    
    @transaction.atomic
    def post(self, request, workspace_id, user_id):
        """
        POST /api/workspaces/{workspace_id}/admin/users/{user_id}/reset-password/
        
        Request body (optional):
        {
            "send_email": true  // whether to send email with temporary password
        }
        
        Response:
        {
            "success": true,
            "message": "Password reset successfully",
            "temporary_password": "aBc123XyZ!@#",  // only shown if send_email=false
            "email_sent": true
        }
        """
        try:
            workspace = Workspace.objects.get(id=workspace_id)
        except Workspace.DoesNotExist:
            return Response(
                {'error': 'Workspace not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if requester is workspace admin
        admin_member = WorkspaceUser.objects.filter(
            workspace=workspace,
            user=request.user,
            role='admin',
            is_active=True
        ).first()
        
        if not admin_member:
            return Response(
                {'error': 'Only workspace admins can reset passwords'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get the user to reset password for
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if target user is staff/manager in workspace (not admin, not owner)
        target_member = WorkspaceUser.objects.filter(
            workspace=workspace,
            user=target_user,
            role__in=['manager', 'staff'],  # Only allow reset for staff/manager
            is_active=True
        ).first()
        
        if not target_member:
            return Response(
                {'error': 'Can only reset passwords for staff and managers'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Generate temporary password
        alphabet = string.ascii_letters + string.digits + '!@#$%^&*'
        temporary_password = ''.join(secrets.choice(alphabet) for _ in range(12))
        
        # Update user
        target_user.set_password(temporary_password)
        target_user.force_password_change = True  # Force change on next login
        target_user.save()
        
        # Determine if we should send email
        send_email = request.data.get('send_email', True)
        
        response_data = {
            'success': True,
            'message': 'Password reset successfully',
            'email_sent': False
        }
        
        if send_email:
            # Send email with temporary password
            send_notification.delay(
                user_id=str(target_user.id),
                notification_type='password_reset',
                title='Password Reset by Administrator',
                message=f'Your password has been reset by {request.user.full_name}. Use the temporary password below to login and set a new password.',
                channels=['email'],
                workspace_id=str(workspace.id),
                extra_data={
                    'temporary_password': temporary_password,
                    'workspace_name': workspace.name,
                    'admin_name': request.user.full_name
                }
            )
            response_data['email_sent'] = True
        else:
            # Return temporary password only if email not sent
            response_data['temporary_password'] = temporary_password
        
        return Response(response_data, status=status.HTTP_200_OK)


class AdminForcePasswordChangeView(APIView):
    """
    Admin endpoint to force a staff/manager to change password on next login
    """
    
    permission_classes = [IsAuthenticated]
    serializer_class = AdminForcePasswordChangeSerializer
    
    def post(self, request, workspace_id, user_id):
        """
        POST /api/workspaces/{workspace_id}/admin/users/{user_id}/force-password-change/
        
        Forces user to change password on next login attempt
        """
        try:
            workspace = Workspace.objects.get(id=workspace_id)
        except Workspace.DoesNotExist:
            return Response(
                {'error': 'Workspace not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if requester is workspace admin
        admin_member = WorkspaceUser.objects.filter(
            workspace=workspace,
            user=request.user,
            role='admin',
            is_active=True
        ).first()
        
        if not admin_member:
            return Response(
                {'error': 'Only workspace admins can force password changes'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get the user
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if target user is staff/manager in workspace
        target_member = WorkspaceUser.objects.filter(
            workspace=workspace,
            user=target_user,
            role__in=['manager', 'staff'],
            is_active=True
        ).first()
        
        if not target_member:
            return Response(
                {'error': 'Can only force password change for staff and managers'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Set force password change flag
        target_user.force_password_change = True
        target_user.save()
        
        # Send notification
        send_notification.delay(
            user_id=str(target_user.id),
            notification_type='force_password_change',
            title='Password Change Required',
            message='Your administrator requires you to change your password. Please update it on your next login.',
            workspace_id=str(workspace.id)
        )
        
        return Response(
            {
                'success': True,
                'message': 'User will be required to change password on next login',
                'user_email': target_user.email
            },
            status=status.HTTP_200_OK
        )


class AdminRevokeUserAccessView(APIView):
    """
    Admin endpoint to revoke user access to workspace
    Deactivates the WorkspaceUser membership
    User can no longer access workspace but account remains in database
    """
    
    permission_classes = [IsAuthenticated]
    serializer_class = AdminRevokeAccessSerializer
    
    @transaction.atomic
    def post(self, request, workspace_id, user_id):
        """
        POST /api/workspaces/{workspace_id}/admin/users/{user_id}/revoke-access/
        
        Request body (optional):
        {
            "reason": "Employee left company"  // optional reason for audit trail
        }
        
        Response:
        {
            "success": true,
            "message": "User access revoked",
            "user_email": "user@example.com",
            "workspace_name": "My Workspace"
        }
        """
        try:
            workspace = Workspace.objects.get(id=workspace_id)
        except Workspace.DoesNotExist:
            return Response(
                {'error': 'Workspace not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if requester is workspace admin
        admin_member = WorkspaceUser.objects.filter(
            workspace=workspace,
            user=request.user,
            role='admin',
            is_active=True
        ).first()
        
        if not admin_member:
            return Response(
                {'error': 'Only workspace admins can revoke access'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get the user
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get workspace membership
        target_member = WorkspaceUser.objects.filter(
            workspace=workspace,
            user=target_user
        ).first()
        
        if not target_member:
            return Response(
                {'error': 'User is not a member of this workspace'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Cannot revoke admin access
        if target_member.role == 'admin':
            return Response(
                {'error': 'Cannot revoke access for workspace admins'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Revoke access
        target_member.is_active = False
        target_member.save()
        
        # Get reason if provided
        reason = request.data.get('reason', 'No reason provided')
        
        # Send notification to revoked user
        send_notification.delay(
            user_id=str(target_user.id),
            notification_type='access_revoked',
            title='Access Revoked',
            message=f'Your access to workspace "{workspace.name}" has been revoked. Reason: {reason}',
            workspace_id=str(workspace.id)
        )
        
        return Response(
            {
                'success': True,
                'message': 'User access revoked',
                'user_email': target_user.email,
                'workspace_name': workspace.name,
                'revoked_at': timezone.now().isoformat()
            },
            status=status.HTTP_200_OK
        )


class AdminRestoreUserAccessView(APIView):
    """
    Admin endpoint to restore user access to workspace
    Reactivates the WorkspaceUser membership
    """
    
    permission_classes = [IsAuthenticated]
    serializer_class = AdminRestoreAccessSerializer
    
    @transaction.atomic
    def post(self, request, workspace_id, user_id):
        """
        POST /api/workspaces/{workspace_id}/admin/users/{user_id}/restore-access/
        
        Restores user access that was previously revoked
        """
        try:
            workspace = Workspace.objects.get(id=workspace_id)
        except Workspace.DoesNotExist:
            return Response(
                {'error': 'Workspace not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if requester is workspace admin
        admin_member = WorkspaceUser.objects.filter(
            workspace=workspace,
            user=request.user,
            role='admin',
            is_active=True
        ).first()
        
        if not admin_member:
            return Response(
                {'error': 'Only workspace admins can restore access'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get the user
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get workspace membership
        target_member = WorkspaceUser.objects.filter(
            workspace=workspace,
            user=target_user
        ).first()
        
        if not target_member:
            return Response(
                {'error': 'User is not a member of this workspace'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Restore access
        target_member.is_active = True
        target_member.save()
        
        # Send notification
        send_notification.delay(
            user_id=str(target_user.id),
            notification_type='access_restored',
            title='Access Restored',
            message=f'Your access to workspace "{workspace.name}" has been restored.',
            workspace_id=str(workspace.id)
        )
        
        return Response(
            {
                'success': True,
                'message': 'User access restored',
                'user_email': target_user.email,
                'workspace_name': workspace.name
            },
            status=status.HTTP_200_OK
        )


class AdminDeleteUserAccountView(APIView):
    """
    Admin endpoint to permanently delete user account
    CAUTION: This is destructive and cannot be undone
    Completely removes user from system and all workspaces
    """
    
    permission_classes = [IsAuthenticated]
    serializer_class = AdminDeleteAccountSerializer
    
    @transaction.atomic
    def post(self, request, workspace_id, user_id):
        """
        POST /api/workspaces/{workspace_id}/admin/users/{user_id}/delete-account/
        
        Request body (required):
        {
            "confirm": true,
            "reason": "Account no longer needed"
        }
        
        CAUTION: This permanently deletes the user account and cannot be undone
        """
        try:
            workspace = Workspace.objects.get(id=workspace_id)
        except Workspace.DoesNotExist:
            return Response(
                {'error': 'Workspace not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if requester is workspace admin
        admin_member = WorkspaceUser.objects.filter(
            workspace=workspace,
            user=request.user,
            role='admin',
            is_active=True
        ).first()
        
        if not admin_member:
            return Response(
                {'error': 'Only workspace admins can delete user accounts'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Require explicit confirmation
        if not request.data.get('confirm'):
            return Response(
                {'error': 'Account deletion requires explicit confirmation. Set "confirm": true in request body.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the user
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if target user is staff/manager (cannot delete admin)
        target_member = WorkspaceUser.objects.filter(
            workspace=workspace,
            user=target_user
        ).first()
        
        if target_member and target_member.role == 'admin':
            return Response(
                {'error': 'Cannot delete workspace admin accounts'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Store user info for response
        user_email = target_user.email
        user_name = target_user.full_name
        
        # Delete user (cascade will remove from all workspaces)
        target_user.delete()
        
        return Response(
            {
                'success': True,
                'message': 'User account permanently deleted',
                'deleted_user': {
                    'email': user_email,
                    'name': user_name
                },
                'deleted_at': timezone.now().isoformat(),
                'warning': 'This action cannot be undone. The user account has been permanently removed from the system.'
            },
            status=status.HTTP_200_OK
        )
