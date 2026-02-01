# Push Notifications Setup Guide

## Backend Setup

### 1. Install Required Package
```bash
pip install pywebpush
```

### 2. Generate VAPID Keys
```bash
# In Python shell or create a script
from pywebpush import webpush, WebPushException
from py_vapid import Vapid

vapid = Vapid()
vapid.generate_keys()

print("Public Key:", vapid.public_key.decode('utf-8'))
print("Private Key:", vapid.private_key.decode('utf-8'))
```

### 3. Add to Django Settings
```python
# In settings.py

# VAPID Keys for Web Push Notifications
VAPID_PUBLIC_KEY = "your-public-key-here"
VAPID_PRIVATE_KEY = "your-private-key-here"
VAPID_ADMIN_EMAIL = "admin@xbooking.dev"
```

### 4. Create Database Migration
```bash
cd Xbooking_backend/Xbooking
python manage.py makemigrations notifications
python manage.py migrate
```

### 5. Update Frontend Environment
```bash
# In xbooking/.env.local
NEXT_PUBLIC_VAPID_PUBLIC_KEY=your-public-key-here
```

## Testing Push Notifications

### 1. Enable in User Settings
- Go to Settings page
- Find "Push Notifications" section
- Click "Enable Push Notifications"
- Allow browser permissions when prompted

### 2. Test Notification
- Click "Send Test Notification" button
- You should see a browser notification

### 3. Real Notifications
- When bookings are cancelled, confirmed, etc.
- You will receive browser notifications
- Works even when the browser tab is closed

## Features
✅ Browser push notifications
✅ Works offline (PWA)
✅ Multiple device support
✅ Automatic retry on failure
✅ Subscription management
✅ User preferences integration

## Browser Support
- Chrome/Edge: Full support
- Firefox: Full support
- Safari: iOS 16.4+ and macOS 13+
- Opera: Full support
