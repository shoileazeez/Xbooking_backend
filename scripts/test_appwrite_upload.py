import os
import sys
from pathlib import Path
import json
import requests

# Ensure Django settings are available for appwrite_storage
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Xbooking.Xbooking.settings')

from Xbooking.Xbooking.appwrite_storage import (
    upload_file_to_appwrite,
    appwrite_storage,
)


def one_by_one_png_bytes() -> bytes:
    # Minimal 1x1 transparent PNG
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\x0cIDAT\x08\xd7c\x60\x00\x00\x00\x02\x00\x01\xe2!\xbc3"
        b"\x00\x00\x00\x00IEND\xAE\x42\x60\x82"
    )


def main():
    print("Appwrite upload test starting...")

    # Show configured Appwrite settings for debugging (no secrets printed beyond presence)
    from django.conf import settings
    endpoint = getattr(settings, 'APPWRITE_ENDPOINT', '')
    project_id = getattr(settings, 'APPWRITE_PROJECT_ID', '')
    api_key = getattr(settings, 'APPWRITE_API_KEY', '')
    bucket_id = getattr(settings, 'APPWRITE_BUCKET_ID', '')

    print("Configured endpoint:", endpoint)
    print("Project ID set:", bool(project_id))
    print("API Key set:", bool(api_key))
    print("Bucket ID:", bucket_id)

    png_bytes = one_by_one_png_bytes()
    filename = "test_upload.png"

    result = upload_file_to_appwrite(
        file_data=png_bytes,
        filename=filename,
        permissions=['read("any")'],
    )

    print("Result type:", type(result).__name__)
    print("Result JSON:")
    print(json.dumps(result, indent=2))

    if result.get('success'):
        file_id = result.get('file_id')
        file_url = result.get('file_url')
        download_url = appwrite_storage.get_file_download_url(file_id)

        print("File ID:", file_id)
        print("View URL:", file_url)
        print("Download URL:", download_url)

        # Attempt to fetch the view URL to verify accessibility
        try:
            resp = requests.get(file_url, timeout=10)
            print("View URL status:", resp.status_code)
            print("Content-Type:", resp.headers.get('Content-Type'))

            # Try again with X-Appwrite-Project header
            resp2 = requests.get(file_url, headers={"X-Appwrite-Project": project_id}, timeout=10)
            print("View URL status (with project header):", resp2.status_code)
            print("Content-Type:", resp2.headers.get('Content-Type'))

            # Try with API key for server-side access
            resp3 = requests.get(file_url, headers={"X-Appwrite-Project": project_id, "X-Appwrite-Key": api_key}, timeout=10)
            print("View URL status (with project+key headers):", resp3.status_code)
            print("Content-Type:", resp3.headers.get('Content-Type'))
        except Exception as e:
            print("Error fetching view URL:", str(e))
    else:
        print("Upload failed. Status:", result.get('status_code'))
        print("Error:", result.get('error'))


if __name__ == "__main__":
    main()
