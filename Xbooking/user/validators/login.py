from user.models import User

def authenticate_user(email, password):
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return None
    
    if user.check_password(password):
        return user
    return None