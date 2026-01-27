"""
User Profile Views V1
"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema, OpenApiResponse

from core.responses import SuccessResponse, ErrorResponse
from core.cache import CacheService
from user.serializers.v1 import UserProfileSerializer
from Xbooking.cloudinary_storage import upload_file_to_cloudinary


class UserProfileView(APIView):
    """
    User profile management.
    GET: Retrieve current user profile (cached)
    PATCH: Update user profile (invalidates cache)
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        responses={
            200: UserProfileSerializer,
        },
        description='Get authenticated user profile',
        tags=['User Profile']
    )
    def get(self, request):
        """Get user profile with caching"""
        user = request.user
        cache_key = f"user_profile:{user.id}"
        
        # Try cache first
        cached_data = CacheService.get(cache_key)
        if cached_data:
            return SuccessResponse(
                message='Profile retrieved successfully',
                data=cached_data
            )
        
        # Serialize and cache
        serializer = UserProfileSerializer(user, context={'request': request})
        CacheService.set(cache_key, serializer.data, timeout=300)  # 5 minutes
        
        return SuccessResponse(
            message='Profile retrieved successfully',
            data=serializer.data
        )
    
    @extend_schema(
        request=UserProfileSerializer,
        responses={
            200: UserProfileSerializer,
            400: OpenApiResponse(description='Validation error'),
        },
        description='Update user profile (full_name, phone, avatar_url)',
        tags=['User Profile']
    )
    def patch(self, request):
        """Update user profile"""
        user = request.user
        
        # Prevent email change
        if 'email' in request.data and request.data['email'] != user.email:
            return ErrorResponse(
                message='Email cannot be changed',
                status_code=400
            )
        
        serializer = UserProfileSerializer(
            user,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return ErrorResponse(
                message='Profile update failed',
                errors=serializer.errors,
                status_code=400
            )
        
        user = serializer.save()
        
        # Invalidate cache
        cache_key = f"user_profile:{user.id}"
        CacheService.delete(cache_key)
        
        return SuccessResponse(
            message='Profile updated successfully',
            data=serializer.data
        )


class UploadProfilePictureView(APIView):
    """
    Upload profile picture to Cloudinary
    POST: Upload profile picture
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    @extend_schema(
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'profile_picture': {
                        'type': 'string',
                        'format': 'binary',
                    }
                }
            }
        },
        responses={
            200: OpenApiResponse(description='Profile picture uploaded successfully'),
            400: OpenApiResponse(description='Invalid file or upload failed'),
        },
        description='Upload profile picture to Cloudinary',
        tags=['User Profile']
    )
    def post(self, request):
        """Upload profile picture"""
        user = request.user
        
        # Get uploaded file
        uploaded_file = request.FILES.get('profile_picture')
        if not uploaded_file:
            return ErrorResponse(
                message='No file provided',
                status_code=400
            )
        
        # Validate file type
        allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp']
        file_ext = uploaded_file.name.split('.')[-1].lower() if '.' in uploaded_file.name else ''
        
        if file_ext not in allowed_extensions:
            return ErrorResponse(
                message=f'Invalid file type. Allowed: {", ".join(allowed_extensions)}',
                status_code=400
            )
        
        # Validate file size (max 5MB)
        max_size = 5 * 1024 * 1024  # 5MB
        if uploaded_file.size > max_size:
            return ErrorResponse(
                message='File size exceeds 5MB limit',
                status_code=400
            )
        
        try:
            # Read file data
            file_data = uploaded_file.read()
            
            # Upload to Cloudinary
            public_id = f"user_{user.id}_profile"
            upload_result = upload_file_to_cloudinary(
                file_data=file_data,
                filename=uploaded_file.name,
                folder='xbooking/profile_pictures',
                public_id=public_id,
                resource_type='image'
            )
            
            if not upload_result.get('success'):
                return ErrorResponse(
                    message='Failed to upload file to Cloudinary',
                    errors={'cloudinary_error': upload_result.get('error', 'Unknown error')},
                    status_code=500
                )
            
            # Update user avatar_url
            avatar_url = upload_result.get('file_url')
            user.avatar_url = avatar_url
            user.save(update_fields=['avatar_url'])
            
            # Invalidate cache
            cache_key = f"user_profile:{user.id}"
            CacheService.delete(cache_key)
            
            return SuccessResponse(
                message='Profile picture uploaded successfully',
                data={
                    'avatar_url': avatar_url,
                    'file_id': upload_result.get('file_id'),
                }
            )
            
        except Exception as e:
            return ErrorResponse(
                message='Failed to upload profile picture',
                errors={'error': str(e)},
                status_code=500
            )

