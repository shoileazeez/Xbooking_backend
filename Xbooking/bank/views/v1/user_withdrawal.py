"""
User Withdrawal Views
"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from django.shortcuts import get_object_or_404

from core.views import CachedModelViewSet
from core.responses import SuccessResponse, ErrorResponse
from core.pagination import StandardResultsSetPagination
from bank.models import WithdrawalRequest, BankAccount, Wallet
from bank.serializers.v1.withdrawal import (
    WithdrawalRequestSerializer,
    RequestWithdrawalSerializer
)
from bank.services_withdrawal import WithdrawalService
from payment.gateways import PaystackGateway, FlutterwaveGateway


class UserWithdrawalViewSet(CachedModelViewSet):
    """ViewSet for user withdrawals"""
    serializer_class = WithdrawalRequestSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    cache_timeout = 120
    http_method_names = ['get', 'post']
    
    def get_queryset(self):
        """Get withdrawal requests for current user"""
        return WithdrawalRequest.objects.filter(
            wallet__user=self.request.user
        ).select_related(
            'wallet', 'bank_account', 'requested_by'
        ).order_by('-created_at')
    
    @extend_schema(
        request=RequestWithdrawalSerializer,
        responses={201: WithdrawalRequestSerializer}
    )
    def create(self, request):
        """Create withdrawal request for user"""
        serializer = RequestWithdrawalSerializer(data=request.data)
        
        if not serializer.is_valid():
            return ErrorResponse(
                message='Invalid withdrawal request',
                errors=serializer.errors,
                status_code=400
            )
        
        bank_account_id = serializer.validated_data['bank_account']
        amount = serializer.validated_data['amount']
        payment_provider = serializer.validated_data.get('payment_provider', 'paystack')
        
        try:
            # Get user wallet
            wallet = get_object_or_404(Wallet, user=request.user)
            
            # Get bank account
            bank_account = get_object_or_404(
                BankAccount,
                id=bank_account_id,
                user=request.user,
                is_active=True
            )
            
            # Create withdrawal request
            withdrawal = WithdrawalService.request_withdrawal(
                owner_wallet=wallet,
                bank_account=bank_account,
                amount=amount,
                user=request.user
            )
            
            # Get gateway handler
            if payment_provider == 'paystack':
                gateway = PaystackGateway()
            elif payment_provider == 'flutterwave':
                gateway = FlutterwaveGateway()
            else:
                return ErrorResponse(
                    message='Invalid payment provider',
                    status_code=400
                )
            
            # Process withdrawal immediately
            WithdrawalService.process_withdrawal(withdrawal, gateway)
            
            # Complete withdrawal (in production, wait for webhook)
            WithdrawalService.complete_withdrawal(withdrawal)
            
            serializer = WithdrawalRequestSerializer(withdrawal)
            return SuccessResponse(
                message='Withdrawal request processed successfully',
                data=serializer.data,
                status_code=201
            )
        except Exception as e:
            return ErrorResponse(
                message=str(e),
                status_code=400
            )
    
    @extend_schema(
        responses={200: WithdrawalRequestSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def history(self, request):
        """Get withdrawal history for user"""
        withdrawals = self.get_queryset()
        
        page = self.paginate_queryset(withdrawals)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(withdrawals, many=True)
        return SuccessResponse(
            message='Withdrawal history retrieved successfully',
            data=serializer.data
        )
