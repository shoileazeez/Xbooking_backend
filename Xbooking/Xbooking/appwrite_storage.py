"""
Appwrite Cloud Storage Utility
Global utility for uploading files to Appwrite cloud storage
"""
import requests
import logging
from django.conf import settings
from typing import Optional, Dict, Any
import io
import uuid

logger = logging.getLogger(__name__)


class AppwriteStorage:
    """
    Global utility class for managing file uploads to Appwrite cloud storage.
    Can be used for QR codes, images, documents, and any other file types.
    """
    
    def __init__(self):
        """Initialize Appwrite storage with credentials from settings"""
        self.endpoint = getattr(settings, 'APPWRITE_ENDPOINT', 'https://cloud.appwrite.io/v1')
        self.project_id = getattr(settings, 'APPWRITE_PROJECT_ID', '')
        self.api_key = getattr(settings, 'APPWRITE_API_KEY', '')
        self.bucket_id = getattr(settings, 'APPWRITE_BUCKET_ID', '')
        
        if not all([self.project_id, self.api_key, self.bucket_id]):
            logger.warning("Appwrite credentials not fully configured. Please set APPWRITE_PROJECT_ID, APPWRITE_API_KEY, and APPWRITE_BUCKET_ID in settings.")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for Appwrite API requests"""
        return {
            'X-Appwrite-Project': self.project_id,
            'X-Appwrite-Key': self.api_key,
        }
    
    def upload_file(
        self,
        file_data: bytes,
        filename: str,
        file_id: Optional[str] = None,
        permissions: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Upload a file to Appwrite storage.
        
        Args:
            file_data: File content as bytes
            filename: Name of the file to store
            file_id: Optional custom file ID (will generate UUID if not provided)
            permissions: Optional list of permissions (e.g., ['read("any")'])
        
        Returns:
            dict: Response containing success status, file_id, and file_url
            {
                'success': True,
                'file_id': 'abc123',
                'file_url': 'https://cloud.appwrite.io/v1/storage/buckets/.../files/.../view'
            }
        """
        try:
            # Generate file ID if not provided
            if not file_id:
                file_id = str(uuid.uuid4())
            
            # Prepare the upload URL
            upload_url = f"{self.endpoint}/storage/buckets/{self.bucket_id}/files"
            
            # Prepare headers
            headers = self._get_headers()
            
            # Prepare files for multipart upload
            files = {
                'fileId': (None, file_id),
                'file': (filename, io.BytesIO(file_data), 'image/png')
            }
            
            # Add permissions if provided
            if permissions:
                files['permissions'] = (None, str(permissions))
            else:
                # Default: allow anyone to read
                files['permissions'] = (None, '["read(\\"any\\")"]')
            
            # Make the upload request
            response = requests.post(
                upload_url,
                headers=headers,
                files=files,
                timeout=30
            )
            
            # Check response
            if response.status_code in [200, 201]:
                result = response.json()
                
                # Generate file URL for viewing
                file_url = f"{self.endpoint}/storage/buckets/{self.bucket_id}/files/{file_id}/view?project={self.project_id}"
                
                logger.info(f"Successfully uploaded file to Appwrite: {file_id}")
                
                return {
                    'success': True,
                    'file_id': file_id,
                    'file_url': file_url,
                    'bucket_id': self.bucket_id,
                    'filename': filename,
                    'size': result.get('sizeOriginal', 0)
                }
            else:
                error_msg = response.text
                logger.error(f"Appwrite upload failed: {response.status_code} - {error_msg}")
                return {
                    'success': False,
                    'error': f"Upload failed: {error_msg}",
                    'status_code': response.status_code
                }
        
        except requests.exceptions.Timeout:
            logger.error("Appwrite upload timeout")
            return {
                'success': False,
                'error': 'Upload timeout - please try again'
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Appwrite upload request error: {str(e)}")
            return {
                'success': False,
                'error': f'Network error: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Appwrite upload error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def delete_file(self, file_id: str) -> Dict[str, Any]:
        """
        Delete a file from Appwrite storage.
        
        Args:
            file_id: ID of the file to delete
        
        Returns:
            dict: Response containing success status
        """
        try:
            delete_url = f"{self.endpoint}/storage/buckets/{self.bucket_id}/files/{file_id}"
            headers = self._get_headers()
            
            response = requests.delete(
                delete_url,
                headers=headers,
                timeout=10
            )
            
            if response.status_code in [200, 204]:
                logger.info(f"Successfully deleted file from Appwrite: {file_id}")
                return {
                    'success': True,
                    'message': 'File deleted successfully'
                }
            else:
                logger.error(f"Appwrite delete failed: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'error': f"Delete failed: {response.text}"
                }
        
        except Exception as e:
            logger.error(f"Appwrite delete error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_file_url(self, file_id: str) -> str:
        """
        Get the public URL for a file.
        
        Args:
            file_id: ID of the file
        
        Returns:
            str: Public URL to view the file
        """
        return f"{self.endpoint}/storage/buckets/{self.bucket_id}/files/{file_id}/view?project={self.project_id}"
    
    def get_file_download_url(self, file_id: str) -> str:
        """
        Get the download URL for a file.
        
        Args:
            file_id: ID of the file
        
        Returns:
            str: URL to download the file
        """
        return f"{self.endpoint}/storage/buckets/{self.bucket_id}/files/{file_id}/download?project={self.project_id}"


# Global instance for easy access
appwrite_storage = AppwriteStorage()


def upload_qr_code_to_appwrite(
    qr_image_bytes: bytes,
    filename: str,
    file_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Helper function to upload QR code images to Appwrite.
    
    Args:
        qr_image_bytes: QR code image as bytes
        filename: Filename for the QR code (e.g., 'qr_ORD-123.png')
        file_id: Optional custom file ID
    
    Returns:
        dict: Upload result with file_url
    
    Example:
        >>> from io import BytesIO
        >>> img_io = BytesIO()
        >>> qr_image.save(img_io, format='PNG')
        >>> result = upload_qr_code_to_appwrite(img_io.getvalue(), 'qr_order_123.png')
        >>> if result['success']:
        >>>     qr_url = result['file_url']
    """
    return appwrite_storage.upload_file(
        file_data=qr_image_bytes,
        filename=filename,
        file_id=file_id,
        permissions=['read("any")']  # Public read access for QR codes
    )


def upload_file_to_appwrite(
    file_data: bytes,
    filename: str,
    file_id: Optional[str] = None,
    permissions: Optional[list] = None
) -> Dict[str, Any]:
    """
    Generic helper function to upload any file to Appwrite.
    
    Args:
        file_data: File content as bytes
        filename: Name of the file
        file_id: Optional custom file ID
        permissions: Optional list of permissions
    
    Returns:
        dict: Upload result with file_url
    
    Example:
        >>> with open('document.pdf', 'rb') as f:
        >>>     result = upload_file_to_appwrite(f.read(), 'document.pdf')
        >>>     if result['success']:
        >>>         file_url = result['file_url']
    """
    return appwrite_storage.upload_file(
        file_data=file_data,
        filename=filename,
        file_id=file_id,
        permissions=permissions
    )


def delete_file_from_appwrite(file_id: str) -> Dict[str, Any]:
    """
    Helper function to delete a file from Appwrite.
    
    Args:
        file_id: ID of the file to delete
    
    Returns:
        dict: Delete result
    """
    return appwrite_storage.delete_file(file_id)
