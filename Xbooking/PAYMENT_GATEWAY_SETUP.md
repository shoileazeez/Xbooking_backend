# Paystack & Flutterwave Integration Guide

## Overview
Complete Paystack and Flutterwave payment gateway integration for the Xbooking platform.

## Setup Instructions

### 1. **Environment Variables (.env)**
Add these to your `.env` file:

```bash
# Paystack Configuration
PAYSTACK_SECRET_KEY=sk_test_xxxxxxxxxxxxx  # Get from Paystack Dashboard
PAYSTACK_PUBLIC_KEY=pk_test_xxxxxxxxxxxxx  # Get from Paystack Dashboard

# Flutterwave Configuration
FLUTTERWAVE_SECRET_KEY=FLWSECK_TEST-xxxxxxxxxxxxx  # Get from Flutterwave Dashboard
FLUTTERWAVE_PUBLIC_KEY=FLWPUBK_TEST-xxxxxxxxxxxxx  # Get from Flutterwave Dashboard

# Redis Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
REDIS_URL=redis://localhost:6379/1
```

### 2. **Required Packages**
Already added to `requirements.txt`:
- `requests==2.32.5` - For API calls
- `paystack-python==3.0.3` - Paystack SDK (optional, we use requests)
- `flutterwave-python==3.0.0` - Flutterwave SDK (optional, we use requests)

Install:
```bash
pip install -r requirements.txt
```

### 3. **Payment Flow**

#### Step 1: Create Order
```bash
POST /api/payment/workspaces/{workspace_id}/orders/create/
{
    "booking_ids": ["booking-id-1", "booking-id-2"],
    "discount_amount": 0,
    "notes": "Special request"
}
```

Response:
```json
{
    "id": "order-uuid",
    "order_number": "ORD-20251019-12345",
    "user": "user-uuid",
    "status": "pending",
    "subtotal": "50000.00",
    "discount_amount": "0.00",
    "tax_amount": "5000.00",
    "total_amount": "55000.00",
    "bookings": [...]
}
```

#### Step 2: Initiate Payment
```bash
POST /api/payment/workspaces/{workspace_id}/payment/initiate/
{
    "order_id": "order-uuid",
    "payment_method": "paystack",  # or "flutterwave"
    "email": "user@example.com"
}
```

Response:
```json
{
    "payment_url": "https://checkout.paystack.com/xxxxx",
    "payment_id": "payment-uuid",
    "reference": "payment-uuid",
    "amount": "55000.00",
    "currency": "NGN"
}
```

#### Step 3: User Pays
- User is redirected to `payment_url`
- Pays through Paystack or Flutterwave interface
- Gateway redirects back with success/failure

#### Step 4: Webhook Verification
```bash
POST /api/payment/callback/
{
    "reference": "payment-uuid",
    "status": "success"
}
```

On successful payment:
- Order status → `paid`
- Bookings status → `confirmed`
- QR code generation triggered (background task)
- Payment confirmation email sent (background task)

### 4. **Paystack Integration Details**

#### Gateway Methods

**Initialize Transaction:**
```python
from payment.gateways import PaystackGateway

gateway = PaystackGateway()
result = gateway.initialize_transaction(
    email="user@example.com",
    amount=Decimal("50000"),  # In Naira
    reference="unique-ref",
    metadata={"order_number": "ORD-123"}
)

# result = {
#     'success': True,
#     'authorization_url': 'https://checkout.paystack.com/xxxx',
#     'access_code': 'xxxxx',
#     'reference': 'unique-ref'
# }
```

**Verify Transaction:**
```python
result = gateway.verify_transaction(reference="unique-ref")

# result = {
#     'success': True,
#     'status': 'success',
#     'amount': Decimal('50000'),
#     'customer_email': 'user@example.com',
#     'payment_method': 'card',
#     'reference': 'unique-ref',
#     'authorization': {...}
# }
```

**Create Transfer Recipient:**
```python
result = gateway.create_transfer_recipient(
    type_account="nuban",
    account_number="0123456789",
    bank_code="058",  # GTBank
    name="John Doe"
)

# result = {
#     'success': True,
#     'recipient_code': 'RCP_xxxxx'
# }
```

**Initiate Transfer (Payout):**
```python
result = gateway.initiate_transfer(
    source="balance",
    reason="Commission payout",
    amount=Decimal("10000"),
    recipient_code="RCP_xxxxx"
)

# result = {
#     'success': True,
#     'transfer_code': 'TRF_xxxxx',
#     'reference': 'unique-ref'
# }
```

### 5. **Flutterwave Integration Details**

#### Gateway Methods

**Initialize Transaction:**
```python
from payment.gateways import FlutterwaveGateway

gateway = FlutterwaveGateway()
result = gateway.initialize_transaction(
    email="user@example.com",
    amount=Decimal("50000"),  # In Naira
    tx_ref="unique-ref",
    metadata={"order_number": "ORD-123"}
)

# result = {
#     'success': True,
#     'payment_link': 'https://checkout.flutterwave.com/xxxx',
#     'reference': 'transaction-id'
# }
```

**Verify Transaction:**
```python
result = gateway.verify_transaction(transaction_id="123456")

# result = {
#     'success': True,
#     'status': 'successful',
#     'amount': Decimal('50000'),
#     'customer_email': 'user@example.com',
#     'payment_method': 'card',
#     'reference': 'tx_ref',
#     'currency': 'NGN'
# }
```

### 6. **Webhook Setup**

#### Paystack Webhook
1. Go to Paystack Dashboard → Settings → API Keys & Webhooks
2. Set Webhook URL: `https://your-domain.com/api/payment/callback/`
3. Paystack will POST payment events to this URL

#### Flutterwave Webhook
1. Go to Flutterwave Dashboard → Settings → Webhooks
2. Set Webhook URL: `https://your-domain.com/api/payment/callback/`
3. Configure events: `charge.completed`, `charge.failed`

### 7. **Testing**

#### Test Paystack
- Use test secret key from Paystack Dashboard
- Test card: `4084084084084081` (expires any future date, CVV: 408)
- OTP: `123456`

#### Test Flutterwave
- Use test secret key from Flutterwave Dashboard
- Test card: `5531886652142950` (expires any future date, CVV: 564)
- OTP: `12345`

### 8. **Error Handling**

All gateway methods return structured responses:
```python
{
    'success': True/False,
    'error': 'Error message if failed',
    'status_code': 'HTTP status code if API error',
    # ... other response fields
}
```

### 9. **Security Considerations**

✅ **Implemented:**
- API keys stored in environment variables (never in code)
- HTTPS only communication with gateways
- Request timeouts (30 seconds)
- Comprehensive logging for debugging
- Payment verification before order completion
- Webhook signature verification (ready to implement)

⚠️ **Recommendations:**
- Verify webhook signatures before processing
- Implement rate limiting on payment endpoints
- Log all payment transactions for audit
- Set up email alerts for failed payments
- Regularly rotate API keys
- Use HTTPS in production

### 10. **Background Tasks**

When payment succeeds:
1. **send_payment_confirmation_email** - Email sent via Celery
2. **generate_qr_code_for_order** - QR code generated in background
3. **send_qr_code_email** - QR code emailed to user

### 11. **Database Models**

- **Order** - Stores order details and status
- **Payment** - Stores payment transactions
- **PaymentWebhook** - Stores webhook payloads for audit
- **Refund** - Stores refund requests

### 12. **Troubleshooting**

| Issue | Solution |
|-------|----------|
| "Secret key not found" | Check `.env` file and `PAYSTACK_SECRET_KEY` variable |
| Payment URL blank | Check gateway response and error logs |
| Webhook not received | Verify webhook URL is publicly accessible |
| Payment verification fails | Check payment reference and ensure transaction exists on gateway |
| Timeout errors | Increase timeout or check internet connection |

### 13. **Production Checklist**

- [ ] Get production API keys from Paystack & Flutterwave
- [ ] Update `.env` with production keys
- [ ] Set DEBUG=False in settings
- [ ] Configure ALLOWED_HOSTS
- [ ] Set up webhook URLs on both gateways
- [ ] Test payment flow end-to-end
- [ ] Set up error monitoring/logging
- [ ] Configure database backups
- [ ] Set up Redis persistence
- [ ] Configure email backend for production
- [ ] SSL certificate installed
- [ ] Load testing performed

---

**Support:** For API issues, check gateway documentation:
- Paystack: https://paystack.com/docs/api/
- Flutterwave: https://developer.flutterwave.com/
