from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.contrib.auth.hashers import make_password, check_password
import uuid
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    full_name = models.CharField(max_length=200, null=False, blank=False)
    email = models.EmailField(unique=True, blank=False)
    # password and last_login are provided by AbstractBaseUser
    
    avatar_url = models.URLField(blank=True, null=True)
    google_id = models.CharField(max_length=255, blank=True, null=True)
    date_joined = models.DateTimeField(_("date joined"), default=timezone.now)
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    force_password_change = models.BooleanField(default=False, help_text="Force user to change password on next login")
    
    objects = CustomUserManager()
    
    # Required fields for custom user model
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']
    
    def __str__(self):
        return self.full_name or self.email
    
    # AbstractBaseUser provides set_password, check_password, is_anonymous, is_authenticated


class VerificationCode(models.Model):
    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(_("created_at"), default=timezone.now)
    is_used = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Verification code for {self.user.email}"
    
    class Meta:
        ordering = ['-created_at']