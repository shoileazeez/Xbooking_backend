"""
Event Handlers for User Module
Handles background tasks triggered by user events
"""
import logging
from core.services import EventBus, EventTypes

logger = logging.getLogger(__name__)


def handle_user_registered(event):
    """
    Handle user registration event - create default preferences in background
    
    Args:
        event: Event object containing user data
    """
    try:
        from user.models import User, UserPreference
        
        user_id = event.data.get('user_id')
        user = User.objects.get(id=user_id)
        
        # Create default preferences if not exists
        UserPreference.objects.get_or_create(user=user)
        
        logger.info(f"Created preferences for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to create preferences for user: {str(e)}")


# Register event handlers
def register_handlers():
    """Register all user event handlers"""
    EventBus.subscribe(EventTypes.USER_REGISTERED, handle_user_registered)
    logger.info("User event handlers registered")
