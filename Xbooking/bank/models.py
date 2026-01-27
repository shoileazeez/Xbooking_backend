"""
Bank/Wallet Models for In-App Banking System
"""
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.utils import timezone
from user.models import User
from workspace.models import Workspace
from core.mixins import UUIDModelMixin, TimestampedModelMixin


class Wallet(UUIDModelMixin, TimestampedModelMixin, models.Model):
    """User's in-app wallet for deposits and refunds"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    
    # Balance
    balance = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0'))]
    )
    
    # Currency
    currency = models.CharField(max_length=3, default='NGN')
    
    # Status
    is_active = models.BooleanField(default=True)
    is_locked = models.BooleanField(default=False, help_text='Lock wallet for security reasons')
    
    class Meta:
        db_table = 'bank_wallet'
        indexes = [
            models.Index(fields=['user', 'is_active']),
        ]
    
    def __str__(self):
        return f"Wallet {self.user.email} - {self.currency} {self.balance}"
    
    def can_debit(self, amount):
        """Check if wallet has sufficient balance"""
        return self.balance >= amount and self.is_active and not self.is_locked


class WorkspaceWallet(UUIDModelMixin, TimestampedModelMixin, models.Model):
    """Workspace wallet for earnings from bookings"""
    
    workspace = models.OneToOneField(Workspace, on_delete=models.CASCADE, related_name='wallet')
    
    # Balance
    balance = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0'))]
    )
    
    # Total earnings (lifetime)
    total_earnings = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0'))]
    )
    
    # Total withdrawn
    total_withdrawn = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0'))]
    )
    
    # Currency
    currency = models.CharField(max_length=3, default='NGN')
    
    # Status
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'bank_workspace_wallet'
        indexes = [
            models.Index(fields=['workspace', 'is_active']),
        ]
    
    def __str__(self):
        return f"Workspace Wallet {self.workspace.name} - {self.currency} {self.balance}"
    
    def can_withdraw(self, amount):
        """Check if workspace can withdraw amount"""
        return self.balance >= amount and self.is_active


class Transaction(UUIDModelMixin, TimestampedModelMixin, models.Model):
    """Transaction records for all wallet activities"""
    
    TRANSACTION_TYPE_CHOICES = [
        ('credit', 'Credit'),
        ('debit', 'Debit'),
    ]
    
    TRANSACTION_CATEGORY_CHOICES = [
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('refund', 'Refund'),
        ('booking_payment', 'Booking Payment'),
        ('booking_earning', 'Booking Earning'),
        ('cancellation_refund', 'Cancellation Refund'),
        ('transfer', 'Transfer'),
        ('fee', 'Fee'),
    ]
    
    TRANSACTION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('reversed', 'Reversed'),
    ]
    
    # Transaction details
    reference = models.CharField(max_length=100, unique=True)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE_CHOICES)
    category = models.CharField(max_length=30, choices=TRANSACTION_CATEGORY_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    currency = models.CharField(max_length=3, default='NGN')
    
    # Wallet references
    wallet = models.ForeignKey('Wallet', on_delete=models.CASCADE, related_name='transactions', null=True, blank=True)
    workspace_wallet = models.ForeignKey('WorkspaceWallet', on_delete=models.CASCADE, related_name='transactions', null=True, blank=True)
    
    # Related objects
    booking = models.ForeignKey('booking.Booking', on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    order = models.ForeignKey('payment.Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='bank_transactions')
    withdrawal_request = models.ForeignKey('WithdrawalRequest', on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    
    # Balance tracking
    balance_before = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    balance_after = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    
    # Status
    status = models.CharField(max_length=20, choices=TRANSACTION_STATUS_CHOICES, default='pending')
    
    # Description and metadata
    description = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    
    # Processing details
    processed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'bank_transaction'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['wallet', 'status']),
            models.Index(fields=['workspace_wallet', 'status']),
            models.Index(fields=['reference']),
            models.Index(fields=['category', 'status']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.transaction_type.upper()} - {self.reference} - {self.currency} {self.amount}"


class BankAccount(UUIDModelMixin, TimestampedModelMixin, models.Model):
    """Bank account details for withdrawals"""
    
    ACCOUNT_TYPE_CHOICES = [
        ('savings', 'Savings Account'),
        ('current', 'Current Account'),
    ]
    
    # Owner (can be user or workspace)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bank_accounts', null=True, blank=True)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='bank_accounts', null=True, blank=True)
    
    # Account details
    account_number = models.CharField(max_length=20)
    account_name = models.CharField(max_length=200)
    bank_name = models.CharField(max_length=100)
    bank_code = models.CharField(max_length=10, help_text="Bank code (e.g., 058 for GTBank)")
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES, default='savings')
    
    # Verification
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_method = models.CharField(max_length=50, blank=True, help_text="Method used to verify account")
    
    # Default flag
    is_default = models.BooleanField(default=False)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'bank_account'
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['workspace', 'is_active']),
            models.Index(fields=['account_number']),
        ]
    
    def __str__(self):
        owner = self.user.email if self.user else self.workspace.name
        return f"{self.bank_name} - {self.account_number} ({owner})"


class WithdrawalRequest(UUIDModelMixin, TimestampedModelMixin, models.Model):
    """Withdrawal requests from workspace wallets"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Request details - either user wallet or workspace wallet
    wallet = models.ForeignKey('Wallet', on_delete=models.CASCADE, related_name='withdrawal_requests', null=True, blank=True)
    workspace_wallet = models.ForeignKey(WorkspaceWallet, on_delete=models.CASCADE, related_name='withdrawal_requests', null=True, blank=True)
    bank_account = models.ForeignKey(BankAccount, on_delete=models.PROTECT, related_name='withdrawal_requests')
    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='bank_withdrawal_requests')
    
    # Amount
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('1.00'))])
    fee = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    net_amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='NGN')
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Processing details
    reference = models.CharField(max_length=100, unique=True)
    gateway_reference = models.CharField(max_length=100, blank=True, null=True)
    gateway_response = models.JSONField(default=dict, blank=True)
    payment_provider = models.CharField(max_length=20, choices=[('paystack', 'Paystack'), ('flutterwave', 'Flutterwave')], default='paystack')
    
    # Timestamps
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='bank_approved_withdrawals')
    processed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    admin_notes = models.TextField(blank=True)
    failure_reason = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'bank_withdrawal_request'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['workspace_wallet', 'status']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['reference']),
        ]
    
    def __str__(self):
        return f"Withdrawal {self.reference} - {self.currency} {self.amount} ({self.status})"
    
    def save(self, *args, **kwargs):
        # Calculate net amount
        if not self.net_amount:
            self.net_amount = self.amount - self.fee
        super().save(*args, **kwargs)


class Deposit(UUIDModelMixin, TimestampedModelMixin, models.Model):
    """Deposit records for user wallet top-ups"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('card', 'Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('paystack', 'Paystack'),
        ('flutterwave', 'Flutterwave'),
    ]
    
    # Deposit details
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='deposits')
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('100.00'))])
    currency = models.CharField(max_length=3, default='NGN')
    
    # Payment details
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    reference = models.CharField(max_length=100, unique=True)
    gateway_reference = models.CharField(max_length=100, blank=True, null=True)
    gateway_response = models.JSONField(default=dict, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Timestamps
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    failure_reason = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'bank_deposit'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['wallet', 'status']),
            models.Index(fields=['reference']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"Deposit {self.reference} - {self.currency} {self.amount} ({self.status})"
