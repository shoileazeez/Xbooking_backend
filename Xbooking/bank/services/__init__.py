"""
Bank Service Layer - Handles all wallet and banking operations
"""
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from core.services import EventBus, Event
from core.cache import CacheService
from bank.models import (
    Wallet, WorkspaceWallet, Transaction, BankAccount,
    WithdrawalRequest, Deposit
)
import uuid


class BankService:
    """Service for managing in-app banking operations"""
    
    @staticmethod
    @transaction.atomic
    def create_wallet(user):
        """Create wallet for user"""
        wallet, created = Wallet.objects.get_or_create(
            user=user,
            defaults={'balance': Decimal('0.00')}
        )
        
        if created:
            event = Event(
                event_type='WALLET_CREATED',
                data={
                    'wallet_id': str(wallet.id),
                    'user_id': str(user.id),
                    'user_email': user.email,
                    'balance': str(wallet.balance),
                    'currency': wallet.currency,
                    'timestamp': timezone.now().isoformat()
                },
                source_module='bank'
            )
            EventBus.publish(event)
        
        return wallet, created
    
    @staticmethod
    @transaction.atomic
    def create_workspace_wallet(workspace):
        """Create wallet for workspace"""
        wallet, created = WorkspaceWallet.objects.get_or_create(
            workspace=workspace,
            defaults={'balance': Decimal('0.00')}
        )
        
        if created:
            event = Event(
                event_type='WORKSPACE_WALLET_CREATED',
                data={
                    'wallet_id': str(wallet.id),
                    'workspace_id': str(workspace.id),
                    'workspace_name': workspace.name,
                    'balance': str(wallet.balance),
                    'currency': wallet.currency,
                    'timestamp': timezone.now().isoformat()
                },
                source_module='bank'
            )
            EventBus.publish(event)
        
        return wallet, created
    
    @staticmethod
    @transaction.atomic
    def credit_wallet(wallet, amount, category, description, **kwargs):
        """Credit user wallet"""
        if amount <= 0:
            raise ValueError("Amount must be greater than zero")
        
        balance_before = wallet.balance
        wallet.balance += amount
        wallet.save(update_fields=['balance', 'updated_at'])
        
        # Create transaction record
        transaction_obj = Transaction.objects.create(
            reference=f"TXN-{uuid.uuid4().hex[:12].upper()}",
            transaction_type='credit',
            category=category,
            amount=amount,
            currency=wallet.currency,
            wallet=wallet,
            balance_before=balance_before,
            balance_after=wallet.balance,
            status='completed',
            description=description,
            processed_at=timezone.now(),
            **kwargs
        )
        
        # Publish event
        event = Event(
            event_type='WALLET_CREDITED',
            data={
                'transaction_id': str(transaction_obj.id),
                'wallet_id': str(wallet.id),
                'user_id': str(wallet.user.id),
                'user_email': wallet.user.email,
                'amount': str(amount),
                'balance': str(wallet.balance),
                'category': category,
                'description': description,
                'timestamp': timezone.now().isoformat()
            },
            source_module='bank'
        )
        EventBus.publish(event)
        
        # Invalidate cache
        CacheService.invalidate_model('wallet', str(wallet.id))
        
        return transaction_obj
    
    @staticmethod
    @transaction.atomic
    def debit_wallet(wallet, amount, category, description, **kwargs):
        """Debit user wallet"""
        if amount <= 0:
            raise ValueError("Amount must be greater than zero")
        
        if not wallet.can_debit(amount):
            raise ValueError("Insufficient balance or wallet is locked")
        
        balance_before = wallet.balance
        wallet.balance -= amount
        wallet.save(update_fields=['balance', 'updated_at'])
        
        # Create transaction record
        # Use provided reference or generate one
        reference = kwargs.pop('reference', f"TXN-{uuid.uuid4().hex[:12].upper()}")
        
        transaction_obj = Transaction.objects.create(
            reference=reference,
            transaction_type='debit',
            category=category,
            amount=amount,
            currency=wallet.currency,
            wallet=wallet,
            balance_before=balance_before,
            balance_after=wallet.balance,
            status='completed',
            description=description,
            processed_at=timezone.now(),
            **kwargs
        )
        
        # Publish event
        event = Event(
            event_type='WALLET_DEBITED',
            data={
                'transaction_id': str(transaction_obj.id),
                'wallet_id': str(wallet.id),
                'user_id': str(wallet.user.id),
                'user_email': wallet.user.email,
                'amount': str(amount),
                'balance': str(wallet.balance),
                'category': category,
                'description': description,
                'timestamp': timezone.now().isoformat()
            },
            source_module='bank'
        )
        EventBus.publish(event)
        
        # Invalidate cache
        CacheService.invalidate_model('wallet', str(wallet.id))
        
        return transaction_obj
    
    @staticmethod
    @transaction.atomic
    def credit_workspace_wallet(workspace_wallet, amount, category, description, **kwargs):
        """Credit workspace wallet (from booking payments)"""
        if amount <= 0:
            raise ValueError("Amount must be greater than zero")
        
        balance_before = workspace_wallet.balance
        workspace_wallet.balance += amount
        workspace_wallet.total_earnings += amount
        workspace_wallet.save(update_fields=['balance', 'total_earnings', 'updated_at'])
        
        # Create transaction record
        transaction_obj = Transaction.objects.create(
            reference=f"TXN-{uuid.uuid4().hex[:12].upper()}",
            transaction_type='credit',
            category=category,
            amount=amount,
            currency=workspace_wallet.currency,
            workspace_wallet=workspace_wallet,
            balance_before=balance_before,
            balance_after=workspace_wallet.balance,
            status='completed',
            description=description,
            processed_at=timezone.now(),
            **kwargs
        )
        
        # Publish event
        event = Event(
            event_type='WORKSPACE_WALLET_CREDITED',
            data={
                'transaction_id': str(transaction_obj.id),
                'wallet_id': str(workspace_wallet.id),
                'workspace_id': str(workspace_wallet.workspace.id),
                'workspace_name': workspace_wallet.workspace.name,
                'amount': str(amount),
                'balance': str(workspace_wallet.balance),
                'total_earnings': str(workspace_wallet.total_earnings),
                'category': category,
                'description': description,
                'timestamp': timezone.now().isoformat()
            },
            source_module='bank'
        )
        EventBus.publish(event)
        
        # Invalidate cache
        CacheService.invalidate_model('workspacewallet', str(workspace_wallet.id))
        
        return transaction_obj
    
    @staticmethod
    @transaction.atomic
    def debit_workspace_wallet(workspace_wallet, amount, category, description, **kwargs):
        """Debit workspace wallet (for withdrawals)"""
        if amount <= 0:
            raise ValueError("Amount must be greater than zero")
        
        if not workspace_wallet.can_withdraw(amount):
            raise ValueError("Insufficient balance")
        
        balance_before = workspace_wallet.balance
        workspace_wallet.balance -= amount
        workspace_wallet.save(update_fields=['balance', 'updated_at'])
        
        # Create transaction record
        transaction_obj = Transaction.objects.create(
            reference=f"TXN-{uuid.uuid4().hex[:12].upper()}",
            transaction_type='debit',
            category=category,
            amount=amount,
            currency=workspace_wallet.currency,
            workspace_wallet=workspace_wallet,
            balance_before=balance_before,
            balance_after=workspace_wallet.balance,
            status='completed',
            description=description,
            processed_at=timezone.now(),
            **kwargs
        )
        
        # Publish event
        event = Event(
            event_type='WORKSPACE_WALLET_DEBITED',
            data={
                'transaction_id': str(transaction_obj.id),
                'wallet_id': str(workspace_wallet.id),
                'workspace_id': str(workspace_wallet.workspace.id),
                'workspace_name': workspace_wallet.workspace.name,
                'amount': str(amount),
                'balance': str(workspace_wallet.balance),
                'category': category,
                'description': description,
                'timestamp': timezone.now().isoformat()
            },
            source_module='bank'
        )
        EventBus.publish(event)
        
        # Invalidate cache
        CacheService.invalidate_model('workspacewallet', str(workspace_wallet.id))
        
        return transaction_obj
    
    @staticmethod
    @transaction.atomic
    def initiate_deposit(wallet, amount, payment_method, gateway_handler=None):
        """Initiate deposit to user wallet with payment gateway integration"""
        deposit = Deposit.objects.create(
            wallet=wallet,
            amount=amount,
            payment_method=payment_method,
            reference=f"DEP-{uuid.uuid4().hex[:12].upper()}",
            status='pending'
        )
        
        # Initialize payment with gateway if provided
        gateway_response = None
        if gateway_handler:
            try:
                metadata = {
                    'deposit_id': str(deposit.id),
                    'wallet_id': str(wallet.id),
                    'user_id': str(wallet.user.id),
                    'user_email': wallet.user.email,
                    'type': 'wallet_deposit',
                    'description': 'Wallet Deposit'
                }
                from django.conf import settings
                deposit_redirect_url = getattr(settings, 'DEPOSIT_REDIRECT_URL', None)
                if deposit_redirect_url:
                    # Always add provider
                    sep = '&' if '?' in deposit_redirect_url else '?'
                    deposit_redirect_url = f"{deposit_redirect_url}{sep}provider={payment_method}"
                    # Add deposit_id if present
                    if deposit and getattr(deposit, 'id', None):
                        deposit_redirect_url += f"&deposit_id={deposit.id}"
                if payment_method == 'paystack':
                    gateway_response = gateway_handler.initialize_transaction(
                        email=wallet.user.email,
                        amount=float(amount),
                        reference=deposit.reference,
                        metadata=metadata,
                        redirect_url=deposit_redirect_url
                    )
                elif payment_method == 'flutterwave':
                    gateway_response = gateway_handler.initialize_transaction(
                        email=wallet.user.email,
                        amount=float(amount),
                        reference=deposit.reference,
                        metadata=metadata,
                        redirect_url=deposit_redirect_url
                    )
                
                if gateway_response and gateway_response.get('success'):
                    deposit.gateway_response = gateway_response
                    deposit.gateway_reference = gateway_response.get('reference')
                    deposit.status = 'processing'
                    deposit.save(update_fields=['gateway_response', 'gateway_reference', 'status', 'updated_at'])
                else:
                    deposit.status = 'failed'
                    deposit.failure_reason = gateway_response.get('error', 'Failed to initialize payment') if gateway_response else 'Gateway initialization failed'
                    deposit.failed_at = timezone.now()
                    deposit.save(update_fields=['status', 'failure_reason', 'failed_at', 'updated_at'])
                    
            except Exception as e:
                deposit.status = 'failed'
                deposit.failure_reason = str(e)
                deposit.failed_at = timezone.now()
                deposit.save(update_fields=['status', 'failure_reason', 'failed_at', 'updated_at'])
        
        # Publish event
        event = Event(
            event_type='DEPOSIT_INITIATED',
            data={
                'deposit_id': str(deposit.id),
                'wallet_id': str(wallet.id),
                'user_id': str(wallet.user.id),
                'user_email': wallet.user.email,
                'amount': str(amount),
                'payment_method': payment_method,
                'reference': deposit.reference,
                'status': deposit.status,
                'gateway_reference': deposit.gateway_reference,
                'timestamp': timezone.now().isoformat()
            },
            source_module='bank'
        )
        EventBus.publish(event)
        
        return deposit
    
    @staticmethod
    @transaction.atomic
    def complete_deposit(deposit, gateway_response=None):
        """Complete deposit and credit wallet"""
        if deposit.status == 'completed':
            return deposit  # Already completed
        
        deposit.status = 'completed'
        deposit.completed_at = timezone.now()
        if gateway_response:
            # Convert any Decimal values to floats for JSON serialization
            def convert_decimals(obj):
                if isinstance(obj, dict):
                    return {k: convert_decimals(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_decimals(item) for item in obj]
                elif isinstance(obj, Decimal):
                    return float(obj)
                else:
                    return obj
            deposit.gateway_response = convert_decimals(gateway_response)
        deposit.save(update_fields=['status', 'completed_at', 'gateway_response', 'updated_at'])
        
        # Credit wallet
        BankService.credit_wallet(
            wallet=deposit.wallet,
            amount=deposit.amount,
            category='deposit',
            description=f"Wallet deposit via {deposit.payment_method}",
            metadata={'deposit_id': str(deposit.id)}
        )
        
        # Publish event
        event = Event(
            event_type='DEPOSIT_COMPLETED',
            data={
                'deposit_id': str(deposit.id),
                'wallet_id': str(deposit.wallet.id),
                'user_id': str(deposit.wallet.user.id),
                'user_email': deposit.wallet.user.email,
                'amount': str(deposit.amount),
                'new_balance': str(deposit.wallet.balance),
                'reference': deposit.reference,
                'payment_method': deposit.payment_method,
                'timestamp': timezone.now().isoformat()
            },
            source_module='bank'
        )
        EventBus.publish(event)
        
        # Invalidate cache
        CacheService.invalidate_model('wallet', str(deposit.wallet.id))
        
        return deposit
    
    @staticmethod
    @transaction.atomic
    def verify_and_complete_deposit(deposit, gateway_handler):
        """Verify deposit with payment gateway and complete if successful"""
        try:
            if deposit.payment_method == 'paystack':
                verification = gateway_handler.verify_transaction(deposit.reference)
                status_success_values = ['success']
            elif deposit.payment_method == 'flutterwave':
                # Use gateway_reference if available, else reference (should be transaction_id)
                verification = gateway_handler.verify_transaction(deposit.gateway_reference or deposit.reference)
                status_success_values = ['success', 'successful']
            else:
                raise ValueError(f"Unsupported payment method: {deposit.payment_method}")

            if verification.get('success') and verification.get('status') in status_success_values:
                # Verify amount matches
                paid_amount = verification.get('amount')
                if paid_amount and Decimal(str(paid_amount)) >= deposit.amount:
                    return BankService.complete_deposit(deposit, verification)
                else:
                    deposit.status = 'failed'
                    deposit.failure_reason = f"Amount mismatch. Expected: {deposit.amount}, Got: {paid_amount}"
                    deposit.failed_at = timezone.now()
                    deposit.save()
                    raise ValueError(deposit.failure_reason)
            else:
                deposit.status = 'failed'
                deposit.failure_reason = verification.get('error', 'Payment verification failed')
                deposit.failed_at = timezone.now()
                deposit.save()
                raise ValueError(deposit.failure_reason)
        except Exception as e:
            deposit.status = 'failed'
            deposit.failure_reason = str(e)
            deposit.failed_at = timezone.now()
            deposit.save()
            raise
    
    @staticmethod
    @transaction.atomic
    def create_withdrawal_request(workspace_wallet, bank_account, amount, requested_by, notes=''):
        """Create withdrawal request for workspace admin"""
        if not workspace_wallet.can_withdraw(amount):
            raise ValueError("Insufficient balance")
        
        # Calculate fee (e.g., 1% or flat fee)
        fee = Decimal('0.00')  # Can be configured
        
        withdrawal = WithdrawalRequest.objects.create(
            workspace_wallet=workspace_wallet,
            bank_account=bank_account,
            requested_by=requested_by,
            amount=amount,
            fee=fee,
            net_amount=amount - fee,
            reference=f"WDR-{uuid.uuid4().hex[:12].upper()}",
            status='pending',
            notes=notes
        )
        
        # Publish event
        event = Event(
            event_type='WITHDRAWAL_REQUESTED',
            data={
                'withdrawal_id': str(withdrawal.id),
                'wallet_id': str(workspace_wallet.id),
                'workspace_id': str(workspace_wallet.workspace.id),
                'workspace_name': workspace_wallet.workspace.name,
                'amount': str(amount),
                'net_amount': str(withdrawal.net_amount),
                'bank_account': bank_account.account_number,
                'reference': withdrawal.reference,
                'timestamp': timezone.now().isoformat()
            },
            source_module='bank'
        )
        EventBus.publish(event)
        
        return withdrawal
    
    @staticmethod
    @transaction.atomic
    def process_withdrawal(withdrawal):
        """Process withdrawal request"""
        withdrawal.status = 'processing'
        withdrawal.processed_at = timezone.now()
        withdrawal.save(update_fields=['status', 'processed_at', 'updated_at'])
        
        # Debit workspace wallet
        BankService.debit_workspace_wallet(
            workspace_wallet=withdrawal.workspace_wallet,
            amount=withdrawal.amount,
            category='withdrawal',
            description=f"Withdrawal to {withdrawal.bank_account.account_number}",
            withdrawal_request=withdrawal,
            metadata={'withdrawal_id': str(withdrawal.id)}
        )
        
        # Update withdrawal
        withdrawal.workspace_wallet.total_withdrawn += withdrawal.amount
        withdrawal.workspace_wallet.save(update_fields=['total_withdrawn'])
        
        # Publish event
        event = Event(
            event_type='WITHDRAWAL_PROCESSING',
            data={
                'withdrawal_id': str(withdrawal.id),
                'workspace_id': str(withdrawal.workspace_wallet.workspace.id),
                'amount': str(withdrawal.amount),
                'reference': withdrawal.reference,
                'timestamp': timezone.now().isoformat()
            },
            source_module='bank'
        )
        EventBus.publish(event)
        
        return withdrawal
    
    @staticmethod
    @transaction.atomic
    def complete_withdrawal(withdrawal, gateway_reference=None):
        """Complete withdrawal request"""
        withdrawal.status = 'completed'
        withdrawal.completed_at = timezone.now()
        if gateway_reference:
            withdrawal.gateway_reference = gateway_reference
        withdrawal.save(update_fields=['status', 'completed_at', 'gateway_reference', 'updated_at'])
        
        # Publish event
        event = Event(
            event_type='WITHDRAWAL_COMPLETED',
            data={
                'withdrawal_id': str(withdrawal.id),
                'workspace_id': str(withdrawal.workspace_wallet.workspace.id),
                'workspace_name': withdrawal.workspace_wallet.workspace.name,
                'amount': str(withdrawal.amount),
                'reference': withdrawal.reference,
                'timestamp': timezone.now().isoformat()
            },
            source_module='bank'
        )
        EventBus.publish(event)
        
        return withdrawal
    
    @staticmethod
    @transaction.atomic
    def process_booking_payment(booking, payment):
        """Process booking payment - create pending transaction until check-in
        
        Money is held in pending state until user checks in.
        This allows easy refunds for cancellations without debiting workspace.
        """
        workspace = booking.workspace
        workspace_wallet, _ = BankService.create_workspace_wallet(workspace)
        
        # Create PENDING transaction (not credited yet)
        # This will be released when user checks in
        transaction_obj = Transaction.objects.create(
            reference=f"TXN-{uuid.uuid4().hex[:12].upper()}",
            transaction_type='credit',
            category='booking_payment',
            amount=booking.total_price,
            currency=workspace_wallet.currency,
            workspace_wallet=workspace_wallet,
            booking=booking,
            order=payment.order if hasattr(payment, 'order') else None,
            balance_before=workspace_wallet.balance,
            balance_after=workspace_wallet.balance,  # No change yet
            status='pending',  # Key: pending until check-in
            description=f"Pending payment for booking at {booking.space.name} (Released on check-in)",
            metadata={
                'booking_id': str(booking.id),
                'payment_id': str(payment.id) if payment else None,
                'held_until': 'check_in'
            }
        )
        
        # Publish event
        event = Event(
            event_type='BOOKING_PAYMENT_HELD',
            data={
                'transaction_id': str(transaction_obj.id),
                'wallet_id': str(workspace_wallet.id),
                'workspace_id': str(workspace.id),
                'workspace_name': workspace.name,
                'booking_id': str(booking.id),
                'amount': str(booking.total_price),
                'status': 'pending',
                'message': 'Payment held until check-in',
                'timestamp': timezone.now().isoformat()
            },
            source_module='bank'
        )
        EventBus.publish(event)
        
        return workspace_wallet, transaction_obj
    
    @staticmethod
    @transaction.atomic
    def process_booking_refund(booking, refund_amount, description=None):
        """Process booking refund - credit user wallet and handle pending/completed transactions
        
        Smart refund logic:
        - If payment is still pending (not checked in): Just cancel pending transaction
        - If payment is completed (checked in): Debit workspace and credit user
        
        Returns:
            tuple: (user_wallet, refund_transaction, refund_reference)
        """
        user = booking.user
        user_wallet, _ = BankService.create_wallet(user)
        workspace_wallet = booking.workspace.wallet
        
        # Check if there's a pending transaction for this booking
        pending_transaction = Transaction.objects.filter(
            booking=booking,
            category='booking_payment',
            status='pending'
        ).first()
        
        refund_description = description or f"Refund for cancelled booking at {booking.space.name}"
        
        if pending_transaction:
            # SCENARIO 1: Payment still pending (user hasn't checked in)
            # Just mark the pending transaction as failed/cancelled
            # No need to move money around
            pending_transaction.status = 'reversed'
            pending_transaction.failed_at = timezone.now()
            pending_transaction.failure_reason = 'Booking cancelled before check-in'
            pending_transaction.save()
            
            # Credit user wallet with refund
            refund_txn = BankService.credit_wallet(
                wallet=user_wallet,
                amount=refund_amount,
                category='cancellation_refund',
                description=refund_description + ' (from pending payment)',
                booking=booking,
                metadata={
                    'booking_id': str(booking.id),
                    'refund_from': 'pending',
                    'reversed_transaction_id': str(pending_transaction.id)
                }
            )
            
            refund_reference = refund_txn.reference
            
        else:
            # SCENARIO 2: Payment was already released to workspace (user checked in)
            # Need to debit workspace and credit user
            if workspace_wallet and workspace_wallet.balance >= refund_amount:
                # Debit workspace wallet
                BankService.debit_workspace_wallet(
                    workspace_wallet=workspace_wallet,
                    amount=refund_amount,
                    category='refund',
                    description=f"Refund for cancelled booking {booking.id}",
                    booking=booking,
                    metadata={'booking_id': str(booking.id)}
                )
            
            # Credit user wallet
            refund_txn = BankService.credit_wallet(
                wallet=user_wallet,
                amount=refund_amount,
                category='cancellation_refund',
                description=refund_description + ' (from workspace)',
                booking=booking,
                metadata={
                    'booking_id': str(booking.id),
                    'refund_from': 'workspace'
                }
            )
            
            refund_reference = refund_txn.reference
        
        # Publish refund event
        event = Event(
            event_type='BOOKING_REFUND_PROCESSED',
            data={
                'booking_id': str(booking.id),
                'user_id': str(user.id),
                'user_email': user.email,
                'workspace_id': str(booking.workspace.id),
                'refund_amount': str(refund_amount),
                'refund_reference': refund_reference,
                'refund_from': 'pending' if pending_transaction else 'workspace',
                'timestamp': timezone.now().isoformat()
            },
            source_module='bank'
        )
        EventBus.publish(event)
        
        return user_wallet, refund_txn, refund_reference
    
    @staticmethod
    @transaction.atomic
    def release_pending_payment(booking):
        """Release pending payment to workspace wallet when user checks in
        
        Args:
            booking: Booking instance that was checked in
            
        Returns:
            Transaction object or None if no pending transaction
        """
        workspace_wallet = booking.workspace.wallet
        if not workspace_wallet:
            workspace_wallet, _ = BankService.create_workspace_wallet(booking.workspace)
        
        # Find pending transaction for this booking
        pending_transaction = Transaction.objects.filter(
            booking=booking,
            category='booking_payment',
            status='pending'
        ).first()
        
        if not pending_transaction:
            # No pending transaction found
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"No pending transaction found for booking {booking.id}")
            return None
        
        # Update workspace wallet balance
        balance_before = workspace_wallet.balance
        workspace_wallet.balance += pending_transaction.amount
        workspace_wallet.total_earnings += pending_transaction.amount
        workspace_wallet.save(update_fields=['balance', 'total_earnings', 'updated_at'])
        
        # Update transaction status from pending to completed
        pending_transaction.status = 'completed'
        pending_transaction.balance_after = workspace_wallet.balance
        pending_transaction.processed_at = timezone.now()
        pending_transaction.category = 'booking_earning'  # Change from booking_payment to booking_earning
        pending_transaction.description = f"Payment released for booking at {booking.space.name} (User checked in)"
        pending_transaction.save()
        
        # Publish event
        event = Event(
            event_type='BOOKING_PAYMENT_RELEASED',
            data={
                'transaction_id': str(pending_transaction.id),
                'wallet_id': str(workspace_wallet.id),
                'workspace_id': str(booking.workspace.id),
                'workspace_name': booking.workspace.name,
                'booking_id': str(booking.id),
                'amount': str(pending_transaction.amount),
                'balance': str(workspace_wallet.balance),
                'message': 'Payment released to workspace after check-in',
                'timestamp': timezone.now().isoformat()
            },
            source_module='bank'
        )
        EventBus.publish(event)


__all__ = ['BankService']
