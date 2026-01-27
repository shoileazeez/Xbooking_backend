# XBooking Feature Implementation Plan
## Created: January 21, 2026

This document outlines the comprehensive implementation for booking cancellation, refunds, bank accounts, and withdrawal system.

## 1. DATABASE MODELS

### BankAccount Model (payment/models.py)
```python
class BankAccount(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bank_accounts')
    account_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=50)
    bank_name = models.CharField(max_length=255)
    bank_code = models.CharField(max_length=10)
    is_verified = models.BooleanField(default=False)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### WalletTransaction Model (payment/models.py)
```python
class WalletTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('credit', 'Credit'),
        ('debit', 'Debit'),
        ('refund', 'Refund'),
        ('withdrawal', 'Withdrawal'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    balance_before = models.DecimalField(max_digits=10, decimal_places=2)
    balance_after = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reference = models.CharField(max_length=255, unique=True)
    description = models.TextField()
    bank_account = models.ForeignKey(BankAccount, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
```

### BookingCancellation Model (booking/models.py)
```python
class BookingCancellation(models.Model):
    CANCELLATION_REASONS = [
        ('schedule_change', 'Schedule Change'),
        ('emergency', 'Emergency'),
        ('duplicate', 'Duplicate Booking'),
        ('other', 'Other'),
    ]
    
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='cancellation')
    cancelled_by = models.ForeignKey(User, on_delete=models.CASCADE)
    reason = models.CharField(max_length=50, choices=CANCELLATION_REASONS)
    detailed_reason = models.TextField(blank=True)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2)
    refund_status = models.CharField(max_length=20, default='pending')
    cancelled_at = models.DateTimeField(auto_now_add=True)
```

## 2. CANCELLATION POLICY

### Rules:
- Can cancel up to 6 hours before check-in
- Refund: 100% if cancelled 24+ hours before
- Refund: 50% if cancelled 6-24 hours before
- No refund if cancelled less than 6 hours before

### Implementation:
```python
def calculate_refund_amount(booking):
    hours_until_checkin = (booking.check_in - timezone.now()).total_seconds() / 3600
    
    if hours_until_checkin >= 24:
        return booking.total_price  # 100% refund
    elif hours_until_checkin >= 6:
        return booking.total_price * Decimal('0.50')  # 50% refund
    else:
        return Decimal('0')  # No refund
```

## 3. API ENDPOINTS

### Bank Accounts
- POST /api/v1/payment/bank-accounts/ - Add bank account
- GET /api/v1/payment/bank-accounts/ - List user's bank accounts
- PATCH /api/v1/payment/bank-accounts/{id}/set-default/ - Set default
- DELETE /api/v1/payment/bank-accounts/{id}/ - Remove account

### Withdrawals
- POST /api/v1/payment/withdrawal/ - Request withdrawal
- GET /api/v1/payment/withdrawals/ - List withdrawal history
- GET /api/v1/payment/wallet/balance/ - Get wallet balance

### Cancellations
- POST /api/v1/booking/{id}/cancel/ - Cancel booking
- GET /api/v1/booking/cancellations/ - List cancellations
- POST /api/v1/booking/{id}/approve-cancellation/ - Admin approve

## 4. CELERY TASKS

### Email Tasks
- send_cancellation_email(booking_id, cancellation_id)
- send_refund_confirmation_email(user_id, amount)
- send_withdrawal_confirmation_email(user_id, withdrawal_id)

### Processing Tasks
- process_booking_refund(cancellation_id)
- process_withdrawal_request(withdrawal_id)

## 5. EMAIL TEMPLATES (Purple/White)

### booking_cancelled_email.html
- Cancellation confirmation
- Refund amount and timeline
- Booking details

### refund_processed_email.html
- Refund confirmation
- Amount credited to wallet
- New wallet balance

### withdrawal_requested_email.html
- Withdrawal request confirmation
- Processing timeline (2-3 business days)
- Bank account details

### withdrawal_completed_email.html
- Transfer confirmation
- Amount and bank details
- Receipt/reference number

## 6. FRONTEND PAGES

### /bookings/[id]/cancel
- Cancellation form
- Reason selection
- Refund calculation display
- Confirmation modal

### /wallet
- Balance display
- Transaction history
- Withdrawal button

### /wallet/withdraw
- Amount input
- Bank account selection
- Withdrawal confirmation

### /wallet/bank-accounts
- List of bank accounts
- Add new account form
- Set default option

### /admin/bookings/cancellations
- List of pending cancellations
- Approve/reject actions
- Refund status tracking

## 7. IMPLEMENTATION ORDER

1. ✅ Create email templates (purple/white)
2. ⏳ Create database models
3. ⏳ Create serializers and validators
4. ⏳ Create API views and URLs
5. ⏳ Create Celery tasks
6. ⏳ Create frontend components
7. ⏳ Testing and integration

## 8. TESTING CHECKLIST

- [ ] Test cancellation within allowed time
- [ ] Test cancellation outside allowed time
- [ ] Test refund calculation
- [ ] Test wallet credit
- [ ] Test withdrawal request
- [ ] Test bank account verification
- [ ] Test email notifications
- [ ] Test frontend flows

## NOTES

- Ensure all monetary transactions are atomic
- Log all wallet transactions
- Implement idempotency for refunds
- Add rate limiting for withdrawals
- Validate bank account details with Paystack
- Store audit trail for cancellations
