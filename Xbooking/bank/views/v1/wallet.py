"""
Wallet Views V1
"""
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, extend_schema_view

logger = logging.getLogger(__name__)

from core.views import CachedModelViewSet
from core.responses import SuccessResponse, ErrorResponse
from core.pagination import StandardResultsSetPagination
from bank.models import Wallet, WorkspaceWallet, Transaction, Deposit
from bank.serializers.v1 import (
    WalletSerializer,
    WorkspaceWalletSerializer,
    TransactionSerializer,
    DepositSerializer,
    InitiateDepositSerializer
)
from bank.services import BankService
from workspace.permissions import check_workspace_member


@extend_schema_view(
    list=extend_schema(description="Get user wallet"),
    retrieve=extend_schema(description="Retrieve wallet details"),
)
class WalletViewSet(CachedModelViewSet):
    """ViewSet for managing user wallets"""
    serializer_class = WalletSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    cache_timeout = 300
    http_method_names = ['get', 'post']
    
    def get_queryset(self):
        return Wallet.objects.filter(user=self.request.user)
    
    def list(self, request):
        """Get or create user wallet"""
        wallet, _ = BankService.create_wallet(request.user)
        serializer = self.get_serializer(wallet)
        return SuccessResponse(
            message='Wallet retrieved successfully',
            data=serializer.data
        )
    
    @action(detail=False, methods=['get'], url_path='my-wallet')
    def my_wallet(self, request):
        """Get or create user wallet (alternative endpoint)"""
        wallet, _ = BankService.create_wallet(request.user)
        serializer = self.get_serializer(wallet)
        
        logger.info(f"Wallet data for user {request.user.email}: {serializer.data}")
        logger.info(f"Wallet balance: {wallet.balance}")
        
        response_data = {
            'message': 'Wallet retrieved successfully',
            'data': serializer.data
        }
        logger.info(f"Response being sent: {response_data}")
        
        return SuccessResponse(
            message='Wallet retrieved successfully',
            data=serializer.data
        )
    
    @extend_schema(
        responses={200: TransactionSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def transactions(self, request):
        """Get wallet transactions"""
        wallet, _ = BankService.create_wallet(request.user)
        transactions = Transaction.objects.filter(wallet=wallet).order_by('-created_at')
        
        page = self.paginate_queryset(transactions)
        if page is not None:
            serializer = TransactionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = TransactionSerializer(transactions, many=True)
        return SuccessResponse(
            message='Transactions retrieved successfully',
            data=serializer.data
        )


    @extend_schema(
        request=None,
        responses={200: DepositSerializer},
        description="Verify deposit payment with gateway using deposit_id"
    )
    @action(detail=False, methods=['post'], url_path='verify')
    def verify(self, request):
        """
        Verify deposit payment with gateway using deposit_id.
        Expects: {"deposit_id": "..."}
        """
        from payment.gateways import PaystackGateway, FlutterwaveGateway
        deposit_id = request.data.get('deposit_id')
        if not deposit_id:
            return ErrorResponse(
                message='deposit_id is required',
                status_code=400
            )
        try:
            deposit = Deposit.objects.get(id=deposit_id)
        except Deposit.DoesNotExist:
            return ErrorResponse(
                message='Deposit not found for provided deposit_id',
                status_code=404
            )
        if deposit.status == 'completed':
            return SuccessResponse(
                message='Deposit already completed',
                data=DepositSerializer(deposit).data
            )
        # Get gateway handler
        if deposit.payment_method == 'paystack':
            gateway_handler = PaystackGateway()
        elif deposit.payment_method == 'flutterwave':
            gateway_handler = FlutterwaveGateway()
        else:
            return ErrorResponse(
                message=f'Unsupported payment method: {deposit.payment_method}',
                status_code=400
            )
        import logging
        logger = logging.getLogger(__name__)
        try:
            deposit = BankService.verify_and_complete_deposit(deposit, gateway_handler)
            serializer = DepositSerializer(deposit)
            logger.error(f"Deposit verification success: {serializer.data}")
            return SuccessResponse(
                message='Deposit verified and completed successfully',
                data=serializer.data
            )
        except ValueError as e:
            logger.error(f"Deposit verification ValueError: {str(e)}")
            return ErrorResponse(
                message=str(e),
                status_code=400
            )
        except Exception as e:
            logger.error(f"Deposit verification Exception: {str(e)}")
            return ErrorResponse(
                message=f'Failed to verify deposit: {str(e)}',
                status_code=500
            )


@extend_schema_view(
    list=extend_schema(description="List workspace wallets (admin only)"),
    retrieve=extend_schema(description="Retrieve workspace wallet details"),
)
class WorkspaceWalletViewSet(CachedModelViewSet):
    """ViewSet for managing workspace wallets (admin only)"""
    serializer_class = WorkspaceWalletSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    cache_timeout = 300
    http_method_names = ['get']
    
    def get_queryset(self):
        """Get wallets for workspaces where user is admin"""
        from workspace.models import WorkspaceMember
        
        admin_workspaces = WorkspaceMember.objects.filter(
            user=self.request.user,
            role__in=['admin', 'manager']
        ).values_list('workspace_id', flat=True)
        
        return WorkspaceWallet.objects.filter(
            workspace_id__in=admin_workspaces
        ).select_related('workspace')
    
    @extend_schema(
        responses={200: TransactionSerializer(many=True)}
    )
    @action(detail=True, methods=['get'])
    def transactions(self, request, pk=None):
        """Get workspace wallet transactions"""
        workspace_wallet = self.get_object()
        
        # Check permission
        if not check_workspace_member(
            request.user, 
            workspace_wallet.workspace.id, 
            ['admin', 'manager']
        ):
            return ErrorResponse(
                message="You don't have permission to view this workspace wallet",
                status_code=403
            )
        
        transactions = Transaction.objects.filter(
            workspace_wallet=workspace_wallet
        ).order_by('-created_at')
        
        page = self.paginate_queryset(transactions)
        if page is not None:
            serializer = TransactionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = TransactionSerializer(transactions, many=True)
        return SuccessResponse(
            message='Transactions retrieved successfully',
            data=serializer.data
        )
    
    @extend_schema(
        responses={200: WorkspaceWalletSerializer}
    )
    @action(detail=False, methods=['get'], url_path='workspace/(?P<workspace_id>[^/.]+)')
    def by_workspace(self, request, workspace_id=None):
        """Get workspace wallet by workspace ID"""
        # Check permission
        if not check_workspace_member(request.user, workspace_id, ['admin', 'manager']):
            return ErrorResponse(
                message="You don't have permission to view this workspace wallet",
                status_code=403
            )
        
        from workspace.models import Workspace
        workspace = Workspace.objects.get(id=workspace_id)
        workspace_wallet = BankService.create_workspace_wallet(workspace)
        
        serializer = self.get_serializer(workspace_wallet)
        return SuccessResponse(
            message='Workspace wallet retrieved successfully',
            data=serializer.data
        )


@extend_schema_view(
    list=extend_schema(description="List user transactions"),
    retrieve=extend_schema(description="Retrieve transaction details"),
)
class TransactionViewSet(CachedModelViewSet):
    """ViewSet for viewing transactions"""
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    cache_timeout = 600
    http_method_names = ['get']
    
    def get_queryset(self):
        """Get transactions for user's wallet"""
        wallet, _ = BankService.create_wallet(self.request.user)
        return Transaction.objects.filter(wallet=wallet).order_by('-created_at')


@extend_schema_view(
    list=extend_schema(description="List user deposits"),
    retrieve=extend_schema(description="Retrieve deposit details"),
    create=extend_schema(description="Initiate wallet deposit"),
)
class DepositViewSet(CachedModelViewSet):
    """ViewSet for managing wallet deposits"""
    serializer_class = DepositSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    cache_timeout = 300
    http_method_names = ['get', 'post']
    
    def get_queryset(self):
        """Get deposits for user's wallet"""
        wallet, _ = BankService.create_wallet(self.request.user)
        return Deposit.objects.filter(wallet=wallet).order_by('-created_at')
    
    @extend_schema(
        request=InitiateDepositSerializer,
        responses={201: DepositSerializer}
    )
    def create(self, request):
        """Initiate deposit to wallet with payment gateway integration"""
        serializer = InitiateDepositSerializer(data=request.data)
        
        if not serializer.is_valid():
            return ErrorResponse(
                message='Invalid deposit data',
                errors=serializer.errors,
                status_code=400
            )
        
        wallet, _ = BankService.create_wallet(request.user)
        amount = serializer.validated_data['amount']
        payment_method = serializer.validated_data.get('payment_method', 'paystack')
        
        try:
            # Get payment gateway handler
            from payment.gateways import PaystackGateway, FlutterwaveGateway
            
            gateway_handler = None
            if payment_method == 'paystack':
                gateway_handler = PaystackGateway()
            elif payment_method == 'flutterwave':
                gateway_handler = FlutterwaveGateway()
            
            # Initiate deposit with gateway
            deposit = BankService.initiate_deposit(
                wallet=wallet,
                amount=amount,
                payment_method=payment_method,
                gateway_handler=gateway_handler
            )
            
            # Prepare response
            response_data = DepositSerializer(deposit).data
            
            # Add payment URL to response if available
            if deposit.gateway_response and deposit.gateway_response.get('success'):
                if payment_method == 'paystack':
                    response_data['authorization_url'] = deposit.gateway_response.get('authorization_url')
                    response_data['access_code'] = deposit.gateway_response.get('access_code')
                elif payment_method == 'flutterwave':
                    response_data['authorization_url'] = deposit.gateway_response.get('payment_link')
            
            return SuccessResponse(
                message='Deposit initiated successfully',
                data=response_data,
                status_code=201
            )
        except Exception as e:
            return ErrorResponse(
                message=f'Failed to initiate deposit: {str(e)}',
                status_code=500
            )
