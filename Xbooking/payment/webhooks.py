"""
Payment Webhook Handlers for Paystack and Flutterwave
"""
import hashlib
import json
import logging
from django.utils import timezone
from django.conf import settings
from payment.models import Payment, PaymentWebhook, Order
from payment.gateways import PaystackGateway, FlutterwaveGateway
from booking.models import Booking
from notifications.models import Notification

logger = logging.getLogger(__name__)


class PaystackWebhookHandler:
    """Handle Paystack payment webhooks"""
    
    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
    
    def verify_signature(self, request_body, signature_header):
        """
        Verify Paystack webhook signature
        
        Args:
            request_body (str): Raw request body
            signature_header (str): X-Paystack-Signature header
            
        Returns:
            bool: True if signature is valid
        """
        try:
            hash_object = hashlib.sha512(
                f"{request_body}{self.secret_key}".encode('utf-8')
            )
            computed_signature = hash_object.hexdigest()
            return computed_signature == signature_header
        except Exception as e:
            logger.error(f"Signature verification error: {str(e)}")
            return False
    
    def handle_charge_success(self, payload):
        """
        Handle successful charge event from Paystack
        
        Args:
            payload (dict): Webhook payload
            
        Returns:
            dict: Response status
        """
        try:
            reference = payload.get('data', {}).get('reference')
            
            if not reference:
                return {
                    'success': False,
                    'error': 'No reference in payload'
                }
            
            # Get payment
            try:
                payment = Payment.objects.get(gateway_transaction_id=reference)
            except Payment.DoesNotExist:
                logger.warning(f"Payment with reference {reference} not found")
                return {
                    'success': False,
                    'error': 'Payment not found'
                }
            
            # Verify transaction with Paystack
            gateway = PaystackGateway()
            verify_result = gateway.verify_transaction(reference)
            
            if not verify_result['success']:
                logger.error(f"Verification failed for reference {reference}")
                return {
                    'success': False,
                    'error': 'Verification failed'
                }
            
            # Check status
            if verify_result['status'] != 'success':
                payment.status = 'failed'
                payment.save()
                return {
                    'success': False,
                    'error': f"Payment status: {verify_result['status']}"
                }
            
            # Verify amount
            if verify_result['amount'] != payment.amount:
                logger.error(f"Amount mismatch for payment {payment.id}")
                payment.status = 'failed'
                payment.save()
                return {
                    'success': False,
                    'error': 'Amount mismatch'
                }
            
            # Update payment
            payment.status = 'success'
            payment.completed_at = timezone.now()
            payment.gateway_response = payload
            payment.save()
            
            # Update order
            order = payment.order
            order.status = 'paid'
            order.payment_method = 'paystack'
            order.payment_reference = reference
            order.paid_at = timezone.now()
            order.save()
            
            # Update bookings
            for booking in order.bookings.all():
                booking.status = 'confirmed'
                booking.confirmed_at = timezone.now()
                booking.save()
            
            # Trigger background tasks
            from qr_code.tasks import generate_qr_code_for_order, send_payment_confirmation_email
            send_payment_confirmation_email.delay(str(order.id))
            generate_qr_code_for_order.delay(str(order.id))
            
            logger.info(f"Payment {payment.id} processed successfully")
            
            return {
                'success': True,
                'message': 'Payment processed successfully'
            }
        
        except Exception as e:
            logger.error(f"Error handling Paystack charge.success: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def handle_charge_failed(self, payload):
        """
        Handle failed charge event from Paystack
        
        Args:
            payload (dict): Webhook payload
            
        Returns:
            dict: Response status
        """
        try:
            reference = payload.get('data', {}).get('reference')
            
            if not reference:
                return {'success': False, 'error': 'No reference in payload'}
            
            # Get payment
            try:
                payment = Payment.objects.get(gateway_transaction_id=reference)
            except Payment.DoesNotExist:
                return {'success': False, 'error': 'Payment not found'}
            
            # Update payment
            payment.status = 'failed'
            payment.gateway_response = payload
            payment.save()
            
            # Notify user
            order = payment.order
            Notification.objects.create(
                user=order.user,
                notification_type='payment_failed',
                channel='email',
                title='Payment Failed',
                message=f'Payment for order {order.order_number} failed. Please try again.',
                is_sent=True,
                sent_at=timezone.now(),
                data={'order_id': str(order.id), 'payment_id': str(payment.id)}
            )
            
            logger.info(f"Payment {payment.id} marked as failed")
            
            return {
                'success': True,
                'message': 'Payment failure recorded'
            }
        
        except Exception as e:
            logger.error(f"Error handling Paystack charge.failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def process_webhook(self, event, payload):
        """
        Process Paystack webhook events
        
        Args:
            event (str): Event type (e.g., 'charge.success')
            payload (dict): Event payload
            
        Returns:
            dict: Processing result
        """
        if event == 'charge.success':
            return self.handle_charge_success(payload)
        elif event == 'charge.failed':
            return self.handle_charge_failed(payload)
        else:
            logger.info(f"Unhandled Paystack event: {event}")
            return {'success': True, 'message': f'Event {event} ignored'}


class FlutterwaveWebhookHandler:
    """Handle Flutterwave payment webhooks"""
    
    def __init__(self):
        self.secret_hash = settings.FLUTTERWAVE_SECRET_KEY
    
    def verify_signature(self, request_body, signature_header):
        """
        Verify Flutterwave webhook signature
        
        Args:
            request_body (str): Raw request body
            signature_header (str): verifi-hash header
            
        Returns:
            bool: True if signature is valid
        """
        try:
            hash_object = hashlib.sha256(
                f"{request_body}{self.secret_hash}".encode('utf-8')
            )
            computed_hash = hash_object.hexdigest()
            return computed_hash == signature_header
        except Exception as e:
            logger.error(f"Signature verification error: {str(e)}")
            return False
    
    def handle_charge_completed(self, payload):
        """
        Handle charge.completed event from Flutterwave
        
        Args:
            payload (dict): Webhook payload
            
        Returns:
            dict: Response status
        """
        try:
            data = payload.get('data', {})
            tx_ref = data.get('tx_ref')
            status = data.get('status')
            
            if not tx_ref:
                return {
                    'success': False,
                    'error': 'No tx_ref in payload'
                }
            
            # Get payment
            try:
                payment = Payment.objects.get(gateway_transaction_id=tx_ref)
            except Payment.DoesNotExist:
                logger.warning(f"Payment with tx_ref {tx_ref} not found")
                return {
                    'success': False,
                    'error': 'Payment not found'
                }
            
            # Verify transaction with Flutterwave
            gateway = FlutterwaveGateway()
            verify_result = gateway.verify_transaction(data.get('id'))
            
            if not verify_result['success']:
                logger.error(f"Verification failed for tx_ref {tx_ref}")
                return {
                    'success': False,
                    'error': 'Verification failed'
                }
            
            # Check status
            if verify_result['status'] != 'successful':
                payment.status = 'failed'
                payment.save()
                return {
                    'success': False,
                    'error': f"Payment status: {verify_result['status']}"
                }
            
            # Verify amount
            if verify_result['amount'] != payment.amount:
                logger.error(f"Amount mismatch for payment {payment.id}")
                payment.status = 'failed'
                payment.save()
                return {
                    'success': False,
                    'error': 'Amount mismatch'
                }
            
            # Update payment
            payment.status = 'success'
            payment.completed_at = timezone.now()
            payment.gateway_response = payload
            payment.save()
            
            # Update order
            order = payment.order
            order.status = 'paid'
            order.payment_method = 'flutterwave'
            order.payment_reference = tx_ref
            order.paid_at = timezone.now()
            order.save()
            
            # Update bookings
            for booking in order.bookings.all():
                booking.status = 'confirmed'
                booking.confirmed_at = timezone.now()
                booking.save()
            
            # Trigger background tasks
            from qr_code.tasks import generate_qr_code_for_order, send_payment_confirmation_email
            send_payment_confirmation_email.delay(str(order.id))
            generate_qr_code_for_order.delay(str(order.id))
            
            logger.info(f"Payment {payment.id} processed successfully via Flutterwave")
            
            return {
                'success': True,
                'message': 'Payment processed successfully'
            }
        
        except Exception as e:
            logger.error(f"Error handling Flutterwave charge.completed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def process_webhook(self, event, payload):
        """
        Process Flutterwave webhook events
        
        Args:
            event (str): Event type
            payload (dict): Event payload
            
        Returns:
            dict: Processing result
        """
        if event == 'charge.completed':
            return self.handle_charge_completed(payload)
        else:
            logger.info(f"Unhandled Flutterwave event: {event}")
            return {'success': True, 'message': f'Event {event} ignored'}


def handle_webhook(request_data, payment_method, signature_header=None):
    """
    Main webhook handler router
    
    Args:
        request_data (dict): Webhook payload
        payment_method (str): 'paystack' or 'flutterwave'
        signature_header (str): Signature from header for verification
        
    Returns:
        dict: Processing result
    """
    try:
        if payment_method == 'paystack':
            handler = PaystackWebhookHandler()
            
            # Verify signature if provided
            if signature_header:
                request_body = json.dumps(request_data)
                if not handler.verify_signature(request_body, signature_header):
                    logger.error("Paystack signature verification failed")
                    return {
                        'success': False,
                        'error': 'Invalid signature'
                    }
            
            # Process event
            event = request_data.get('event')
            return handler.process_webhook(event, request_data)
        
        elif payment_method == 'flutterwave':
            handler = FlutterwaveWebhookHandler()
            
            # Verify signature if provided
            if signature_header:
                request_body = json.dumps(request_data)
                if not handler.verify_signature(request_body, signature_header):
                    logger.error("Flutterwave signature verification failed")
                    return {
                        'success': False,
                        'error': 'Invalid signature'
                    }
            
            # Process event
            event = request_data.get('event')
            return handler.process_webhook(event, request_data)
        
        else:
            return {
                'success': False,
                'error': f'Unknown payment method: {payment_method}'
            }
    
    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }
