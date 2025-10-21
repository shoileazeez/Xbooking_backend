"""
Custom JWT Authentication to handle UUID user IDs
"""
from rest_framework_simplejwt.authentication import JWTAuthentication as SimpleJWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt import settings as jwt_settings
from django.contrib.auth import get_user_model
import uuid
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class UUIDJWTAuthentication(SimpleJWTAuthentication):
    """
    Custom JWT Authentication that properly converts UUID strings to UUID objects
    for user lookup
    """
    
    def get_user(self, validated_token):
        """
        Override to handle UUID conversion when looking up user
        """
        try:
            # Get settings from jwt_settings
            user_id_field = jwt_settings.api_settings.USER_ID_FIELD
            user_id_claim = jwt_settings.api_settings.USER_ID_CLAIM
            
            logger.debug(f"Looking up user with field '{user_id_field}' using claim '{user_id_claim}'")
            
            # Extract user_id from token
            if user_id_claim not in validated_token:
                logger.error(f"Token missing claim: {user_id_claim}")
                raise AuthenticationFailed(f'Token missing claim: {user_id_claim}')
            
            user_id = validated_token[user_id_claim]
            logger.debug(f"User ID from token: {user_id} (type: {type(user_id).__name__})")
            
            # Convert string UUID to UUID object for lookup
            if isinstance(user_id, str):
                try:
                    # Try to convert to UUID
                    user_id_converted = uuid.UUID(user_id)
                    logger.debug(f"Converted to UUID: {user_id_converted}")
                    user_id = user_id_converted
                except (ValueError, TypeError) as e:
                    logger.warning(f"Could not convert to UUID: {e}, using as-is")
                    # If it's not a valid UUID string, use as-is (for backwards compatibility)
                    pass
            
            # Debug: list all users
            logger.debug(f"Total users in database: {User.objects.count()}")
            for u in User.objects.all()[:5]:
                logger.debug(f"  User: {u.email}, ID: {u.id}")
            
            # Query user with the converted ID
            logger.debug(f"Querying User with {user_id_field}={user_id} (type: {type(user_id).__name__})")
            user = User.objects.get(**{user_id_field: user_id})
            logger.info(f"User found: {user.email}")
            
        except User.DoesNotExist as e:
            logger.error(f"User not found with {user_id_field}={user_id}, error: {e}")
            logger.error(f"Total users: {User.objects.count()}")
            raise AuthenticationFailed('User not found')
        except AuthenticationFailed:
            raise
        except Exception as e:
            logger.exception(f"Authentication error: {str(e)}")
            raise AuthenticationFailed(f'Authentication failed: {str(e)}')

        if not user.is_active:
            logger.warning(f"User {user.email} is inactive")
            raise AuthenticationFailed('User account is disabled')

        return user
