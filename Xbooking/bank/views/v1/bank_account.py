"""
Bank Account Views V1
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, extend_schema_view

from core.views import CachedModelViewSet
from core.responses import SuccessResponse, ErrorResponse
from core.pagination import StandardResultsSetPagination
from bank.models import BankAccount
from bank.serializers.v1 import BankAccountSerializer, CreateBankAccountSerializer
from workspace.permissions import check_workspace_member


@extend_schema_view(
    list=extend_schema(description="List user/workspace bank accounts"),
    retrieve=extend_schema(description="Retrieve bank account details"),
    create=extend_schema(description="Create bank account"),
)
class BankAccountViewSet(CachedModelViewSet):
    """ViewSet for managing bank accounts"""
    serializer_class = BankAccountSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    cache_timeout = 600
    http_method_names = ['get', 'post', 'patch', 'delete']
    
    def get_queryset(self):
        """Get bank accounts for user"""
        return BankAccount.objects.filter(
            user=self.request.user,
            is_active=True
        ).order_by('-is_default', '-created_at')
    
    @extend_schema(
        request=CreateBankAccountSerializer,
        responses={201: BankAccountSerializer}
    )
    def create(self, request):
        """Create bank account for user"""
        serializer = CreateBankAccountSerializer(data=request.data)
        
        if not serializer.is_valid():
            return ErrorResponse(
                message='Invalid bank account data',
                errors=serializer.errors,
                status_code=400
            )
        
        data = serializer.validated_data
        
        # If set as default, unset other defaults
        if data.get('is_default'):
            BankAccount.objects.filter(
                user=request.user,
                is_default=True
            ).update(is_default=False)
        
        bank_account = BankAccount.objects.create(
            user=request.user,
            **data
        )
        
        serializer = BankAccountSerializer(bank_account)
        return SuccessResponse(
            message='Bank account created successfully',
            data=serializer.data,
            status_code=201
        )
    
    @extend_schema(
        request=None,
        responses={200: BankAccountSerializer}
    )
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """Set bank account as default"""
        bank_account = self.get_object()
        
        # Unset other defaults
        BankAccount.objects.filter(
            user=request.user,
            is_default=True
        ).update(is_default=False)
        
        bank_account.is_default = True
        bank_account.save(update_fields=['is_default'])
        
        serializer = self.get_serializer(bank_account)
        return SuccessResponse(
            message='Default bank account updated',
            data=serializer.data
        )
    
    @extend_schema(
        responses={200: BankAccountSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='workspace/(?P<workspace_id>[^/.]+)')
    def workspace_accounts(self, request, workspace_id=None):
        """Get bank accounts for workspace (admin only)"""
        if not check_workspace_member(request.user, workspace_id, ['admin', 'manager']):
            return ErrorResponse(
                message="You don't have permission to view workspace bank accounts",
                status_code=403
            )
        
        accounts = BankAccount.objects.filter(
            workspace_id=workspace_id,
            is_active=True
        ).order_by('-is_default', '-created_at')
        
        page = self.paginate_queryset(accounts)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(accounts, many=True)
        return SuccessResponse(
            message='Bank accounts retrieved successfully',
            data=serializer.data
        )
    
    @extend_schema(
        request=CreateBankAccountSerializer,
        responses={201: BankAccountSerializer}
    )
    @action(detail=False, methods=['post'], url_path='workspace/(?P<workspace_id>[^/.]+)/create')
    def create_workspace_account(self, request, workspace_id=None):
        """Create bank account for workspace (admin only)"""
        if not check_workspace_member(request.user, workspace_id, ['admin', 'manager']):
            return ErrorResponse(
                message="You don't have permission to create workspace bank accounts",
                status_code=403
            )
        
        serializer = CreateBankAccountSerializer(data=request.data)
        
        if not serializer.is_valid():
            return ErrorResponse(
                message='Invalid bank account data',
                errors=serializer.errors,
                status_code=400
            )
        
        data = serializer.validated_data
        
        # If set as default, unset other defaults
        if data.get('is_default'):
            BankAccount.objects.filter(
                workspace_id=workspace_id,
                is_default=True
            ).update(is_default=False)
        
        bank_account = BankAccount.objects.create(
            workspace_id=workspace_id,
            **data
        )
        
        serializer = BankAccountSerializer(bank_account)
        return SuccessResponse(
            message='Bank account created successfully',
            data=serializer.data,
            status_code=201
        )
