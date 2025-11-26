"""
Payment and Order URLs
"""
from django.urls import path, include
from payment.views import (
    CreateOrderView, ListOrdersView, OrderDetailView,
    InitiatePaymentView, PaymentWebhookView, PaymentCallbackView,
    ListPaymentsView, RequestRefundView, PaymentStatusView
)

app_name = 'payment'

urlpatterns = [
    # Order URLs
    path('orders/create/', CreateOrderView.as_view(), name='create_order'),
    path('orders/', ListOrdersView.as_view(), name='list_orders'),
    path('orders/<uuid:order_id>/', OrderDetailView.as_view(), name='order_detail'),
    
    # Payment URLs
    path('payments/initiate/', InitiatePaymentView.as_view(), name='initiate_payment'),
    path('payments/', ListPaymentsView.as_view(), name='list_payments'),
    path('payments/<uuid:payment_id>/', PaymentStatusView.as_view(), name='payment_status'),
    
    # Payment Webhook (Paystack/Flutterwave → Your Server)
    path('webhook/paystack/', PaymentWebhookView.as_view(), name='paystack_webhook'),
    path('webhook/flutterwave/', PaymentWebhookView.as_view(), name='flutterwave_webhook'),
    
    # Payment Callback (User Redirect)
    path('payments/callback/', PaymentCallbackView.as_view(), name='payment_callback'),
    
    # Refund URLs
    path('refunds/request/', RequestRefundView.as_view(), name='request_refund'),
    
    # Withdrawal URLs (Keep workspace specific for now as withdrawals are usually per workspace admin)
    path('workspaces/<uuid:workspace_id>/withdrawals/', include('payment.withdrawal_urls')),
]
