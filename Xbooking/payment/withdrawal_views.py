"""
Views for Withdrawal and Bank Account Management
"""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from workspace.models import Workspace, WorkspaceUser
from payment.models import Payment, Order
from payment.withdrawal_models import BankAccount, Withdrawal, WithdrawalLog
from payment.withdrawal_serializers import (
    BankAccountSerializer, CreateBankAccountSerializer,
    WithdrawalSerializer, CreateWithdrawalSerializer,
    ApproveWithdrawalSerializer, RejectWithdrawalSerializer,
    ProcessWithdrawalSerializer, WithdrawalListSerializer
)
from payment.withdrawal_tasks import process_withdrawal_payout
from notifications.tasks import send_notification
import logging

logger = logging.getLogger(__name__)


class BankAccountViewSet(viewsets.ModelViewSet):
    """ViewSet for Bank Account Management"""
    
    permission_classes = [IsAuthenticated]
    serializer_class = BankAccountSerializer
    
    def get_queryset(self):
        """Filter bank accounts by workspace"""
        workspace_id = self.request.query_params.get('workspace_id')
        if workspace_id:
            return BankAccount.objects.filter(
                workspace_id=workspace_id,
                user=self.request.user
            )
        return BankAccount.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == 'create':
            return CreateBankAccountSerializer
        return BankAccountSerializer
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Create a new bank account"""
        workspace_id = request.query_params.get('workspace_id')
        if not workspace_id:
            return Response(
                {'error': 'workspace_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user is workspace admin
        workspace = Workspace.objects.get(id=workspace_id)
        member = WorkspaceUser.objects.filter(
            workspace=workspace,
            user=request.user,
            role__in=['admin']
        ).first()
        
        if not member:
            return Response(
                {'error': 'Only workspace admins can add bank accounts'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Check if account already exists
        existing = BankAccount.objects.filter(
            workspace=workspace,
            user=request.user,
            account_number=serializer.validated_data['account_number']
        ).first()
        
        if existing:
            return Response(
                {'error': 'Bank account already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create bank account
        bank_account = BankAccount.objects.create(
            user=request.user,
            workspace=workspace,
            **serializer.validated_data,
            is_default=not BankAccount.objects.filter(
                workspace=workspace,
                user=request.user,
                is_active=True
            ).exists()
        )
        
        return Response(
            BankAccountSerializer(bank_account).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """Set a bank account as default"""
        bank_account = self.get_object()
        
        # Check workspace membership
        if not WorkspaceUser.objects.filter(
            workspace=bank_account.workspace,
            user=request.user,
            role__in=['admin']
        ).exists():
            return Response(
                {'error': 'Only workspace admins can change default account'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Set as default
        BankAccount.objects.filter(
            workspace=bank_account.workspace,
            user=request.user,
            is_active=True
        ).update(is_default=False)
        
        bank_account.is_default = True
        bank_account.save()
        
        return Response(
            BankAccountSerializer(bank_account).data,
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a bank account"""
        bank_account = self.get_object()
        
        # Check workspace membership
        if not WorkspaceUser.objects.filter(
            workspace=bank_account.workspace,
            user=request.user,
            role__in=['admin']
        ).exists():
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Can't deactivate if it's the only active account
        active_count = BankAccount.objects.filter(
            workspace=bank_account.workspace,
            user=request.user,
            is_active=True
        ).count()
        
        if active_count == 1:
            return Response(
                {'error': 'Cannot deactivate the only active bank account'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        bank_account.is_active = False
        if bank_account.is_default:
            # Set another active account as default
            another = BankAccount.objects.filter(
                workspace=bank_account.workspace,
                user=request.user,
                is_active=True
            ).exclude(id=bank_account.id).first()
            if another:
                another.is_default = True
                another.save()
        bank_account.save()
        
        return Response(
            BankAccountSerializer(bank_account).data,
            status=status.HTTP_200_OK
        )


class CreateWithdrawalView(APIView):
    """Create a withdrawal request"""
    
    permission_classes = [IsAuthenticated]
    serializer_class = CreateWithdrawalSerializer
    
    @transaction.atomic
    def post(self, request):
        serializer = CreateWithdrawalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        workspace_id = request.query_params.get('workspace_id')
        if not workspace_id:
            return Response(
                {'error': 'workspace_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        workspace = Workspace.objects.get(id=workspace_id)
        
        # Check if user can request withdrawal (admin only)
        if not WorkspaceUser.objects.filter(
            workspace=workspace,
            user=request.user,
            role__in=['admin']
        ).exists():
            return Response(
                {'error': 'Only workspace admins can request withdrawals'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validate amount
        amount = serializer.validated_data['amount']
        if amount < Decimal('100'):
            return Response(
                {'error': 'Minimum withdrawal amount is 100 NGN'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get bank account
        bank_account_id = serializer.validated_data.get('bank_account_id')
        if bank_account_id:
            bank_account = BankAccount.objects.filter(
                id=bank_account_id,
                workspace=workspace,
                user=request.user,
                is_active=True,
                is_verified=True
            ).first()
            if not bank_account:
                return Response(
                    {'error': 'Bank account not found or not verified'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            # Use default account
            bank_account = BankAccount.objects.filter(
                workspace=workspace,
                user=request.user,
                is_active=True,
                is_verified=True,
                is_default=True
            ).first()
            if not bank_account:
                return Response(
                    {'error': 'No default verified bank account found. Please add and verify a bank account first.'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Create withdrawal
        withdrawal = Withdrawal.objects.create(
            workspace=workspace,
            requested_by=request.user,
            bank_account=bank_account,
            amount=amount,
            currency='NGN',
            withdrawal_type=serializer.validated_data['withdrawal_type'],
            description=serializer.validated_data.get('description', ''),
            status='pending'
        )
        
        # Create initial log entry
        WithdrawalLog.objects.create(
            withdrawal=withdrawal,
            status='pending',
            message='Withdrawal request created',
            created_by=request.user
        )
        
        # Send notification to approvers (workspace admins)
        send_notification.delay(
            user_id=None,  # Broadcast to admins
            notification_type='withdrawal_requested',
            title='New Withdrawal Request',
            message=f'{request.user.email} requested a withdrawal of {amount} NGN',
            workspace_id=str(workspace.id),
            target_roles=['admin']
        )
        
        logger.info(f"Withdrawal created: {withdrawal.withdrawal_number} for user {request.user.id}")
        
        return Response(
            WithdrawalSerializer(withdrawal).data,
            status=status.HTTP_201_CREATED
        )


class ListWithdrawalsView(APIView):
    """List withdrawals for a workspace"""
    
    permission_classes = [IsAuthenticated]
    serializer_class = WithdrawalListSerializer
    
    def get(self, request):
        workspace_id = request.query_params.get('workspace_id')
        if not workspace_id:
            return Response(
                {'error': 'workspace_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        withdrawals = Withdrawal.objects.filter(
            workspace_id=workspace_id,
            requested_by=request.user
        ).order_by('-requested_at')
        
        serializer = WithdrawalListSerializer(withdrawals, many=True)
        return Response(serializer.data)


class AdminApproveWithdrawalView(APIView):
    """Admin approve a withdrawal request"""
    
    permission_classes = [IsAuthenticated]
    serializer_class = ApproveWithdrawalSerializer
    
    @transaction.atomic
    def post(self, request, withdrawal_id):
        withdrawal = Withdrawal.objects.get(id=withdrawal_id)
        
        # Check if user is workspace admin
        if not WorkspaceUser.objects.filter(
            workspace=withdrawal.workspace,
            user=request.user,
            role__in=['admin']
        ).exists():
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if withdrawal.status != 'pending':
            return Response(
                {'error': f'Can only approve pending withdrawals. Current status: {withdrawal.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = ApproveWithdrawalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Approve withdrawal
        withdrawal.status = 'approved'
        withdrawal.approved_by = request.user
        withdrawal.approved_at = timezone.now()
        withdrawal.approval_notes = serializer.validated_data.get('approval_notes', '')
        withdrawal.save()
        
        # Create log entry
        WithdrawalLog.objects.create(
            withdrawal=withdrawal,
            status='approved',
            message=f'Approved by {request.user.email}',
            metadata={'approval_notes': withdrawal.approval_notes},
            created_by=request.user
        )
        
        # Send notification to requester
        send_notification.delay(
            user_id=str(withdrawal.requested_by.id),
            notification_type='withdrawal_approved',
            title='Withdrawal Approved',
            message=f'Your withdrawal request of {withdrawal.amount} NGN has been approved',
            workspace_id=str(withdrawal.workspace.id)
        )
        
        logger.info(f"Withdrawal approved: {withdrawal.withdrawal_number} by {request.user.id}")
        
        return Response(
            WithdrawalSerializer(withdrawal).data,
            status=status.HTTP_200_OK
        )


class AdminRejectWithdrawalView(APIView):
    """Admin reject a withdrawal request"""
    
    permission_classes = [IsAuthenticated]
    serializer_class = RejectWithdrawalSerializer
    
    @transaction.atomic
    def post(self, request, withdrawal_id):
        withdrawal = Withdrawal.objects.get(id=withdrawal_id)
        
        # Check if user is workspace admin
        if not WorkspaceUser.objects.filter(
            workspace=withdrawal.workspace,
            user=request.user,
            role__in=['admin']
        ).exists():
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if withdrawal.status != 'pending':
            return Response(
                {'error': f'Can only reject pending withdrawals. Current status: {withdrawal.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = RejectWithdrawalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        reason = serializer.validated_data['reason']
        
        # Reject withdrawal
        withdrawal.status = 'cancelled'
        withdrawal.error_message = reason
        withdrawal.save()
        
        # Create log entry
        WithdrawalLog.objects.create(
            withdrawal=withdrawal,
            status='cancelled',
            message=f'Rejected by {request.user.email}: {reason}',
            metadata={'rejection_reason': reason},
            created_by=request.user
        )
        
        # Send notification to requester
        send_notification.delay(
            user_id=str(withdrawal.requested_by.id),
            notification_type='withdrawal_rejected',
            title='Withdrawal Rejected',
            message=f'Your withdrawal request of {withdrawal.amount} NGN has been rejected. Reason: {reason}',
            workspace_id=str(withdrawal.workspace.id)
        )
        
        logger.info(f"Withdrawal rejected: {withdrawal.withdrawal_number} by {request.user.id}")
        
        return Response(
            WithdrawalSerializer(withdrawal).data,
            status=status.HTTP_200_OK
        )


class AdminListPendingWithdrawalsView(APIView):
    """List all pending withdrawals for admin"""
    
    permission_classes = [IsAuthenticated]
    serializer_class = WithdrawalListSerializer
    
    def get(self, request):
        workspace_id = request.query_params.get('workspace_id')
        if not workspace_id:
            return Response(
                {'error': 'workspace_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        workspace = Workspace.objects.get(id=workspace_id)
        
        # Check if user is workspace admin
        if not WorkspaceUser.objects.filter(
            workspace=workspace,
            user=request.user,
            role__in=['admin']
        ).exists():
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        withdrawals = Withdrawal.objects.filter(
            workspace=workspace,
            status__in=['pending', 'approved']
        ).order_by('-requested_at')
        
        serializer = WithdrawalListSerializer(withdrawals, many=True)
        return Response(serializer.data)


class AdminProcessWithdrawalView(APIView):
    """Admin process a withdrawal (send payout)"""
    
    permission_classes = [IsAuthenticated]
    serializer_class = ProcessWithdrawalSerializer
    
    @transaction.atomic
    def post(self, request, withdrawal_id):
        withdrawal = Withdrawal.objects.get(id=withdrawal_id)
        
        # Check if user is workspace admin
        if not WorkspaceUser.objects.filter(
            workspace=withdrawal.workspace,
            user=request.user,
            role__in=['admin']
        ).exists():
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if withdrawal.status != 'approved':
            return Response(
                {'error': f'Only approved withdrawals can be processed. Current status: {withdrawal.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = ProcessWithdrawalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Trigger payout task
        process_withdrawal_payout.delay(str(withdrawal.id))
        
        # Update status to processing
        withdrawal.status = 'processing'
        withdrawal.processed_by = request.user
        withdrawal.processed_at = timezone.now()
        withdrawal.gateway_transaction_id = serializer.validated_data.get('gateway_transaction_id', '')
        withdrawal.save()
        
        # Create log entry
        WithdrawalLog.objects.create(
            withdrawal=withdrawal,
            status='processing',
            message=f'Processing initiated by {request.user.email}',
            metadata={
                'gateway_transaction_id': withdrawal.gateway_transaction_id,
                'notes': serializer.validated_data.get('notes', '')
            },
            created_by=request.user
        )
        
        # Send notification to requester
        send_notification.delay(
            user_id=str(withdrawal.requested_by.id),
            notification_type='withdrawal_processing',
            title='Withdrawal Processing',
            message=f'Your withdrawal of {withdrawal.amount} NGN is being processed',
            workspace_id=str(withdrawal.workspace.id)
        )
        
        logger.info(f"Withdrawal processing started: {withdrawal.withdrawal_number} by {request.user.id}")
        
        return Response(
            WithdrawalSerializer(withdrawal).data,
            status=status.HTTP_200_OK
        )


class WithdrawalDetailView(APIView):
    """Get withdrawal details"""
    
    permission_classes = [IsAuthenticated]
    serializer_class = WithdrawalSerializer
    
    def get(self, request, withdrawal_id):
        withdrawal = Withdrawal.objects.get(id=withdrawal_id)
        
        # Check if user can access this withdrawal
        can_access = (
            withdrawal.requested_by == request.user or
            WorkspaceUser.objects.filter(
                workspace=withdrawal.workspace,
                user=request.user,
                role__in=['admin', 'manager', 'staff']
            ).exists()
        )
        
        if not can_access:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = WithdrawalSerializer(withdrawal)
        return Response(serializer.data)
