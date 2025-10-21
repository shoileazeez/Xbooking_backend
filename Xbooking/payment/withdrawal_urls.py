"""
URL routing for Withdrawal Management
"""
from django.urls import path
from rest_framework.routers import SimpleRouter
from payment.withdrawal_views import (
    BankAccountViewSet,
    CreateWithdrawalView,
    ListWithdrawalsView,
    AdminApproveWithdrawalView,
    AdminRejectWithdrawalView,
    AdminListPendingWithdrawalsView,
    AdminProcessWithdrawalView,
    WithdrawalDetailView
)

router = SimpleRouter()
router.register(r'bank-accounts', BankAccountViewSet, basename='bank-account')

urlpatterns = [
    # Withdrawal management
    path('withdrawals/create/', CreateWithdrawalView.as_view(), name='create-withdrawal'),
    path('withdrawals/list/', ListWithdrawalsView.as_view(), name='list-withdrawals'),
    path('withdrawals/<uuid:withdrawal_id>/', WithdrawalDetailView.as_view(), name='withdrawal-detail'),
    
    # Admin operations
    path('withdrawals/<uuid:withdrawal_id>/approve/', AdminApproveWithdrawalView.as_view(), name='approve-withdrawal'),
    path('withdrawals/<uuid:withdrawal_id>/reject/', AdminRejectWithdrawalView.as_view(), name='reject-withdrawal'),
    path('withdrawals/<uuid:withdrawal_id>/process/', AdminProcessWithdrawalView.as_view(), name='process-withdrawal'),
    path('admin/withdrawals/pending/', AdminListPendingWithdrawalsView.as_view(), name='list-pending-withdrawals'),
] + router.urls
