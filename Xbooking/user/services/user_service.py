"""
User Service Layer
Handles user business logic and event publishing
"""
import secrets
import string
from typing import Optional, Tuple
from django.utils import timezone
from django.db import transaction

from core.services import EventBus, Event, EventTypes
from core.cache import CacheService
from user.validators.business_email import is_business_email, get_email_domain


def generate_random_password(length=12):
    """Generate a secure random password"""
    alphabet = string.ascii_letters + string.digits + '!@#$%^&*'
    return ''.join(secrets.choice(alphabet) for _ in range(length))


class UserService:
    """Service class for user business logic"""
    
    @staticmethod
    def create_user(user, created_by=None) -> None:
        """
        Handle user creation business logic and publish event.
        
        Args:
            user: The created user instance
            created_by: User who created this account (for workspace invites)
        """
        event = Event(
            event_type=EventTypes.USER_REGISTERED,
            data={
                'user_id': str(user.id),
                'email': user.email,
                'full_name': user.full_name,
                'role': user.role,
                'is_business_email': user.is_business_email,
                'created_by_id': str(created_by.id) if created_by else None,
                'force_password_change': user.force_password_change,
                'created_at': timezone.now().isoformat(),
            },
            source_module='user'
        )
        EventBus.publish(event)
    
    @staticmethod
    def update_user(user, updated_by=None) -> None:
        """Handle user update business logic"""
        CacheService.delete(user.get_cache_key())
        
        event = Event(
            event_type=EventTypes.USER_UPDATED,
            data={
                'user_id': str(user.id),
                'email': user.email,
                'updated_by_id': str(updated_by.id) if updated_by else str(user.id),
                'updated_at': timezone.now().isoformat(),
            },
            source_module='user'
        )
        EventBus.publish(event)
    
    @staticmethod
    @transaction.atomic
    def create_or_get_user_for_workspace_invite(email: str, full_name: str, created_by) -> Tuple:
        """
        Create a new user for workspace invite or get existing user.
        Sets random password and forces password change for new users only.
        
        Args:
            email: User email
            full_name: User full name
            created_by: Admin who is inviting the user
            
        Returns:
            tuple: (user, password, is_new)
                - user: User instance
                - password: Temporary password (None if user already exists)
                - is_new: True if user was just created
        """
        from user.models import User, UserRole
        
        # Check if user exists
        user = User.objects.filter(email=email).first()
        
        if user:
            # User exists, return without password
            return user, None, False
        
        # Create new user with random password
        password = generate_random_password()
        
        # Check if business email (informational only, not required for workspace members)
        is_biz_email = is_business_email(email)
        domain = get_email_domain(email) if is_biz_email else None
        
        user = User.objects.create_user(
            email=email,
            password=password,
            full_name=full_name,
            role=UserRole.USER,  # Default to regular user
            is_business_email=is_biz_email,
            business_domain=domain,
            force_password_change=True,  # Must change password on first login
            is_active=True
        )
        
        # Publish user creation event
        UserService.create_user(user, created_by=created_by)
        
        # Publish email notification event
        event = Event(
            event_type=EventTypes.EMAIL_SENT,
            data={
                'user_id': str(user.id),
                'notification_type': 'workspace_invite',
                'title': 'You have been invited to a workspace',
                'message': f'{created_by.full_name} invited you to join their workspace.',
                'channels': ['email'],
                'temporary_password': password,
                'invited_by_name': created_by.full_name,
                'invited_by_email': created_by.email
            },
            source_module='user'
        )
        EventBus.publish(event)
        
        return user, password, True
    
    @staticmethod
    def complete_onboarding(user) -> None:
        """Mark user onboarding as complete"""
        user.onboarding_completed = True
        user.save()
        
        # Clear cache
        CacheService.delete(user.get_cache_key())
        
        # Publish event
        event = Event(
            event_type=EventTypes.USER_UPDATED,
            data={
                'user_id': str(user.id),
                'onboarding_completed': True,
                'completed_at': timezone.now().isoformat(),
            },
            source_module='user'
        )
        EventBus.publish(event)
