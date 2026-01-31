"""
In-App Notification Service
Handles creation of in-app notifications via EventBus subscription
"""
import logging
from datetime import timedelta
from django.utils import timezone
from core.services import EventBus, Event, EventTypes

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Notification service that subscribes to various events and creates in-app notifications
    """
    
    @staticmethod
    def create_notification(user_id: str, notification_type: str, title: str, message: str, data: dict = None):
        """
        Create an in-app notification and trigger async delivery
        Also creates an email notification for the same event
        
        Args:
            user_id: User ID to notify
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            data: Additional data (optional)
        """
        try:
            from notifications.models import Notification
            from user.models import User
            
            user = User.objects.get(id=user_id)
            
            # Define notification types that should be unique per user (no duplicates ever)
            unique_notifications = {
                'user_registered',  # Welcome message - only once per user
                'wallet_created',   # Wallet creation - only once per user
            }
            
            # Check for existing notification to prevent duplicates
            if notification_type in unique_notifications:
                # For unique notifications, check if user has ever received this type
                existing_notification = Notification.objects.filter(
                    user=user,
                    notification_type=notification_type
                ).first()
            else:
                # For other notifications, check within last 24 hours to prevent spam
                existing_notification = Notification.objects.filter(
                    user=user,
                    notification_type=notification_type,
                    created_at__gte=timezone.now() - timedelta(hours=24)
                ).first()
            
            if existing_notification:
                logger.info(f"Duplicate notification prevented for user {user.email}: {title}")
                return existing_notification
            
            # Create in-app notification
            in_app_notification = Notification.objects.create(
                user=user,
                notification_type=notification_type,
                channel='in_app',
                title=title,
                message=message,
                data=data or {}
            )
            
            # Create email notification for the same event
            email_notification = Notification.objects.create(
                user=user,
                notification_type=notification_type,
                channel='email',
                title=title,
                message=message,
                data=data or {}
            )
            
            # Trigger async notification delivery tasks
            try:
                from notifications.tasks import send_notification
                send_notification.delay(str(in_app_notification.id))
                send_notification.delay(str(email_notification.id))
            except Exception as task_error:
                logger.error(f"Failed to trigger notification task: {str(task_error)}")
            
            logger.info(f"Created notification for user {user.email}: {title}")
            return in_app_notification
        
        except Exception as e:
            logger.error(f"Failed to create notification: {str(e)}")
            return None
    
    @staticmethod
    def handle_user_events(event: Event):
        """Handle user-related events"""
        data = event.data
        user_id = data.get('user_id')
        
        if not user_id:
            return
        
        if event.event_type == EventTypes.USER_REGISTERED:
            NotificationService.create_notification(
                user_id=user_id,
                notification_type='user_registered',
                title='Welcome to Xbooking!',
                message='Your account has been created successfully.',
                data=data
            )
    
    @staticmethod
    def handle_workspace_events(event: Event):
        """Handle workspace-related events"""
        data = event.data
        
        if event.event_type == EventTypes.WORKSPACE_MEMBER_ADDED:
            user_id = data.get('user_id')
            workspace_name = data.get('workspace_name', 'a workspace')
            
            if user_id:
                NotificationService.create_notification(
                    user_id=user_id,
                    notification_type='workspace_member_added',
                    title='Added to Workspace',
                    message=f'You have been added to {workspace_name}.',
                    data=data
                )
        
        elif event.event_type == EventTypes.WORKSPACE_CREATED:
            user_id = data.get('owner_id')
            workspace_name = data.get('workspace_name')
            
            if user_id:
                NotificationService.create_notification(
                    user_id=user_id,
                    notification_type='workspace_created',
                    title='Workspace Created',
                    message=f'Your workspace "{workspace_name}" has been created successfully.',
                    data=data
                )
    
    @staticmethod
    def handle_booking_events(event: Event):
        """Handle booking-related events"""
        data = event.data
        user_id = data.get('user_id')
        
        if not user_id:
            return
        
        if event.event_type == EventTypes.BOOKING_CREATED:
            NotificationService.create_notification(
                user_id=user_id,
                notification_type='booking_created',
                title='Booking Created',
                message='Your booking has been created successfully.',
                data=data
            )
        
        elif event.event_type == EventTypes.BOOKING_CONFIRMED:
            NotificationService.create_notification(
                user_id=user_id,
                notification_type='booking_confirmed',
                title='Booking Confirmed',
                message='Your booking has been confirmed.',
                data=data
            )
        
        elif event.event_type == EventTypes.BOOKING_CANCELLED:
            NotificationService.create_notification(
                user_id=user_id,
                notification_type='booking_cancelled',
                title='Booking Cancelled',
                message='Your booking has been cancelled.',
                data=data
            )
    
    @staticmethod
    def handle_payment_events(event: Event):
        """Handle payment-related events"""
        data = event.data
        user_id = data.get('user_id')
        
        if not user_id:
            return
        
        if event.event_type == EventTypes.ORDER_CREATED:
            NotificationService.create_notification(
                user_id=user_id,
                notification_type='order_created',
                title='Order Created',
                message=f'Your order #{data.get("order_number")} has been created.',
                data=data
            )
        
        elif event.event_type == EventTypes.PAYMENT_INITIATED:
            NotificationService.create_notification(
                user_id=user_id,
                notification_type='payment_initiated',
                title='Payment Processing',
                message=f'Payment for order #{data.get("order_number")} is being processed.',
                data=data
            )
        
        elif event.event_type == EventTypes.PAYMENT_COMPLETED:
            NotificationService.create_notification(
                user_id=user_id,
                notification_type='payment_completed',
                title='Payment Successful',
                message=f'Your payment of {data.get("currency")} {data.get("amount")} has been processed successfully.',
                data=data
            )
        
        elif event.event_type == EventTypes.PAYMENT_FAILED:
            NotificationService.create_notification(
                user_id=user_id,
                notification_type='payment_failed',
                title='Payment Failed',
                message='Your payment could not be processed. Please try again.',
                data=data
            )
        
        elif event.event_type == EventTypes.REFUND_REQUESTED:
            NotificationService.create_notification(
                user_id=user_id,
                notification_type='refund_requested',
                title='Refund Requested',
                message=f'Your refund request for order #{data.get("order_number")} has been received.',
                data=data
            )
        
        elif event.event_type == EventTypes.REFUND_COMPLETED:
            NotificationService.create_notification(
                user_id=user_id,
                notification_type='refund_completed',
                title='Refund Completed',
                message=f'Your refund of {data.get("amount")} has been processed.',
                data=data
            )
    
    @staticmethod
    def handle_reservation_events(event: Event):
        """Handle reservation-related events"""
        data = event.data
        user_id = data.get('user_id')
        
        if not user_id:
            return
        
        if event.event_type == EventTypes.RESERVATION_CREATED:
            NotificationService.create_notification(
                user_id=user_id,
                notification_type='reservation_created',
                title='Space Reserved',
                message=f'Your space "{data.get("space_name")}" has been reserved. Complete payment within {data.get("expires_in_minutes")} minutes.',
                data=data
            )
        
        elif event.event_type == EventTypes.RESERVATION_CONFIRMED:
            NotificationService.create_notification(
                user_id=user_id,
                notification_type='reservation_confirmed',
                title='Reservation Confirmed',
                message=f'Your reservation for "{data.get("space_name")}" has been confirmed.',
                data=data
            )
        
        elif event.event_type == EventTypes.RESERVATION_EXPIRING:
            NotificationService.create_notification(
                user_id=user_id,
                notification_type='reservation_expiring',
                title='Reservation Expiring Soon',
                message=f'Your reservation for "{data.get("space_name")}" will expire in 2 minutes. Complete payment now!',
                data=data
            )
        
        elif event.event_type == EventTypes.RESERVATION_EXPIRED:
            NotificationService.create_notification(
                user_id=user_id,
                notification_type='reservation_expired',
                title='Reservation Expired',
                message=f'Your reservation for "{data.get("space_name")}" has expired.',
                data=data
            )
        
        elif event.event_type == EventTypes.RESERVATION_CANCELLED:
            NotificationService.create_notification(
                user_id=user_id,
                notification_type='reservation_cancelled',
                title='Reservation Cancelled',
                message='Your reservation has been cancelled.',
                data=data
            )
    
    @staticmethod
    def handle_bank_events(event: Event):
        """Handle bank/wallet events"""
        data = event.data
        user_id = data.get('user_id')
        
        if not user_id:
            return
        
        if event.event_type == EventTypes.WALLET_CREATED:
            NotificationService.create_notification(
                user_id=user_id,
                notification_type='wallet_created',
                title='Wallet Created',
                message='Your wallet has been created successfully. You can now deposit funds.',
                data=data
            )
        
        elif event.event_type == EventTypes.WALLET_CREDITED:
            NotificationService.create_notification(
                user_id=user_id,
                notification_type='wallet_credited',
                title='Wallet Credited',
                message=f'Your wallet has been credited with {data.get("currency")} {data.get("amount")}. New balance: {data.get("balance")}',
                data=data
            )
        
        elif event.event_type == EventTypes.WALLET_DEBITED:
            NotificationService.create_notification(
                user_id=user_id,
                notification_type='wallet_debited',
                title='Wallet Debited',
                message=f'{data.get("currency")} {data.get("amount")} has been deducted from your wallet. New balance: {data.get("balance")}',
                data=data
            )
        
        elif event.event_type == EventTypes.DEPOSIT_INITIATED:
            NotificationService.create_notification(
                user_id=user_id,
                notification_type='deposit_initiated',
                title='Deposit Initiated',
                message=f'Deposit of {data.get("currency")} {data.get("amount")} is being processed.',
                data=data
            )
        
        elif event.event_type == EventTypes.DEPOSIT_COMPLETED:
            NotificationService.create_notification(
                user_id=user_id,
                notification_type='deposit_completed',
                title='Deposit Completed',
                message=f'Your deposit of {data.get("currency")} {data.get("amount")} has been completed. New balance: {data.get("new_balance")}',
                data=data
            )
    
    @staticmethod
    def handle_workspace_wallet_events(event: Event):
        """Handle workspace wallet events"""
        data = event.data
        workspace_id = data.get('workspace_id')
        
        if not workspace_id:
            return
        
        # Get workspace admins
        try:
            from workspace.models import WorkspaceMember
            admin_users = WorkspaceMember.objects.filter(
                workspace_id=workspace_id,
                role__in=['admin', 'manager']
            ).values_list('user_id', flat=True)
            
            for admin_id in admin_users:
                if event.event_type == EventTypes.WORKSPACE_WALLET_CREDITED:
                    NotificationService.create_notification(
                        user_id=str(admin_id),
                        notification_type='workspace_wallet_credited',
                        title='Workspace Earnings',
                        message=f'{data.get("workspace_name")} earned {data.get("currency")} {data.get("amount")} from a booking. Balance: {data.get("balance")}',
                        data=data
                    )
                
                elif event.event_type == EventTypes.WITHDRAWAL_REQUESTED:
                    NotificationService.create_notification(
                        user_id=str(admin_id),
                        notification_type='withdrawal_requested',
                        title='Withdrawal Requested',
                        message=f'Withdrawal request of {data.get("currency")} {data.get("amount")} has been submitted.',
                        data=data
                    )
                
                elif event.event_type == EventTypes.WITHDRAWAL_COMPLETED:
                    NotificationService.create_notification(
                        user_id=str(admin_id),
                        notification_type='withdrawal_completed',
                        title='Withdrawal Completed',
                        message=f'Withdrawal of {data.get("currency")} {data.get("amount")} has been completed.',
                        data=data
                    )
        except Exception as e:
            logger.error(f"Failed to notify workspace admins: {str(e)}")
    
    @classmethod
    def initialize(cls):
        """
        Initialize notification service by subscribing to events
        """
        # Subscribe to user events
        EventBus.subscribe(EventTypes.USER_REGISTERED, cls.handle_user_events)
        
        # Subscribe to workspace events
        EventBus.subscribe(EventTypes.WORKSPACE_CREATED, cls.handle_workspace_events)
        EventBus.subscribe(EventTypes.WORKSPACE_MEMBER_ADDED, cls.handle_workspace_events)
        
        # Subscribe to booking events
        EventBus.subscribe(EventTypes.BOOKING_CREATED, cls.handle_booking_events)
        EventBus.subscribe(EventTypes.BOOKING_CONFIRMED, cls.handle_booking_events)
        EventBus.subscribe(EventTypes.BOOKING_CANCELLED, cls.handle_booking_events)
        
        # Subscribe to reservation events
        EventBus.subscribe(EventTypes.RESERVATION_CREATED, cls.handle_reservation_events)
        EventBus.subscribe(EventTypes.RESERVATION_CONFIRMED, cls.handle_reservation_events)
        EventBus.subscribe(EventTypes.RESERVATION_EXPIRING, cls.handle_reservation_events)
        EventBus.subscribe(EventTypes.RESERVATION_EXPIRED, cls.handle_reservation_events)
        EventBus.subscribe(EventTypes.RESERVATION_CANCELLED, cls.handle_reservation_events)
        
        # Subscribe to payment events
        EventBus.subscribe(EventTypes.ORDER_CREATED, cls.handle_payment_events)
        EventBus.subscribe(EventTypes.PAYMENT_INITIATED, cls.handle_payment_events)
        EventBus.subscribe(EventTypes.PAYMENT_COMPLETED, cls.handle_payment_events)
        EventBus.subscribe(EventTypes.PAYMENT_FAILED, cls.handle_payment_events)
        EventBus.subscribe(EventTypes.REFUND_REQUESTED, cls.handle_payment_events)
        EventBus.subscribe(EventTypes.REFUND_COMPLETED, cls.handle_payment_events)
        
        # Subscribe to bank/wallet events
        EventBus.subscribe(EventTypes.WALLET_CREATED, cls.handle_bank_events)
        EventBus.subscribe(EventTypes.WALLET_CREDITED, cls.handle_bank_events)
        EventBus.subscribe(EventTypes.WALLET_DEBITED, cls.handle_bank_events)
        EventBus.subscribe(EventTypes.DEPOSIT_INITIATED, cls.handle_bank_events)
        EventBus.subscribe(EventTypes.DEPOSIT_COMPLETED, cls.handle_bank_events)
        EventBus.subscribe(EventTypes.WORKSPACE_WALLET_CREDITED, cls.handle_workspace_wallet_events)
        EventBus.subscribe(EventTypes.WITHDRAWAL_REQUESTED, cls.handle_workspace_wallet_events)
        EventBus.subscribe(EventTypes.WITHDRAWAL_COMPLETED, cls.handle_workspace_wallet_events)
        
        logger.info("NotificationService initialized and subscribed to events")

