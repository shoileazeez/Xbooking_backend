import io
import time
import hashlib
import logging
import requests
from typing import Optional, Dict, Any
from django.conf import settings

logger = logging.getLogger(__name__)


def _cloudinary_endpoint(resource_type: str = 'image') -> str:
    cloud_name = getattr(settings, 'CLOUDINARY_CLOUD_NAME', '')
    return f"https://api.cloudinary.com/v1_1/{cloud_name}/{resource_type}/upload"


def _sign_params(params: Dict[str, Any]) -> str:
    api_secret = getattr(settings, 'CLOUDINARY_API_SECRET', '')
    pieces = [f"{k}={params[k]}" for k in sorted(params.keys())]
    to_sign = "&".join(pieces) + api_secret
    return hashlib.sha1(to_sign.encode('utf-8')).hexdigest()


def upload_file_to_cloudinary(
    file_data: bytes,
    filename: str,
    folder: Optional[str] = None,
    public_id: Optional[str] = None,
    resource_type: Optional[str] = None,
) -> Dict[str, Any]:
    try:
        cloud_name = getattr(settings, 'CLOUDINARY_CLOUD_NAME', '')
        api_key = getattr(settings, 'CLOUDINARY_API_KEY', '')
        api_secret = getattr(settings, 'CLOUDINARY_API_SECRET', '')

        if not all([cloud_name, api_key, api_secret]):
            logger.error("Cloudinary credentials not fully configured")
            return {'success': False, 'error': 'Cloudinary not configured'}

        # Infer resource_type if not provided
        if not resource_type:
            ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
            image_exts = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
            resource_type = 'image' if ext in image_exts else 'raw'

        ts = int(time.time())
        params = {'timestamp': ts}
        if folder:
            params['folder'] = folder
        if public_id:
            params['public_id'] = public_id

        signature = _sign_params(params)

        endpoint = _cloudinary_endpoint(resource_type)

        data = {
            'api_key': api_key,
            'timestamp': ts,
            'signature': signature,
        }
        if folder:
            data['folder'] = folder
        if public_id:
            data['public_id'] = public_id

        files = {
            'file': (filename, io.BytesIO(file_data)),
        }

        resp = requests.post(endpoint, data=data, files=files, timeout=30)
        if resp.status_code in (200, 201):
            result = resp.json()
            return {
                'success': True,
                'file_id': result.get('public_id'),
                'file_url': result.get('secure_url') or result.get('url'),
                'raw_response': result,
                'resource_type': resource_type,
                'filename': filename,
            }
        return {'success': False, 'error': resp.text, 'status_code': resp.status_code}
    except Exception as e:
        logger.error(f"Cloudinary upload error: {str(e)}")
        return {'success': False, 'error': str(e)}


def upload_qr_image_to_cloudinary(qr_bytes: bytes, filename: str, public_id: Optional[str] = None) -> Dict[str, Any]:
    folder = getattr(settings, 'CLOUDINARY_QR_FOLDER', 'xbooking/qr')
    return upload_file_to_cloudinary(qr_bytes, filename, folder=folder, public_id=public_id, resource_type='image')

