"""
Payment and Order URLs
"""
from django.urls import path, include
from payment.views import (
    CreateOrderView, ListOrdersView, OrderDetailView,
    InitiatePaymentView, PaymentCallbackView, ListPaymentsView,
    RequestRefundView, PaymentStatusView
)

app_name = 'payment'

urlpatterns = [
    # Order URLs
    path('workspaces/<uuid:workspace_id>/orders/create/', CreateOrderView.as_view(), name='create_order'),
    path('workspaces/<uuid:workspace_id>/orders/', ListOrdersView.as_view(), name='list_orders'),
    path('workspaces/<uuid:workspace_id>/orders/<uuid:order_id>/', OrderDetailView.as_view(), name='order_detail'),
    
    # Payment URLs
    path('workspaces/<uuid:workspace_id>/payments/initiate/', InitiatePaymentView.as_view(), name='initiate_payment'),
    path('workspaces/<uuid:workspace_id>/payments/', ListPaymentsView.as_view(), name='list_payments'),
    path('workspaces/<uuid:workspace_id>/payments/<uuid:payment_id>/', PaymentStatusView.as_view(), name='payment_status'),
    
    # Payment Callback (Webhook)
    path('payments/callback/', PaymentCallbackView.as_view(), name='payment_callback'),
    
    # Refund URLs
    path('workspaces/<uuid:workspace_id>/refunds/request/', RequestRefundView.as_view(), name='request_refund'),
    
    # Withdrawal URLs
    path('workspaces/<uuid:workspace_id>/', include('payment.withdrawal_urls')),
]
