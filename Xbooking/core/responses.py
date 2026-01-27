"""
Standardized API response utilities
"""

from rest_framework.response import Response
from rest_framework import status
from typing import Any, Dict, Optional


class SuccessResponse(Response):
    """
    Standardized success response
    """
    def __init__(
        self,
        data: Any = None,
        message: str = "Operation successful",
        status_code: int = status.HTTP_200_OK,
        **kwargs
    ):
        response_data = {
            "success": True,
            "message": message,
        }
        
        if data is not None:
            if isinstance(data, dict):
                response_data.update(data)
            else:
                response_data["data"] = data
        
        super().__init__(data=response_data, status=status_code, **kwargs)


class ErrorResponse(Response):
    """
    Standardized error response
    """
    def __init__(
        self,
        message: str = "Operation failed",
        errors: Optional[Dict] = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        **kwargs
    ):
        response_data = {
            "success": False,
            "message": message,
        }
        
        if errors:
            response_data["errors"] = errors
        
        super().__init__(data=response_data, status=status_code, **kwargs)


class PaginatedResponse:
    """
    Helper for creating paginated responses
    """
    @staticmethod
    def create(paginator, queryset, serializer_class, request, **serializer_kwargs):
        """
        Create paginated response
        
        Args:
            paginator: Pagination class instance
            queryset: Queryset to paginate
            serializer_class: Serializer to use for data
            request: Request object
            **serializer_kwargs: Additional serializer kwargs
            
        Returns:
            Paginated response
        """
        page = paginator.paginate_queryset(queryset, request)
        
        if page is not None:
            serializer = serializer_class(page, many=True, **serializer_kwargs)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = serializer_class(queryset, many=True, **serializer_kwargs)
        return SuccessResponse(data={"results": serializer.data})
