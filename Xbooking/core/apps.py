"""
Core App Configuration
Initializes event bus and notification services
"""
from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    
    def ready(self):
        """
        Initialize event bus and services when Django starts
        """
        try:
            from core.services import EventBus
            from core.email_service import EmailService
            from core.notification_service import NotificationService
            
            # Initialize services (subscribe to events)
            EmailService.initialize()
            NotificationService.initialize()
            
            # Start Redis event listener
            EventBus.start_listener()
            
            logger.info("Core services initialized successfully")
        
        except Exception as e:
            logger.error(f"Failed to initialize core services: {str(e)}")
