from rest_framework import serializers
from user.models import User

class GoogleAuthSerializer(serializers.Serializer):
    code = serializers.CharField(required=True)