"""
Withdrawal and Bank Account Models for Payment Processing
"""
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from user.models import User
from workspace.models import Workspace
import uuid


class BankAccount(models.Model):
    """Model for storing bank account details for withdrawals"""
    
    ACCOUNT_TYPE_CHOICES = [
        ('personal', 'Personal Account'),
        ('business', 'Business Account'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='bank_account')
    workspace = models.OneToOneField(Workspace, on_delete=models.CASCADE, related_name='bank_account')
    
    # Account details
    account_number = models.CharField(max_length=20, unique=True)
    account_name = models.CharField(max_length=100)
    bank_name = models.CharField(max_length=100)
    bank_code = models.CharField(max_length=10, help_text="Bank code for the bank (e.g., 058 for GTBank)")
    
    # Account type
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES, default='personal')
    
    # Default flag
    is_default = models.BooleanField(default=True, help_text="Use this account by default for withdrawals")
    
    # Verification
    is_verified = models.BooleanField(default=False, help_text="Account verified with payment gateway")
    verification_code = models.CharField(max_length=10, blank=True, null=True)
    verified_at = models.DateTimeField(blank=True, null=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payment_bank_account'
        unique_together = ['user', 'workspace']
        indexes = [
            models.Index(fields=['workspace', 'is_default']),
            models.Index(fields=['user']),
        ]
    
    def __str__(self):
        return f"{self.account_name} ({self.account_number}) - {self.bank_name}"
    
    def save(self, *args, **kwargs):
        """Ensure only one default account per workspace"""
        if self.is_default:
            # Remove default flag from other accounts for this workspace
            BankAccount.objects.filter(
                workspace=self.workspace,
                is_default=True
            ).exclude(id=self.id).update(is_default=False)
        super().save(*args, **kwargs)


class Withdrawal(models.Model):
    """Model for workspace owner/manager withdrawal requests"""
    
    WITHDRAWAL_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    WITHDRAWAL_TYPE_CHOICES = [
        ('revenue', 'Revenue Share'),
        ('commission', 'Commission'),
        ('refund', 'Refund'),
        ('manual', 'Manual Transfer'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='withdrawals')
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='withdrawal_requests')
    bank_account = models.ForeignKey(BankAccount, on_delete=models.SET_NULL, null=True, related_name='withdrawals')
    
    # Withdrawal details
    withdrawal_number = models.CharField(max_length=50, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('100'))])  # Minimum 100 NGN
    currency = models.CharField(max_length=3, default='NGN')
    withdrawal_type = models.CharField(max_length=20, choices=WITHDRAWAL_TYPE_CHOICES, default='revenue')
    
    # Description/notes
    description = models.TextField(blank=True, null=True)
    
    # Status
    status = models.CharField(max_length=20, choices=WITHDRAWAL_STATUS_CHOICES, default='pending')
    
    # Processing info
    gateway_transaction_id = models.CharField(max_length=255, blank=True, null=True)
    gateway_response = models.JSONField(default=dict, blank=True)
    
    # Approval info
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_withdrawals'
    )
    approved_at = models.DateTimeField(blank=True, null=True)
    approval_notes = models.TextField(blank=True, null=True)
    
    # Processing info
    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_withdrawals'
    )
    processed_at = models.DateTimeField(blank=True, null=True)
    
    # Error tracking
    error_message = models.TextField(blank=True, null=True)
    retry_count = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    last_retry_at = models.DateTimeField(blank=True, null=True)
    
    # Timestamps
    requested_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'payment_withdrawal'
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['workspace', 'status']),
            models.Index(fields=['requested_by', 'status']),
            models.Index(fields=['withdrawal_number']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Withdrawal {self.withdrawal_number} - {self.amount} {self.currency} ({self.status})"
    
    def save(self, *args, **kwargs):
        """Auto-generate withdrawal number if not exists"""
        if not self.withdrawal_number:
            import time
            import random
            timestamp = str(int(time.time()))
            random_num = str(random.randint(1000, 9999))
            self.withdrawal_number = f"WD-{timestamp[-6:]}-{random_num}"
        super().save(*args, **kwargs)
    
    def can_request_withdrawal(self, user):
        """Check if user can request withdrawal"""
        from workspace.models import WorkspaceUser
        
        # Only workspace admin can request
        workspace_user = WorkspaceUser.objects.filter(
            workspace=self.workspace,
            user=user
        ).first()
        
        if not workspace_user:
            return False, "You are not a member of this workspace"
        
        if workspace_user.role not in ['admin']:
            return False, f"Only workspace admins can request withdrawals"
        
        return True, "User can request withdrawal"


class WithdrawalLog(models.Model):
    """Log for tracking withdrawal status changes and processing"""
    
    STATUS_CHOICES = [
        ('requested', 'Withdrawal Requested'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    withdrawal = models.ForeignKey(Withdrawal, on_delete=models.CASCADE, related_name='logs')
    
    # Status
    status = models.CharField(max_length=30, choices=STATUS_CHOICES)
    
    # Details
    message = models.TextField()
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional details about this status change")
    
    # Actor
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'payment_withdrawal_log'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['withdrawal', '-created_at']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Log for {self.withdrawal.withdrawal_number} - {self.status}"
