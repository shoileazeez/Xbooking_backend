from rest_framework.validators import ValidationError

def password_validation(password, confirm_password):
    if len(password) < 8 :
        raise ValidationError("password must be at least 8 character long")
    if password != confirm_password:
        raise ValidationError("Password do not match")
    if not any(char.isalpha() for char in password):
        raise ValidationError("password must include at least one character")
    if not any(char.isupper() for char in password):
        raise ValidationError("password must contain at least one uppercase")
    if not any (char.islower() for char in password):
        raise ValidationError("password must contain at least one lowercase")
    if not any (char.isdigit() for char in password):
        raise ValidationError("password must contain at least one digit")
    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not any (char in special_chars for char in password):
        raise ValidationError("password must include at least one special character")
    return password