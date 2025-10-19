from rest_framework import serializers
from user.models import User

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "full_name", "email", "avatar_url", "date_joined", "last_login"]
        read_only_fields = ["id", "email", "date_joined", "last_login"]
