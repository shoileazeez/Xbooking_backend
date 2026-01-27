"""
Bank Account Management Service for Users and Workspaces
"""
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class BankAccountService:
    """Service for managing bank accounts and user withdrawals"""
    
    @staticmethod
    @transaction.atomic
    def add_bank_account(owner, account_number, account_name, bank_name, bank_code, account_type='savings'):
        """
        Add a new bank account for user or workspace
        
        Args:
            owner: User or Workspace instance
            account_number: Bank account number
            account_name: Account holder name
            bank_name: Bank name
            bank_code: Bank code
            account_type: 'savings' or 'current'
            
        Returns:
            BankAccount instance
            
        Raises:
            ValidationError: If validation fails
        """
        from bank.models import BankAccount
        
        # Validation
        if not account_number or not account_name or not bank_name:
            raise ValidationError("Account number, name, and bank are required")
        
        if len(account_number) < 8 or len(account_number) > 20:
            raise ValidationError("Account number must be 8-20 characters")
        
        # Check for duplicates
        is_user = hasattr(owner, 'email')  # Quick check if it's a User
        
        if is_user:
            existing = BankAccount.objects.filter(
                user=owner,
                account_number=account_number,
                bank_code=bank_code
            ).exists()
        else:
            existing = BankAccount.objects.filter(
                workspace=owner,
                account_number=account_number,
                bank_code=bank_code
            ).exists()
        
        if existing:
            raise ValidationError("This bank account is already registered")
        
        # Create account
        if is_user:
            account = BankAccount.objects.create(
                user=owner,
                account_number=account_number,
                account_name=account_name,
                bank_name=bank_name,
                bank_code=bank_code,
                account_type=account_type,
                is_active=True
            )
        else:
            account = BankAccount.objects.create(
                workspace=owner,
                account_number=account_number,
                account_name=account_name,
                bank_name=bank_name,
                bank_code=bank_code,
                account_type=account_type,
                is_active=True
            )
        
        logger.info(f"Created bank account {account.id} for {account_name}")
        
        return account
    
    @staticmethod
    @transaction.atomic
    def update_bank_account(account, account_name=None, account_type=None):
        """
        Update bank account details
        
        Args:
            account: BankAccount instance
            account_name: New account name
            account_type: New account type
            
        Returns:
            Updated BankAccount instance
        """
        if account_name:
            account.account_name = account_name
        
        if account_type:
            account.account_type = account_type
        
        account.save()
        return account
    
    @staticmethod
    @transaction.atomic
    def set_default_account(account):
        """
        Set account as default for withdrawals
        
        Args:
            account: BankAccount instance
            
        Returns:
            BankAccount instance
        """
        from bank.models import BankAccount
        
        # Get owner
        owner = account.user or account.workspace
        
        # Unset other defaults
        if account.user:
            BankAccount.objects.filter(user=owner).update(is_default=False)
        else:
            BankAccount.objects.filter(workspace=owner).update(is_default=False)
        
        # Set this as default
        account.is_default = True
        account.save()
        
        return account
    
    @staticmethod
    @transaction.atomic
    def delete_bank_account(account):
        """
        Delete a bank account (soft delete)
        
        Args:
            account: BankAccount instance
        """
        # Check if there are pending withdrawals
        if account.withdrawal_requests.filter(status__in=['pending', 'processing']).exists():
            raise ValidationError("Cannot delete account with pending withdrawals")
        
        account.is_active = False
        account.is_default = False
        account.save()
        
        logger.info(f"Deactivated bank account {account.id}")
    
    @staticmethod
    def verify_bank_account(account, verification_method='instant'):
        """
        Mark bank account as verified
        
        In production, this would validate against bank API
        
        Args:
            account: BankAccount instance
            verification_method: Method used ('instant', 'otp', 'transfer')
            
        Returns:
            BankAccount instance
        """
        account.is_verified = True
        account.verified_at = timezone.now()
        account.verification_method = verification_method
        account.save()
        
        return account


class WithdrawalService:
    """Service for handling user and workspace withdrawals"""
    
    @staticmethod
    @transaction.atomic
    def request_withdrawal(owner_wallet, bank_account, amount, user, payment_provider='paystack'):
        """
        Request a withdrawal from wallet to bank account
        
        Args:
            owner_wallet: Wallet or WorkspaceWallet instance
            bank_account: BankAccount instance
            amount: Withdrawal amount
            user: User requesting withdrawal
            payment_provider: Payment provider to use ('paystack' or 'flutterwave')
            
        Returns:
            WithdrawalRequest instance
            
        Raises:
            ValidationError: If withdrawal cannot be processed
        """
        from bank.models import WithdrawalRequest, Transaction, Wallet, WorkspaceWallet
        
        # Validation
        if amount <= Decimal('0'):
            raise ValidationError("Withdrawal amount must be greater than 0")
        
        if amount < Decimal('1000'):  # Minimum 1000 NGN
            raise ValidationError("Minimum withdrawal amount is 1000 NGN")
        
        if not bank_account.is_verified:
            raise ValidationError("Bank account must be verified before withdrawal")
        
        if not bank_account.is_active:
            raise ValidationError("Bank account is not active")
        
        # Check balance
        if owner_wallet.balance < amount:
            raise ValidationError(f"Insufficient balance. Available: {owner_wallet.balance}")
        
        # Calculate fee (2% or fixed, whichever is higher)
        fee = max(amount * Decimal('0.02'), Decimal('100'))  # 2% or 100 NGN minimum
        net_amount = amount - fee
        
        # Create withdrawal request
        import uuid
        reference = f"WD-{uuid.uuid4().hex[:12].upper()}"
        
        # Determine if it's user wallet or workspace wallet
        is_workspace_wallet = isinstance(owner_wallet, WorkspaceWallet)
        
        withdrawal = WithdrawalRequest.objects.create(
            wallet=None if is_workspace_wallet else owner_wallet,
            workspace_wallet=owner_wallet if is_workspace_wallet else None,
            bank_account=bank_account,
            requested_by=user,
            amount=amount,
            fee=fee,
            net_amount=net_amount,
            currency=owner_wallet.currency,
            status='pending',
            reference=reference
        )
        
        # Create pending transaction
        transaction = Transaction.objects.create(
            reference=f"TXN-{reference}",
            transaction_type='debit',
            category='withdrawal',
            amount=amount,
            currency=owner_wallet.currency,
            wallet=None if is_workspace_wallet else owner_wallet,
            workspace_wallet=owner_wallet if is_workspace_wallet else None,
            withdrawal_request=withdrawal,
            balance_before=owner_wallet.balance,
            balance_after=owner_wallet.balance - amount,  # Preview
            status='pending',
            description=f"Withdrawal request to {bank_account.bank_name} - {bank_account.account_number}"
        )
        
        logger.info(f"Created withdrawal request {reference} for {amount} NGN")
        
        # Send notification
        WithdrawalService._notify_withdrawal_request(withdrawal)
        
        return withdrawal
    
    @staticmethod
    @transaction.atomic
    def process_withdrawal(withdrawal, gateway_handler):
        """
        Process withdrawal transfer via payment gateway handler
        
        Args:
            withdrawal: WithdrawalRequest instance
            gateway_handler: PaystackGateway or FlutterwaveGateway instance
            
        Returns:
            WithdrawalRequest instance
            
        Raises:
            ValidationError: If processing fails
        """
        from bank.models import Transaction
        from payment.gateways import PaystackGateway, FlutterwaveGateway
        
        if withdrawal.status != 'pending':
            raise ValidationError(f"Cannot process {withdrawal.status} withdrawal")
        
        if not withdrawal.bank_account.is_verified:
            raise ValidationError("Bank account is not verified")
        
        try:
            bank = withdrawal.bank_account
            
            # Process via appropriate gateway
            if isinstance(gateway_handler, PaystackGateway):
                # Create recipient first
                recipient_result = gateway_handler.create_transfer_recipient(
                    type_account='nuban',
                    account_number=bank.account_number,
                    bank_code=bank.bank_code,
                    name=bank.account_name
                )
                
                if not recipient_result.get('success'):
                    raise ValidationError(f"Failed to create recipient: {recipient_result.get('error')}")
                
                # Initiate transfer
                transfer_result = gateway_handler.initiate_transfer(
                    source='balance',
                    reason=f"Withdrawal: {withdrawal.reference}",
                    amount=withdrawal.net_amount,
                    recipient_code=recipient_result['recipient_code']
                )
                
                if not transfer_result.get('success'):
                    raise ValidationError(f"Transfer failed: {transfer_result.get('error')}")
                
                gateway_reference = transfer_result.get('reference')
                
            elif isinstance(gateway_handler, FlutterwaveGateway):
                # Flutterwave direct transfer
                transfer_result = gateway_handler.initiate_transfer(
                    account_bank=bank.bank_code,
                    account_number=bank.account_number,
                    amount=withdrawal.net_amount,
                    narration=f"Withdrawal: {withdrawal.reference}",
                    beneficiary_name=bank.account_name
                )
                
                if not transfer_result.get('success'):
                    raise ValidationError(f"Transfer failed: {transfer_result.get('error')}")
                
                gateway_reference = transfer_result.get('reference')
            else:
                raise ValidationError("Invalid gateway handler")
            
            # Update withdrawal
            withdrawal.status = 'processing'
            withdrawal.gateway_reference = gateway_reference
            withdrawal.processed_at = timezone.now()
            withdrawal.save()
            
            # Update transaction
            transaction = withdrawal.transactions.first()
            if transaction:
                transaction.status = 'processing'
                transaction.processed_at = timezone.now()
                transaction.save()
            
            logger.info(f"Processing withdrawal {withdrawal.reference} via gateway")
            
            return withdrawal
        except Exception as e:
            logger.error(f"Failed to process withdrawal {withdrawal.reference}: {str(e)}")
            
            # Mark as failed
            withdrawal.status = 'failed'
            withdrawal.failed_at = timezone.now()
            withdrawal.save()
            
            raise ValidationError(f"Withdrawal processing failed: {str(e)}")
    
    @staticmethod
    def complete_withdrawal(withdrawal):
        """
        Mark withdrawal as completed after successful transfer
        
        Args:
            withdrawal: WithdrawalRequest instance
            
        Returns:
            WithdrawalRequest instance
        """
        from bank.models import Transaction
        
        now = timezone.now()
        
        # Update withdrawal
        withdrawal.status = 'completed'
        withdrawal.completed_at = now
        withdrawal.save()
        
        # Update transaction
        transaction = withdrawal.transactions.first()
        if transaction:
            transaction.status = 'completed'
            transaction.processed_at = now
            transaction.save()
        
        # Debit wallet (supports both user and workspace wallets)
        wallet = withdrawal.wallet or withdrawal.workspace_wallet
        wallet.balance -= withdrawal.amount
        
        # Update total_withdrawn for workspace wallets
        if hasattr(wallet, 'total_withdrawn'):
            wallet.total_withdrawn += withdrawal.amount
            wallet.save(update_fields=['balance', 'total_withdrawn'])
        else:
            wallet.save(update_fields=['balance'])
        
        logger.info(f"Completed withdrawal {withdrawal.reference} for {withdrawal.amount}")
        
        # Send notification
        WithdrawalService._notify_withdrawal_completed(withdrawal)
        
        return withdrawal
    
    @staticmethod
    def fail_withdrawal(withdrawal, failure_reason):
        """
        Mark withdrawal as failed
        
        Args:
            withdrawal: WithdrawalRequest instance
            failure_reason: Reason for failure
        """
        from bank.models import Transaction
        
        now = timezone.now()
        
        # Update withdrawal
        withdrawal.status = 'failed'
        withdrawal.failed_at = now
        withdrawal.gateway_response = {'error': failure_reason}
        withdrawal.save()
        
        # Update transaction
        transaction = withdrawal.transactions.first()
        if transaction:
            transaction.status = 'failed'
            transaction.failed_at = now
            transaction.failure_reason = failure_reason
            transaction.save()
        
        logger.error(f"Withdrawal {withdrawal.reference} failed: {failure_reason}")
        
        # Send notification
        WithdrawalService._notify_withdrawal_failed(withdrawal, failure_reason)
    

    
    @staticmethod
    def _notify_withdrawal_request(withdrawal):
        """Send withdrawal request confirmation"""
        from core.notification_service import NotificationService
        
        try:
            user = withdrawal.requested_by
            NotificationService.send_email(
                user=user,
                template='withdrawal_requested',
                context={
                    'user_name': user.full_name or user.email,
                    'amount': str(withdrawal.amount),
                    'fee': str(withdrawal.fee),
                    'net_amount': str(withdrawal.net_amount),
                    'bank_name': withdrawal.bank_account.bank_name,
                    'account_number': withdrawal.bank_account.account_number[-4:],  # Last 4 digits
                    'reference': withdrawal.reference,
                }
            )
        except Exception as e:
            logger.error(f"Failed to send withdrawal request notification: {str(e)}")
    
    @staticmethod
    def _notify_withdrawal_completed(withdrawal):
        """Send withdrawal completion notification"""
        from core.notification_service import NotificationService
        
        try:
            user = withdrawal.requested_by
            NotificationService.send_email(
                user=user,
                template='withdrawal_completed',
                context={
                    'user_name': user.full_name or user.email,
                    'amount': str(withdrawal.net_amount),
                    'bank_name': withdrawal.bank_account.bank_name,
                    'account_number': withdrawal.bank_account.account_number[-4:],
                    'reference': withdrawal.reference,
                    'completed_at': withdrawal.completed_at.strftime('%Y-%m-%d %H:%M'),
                }
            )
        except Exception as e:
            logger.error(f"Failed to send withdrawal completion notification: {str(e)}")
    
    @staticmethod
    def _notify_withdrawal_failed(withdrawal, reason):
        """Send withdrawal failure notification"""
        from core.notification_service import NotificationService
        
        try:
            user = withdrawal.requested_by
            NotificationService.send_email(
                user=user,
                template='withdrawal_failed',
                context={
                    'user_name': user.full_name or user.email,
                    'amount': str(withdrawal.amount),
                    'reason': reason,
                    'reference': withdrawal.reference,
                }
            )
        except Exception as e:
            logger.error(f"Failed to send withdrawal failure notification: {str(e)}")
