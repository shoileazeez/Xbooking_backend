from django.apps import AppConfig


class UserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'user'
    
    def ready(self):
        """Initialize app - register event handlers"""
        try:
            from user.event_handlers import register_handlers
            register_handlers()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to register user event handlers: {str(e)}")
