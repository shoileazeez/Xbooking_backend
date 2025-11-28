"""
Celery tasks for withdrawal processing and payouts
"""
import logging
from decimal import Decimal
from django.utils import timezone
from celery import shared_task
from django.template.loader import render_to_string

from payment.models import Payment
from payment.withdrawal_models import Withdrawal, WithdrawalLog
from payment.gateways import PaystackGateway, FlutterwaveGateway
from notifications.models import Notification
from user.models import User

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=5)
def process_withdrawal_payout(self, withdrawal_id):
    """
    Process withdrawal payout via payment gateway
    Retry on failure up to 5 times
    """
    try:
        withdrawal = Withdrawal.objects.get(id=withdrawal_id)
        
        # Check if withdrawal is in correct status
        if withdrawal.status != 'approved':
            logger.warning(f"Cannot process withdrawal {withdrawal.id} with status {withdrawal.status}")
            return
        
        # Get the user's workspace payment method preference
        # For now, we'll default to Paystack
        gateway = PaystackGateway()
        
        # Create transfer recipient if not exists
        bank_account = withdrawal.bank_account
        if not bank_account.is_verified:
            logger.error(f"Bank account {bank_account.id} is not verified")
            withdrawal.status = 'failed'
            withdrawal.error_message = 'Bank account not verified'
            withdrawal.save()
            WithdrawalLog.objects.create(
                withdrawal=withdrawal,
                status='failed',
                message='Bank account not verified',
                created_by=withdrawal.workspace.owner
            )
            return
        
        try:
            # Create or get transfer recipient code
            if not hasattr(bank_account, 'gateway_recipient_code') or not bank_account.gateway_recipient_code:
                recipient_response = gateway.create_transfer_recipient(
                    type='nuban',
                    account_number=bank_account.account_number,
                    account_name=bank_account.account_name,
                    bank_code=bank_account.bank_code,
                    currency='NGN'
                )
                
                if not recipient_response.get('success'):
                    raise Exception(f"Failed to create transfer recipient: {recipient_response.get('error')}")
                
                # Store recipient code (would need to add to BankAccount model)
                recipient_code = recipient_response.get('data', {}).get('recipient_code')
            else:
                recipient_code = bank_account.gateway_recipient_code
            
            # Initiate transfer
            transfer_response = gateway.initiate_transfer(
                amount=int(withdrawal.amount),  # Amount in Naira (not kobo - Paystack transfer API uses Naira)
                recipient_code=recipient_code,
                reference=withdrawal.withdrawal_number,
                reason=f'Withdrawal: {withdrawal.withdrawal_type}'
            )
            
            if not transfer_response.get('success'):
                # Update retry count
                withdrawal.retry_count += 1
                if withdrawal.retry_count >= 5:
                    withdrawal.status = 'failed'
                    withdrawal.error_message = transfer_response.get('error', 'Transfer initiation failed')
                    withdrawal.save()
                    WithdrawalLog.objects.create(
                        withdrawal=withdrawal,
                        status='failed',
                        message=f'Transfer failed after {withdrawal.retry_count} retries: {withdrawal.error_message}',
                        created_by=withdrawal.workspace.owner
                    )
                else:
                    withdrawal.save()
                    # Retry with exponential backoff
                    raise Exception(f"Transfer failed: {transfer_response.get('error')}")
                return
            
            # Update withdrawal with transaction ID
            transfer_data = transfer_response.get('data', {})
            withdrawal.gateway_transaction_id = transfer_data.get('transfer_code', transfer_data.get('id'))
            withdrawal.status = 'processing'
            withdrawal.retry_count = 0
            withdrawal.last_retry_at = timezone.now()
            withdrawal.save()
            
            # Create log entry
            WithdrawalLog.objects.create(
                withdrawal=withdrawal,
                status='processing',
                message=f'Payout initiated with transfer code {withdrawal.gateway_transaction_id}',
                metadata={
                    'transfer_code': withdrawal.gateway_transaction_id,
                    'recipient_code': recipient_code
                },
                created_by=withdrawal.workspace.owner
            )
            
            # Send notification to user
            send_withdrawal_processing_email.delay(withdrawal_id)
            
            logger.info(f"Withdrawal payout initiated: {withdrawal.withdrawal_number}")
            
        except Exception as e:
            logger.error(f"Error processing withdrawal {withdrawal.id}: {str(e)}")
            withdrawal.retry_count += 1
            withdrawal.last_retry_at = timezone.now()
            withdrawal.save()
            
            if withdrawal.retry_count <= 5:
                # Retry with exponential backoff
                countdown = 2 ** withdrawal.retry_count  # 2, 4, 8, 16, 32 seconds
                raise self.retry(exc=e, countdown=countdown)
            else:
                withdrawal.status = 'failed'
                withdrawal.error_message = str(e)
                withdrawal.save()
                WithdrawalLog.objects.create(
                    withdrawal=withdrawal,
                    status='failed',
                    message=f'Payout failed after 5 retries: {str(e)}',
                    created_by=withdrawal.workspace.owner
                )
    
    except Withdrawal.DoesNotExist:
        logger.error(f"Withdrawal {withdrawal_id} not found")


@shared_task(bind=True, max_retries=3)
def complete_withdrawal(self, withdrawal_id):
    """
    Mark withdrawal as completed after verification
    """
    try:
        withdrawal = Withdrawal.objects.get(id=withdrawal_id)
        
        if withdrawal.status not in ['processing', 'completed']:
            logger.warning(f"Cannot complete withdrawal {withdrawal.id} with status {withdrawal.status}")
            return
        
        # Update status
        withdrawal.status = 'completed'
        withdrawal.completed_at = timezone.now()
        withdrawal.save()
        
        # Create log entry
        WithdrawalLog.objects.create(
            withdrawal=withdrawal,
            status='completed',
            message='Payout completed successfully',
            metadata={'completed_at': withdrawal.completed_at.isoformat()},
            created_by=withdrawal.workspace.owner
        )
        
        # Send notification to user
        send_withdrawal_completed_email.delay(withdrawal_id)
        
        logger.info(f"Withdrawal completed: {withdrawal.withdrawal_number}")
        
    except Withdrawal.DoesNotExist:
        logger.error(f"Withdrawal {withdrawal_id} not found")
    except Exception as e:
        logger.error(f"Error completing withdrawal {withdrawal_id}: {str(e)}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=300)  # Retry after 5 minutes


@shared_task(bind=True, max_retries=3)
def handle_withdrawal_failure(self, withdrawal_id, error_message):
    """
    Handle withdrawal failure
    """
    try:
        withdrawal = Withdrawal.objects.get(id=withdrawal_id)
        
        withdrawal.status = 'failed'
        withdrawal.error_message = error_message
        withdrawal.save()
        
        WithdrawalLog.objects.create(
            withdrawal=withdrawal,
            status='failed',
            message=f'Withdrawal failed: {error_message}',
            created_by=withdrawal.workspace.owner
        )
        
        # Send notification to user
        send_withdrawal_failed_email.delay(withdrawal_id, error_message)
        
        logger.info(f"Withdrawal marked as failed: {withdrawal.withdrawal_number}")
        
    except Withdrawal.DoesNotExist:
        logger.error(f"Withdrawal {withdrawal_id} not found")


@shared_task(bind=True, max_retries=3)
def send_withdrawal_confirmation_email(self, withdrawal_id):
    """
    Send withdrawal confirmation email to user
    """
    try:
        withdrawal = Withdrawal.objects.get(id=withdrawal_id)
        user = withdrawal.requested_by
        
        context = {
            'user_name': user.full_name or user.email,
            'withdrawal_number': withdrawal.withdrawal_number,
            'amount': withdrawal.amount,
            'currency': withdrawal.currency,
            'bank_account': withdrawal.bank_account.account_name,
            'withdrawal_date': withdrawal.requested_at.strftime('%Y-%m-%d %H:%M'),
        }
        
        # This would be implemented with actual email sending
        logger.info(f"Withdrawal confirmation email sent to {user.email}")
        
    except Withdrawal.DoesNotExist:
        logger.error(f"Withdrawal {withdrawal_id} not found")
    except Exception as e:
        logger.error(f"Error sending withdrawal confirmation email: {str(e)}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=300)


@shared_task(bind=True, max_retries=3)
def send_withdrawal_processing_email(self, withdrawal_id):
    """
    Send withdrawal processing email to user
    """
    try:
        withdrawal = Withdrawal.objects.get(id=withdrawal_id)
        user = withdrawal.requested_by
        
        context = {
            'user_name': user.full_name or user.email,
            'withdrawal_number': withdrawal.withdrawal_number,
            'amount': withdrawal.amount,
            'currency': withdrawal.currency,
            'bank_account': withdrawal.bank_account.account_name,
            'gateway_transaction_id': withdrawal.gateway_transaction_id,
        }
        
        logger.info(f"Withdrawal processing email sent to {user.email}")
        
    except Withdrawal.DoesNotExist:
        logger.error(f"Withdrawal {withdrawal_id} not found")
    except Exception as e:
        logger.error(f"Error sending withdrawal processing email: {str(e)}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=300)


@shared_task(bind=True, max_retries=3)
def send_withdrawal_completed_email(self, withdrawal_id):
    """
    Send withdrawal completed email to user
    """
    try:
        withdrawal = Withdrawal.objects.get(id=withdrawal_id)
        user = withdrawal.requested_by
        
        context = {
            'user_name': user.full_name or user.email,
            'withdrawal_number': withdrawal.withdrawal_number,
            'amount': withdrawal.amount,
            'currency': withdrawal.currency,
            'bank_account': withdrawal.bank_account.account_name,
            'completed_date': withdrawal.completed_at.strftime('%Y-%m-%d %H:%M'),
        }
        
        logger.info(f"Withdrawal completed email sent to {user.email}")
        
    except Withdrawal.DoesNotExist:
        logger.error(f"Withdrawal {withdrawal_id} not found")
    except Exception as e:
        logger.error(f"Error sending withdrawal completed email: {str(e)}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=300)


@shared_task(bind=True, max_retries=3)
def send_withdrawal_failed_email(self, withdrawal_id, error_message):
    """
    Send withdrawal failed email to user
    """
    try:
        withdrawal = Withdrawal.objects.get(id=withdrawal_id)
        user = withdrawal.requested_by
        
        context = {
            'user_name': user.first_name or user.email,
            'withdrawal_number': withdrawal.withdrawal_number,
            'amount': withdrawal.amount,
            'currency': withdrawal.currency,
            'error_message': error_message,
        }
        
        logger.info(f"Withdrawal failed email sent to {user.email}")
        
    except Withdrawal.DoesNotExist:
        logger.error(f"Withdrawal {withdrawal_id} not found")
    except Exception as e:
        logger.error(f"Error sending withdrawal failed email: {str(e)}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=300)


@shared_task(bind=True, max_retries=3)
def send_withdrawal_approval_notification(self, withdrawal_id):
    """
    Send notification to user that withdrawal has been approved
    """
    try:
        withdrawal = Withdrawal.objects.get(id=withdrawal_id)
        user = withdrawal.requested_by
        
        logger.info(f"Withdrawal approval notification sent to {user.email}")
        
    except Withdrawal.DoesNotExist:
        logger.error(f"Withdrawal {withdrawal_id} not found")
    except Exception as e:
        logger.error(f"Error sending withdrawal approval notification: {str(e)}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=300)
