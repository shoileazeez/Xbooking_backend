"""
User password change views
Includes forced password change on first login after admin reset
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db import transaction
from user.models import User
from user.views.password_change_serializers import (
    ChangePasswordSerializer,
    ForcedPasswordChangeSerializer,
    CheckPasswordChangeRequiredSerializer,
    PasswordChangeResponseSerializer
)


class ChangePasswordView(APIView):
    """
    User endpoint to change their own password
    If force_password_change is True, user MUST change password
    """
    
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer
    
    @transaction.atomic
    def post(self, request):
        """
        POST /api/users/change-password/
        
        Request body:
        {
            "current_password": "old_password_here",
            "new_password": "new_password_here"
        }
        
        Response:
        {
            "success": true,
            "message": "Password changed successfully",
            "force_password_change": false
        }
        """
        user = request.user
        
        # Validate request data
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')
        
        if not current_password or not new_password:
            return Response(
                {'error': 'current_password and new_password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify current password
        if not user.check_password(current_password):
            return Response(
                {'error': 'Current password is incorrect'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Validate new password strength
        if len(new_password) < 8:
            return Response(
                {'error': 'Password must be at least 8 characters long'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not any(char.isdigit() for char in new_password):
            return Response(
                {'error': 'Password must contain at least one number'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not any(char.isupper() for char in new_password):
            return Response(
                {'error': 'Password must contain at least one uppercase letter'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update password
        user.set_password(new_password)
        user.force_password_change = False  # Clear forced password change flag
        user.save()
        
        return Response(
            {
                'success': True,
                'message': 'Password changed successfully',
                'force_password_change': False
            },
            status=status.HTTP_200_OK
        )


class CheckPasswordChangeRequiredView(APIView):
    """
    GET endpoint to check if user needs to change password
    Useful for frontend to redirect to password change page on login
    """
    
    permission_classes = [IsAuthenticated]
    serializer_class = CheckPasswordChangeRequiredSerializer
    
    def get(self, request):
        """
        GET /api/users/password-change-required/
        
        Response:
        {
            "force_password_change": true,
            "message": "You must change your password before continuing",
            "reason": "Password was reset by administrator"
        }
        """
        user = request.user
        
        return Response(
            {
                'force_password_change': user.force_password_change,
                'message': 'You must change your password before continuing' if user.force_password_change else 'No password change required',
                'reason': 'Password was reset by administrator' if user.force_password_change else None
            },
            status=status.HTTP_200_OK
        )


class ForcedPasswordChangeView(APIView):
    """
    Special endpoint for users with force_password_change flag
    Only accepts new password (no current password verification needed)
    """
    
    permission_classes = [IsAuthenticated]
    serializer_class = ForcedPasswordChangeSerializer
    
    @transaction.atomic
    def post(self, request):
        """
        POST /api/users/forced-password-change/
        
        Used when admin resets password and user logs in with temporary password
        Only requires new password
        
        Request body:
        {
            "new_password": "new_strong_password"
        }
        
        Response:
        {
            "success": true,
            "message": "Password changed successfully",
            "force_password_change": false
        }
        """
        user = request.user
        
        # Check if user actually needs forced password change
        if not user.force_password_change:
            return Response(
                {'error': 'You are not required to change your password'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        new_password = request.data.get('new_password')
        
        if not new_password:
            return Response(
                {'error': 'new_password is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate password strength
        if len(new_password) < 8:
            return Response(
                {'error': 'Password must be at least 8 characters long'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not any(char.isdigit() for char in new_password):
            return Response(
                {'error': 'Password must contain at least one number'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not any(char.isupper() for char in new_password):
            return Response(
                {'error': 'Password must contain at least one uppercase letter'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update password
        user.set_password(new_password)
        user.force_password_change = False  # Clear the flag
        user.save()
        
        return Response(
            {
                'success': True,
                'message': 'Password changed successfully. You can now access all features.',
                'force_password_change': False
            },
            status=status.HTTP_200_OK
        )
