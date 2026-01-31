"""
Service layer for decoupled inter-module communication
Implements event-driven architecture using Redis pub/sub
"""

import json
import logging
import redis
from typing import Any, Callable, Dict, Optional, List
from django.core.cache import cache
from django.conf import settings
import threading

logger = logging.getLogger(__name__)


class Event:
    """
    Event object for inter-module communication
    """
    def __init__(self, event_type: str, data: Dict[str, Any], source_module: str, event_id: str = None):
        self.event_type = event_type
        self.data = data
        self.source_module = source_module
        self.event_id = event_id or self._generate_id()
    
    def _generate_id(self):
        import uuid
        from django.utils import timezone
        return f"{self.event_type}:{timezone.now().timestamp()}:{uuid.uuid4().hex[:8]}"
    
    def to_dict(self):
        return {
            'event_id': self.event_id,
            'event_type': self.event_type,
            'data': self.data,
            'source_module': self.source_module
        }
    
    @classmethod
    def from_dict(cls, data: Dict):
        return cls(
            event_type=data['event_type'],
            data=data['data'],
            source_module=data['source_module'],
            event_id=data.get('event_id')
        )


class EventBus:
    """
    Event bus for publishing and subscribing to events
    Uses Redis pub/sub for distributed communication
    """
    
    _subscribers: Dict[str, List[Callable]] = {}
    _redis_client: Optional[redis.Redis] = None
    _pubsub = None
    _listener_thread = None
    _processed_events: set = set()  # Track processed event IDs to prevent duplicates
    
    @classmethod
    def _get_redis_client(cls):
        """Get or create Redis client"""
        if cls._redis_client is None:
            try:
                cls._redis_client = redis.Redis(
                    host=getattr(settings, 'REDIS_HOST', 'localhost'),
                    port=getattr(settings, 'REDIS_PORT', 6379),
                    db=getattr(settings, 'REDIS_DB', 1),
                    decode_responses=True
                )
                cls._redis_client.ping()
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {str(e)}")
                cls._redis_client = None
        return cls._redis_client
    
    @classmethod
    def publish(cls, event: Event):
        """
        Publish an event to the event bus (both Redis and local)
        
        Args:
            event: Event to publish
        """
        try:
            # Publish to Redis channel for distributed processing
            redis_client = cls._get_redis_client()
            if redis_client:
                channel = f"xbooking:events:{event.event_type}"
                message = json.dumps(event.to_dict())
                redis_client.publish(channel, message)
                logger.debug(f"Published to Redis: {event.event_type}")
            else:
                # No Redis, handle locally
                cls._notify_local_subscribers(event)
            
            logger.info(f"Event published: {event.event_type} from {event.source_module}")
        except Exception as e:
            logger.error(f"Failed to publish event {event.event_type}: {str(e)}")
    
    @classmethod
    def subscribe(cls, event_type: str, handler: Callable):
        """
        Subscribe to an event type (local subscription)
        
        Args:
            event_type: Type of event to subscribe to
            handler: Callback function to handle the event
        """
        if event_type not in cls._subscribers:
            cls._subscribers[event_type] = []
        
        if handler not in cls._subscribers[event_type]:
            cls._subscribers[event_type].append(handler)
            logger.info(f"Subscribed to event: {event_type}")
    
    @classmethod
    def _notify_local_subscribers(cls, event: Event):
        """
        Notify local subscribers of an event
        """
        # Prevent duplicate processing of the same event
        if event.event_id in cls._processed_events:
            logger.debug(f"Skipping duplicate event: {event.event_id}")
            return
        
        cls._processed_events.add(event.event_id)
        
        # Limit processed events cache to prevent memory leaks
        if len(cls._processed_events) > 10000:
            # Remove oldest 1000 events
            cls._processed_events = set(list(cls._processed_events)[1000:])
        
        if event.event_type in cls._subscribers:
            for handler in cls._subscribers[event.event_type]:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(f"Error in event handler for {event.event_type}: {str(e)}")
    
    @classmethod
    def start_listener(cls):
        """
        Start Redis pub/sub listener in background thread
        """
        if cls._listener_thread and cls._listener_thread.is_alive():
            logger.info("Event listener already running")
            return
        
        redis_client = cls._get_redis_client()
        if not redis_client:
            logger.warning("Redis not available, using local-only event bus")
            return
        
        cls._pubsub = redis_client.pubsub()
        cls._pubsub.psubscribe('xbooking:events:*')
        
        def listen():
            logger.info("Redis event listener started")
            for message in cls._pubsub.listen():
                if message['type'] == 'pmessage':
                    try:
                        event_data = json.loads(message['data'])
                        event = Event.from_dict(event_data)
                        cls._notify_local_subscribers(event)
                    except Exception as e:
                        logger.error(f"Error processing event: {str(e)}")
        
        cls._listener_thread = threading.Thread(target=listen, daemon=True)
        cls._listener_thread.start()
        logger.info("Event listener thread started")
    
    @classmethod
    def stop_listener(cls):
        """Stop Redis pub/sub listener"""
        if cls._pubsub:
            cls._pubsub.close()
            cls._pubsub = None
        logger.info("Event listener stopped")


# Event type constants
class EventTypes:
    # User events
    USER_REGISTERED = "user.registered"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    
    # Workspace events
    WORKSPACE_CREATED = "workspace.created"
    WORKSPACE_UPDATED = "workspace.updated"
    WORKSPACE_DELETED = "workspace.deleted"
    WORKSPACE_MEMBER_ADDED = "workspace.member_added"
    WORKSPACE_MEMBER_REMOVED = "workspace.member_removed"
    
    # Booking events
    BOOKING_CREATED = "booking.created"
    BOOKING_CONFIRMED = "booking.confirmed"
    BOOKING_CANCELLED = "booking.cancelled"
    BOOKING_COMPLETED = "booking.completed"
    BOOKING_CHECKED_IN = "booking.checked_in"
    BOOKING_CHECKED_OUT = "booking.checked_out"
    
    # Reservation events
    RESERVATION_CREATED = "reservation.created"
    RESERVATION_CONFIRMED = "reservation.confirmed"
    RESERVATION_CANCELLED = "reservation.cancelled"
    RESERVATION_EXPIRED = "reservation.expired"
    RESERVATION_EXPIRING = "reservation.expiring"
    
    # Bank/Wallet events
    WALLET_CREATED = "wallet.created"
    WALLET_CREDITED = "wallet.credited"
    WALLET_DEBITED = "wallet.debited"
    WORKSPACE_WALLET_CREATED = "workspace_wallet.created"
    WORKSPACE_WALLET_CREDITED = "workspace_wallet.credited"
    WORKSPACE_WALLET_DEBITED = "workspace_wallet.debited"
    DEPOSIT_INITIATED = "deposit.initiated"
    DEPOSIT_COMPLETED = "deposit.completed"
    WITHDRAWAL_REQUESTED = "withdrawal.requested"
    WITHDRAWAL_PROCESSING = "withdrawal.processing"
    WITHDRAWAL_COMPLETED = "withdrawal.completed"
    WITHDRAWAL_FAILED = "withdrawal.failed"
    
    # Payment events
    ORDER_CREATED = "order.created"
    PAYMENT_INITIATED = "payment.initiated"
    PAYMENT_COMPLETED = "payment.completed"
    PAYMENT_FAILED = "payment.failed"
    PAYMENT_REFUNDED = "payment.refunded"
    REFUND_REQUESTED = "refund.requested"
    REFUND_COMPLETED = "refund.completed"
    
    # QR Code events
    QR_CODE_GENERATED = "qr_code.generated"
    QR_CODE_SCANNED = "qr_code.scanned"
    
    # Notification events
    NOTIFICATION_SENT = "notification.sent"
    EMAIL_SENT = "email.sent"


class ServiceRegistry:
    """
    Registry for service discovery and communication
    """
    _services: Dict[str, Any] = {}
    
    @classmethod
    def register(cls, service_name: str, service_instance: Any):
        """
        Register a service
        
        Args:
            service_name: Name of the service
            service_instance: Service instance
        """
        cls._services[service_name] = service_instance
        logger.info(f"Registered service: {service_name}")
    
    @classmethod
    def get(cls, service_name: str) -> Optional[Any]:
        """
        Get a service by name
        
        Args:
            service_name: Name of the service
            
        Returns:
            Service instance or None
        """
        return cls._services.get(service_name)
    
    @classmethod
    def call(cls, service_name: str, method_name: str, *args, **kwargs) -> Any:
        """
        Call a service method
        
        Args:
            service_name: Name of the service
            method_name: Method to call
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Result of the method call
        """
        service = cls.get(service_name)
        if service is None:
            logger.error(f"Service not found: {service_name}")
            return None
        
        method = getattr(service, method_name, None)
        if method is None:
            logger.error(f"Method not found: {service_name}.{method_name}")
            return None
        
        try:
            return method(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error calling {service_name}.{method_name}: {str(e)}")
            return None
