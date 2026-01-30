"""
Payment Service Layer with EventBus Integration
"""
import logging
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from core.services import EventBus, Event, EventTypes
from core.cache import CacheService
from payment.models import Order, Payment, Refund
from booking.models import Booking

logger = logging.getLogger(__name__)


class PaymentService:
    """Service for managing payments with event publishing"""
    
    @staticmethod
    @transaction.atomic
    def create_order(booking_ids, user, notes=None):
        """Create an order from bookings and publish event"""
        bookings = Booking.objects.filter(
            id__in=booking_ids,
            user=user,
            status='pending'
        ).select_related('workspace', 'space')
        
        if bookings.count() != len(booking_ids):
            raise ValueError("Some bookings not found or not pending")
        
        # Remove bookings from old pending orders
        old_orders = Order.objects.filter(
            bookings__in=bookings,
            status='pending'
        ).distinct()
        
        for old_order in old_orders:
            old_order.bookings.remove(*bookings)
            if old_order.bookings.count() == 0:
                old_order.delete()
        
        # Calculate totals
        subtotal = sum(b.base_price for b in bookings)
        discount = Decimal('0')
        tax = sum(b.tax_amount for b in bookings)
        total = subtotal - discount + tax
        
        # Create order
        primary_workspace = bookings.first().workspace
        order = Order.objects.create(
            workspace=primary_workspace,
            user=user,
            subtotal=subtotal,
            discount_amount=discount,
            tax_amount=tax,
            total_amount=total,
            notes=notes or ''
        )
        order.bookings.set(bookings)
        
        # Publish order created event
        event = Event(
            event_type=EventTypes.ORDER_CREATED,
            data={
                'order_id': str(order.id),
                'order_number': order.order_number,
                'workspace_id': str(order.workspace.id),
                'workspace_name': order.workspace.name,
                'user_id': str(user.id),
                'user_email': user.email,
                'user_name': user.full_name or user.email,
                'subtotal': str(order.subtotal),
                'tax_amount': str(order.tax_amount),
                'total_amount': str(order.total_amount),
                'booking_count': bookings.count(),
                'timestamp': timezone.now().isoformat()
            },
            source_module='payment'
        )
        EventBus.publish(event)
        
        # Invalidate caches
        CacheService.delete_pattern(f'orders:user:{user.id}:*')
        CacheService.delete_pattern(f'orders:workspace:{order.workspace.id}:*')
        
        return order
    
    @staticmethod
    @transaction.atomic
    def pay_with_wallet(order, user):
        """
        Pay for an order using user's wallet balance
        Returns the payment object if successful
        """
        from bank.services import BankService
        from bank.models import Wallet
        
        # Get user's wallet
        try:
            wallet = Wallet.objects.select_for_update().get(user=user)
        except Wallet.DoesNotExist:
            raise ValueError("User wallet not found")
        
        # Check if wallet has sufficient balance
        if not wallet.can_debit(order.total_amount):
            raise ValueError(f"Insufficient wallet balance. Available: {wallet.currency} {wallet.balance}, Required: {wallet.currency} {order.total_amount}")
        
        # Create payment record
        payment = Payment.objects.create(
            order=order,
            workspace=order.workspace,
            user=user,
            amount=order.total_amount,
            payment_method='wallet',
            status='processing',
            gateway_transaction_id=f"WALLET-{order.order_number}"
        )
        
        try:
            # Debit wallet
            transaction = BankService.debit_wallet(
                wallet=wallet,
                amount=order.total_amount,
                category='booking_payment',
                description=f"Payment for order {order.order_number}",
                reference=str(payment.id),
                metadata={
                    'payment_id': str(payment.id),
                    'order_id': str(order.id),
                    'order_number': order.order_number,
                    'booking_count': order.bookings.count()
                }
            )
            
            # Complete payment
            payment.status = 'success'
            payment.completed_at = timezone.now()
            payment.gateway_response = {
                'transaction_id': str(transaction.id),
                'wallet_balance_before': str(transaction.balance_before),
                'wallet_balance_after': str(transaction.balance_after),
                'payment_source': 'wallet'
            }
            payment.save()
            
            # Update order status
            order.status = 'paid'
            order.paid_at = timezone.now()
            order.payment_method = 'wallet'
            order.payment_reference = payment.gateway_transaction_id
            order.save()
            
            # Update booking statuses and confirm reservations
            from booking.models import CartItem
            from booking.services import BookingService
            
            for booking in order.bookings.all():
                booking.status = 'confirmed'
                booking.save()
                
                # Find and confirm associated reservation
                cart_item = CartItem.objects.filter(
                    reservation__space=booking.space,
                    reservation__start=booking.check_in,
                    reservation__end=booking.check_out,
                    reservation__user=booking.user,
                    reservation__status='active'
                ).first()
                
                if cart_item and cart_item.reservation:
                    try:
                        BookingService.confirm_reservation(cart_item.reservation)
                    except ValueError:
                        pass
                
                # Credit workspace wallet with booking earnings
                try:
                    BankService.process_booking_payment(booking, payment)
                except Exception as e:
                    logger.error(f"Failed to credit workspace wallet for booking {booking.id}: {str(e)}")
            
            # Publish payment completed event
            EventBus.publish(Event(
                event_type=EventTypes.PAYMENT_COMPLETED,
                data={
                    'payment_id': str(payment.id),
                    'order_id': str(order.id),
                    'order_number': order.order_number,
                    'workspace_id': str(order.workspace.id),
                    'workspace_name': order.workspace.name,
                    'user_id': str(user.id),
                    'user_email': user.email,
                    'user_name': user.full_name or user.email,
                    'amount': str(payment.amount),
                    'currency': payment.currency,
                    'payment_method': 'wallet',
                    'gateway_reference': payment.gateway_transaction_id,
                    'booking_ids': [str(b.id) for b in order.bookings.all()],
                    'wallet_balance': str(wallet.balance),
                    'timestamp': timezone.now().isoformat()
                },
                source_module='payment'
            ))
            
            # Invalidate caches
            CacheService.delete_pattern(f'payment:{payment.id}:*')
            CacheService.delete_pattern(f'order:{order.id}:*')
            CacheService.delete_pattern(f'payments:user:{user.id}:*')
            CacheService.delete_pattern(f'orders:user:{user.id}:*')
            CacheService.delete_pattern(f'wallets:user:{user.id}:*')
            
            # Trigger background tasks for QR codes and notifications
            try:
                from qr_code.tasks import (
                    generate_order_receipt,
                    send_payment_confirmation_email,
                    generate_booking_qr_codes_for_order
                )
                from booking.tasks import generate_guest_qr_codes_for_booking
                from qr_code.models import BookingQRCode
                
                # Check if booking QR codes already exist (prevent duplicates from callback + webhook)
                booking_qrs_exist = BookingQRCode.objects.filter(booking__in=order.bookings.all()).exists()
                
                # Send payment confirmation email
                send_payment_confirmation_email.delay(str(order.id))
                
                # Generate order receipt (replaces order QR code)
                generate_order_receipt.delay(str(order.id))
                logger.info(f"Triggered order receipt generation for {order.id}")
                
                # Generate QR code per booking (only if doesn't exist)
                if not booking_qrs_exist:
                    generate_booking_qr_codes_for_order.delay(str(order.id))
                    logger.info(f"Triggered booking QR generation for {order.id}")
                else:
                    logger.info(f"Booking QRs already exist for {order.id}, skipping generation")
                
                # Generate guest QR codes for each booking
                for booking in order.bookings.all():
                    generate_guest_qr_codes_for_booking.delay(str(booking.id))
                
                logger.info(f"Background tasks triggered for wallet payment order {order.id}")
            except Exception as e:
                logger.error(f"Failed to trigger background tasks for order {order.id}: {str(e)}")
            
            return payment
            
        except Exception as e:
            # Rollback: mark payment as failed
            payment.status = 'failed'
            payment.gateway_response = {'error': str(e)}
            payment.save()
            
            # Publish payment failed event
            EventBus.publish(Event(
                event_type=EventTypes.PAYMENT_FAILED,
                data={
                    'payment_id': str(payment.id),
                    'order_id': str(order.id),
                    'order_number': order.order_number,
                    'user_id': str(user.id),
                    'user_email': user.email,
                    'payment_method': 'wallet',
                    'error': str(e),
                    'timestamp': timezone.now().isoformat()
                },
                source_module='payment'
            ))
            
            raise ValueError(f"Wallet payment failed: {str(e)}")
    
    @staticmethod
    @transaction.atomic
    def initiate_payment(order, payment_method, gateway_handler):
        """Initiate payment for an order and publish event"""
        # Create payment record
        payment = Payment.objects.create(
            order=order,
            workspace=order.workspace,
            user=order.user,
            amount=order.total_amount,
            payment_method=payment_method,
            status='pending'
        )
        
        # Initialize payment with gateway
        try:
            from django.conf import settings
            payment_redirect_url = getattr(settings, 'PAYMENT_REDIRECT_URL', None)
            if payment_redirect_url:
                # Append provider as query param
                if '?' in payment_redirect_url:
                    payment_redirect_url = f"{payment_redirect_url}&provider={payment_method}"
                else:
                    payment_redirect_url = f"{payment_redirect_url}?provider={payment_method}"
            gateway_response = gateway_handler.initialize_transaction(
                email=order.user.email,
                amount=float(payment.amount),
                reference=str(payment.id),
                redirect_url=payment_redirect_url
            )
            
            payment.gateway_transaction_id = gateway_response.get('reference')
            payment.gateway_response = gateway_response
            payment.status = 'processing'
            payment.save()
            
            # Publish payment initiated event
            EventBus.publish(Event(
                event_type=EventTypes.PAYMENT_INITIATED,
                data={
                    'payment_id': str(payment.id),
                    'order_id': str(order.id),
                    'order_number': order.order_number,
                    'workspace_id': str(order.workspace.id),
                    'workspace_name': order.workspace.name,
                    'user_id': str(order.user.id),
                    'user_email': order.user.email,
                    'user_name': order.user.full_name or order.user.email,
                    'amount': str(payment.amount),
                    'currency': payment.currency,
                    'payment_method': payment_method,
                    'gateway_reference': payment.gateway_transaction_id,
                    'timestamp': timezone.now().isoformat()
                },
                source_module='payment'
            ))
            
            # Invalidate caches
            CacheService.delete_pattern(f'payments:user:{order.user.id}:*')
            
            return payment, gateway_response
            
        except Exception as e:
            payment.status = 'failed'
            payment.gateway_response = {'error': str(e)}
            payment.save()
            
            # Publish payment failed event
            EventBus.publish(Event(
                event_type=EventTypes.PAYMENT_FAILED,
                data={
                    'payment_id': str(payment.id),
                    'order_id': str(order.id),
                    'order_number': order.order_number,
                    'user_id': str(order.user.id),
                    'user_email': order.user.email,
                    'error': str(e),
                    'timestamp': timezone.now().isoformat()
                },
                source_module='payment'
            ))
            
            raise
    
    @staticmethod
    @transaction.atomic
    def complete_payment(payment, gateway_response=None):
        """Mark payment as completed and publish event, only trigger emails/tasks if not already completed"""
        from decimal import Decimal
        def convert_decimals(obj):
            if isinstance(obj, dict):
                return {k: convert_decimals(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_decimals(i) for i in obj]
            elif isinstance(obj, Decimal):
                return float(obj)
            return obj
        already_completed = payment.status == 'success'
        payment.status = 'success'
        payment.completed_at = timezone.now()
        if gateway_response:
            payment.gateway_response = convert_decimals(gateway_response)
        payment.save()

        # Update order status
        order = payment.order
        order.status = 'paid'
        order.paid_at = timezone.now()
        order.payment_reference = payment.gateway_transaction_id
        order.save()

        # Update booking statuses and confirm reservations
        from booking.models import CartItem
        from booking.services import BookingService

        for booking in order.bookings.all():
            booking.status = 'confirmed'
            booking.save()

            # Find and confirm associated reservation
            cart_item = CartItem.objects.filter(
                reservation__space=booking.space,
                reservation__start=booking.check_in,
                reservation__end=booking.check_out,
                reservation__user=booking.user,
                reservation__status='active'
            ).first()

            if cart_item and cart_item.reservation:
                try:
                    BookingService.confirm_reservation(cart_item.reservation)
                except ValueError:
                    pass

            # Credit workspace wallet with booking earnings
            try:
                from bank.services import BankService
                BankService.process_booking_payment(booking, payment)
            except Exception as e:
                logger.error(f"Failed to credit workspace wallet for booking {booking.id}: {str(e)}")

        # Publish payment completed event
        EventBus.publish(Event(
            event_type=EventTypes.PAYMENT_COMPLETED,
            data={
                'payment_id': str(payment.id),
                'order_id': str(order.id),
                'order_number': order.order_number,
                'workspace_id': str(order.workspace.id),
                'workspace_name': order.workspace.name,
                'user_id': str(order.user.id),
                'user_email': order.user.email,
                'user_name': order.user.full_name or order.user.email,
                'amount': str(payment.amount),
                'currency': payment.currency,
                'payment_method': payment.payment_method,
                'gateway_reference': payment.gateway_transaction_id,
                'booking_ids': [str(b.id) for b in order.bookings.all()],
                'timestamp': timezone.now().isoformat()
            },
            source_module='payment'
        ))

        # Invalidate caches
        CacheService.delete_pattern(f'payment:{payment.id}:*')
        CacheService.delete_pattern(f'order:{order.id}:*')
        CacheService.delete_pattern(f'payments:user:{order.user.id}:*')
        CacheService.delete_pattern(f'orders:user:{order.user.id}:*')

        # Only trigger background tasks if not already completed
        if not already_completed:
            try:
                from qr_code.tasks import (
                    generate_order_receipt,
                    send_payment_confirmation_email,
                    generate_booking_qr_codes_for_order
                )
                from booking.tasks import generate_guest_qr_codes_for_booking
                from qr_code.models import BookingQRCode
                from notifications.tasks import send_notification

                # Check if booking QR codes already exist (prevent duplicates from callback + webhook)
                booking_qrs_exist = BookingQRCode.objects.filter(booking__in=order.bookings.all()).exists()

                # Send payment confirmation email
                send_payment_confirmation_email.delay(str(order.id))

                # Generate order receipt (replaces deprecated OrderQRCode)
                generate_order_receipt.delay(str(order.id))
                logger.info(f"Triggered order receipt generation for {order.id}")

                # Generate QR code per booking (only if doesn't exist)
                if not booking_qrs_exist:
                    generate_booking_qr_codes_for_order.delay(str(order.id))
                    logger.info(f"Triggered booking QR generation for {order.id}")
                else:
                    logger.info(f"Booking QRs already exist for {order.id}, skipping generation")

                # Generate guest QR codes for each booking
                for booking in order.bookings.all():
                    generate_guest_qr_codes_for_booking.delay(str(booking.id))

                # Send in-app notification for payment completion (prevent duplicates)
                try:
                    from notifications.models import Notification
                    # Check if notification already exists for this order
                    existing_notification = Notification.objects.filter(
                        user=order.user,
                        notification_type='payment_completed',
                        data__order_id=str(order.id)
                    ).first()

                    if not existing_notification:
                        notification = Notification.objects.create(
                            user=order.user,
                            notification_type='payment_completed',
                            channel='in_app',
                            title='Payment Successful',
                            message=f'Your payment for order {order.order_number} was successful. Total: {order.total_amount} {payment.currency}',
                            data={
                                'order_id': str(order.id),
                                'order_number': order.order_number,
                                'amount': str(order.total_amount),
                                'payment_method': payment.payment_method
                            }
                        )
                        send_notification.delay(str(notification.id))
                        logger.info(f"Created payment completion notification for order {order.id}")
                    else:
                        logger.info(f"Payment completion notification already exists for order {order.id}, skipping")
                except Exception as notif_error:
                    logger.error(f"Failed to create payment notification: {str(notif_error)}")

                logger.info(f"Background tasks triggered for order {order.id}")
            except Exception as e:
                logger.error(f"Failed to trigger background tasks for order {order.id}: {str(e)}")

        return payment
    
    @staticmethod
    @transaction.atomic
    def fail_payment(payment, error_message=None):
        """Mark payment as failed and publish event"""
        payment.status = 'failed'
        if error_message:
            payment.gateway_response['error'] = error_message
        payment.save()
        
        # Publish payment failed event
        EventBus.publish(Event(
            event_type=EventTypes.PAYMENT_FAILED,
            data={
                'payment_id': str(payment.id),
                'order_id': str(payment.order.id),
                'order_number': payment.order.order_number,
                'user_id': str(payment.user.id),
                'user_email': payment.user.email,
                'user_name': payment.user.full_name or payment.user.email,
                'amount': str(payment.amount),
                'error': error_message or 'Payment failed',
                'timestamp': timezone.now().isoformat()
            },
            source_module='payment'
        ))
        
        # Invalidate caches
        CacheService.delete_pattern(f'payment:{payment.id}:*')
        
        return payment
    
    @staticmethod
    @transaction.atomic
    def request_refund(payment, reason, reason_description, refund_amount=None):
        """Request a refund and publish event"""
        if refund_amount is None:
            refund_amount = payment.amount
        
        refund = Refund.objects.create(
            payment=payment,
            order=payment.order,
            workspace=payment.workspace,
            user=payment.user,
            amount=refund_amount,
            reason=reason,
            reason_description=reason_description,
            status='pending'
        )
        
        # Publish refund requested event
        EventBus.publish(Event(
            event_type=EventTypes.REFUND_REQUESTED,
            data={
                'refund_id': str(refund.id),
                'payment_id': str(payment.id),
                'order_id': str(payment.order.id),
                'order_number': payment.order.order_number,
                'user_id': str(payment.user.id),
                'user_email': payment.user.email,
                'user_name': payment.user.full_name or payment.user.email,
                'amount': str(refund_amount),
                'reason': reason,
                'reason_description': reason_description,
                'timestamp': timezone.now().isoformat()
            },
            source_module='payment'
        ))
        
        # Invalidate caches
        CacheService.delete_pattern(f'refunds:user:{payment.user.id}:*')
        
        return refund
    
    @staticmethod
    @transaction.atomic
    def complete_refund(refund, gateway_refund_id=None):
        """Complete a refund and publish event"""
        refund.status = 'completed'
        refund.completed_at = timezone.now()
        if gateway_refund_id:
            refund.gateway_refund_id = gateway_refund_id
        refund.save()
        
        # Update order status
        refund.order.status = 'refunded'
        refund.order.save()
        
        # Publish refund completed event
        EventBus.publish(Event(
            event_type=EventTypes.REFUND_COMPLETED,
            data={
                'refund_id': str(refund.id),
                'payment_id': str(refund.payment.id),
                'order_id': str(refund.order.id),
                'order_number': refund.order.order_number,
                'user_id': str(refund.user.id),
                'user_email': refund.user.email,
                'user_name': refund.user.full_name or refund.user.email,
                'amount': str(refund.amount),
                'timestamp': timezone.now().isoformat()
            },
            source_module='payment'
        ))
        
        # Invalidate caches
        CacheService.delete_pattern(f'refund:{refund.id}:*')
        CacheService.delete_pattern(f'order:{refund.order.id}:*')
        
        return refund


__all__ = ['PaymentService']
