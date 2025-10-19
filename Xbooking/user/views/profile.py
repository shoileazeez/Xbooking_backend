from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from user.serializers import ProfileSerializer
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProfileSerializer

    @extend_schema(
        responses={200: ProfileSerializer},
        description="Get authenticated user profile"
    )
    def get(self, request):
        serializer = ProfileSerializer(request.user)
        return Response(serializer.data)
