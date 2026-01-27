"""
Withdrawal Views V1
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, extend_schema_view
from django.shortcuts import get_object_or_404

from core.views import CachedModelViewSet
from core.responses import SuccessResponse, ErrorResponse
from core.pagination import StandardResultsSetPagination
from bank.models import WithdrawalRequest, BankAccount, WorkspaceWallet
from bank.serializers.v1 import (
    WithdrawalRequestSerializer,
    CreateWithdrawalRequestSerializer,
    ProcessWithdrawalSerializer
)
from bank.services import BankService
from workspace.permissions import check_workspace_member


@extend_schema_view(
    list=extend_schema(description="List withdrawal requests"),
    retrieve=extend_schema(description="Retrieve withdrawal request details"),
    create=extend_schema(description="Create withdrawal request"),
)
class WithdrawalRequestViewSet(CachedModelViewSet):
    """ViewSet for managing withdrawal requests (workspace admin only)"""
    serializer_class = WithdrawalRequestSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    cache_timeout = 120  # 2 minutes for withdrawal requests
    http_method_names = ['get', 'post', 'patch']
    
    def get_queryset(self):
        """Get withdrawal requests for workspaces where user is admin"""
        from workspace.models import WorkspaceMember
        
        admin_workspaces = WorkspaceMember.objects.filter(
            user=self.request.user,
            role__in=['admin', 'manager']
        ).values_list('workspace_id', flat=True)
        
        return WithdrawalRequest.objects.filter(
            workspace_wallet__workspace_id__in=admin_workspaces
        ).select_related(
            'workspace_wallet', 'workspace_wallet__workspace',
            'bank_account', 'requested_by'
        ).order_by('-created_at')
    
    @extend_schema(
        request=CreateWithdrawalRequestSerializer,
        responses={201: WithdrawalRequestSerializer}
    )
    @action(detail=False, methods=['post'], url_path='workspace/(?P<workspace_id>[^/.]+)/request')
    def create_request(self, request, workspace_id=None):
        """Create withdrawal request for workspace"""
        if not check_workspace_member(request.user, workspace_id, ['admin', 'manager']):
            return ErrorResponse(
                message="You don't have permission to request withdrawals",
                status_code=403
            )
        
        serializer = CreateWithdrawalRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return ErrorResponse(
                message='Invalid withdrawal request data',
                errors=serializer.errors,
                status_code=400
            )
        
        bank_account_id = serializer.validated_data['bank_account']
        amount = serializer.validated_data['amount']
        notes = serializer.validated_data.get('notes', '')
        
        try:
            # Get workspace wallet
            from workspace.models import Workspace
            workspace = get_object_or_404(Workspace, id=workspace_id)
            workspace_wallet = BankService.create_workspace_wallet(workspace)
            
            # Get bank account
            bank_account = get_object_or_404(
                BankAccount,
                id=bank_account_id,
                workspace=workspace,
                is_active=True
            )
            
            # Create withdrawal request
            withdrawal = BankService.create_withdrawal_request(
                workspace_wallet=workspace_wallet,
                bank_account=bank_account,
                amount=amount,
                requested_by=request.user,
                notes=notes
            )
            
            serializer = WithdrawalRequestSerializer(withdrawal)
            return SuccessResponse(
                message='Withdrawal request created successfully',
                data=serializer.data,
                status_code=201
            )
        except ValueError as e:
            return ErrorResponse(
                message=str(e),
                status_code=400
            )
        except Exception as e:
            return ErrorResponse(
                message=f'Failed to create withdrawal request: {str(e)}',
                status_code=500
            )
    
    @extend_schema(
        request=ProcessWithdrawalSerializer,
        responses={200: WithdrawalRequestSerializer}
    )
    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        """Process withdrawal request (admin only)"""
        withdrawal = self.get_object()
        
        # Check permission
        if not check_workspace_member(
            request.user,
            withdrawal.workspace_wallet.workspace.id,
            ['admin']
        ):
            return ErrorResponse(
                message="Only admins can process withdrawals",
                status_code=403
            )
        
        if withdrawal.status != 'pending':
            return ErrorResponse(
                message=f'Cannot process withdrawal with status: {withdrawal.status}',
                status_code=400
            )
        
        serializer = ProcessWithdrawalSerializer(data=request.data)
        if serializer.is_valid():
            admin_notes = serializer.validated_data.get('admin_notes', '')
            if admin_notes:
                withdrawal.admin_notes = admin_notes
                withdrawal.save(update_fields=['admin_notes'])
        
        try:
            # Process withdrawal
            BankService.process_withdrawal(withdrawal)
            
            # TODO: Integrate with payment gateway for actual bank transfer
            # For now, mark as completed
            BankService.complete_withdrawal(withdrawal)
            
            serializer = WithdrawalRequestSerializer(withdrawal)
            return SuccessResponse(
                message='Withdrawal processed successfully',
                data=serializer.data
            )
        except ValueError as e:
            return ErrorResponse(
                message=str(e),
                status_code=400
            )
        except Exception as e:
            return ErrorResponse(
                message=f'Failed to process withdrawal: {str(e)}',
                status_code=500
            )
    
    @extend_schema(
        responses={200: WithdrawalRequestSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='workspace/(?P<workspace_id>[^/.]+)')
    def workspace_withdrawals(self, request, workspace_id=None):
        """Get withdrawal requests for specific workspace"""
        if not check_workspace_member(request.user, workspace_id, ['admin', 'manager']):
            return ErrorResponse(
                message="You don't have permission to view withdrawals",
                status_code=403
            )
        
        withdrawals = self.get_queryset().filter(
            workspace_wallet__workspace_id=workspace_id
        )
        
        page = self.paginate_queryset(withdrawals)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(withdrawals, many=True)
        return SuccessResponse(
            message='Withdrawal requests retrieved successfully',
            data=serializer.data
        )
