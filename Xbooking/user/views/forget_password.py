from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from user.serializers import ForgetPasswordSerializer
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema


class ForgetPasswordView(APIView):
    """
    API endpoint for requesting password reset.
    
    POST /api/user/forget-password/
    {
        "email": "user@example.com"
    }
    """
    permission_classes = [AllowAny]
    serializer_class = ForgetPasswordSerializer
    
    @extend_schema(
        request=ForgetPasswordSerializer,
        description="Request password reset - sends reset link to email"
    )
    def post(self, request):
        """
        Handle password reset request
        """
        serializer = ForgetPasswordSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                result = serializer.save()
                return Response(result, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({
                    'success': False,
                    'message': 'Failed to process password reset request',
                    'errors': {'non_field_errors': [str(e)]}
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'success': False,
            'message': 'Invalid data provided',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
