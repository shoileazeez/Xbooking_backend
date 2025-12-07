from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from user.serializers import ProfileSerializer
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema
from django.db import transaction


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProfileSerializer

    @extend_schema(
        responses={200: ProfileSerializer},
        description="Get authenticated user profile",
        tags=["User Profile"]
    )
    def get(self, request):
        """Get user profile"""
        serializer = ProfileSerializer(request.user)
        return Response(serializer.data)
    
    @extend_schema(
        request=ProfileSerializer,
        responses={200: ProfileSerializer},
        description="Update user profile (full_name, phone, avatar_url). Email is read-only.",
        tags=["User Profile"]
    )
    @transaction.atomic
    def patch(self, request):
        """Update user profile"""
        user = request.user
        serializer = ProfileSerializer(user, data=request.data, partial=True)
        
        if serializer.is_valid():
            # Ensure email cannot be changed
            if 'email' in request.data and request.data['email'] != user.email:
                return Response(
                    {"error": "Email cannot be changed"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
