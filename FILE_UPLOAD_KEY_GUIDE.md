# FILE_UPLOAD_KEY Generation & Usage Guide

## Generate FILE_UPLOAD_KEY

### Using Django Management Command

```bash
# Generate with default settings (64 chars, alphanumeric format)
python manage.py generate_file_upload_key

# Generate with custom length (32 chars)
python manage.py generate_file_upload_key --length 32

# Generate in hex format
python manage.py generate_file_upload_key --format hex

# Generate in base64 format
python manage.py generate_file_upload_key --format base64
```

### Format Options

1. **alphanumeric** (default)
   - Characters: A-Z, a-z, 0-9, `-`, `_`, `.`
   - Most secure for HTTP headers
   - Example: `2p0mO6BmKQksWTO9Wq9q8QIu4QR9Rx1sTdqbW.W3aINqWg6VbyE1GwoQ8km9qP7f`

2. **hex**
   - Characters: 0-9, a-f
   - Shorter but still secure
   - Example: `02944aa9c06e60d18be27bd594ed1420`

3. **base64**
   - URL-safe base64 encoding
   - Most compact format
   - Example: `wEv-oBNn5fiung6iDxP4FtugcFNP__GG0wIHsSdi6P7XG22D`

## Setup

1. Generate a key:
```bash
python manage.py generate_file_upload_key
```

2. Add to your `.env` file:
```env
FILE_UPLOAD_KEY=your_generated_key_here
```

3. The system will load it automatically via Django settings

## Frontend Usage

### Option 1: Send key in Header
```javascript
const fileUploadKey = 'your_FILE_UPLOAD_KEY';
const formData = new FormData();
formData.append('file', file);

fetch('http://localhost:8000/api/qr/upload/file/', {
  method: 'POST',
  headers: {
    'X-File-Upload-Key': fileUploadKey
  },
  body: formData
})
.then(response => response.json())
.then(data => {
  console.log('File URL:', data.file_url);
  console.log('File ID:', data.file_id);
});
```

### Option 2: Send key as Query Parameter
```javascript
const fileUploadKey = 'your_FILE_UPLOAD_KEY';
const formData = new FormData();
formData.append('file', file);

fetch(`http://localhost:8000/api/qr/upload/file/?file_upload_key=${fileUploadKey}`, {
  method: 'POST',
  body: formData
})
.then(response => response.json())
.then(data => {
  console.log('File URL:', data.file_url);
});
```

### Response Example
```json
{
  "success": true,
  "file_id": "abc123xyz",
  "file_url": "https://cloud.appwrite.io/v1/storage/buckets/.../files/.../view",
  "filename": "image.png",
  "size": 12345,
  "message": "File uploaded successfully"
}
```

## Using cURL

```bash
FILE_UPLOAD_KEY="your_FILE_UPLOAD_KEY"

# Upload with header
curl -X POST http://localhost:8000/api/qr-code/upload/file/ \
  -H "X-File-Upload-Key: $FILE_UPLOAD_KEY" \
  -F "file=@image.png"

# Upload with query parameter
curl -X POST "http://localhost:8000/api/qr/upload/file/?file_upload_key=$FILE_UPLOAD_KEY" \
  -F "file=@image.png"
```

## Security Notes

- The FILE_UPLOAD_KEY is stored in your `.env` file and environment variables
- Each uploaded file is stored in Appwrite cloud storage
- File uploads are throttled to 50 per day per IP
- Supported file types are configurable in settings (default: png, jpg, jpeg, gif, pdf, doc, docx, xls, xlsx)
- Maximum file size is configurable (default: 50MB)

## Configuration

Edit `.env` to customize:

```env
# File upload key for authorization
FILE_UPLOAD_KEY=your_key_here

# Maximum file size in MB
MAX_FILE_SIZE_MB=50

# Allowed file types (comma-separated)
ALLOWED_FILE_TYPES=png,jpg,jpeg,gif,pdf,doc,docx,xls,xlsx
```

These settings are defined in `Xbooking/settings.py`.
