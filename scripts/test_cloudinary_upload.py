import os
import sys
from pathlib import Path
import json
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Xbooking.Xbooking.settings')

from django.conf import settings
from Xbooking.Xbooking.cloudinary_storage import upload_file_to_cloudinary


def one_by_one_png_bytes() -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\x0cIDAT\x08\xd7c\x60\x00\x00\x00\x02\x00\x01\xe2!\xbc3"
        b"\x00\x00\x00\x00IEND\xAE\x42\x60\x82"
    )


def main():
    print("Cloudinary upload test starting...")

    print("Cloud name set:", bool(getattr(settings, 'CLOUDINARY_CLOUD_NAME', '')))
    print("API key set:", bool(getattr(settings, 'CLOUDINARY_API_KEY', '')))    
    print("API secret set:", bool(getattr(settings, 'CLOUDINARY_API_SECRET', '')))    
    print("QR folder:", getattr(settings, 'CLOUDINARY_QR_FOLDER', ''))
    print("Upload folder:", getattr(settings, 'CLOUDINARY_UPLOAD_FOLDER', ''))

    png_bytes = one_by_one_png_bytes()
    filename = "test_cloudinary_upload.png"

    result = upload_file_to_cloudinary(
        file_data=png_bytes,
        filename=filename,
        folder=settings.CLOUDINARY_UPLOAD_FOLDER,
    )

    print("Result type:", type(result).__name__)
    print(json.dumps(result, indent=2))

    if result.get('success'):
        url = result.get('file_url')
        print("Secure URL:", url)
        try:
            resp = requests.get(url, timeout=10)
            print("View URL status:", resp.status_code)
            print("Content-Type:", resp.headers.get('Content-Type'))
        except Exception as e:
            print("Error fetching URL:", str(e))
    else:
        print("Upload failed:", result.get('error'))


if __name__ == "__main__":
    main()

