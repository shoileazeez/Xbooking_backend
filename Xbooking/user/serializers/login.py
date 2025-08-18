from rest_framework import serializers
from rest_framework.serializers import ValidationError
from user.validators import authenticate_user
# from rest_framework.validators import ValidationError

class LoginSerializers(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(max_length = 255)
    
    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")
        
        user = authenticate_user(email, password)
        if not user:
            raise ValidationError("Invalid email or password")
        
        attrs['user'] = user
        return attrs
