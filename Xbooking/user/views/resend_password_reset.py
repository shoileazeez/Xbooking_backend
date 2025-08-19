from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from user.serializers import ResendPasswordResetSerializer


class ResendPasswordResetView(APIView):
    """
    API endpoint for resending password reset verification code.
    
    POST /api/user/resend-password-reset/
    {
        "email": "user@example.com"
    }
    """
    
    def post(self, request):
        """
        Handle resend password reset request
        """
        serializer = ResendPasswordResetSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                result = serializer.save()
                return Response(result, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({
                    'success': False,
                    'message': 'Failed to resend verification code',
                    'errors': {'non_field_errors': [str(e)]}
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'success': False,
            'message': 'Invalid data provided',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
