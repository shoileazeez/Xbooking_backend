from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from user.serializers import PasswordResetConfirmSerializer


class PasswordResetConfirmView(APIView):
    """
    API endpoint for confirming password reset with verification code.
    
    POST /api/user/password-reset-confirm/
    {
        "email": "user@example.com",
        "verification_code": "123456",
        "new_password": "NewSecurePass123!",
        "confirm_password": "NewSecurePass123!"
    }
    """
    
    def post(self, request):
        """
        Handle password reset confirmation
        """
        serializer = PasswordResetConfirmSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                result = serializer.save()
                return Response(result, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({
                    'success': False,
                    'message': 'Failed to reset password',
                    'errors': {'non_field_errors': [str(e)]}
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'success': False,
            'message': 'Invalid data provided',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
