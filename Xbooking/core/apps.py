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
    _initialized = False  # Class variable to track initialization
    
    def ready(self):
        """
        Initialize event bus and services when Django starts
        """
        # Prevent multiple initializations (Django can call ready() multiple times)
        if CoreConfig._initialized:
            logger.info("Core services already initialized, skipping")
            return
        
        try:
            from core.services import EventBus
            from core.email_service import EmailService
            from core.notification_service import NotificationService
            
            # Initialize services (subscribe to events)
            EmailService.initialize()
            NotificationService.initialize()
            
            # Start Redis event listener
            EventBus.start_listener()
            
            CoreConfig._initialized = True
            logger.info("Core services initialized successfully")
        
        except Exception as e:
            logger.error(f"Failed to initialize core services: {str(e)}")
