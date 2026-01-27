"""
Bank URLs V1
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from bank.views.v1 import (
    WalletViewSet,
    WorkspaceWalletViewSet,
    TransactionViewSet,
    DepositViewSet,
    BankAccountViewSet,
    WithdrawalRequestViewSet
)
from bank.views.v1.user_withdrawal import UserWithdrawalViewSet


router = DefaultRouter()
router.register(r'wallets', WalletViewSet, basename='wallets')
router.register(r'workspace-wallets', WorkspaceWalletViewSet, basename='workspace-wallets')
router.register(r'transactions', TransactionViewSet, basename='transactions')
router.register(r'deposits', DepositViewSet, basename='deposits')
router.register(r'bank-accounts', BankAccountViewSet, basename='bank-accounts')
router.register(r'withdrawals', WithdrawalRequestViewSet, basename='withdrawals')
router.register(r'user-withdrawals', UserWithdrawalViewSet, basename='user-withdrawals')

urlpatterns = [
    path('', include(router.urls)),
]
