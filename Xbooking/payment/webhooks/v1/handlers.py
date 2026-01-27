"""
Payment Webhook Handlers V1 - Paystack and Flutterwave
"""
import hashlib
import hmac
import logging
from django.utils import timezone
from django.conf import settings
from django.db import transaction

from payment.models import Payment, PaymentWebhook, Order
from payment.gateways import PaystackGateway, FlutterwaveGateway
from payment.services import PaymentService
from booking.models import Booking
from bank.models import Deposit
from bank.services import BankService
from core.services import EventBus, Event

logger = logging.getLogger(__name__)


class PaystackWebhookHandler:
    """Handle Paystack payment webhooks V1"""
    
    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
    
    def verify_signature(self, request_body, signature_header):
        """
        Verify Paystack webhook signature using HMAC-SHA512
        
        Args:
            request_body (bytes or str): Raw request body
            signature_header (str): X-Paystack-Signature header
            
        Returns:
            bool: True if signature is valid
        """
        try:
            if signature_header is None:
                logger.warning("No signature header provided")
                return False
            
            # Ensure request_body is bytes
            if isinstance(request_body, str):
                request_body = request_body.encode('utf-8')
            
            # Compute HMAC-SHA512 signature
            computed_signature = hmac.new(
                self.secret_key.encode('utf-8'),
                request_body,
                hashlib.sha512
            ).hexdigest()
            
            # Compare signatures (timing-safe comparison)
            is_valid = hmac.compare_digest(computed_signature, signature_header)
            
            if not is_valid:
                logger.warning(f"Signature mismatch. Expected: {computed_signature[:20]}..., Got: {signature_header[:20]}...")
            
            return is_valid
        except Exception as e:
            logger.error(f"Signature verification error: {str(e)}")
            return False
    
    @transaction.atomic
    def handle_charge_success(self, payload):
        """Handle successful charge event from Paystack (payments and deposits)"""
        try:
            reference = payload.get('data', {}).get('reference')
            
            if not reference:
                return {'success': False, 'error': 'No reference in payload'}
            
            # Check if it's a deposit (reference starts with DEP-)
            if reference.startswith('DEP-'):
                return self.handle_deposit_success(payload, reference)
            
            # Otherwise handle as payment
            # Get payment
            try:
                payment = Payment.objects.select_related('order', 'order__workspace', 'order__user').get(
                    gateway_transaction_id=reference
                )
            except Payment.DoesNotExist:
                logger.warning(f"Payment with reference {reference} not found")
                return {'success': False, 'error': 'Payment not found'}
            
            # Verify transaction with Paystack
            gateway = PaystackGateway()
            verify_result = gateway.verify_transaction(reference)
            
            if not verify_result['success']:
                logger.error(f"Verification failed for reference {reference}")
                return {'success': False, 'error': 'Verification failed'}
            
            # Check status
            if verify_result['status'] != 'success':
                payment.status = 'failed'
                payment.save()
                return {'success': False, 'error': f"Payment status: {verify_result['status']}"}
            
            # Verify amount
            if verify_result['amount'] != payment.amount:
                logger.error(f"Amount mismatch for payment {payment.id}")
                payment.status = 'failed'
                payment.save()
                return {'success': False, 'error': 'Amount mismatch'}
            
            # Complete payment using service
            PaymentService.complete_payment(payment, gateway_response=payload)
            
            logger.info(f"Paystack payment {payment.id} processed successfully")
            
            return {'success': True, 'message': 'Payment processed successfully'}
        
        except Exception as e:
            logger.error(f"Error handling Paystack charge.success: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    @transaction.atomic
    def handle_deposit_success(self, payload, reference):
        """Handle successful deposit via Paystack"""
        try:
            # Get deposit
            try:
                deposit = Deposit.objects.select_related('wallet', 'wallet__user').get(
                    reference=reference
                )
            except Deposit.DoesNotExist:
                logger.warning(f"Deposit with reference {reference} not found")
                return {'success': False, 'error': 'Deposit not found'}
            
            # Skip if already completed
            if deposit.status == 'completed':
                logger.info(f"Deposit {deposit.id} already completed")
                return {'success': True, 'message': 'Deposit already completed'}
            
            # Verify transaction with Paystack
            gateway = PaystackGateway()
            verify_result = gateway.verify_transaction(reference)
            
            if not verify_result['success']:
                logger.error(f"Deposit verification failed for reference {reference}")
                return {'success': False, 'error': 'Verification failed'}
            
            # Check status
            if verify_result['status'] != 'success':
                deposit.status = 'failed'
                deposit.failed_at = timezone.now()
                deposit.failure_reason = f"Payment status: {verify_result['status']}"
                deposit.save()
                return {'success': False, 'error': f"Payment status: {verify_result['status']}"}
            
            # Verify amount
            from decimal import Decimal
            if Decimal(str(verify_result['amount'])) < deposit.amount:
                logger.error(f"Amount mismatch for deposit {deposit.id}")
                deposit.status = 'failed'
                deposit.failed_at = timezone.now()
                deposit.failure_reason = 'Amount mismatch'
                deposit.save()
                return {'success': False, 'error': 'Amount mismatch'}
            
            # Complete deposit using service
            BankService.complete_deposit(deposit, gateway_response=payload)
            
            logger.info(f"Paystack deposit {deposit.id} processed successfully")
            
            return {'success': True, 'message': 'Deposit processed successfully'}
        
        except Exception as e:
            logger.error(f"Error handling Paystack deposit success: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    @transaction.atomic
    def handle_charge_failed(self, payload):
        """Handle failed charge event from Paystack"""
        try:
            reference = payload.get('data', {}).get('reference')
            
            if not reference:
                return {'success': False, 'error': 'No reference in payload'}
            
            # Get payment
            try:
                payment = Payment.objects.select_related('order__user').get(
                    gateway_transaction_id=reference
                )
            except Payment.DoesNotExist:
                return {'success': False, 'error': 'Payment not found'}
            
            # Update payment
            payment.status = 'failed'
            payment.gateway_response = payload
            payment.save()
            
            # Publish payment failed event
            event = Event(
                event_type='PAYMENT_FAILED',
                data={
                    'payment_id': str(payment.id),
                    'order_id': str(payment.order.id),
                    'order_number': payment.order.order_number,
                    'user_id': str(payment.user.id),
                    'user_email': payment.user.email,
                    'error': 'Charge failed',
                    'timestamp': timezone.now().isoformat()
                },
                source_module='payment'
            )
            EventBus.publish(event)
            
            logger.info(f"Payment {payment.id} marked as failed")
            
            return {'success': True, 'message': 'Payment failure recorded'}
        
        except Exception as e:
            logger.error(f"Error handling Paystack charge.failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def process_webhook(self, event, payload):
        """Process Paystack webhook events"""
        if event == 'charge.success':
            return self.handle_charge_success(payload)
        elif event == 'charge.failed':
            return self.handle_charge_failed(payload)
        else:
            logger.info(f"Unhandled Paystack event: {event}")
            return {'success': True, 'message': f'Event {event} ignored'}


class FlutterwaveWebhookHandler:
    """Handle Flutterwave payment webhooks V1"""
    
    def __init__(self):
        self.secret_hash = settings.FLUTTERWAVE_SECRET_KEY
    
    def verify_signature(self, request_body, signature_header):
        """Verify Flutterwave webhook signature"""
        try:
            hash_object = hashlib.sha256(
                f"{request_body}{self.secret_hash}".encode('utf-8')
            )
            computed_hash = hash_object.hexdigest()
            return computed_hash == signature_header
        except Exception as e:
            logger.error(f"Signature verification error: {str(e)}")
            return False
    
    @transaction.atomic
    def handle_charge_completed(self, payload):
        """Handle charge.completed event from Flutterwave (payments and deposits)"""
        try:
            data = payload.get('data', {})
            tx_ref = data.get('tx_ref') or data.get('txRef')
            
            if not tx_ref:
                return {'success': False, 'error': 'No tx_ref in payload'}
            
            # Check if it's a deposit (tx_ref starts with DEP-)
            if tx_ref.startswith('DEP-'):
                return self.handle_deposit_completed(payload, data, tx_ref)
            
            # Otherwise handle as payment
            # Get payment
            try:
                payment = Payment.objects.select_related('order', 'order__workspace', 'order__user').get(
                    gateway_transaction_id=tx_ref
                )
            except Payment.DoesNotExist:
                logger.warning(f"Payment with tx_ref {tx_ref} not found")
                return {'success': False, 'error': 'Payment not found'}
            
            # Verify transaction with Flutterwave
            gateway = FlutterwaveGateway()
            verify_result = gateway.verify_transaction(data.get('id'))
            
            if not verify_result['success']:
                logger.error(f"Verification failed for tx_ref {tx_ref}")
                return {'success': False, 'error': 'Verification failed'}
            
            # Check status
            if verify_result['status'] != 'successful':
                payment.status = 'failed'
                payment.save()
                return {'success': False, 'error': f"Payment status: {verify_result['status']}"}
            
            # Verify amount
            if verify_result['amount'] != payment.amount:
                logger.error(f"Amount mismatch for payment {payment.id}")
                payment.status = 'failed'
                payment.save()
                return {'success': False, 'error': 'Amount mismatch'}
            
            # Complete payment using service
            PaymentService.complete_payment(payment, gateway_response=payload)
            
            logger.info(f"Flutterwave payment {payment.id} processed successfully")
            
            return {'success': True, 'message': 'Payment processed successfully'}
        
        except Exception as e:
            logger.error(f"Error handling Flutterwave charge.completed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    @transaction.atomic
    def handle_deposit_completed(self, payload, data, tx_ref):
        """Handle successful deposit via Flutterwave"""
        try:
            # Get deposit
            try:
                deposit = Deposit.objects.select_related('wallet', 'wallet__user').get(
                    reference=tx_ref
                )
            except Deposit.DoesNotExist:
                logger.warning(f"Deposit with reference {tx_ref} not found")
                return {'success': False, 'error': 'Deposit not found'}
            
            # Skip if already completed
            if deposit.status == 'completed':
                logger.info(f"Deposit {deposit.id} already completed")
                return {'success': True, 'message': 'Deposit already completed'}
            
            # Verify transaction with Flutterwave
            gateway = FlutterwaveGateway()
            verify_result = gateway.verify_transaction(data.get('id'))
            
            if not verify_result['success']:
                logger.error(f"Deposit verification failed for reference {tx_ref}")
                return {'success': False, 'error': 'Verification failed'}
            
            # Check status
            if verify_result['status'] != 'successful':
                deposit.status = 'failed'
                deposit.failed_at = timezone.now()
                deposit.failure_reason = f"Payment status: {verify_result['status']}"
                deposit.save()
                return {'success': False, 'error': f"Payment status: {verify_result['status']}"}
            
            # Verify amount
            from decimal import Decimal
            if Decimal(str(verify_result['amount'])) < deposit.amount:
                logger.error(f"Amount mismatch for deposit {deposit.id}")
                deposit.status = 'failed'
                deposit.failed_at = timezone.now()
                deposit.failure_reason = 'Amount mismatch'
                deposit.save()
                return {'success': False, 'error': 'Amount mismatch'}
            
            # Complete deposit using service
            BankService.complete_deposit(deposit, gateway_response=payload)
            
            logger.info(f"Flutterwave deposit {deposit.id} processed successfully")
            
            return {'success': True, 'message': 'Deposit processed successfully'}
        
        except Exception as e:
            logger.error(f"Error handling Flutterwave deposit completed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def process_webhook(self, event, payload):
        """Process Flutterwave webhook events"""
        if event == 'charge.completed':
            return self.handle_charge_completed(payload)
        else:
            logger.info(f"Unhandled Flutterwave event: {event}")
            return {'success': True, 'message': f'Event {event} ignored'}
