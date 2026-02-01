# PWA Push Notifications Setup Guide

This guide will help you set up web push notifications for the Xbooking platform.

## Prerequisites

- Python 3.8+ with pip
- Node.js 18+ with pnpm
- Backend and frontend projects set up

## Step 1: Install Python Dependencies

```bash
cd Xbooking_backend/Xbooking
pip install py-vapid pywebpush
```

## Step 2: Generate VAPID Keys

VAPID (Voluntary Application Server Identification) keys are required for web push authentication.

```bash
cd Xbooking_backend
python scripts/generate_vapid_keys.py
```

This will output keys in the following format:

```
============================================================
VAPID Keys Generated Successfully!
============================================================

Add these to your backend .env file:

VAPID_PUBLIC_KEY=<your-public-key>
VAPID_PRIVATE_KEY=<your-private-key>
VAPID_ADMIN_EMAIL=admin@xbooking.dev

============================================================

Add to frontend .env.local file:

NEXT_PUBLIC_VAPID_PUBLIC_KEY=<your-public-key>

============================================================

Keys also saved to:
  - private_key.pem
  - public_key.pem
============================================================
```

## Step 3: Configure Backend Environment

1. Create or update `Xbooking_backend/.env`:

```env
# Copy the keys from Step 2
VAPID_PUBLIC_KEY=<your-public-key>
VAPID_PRIVATE_KEY=<your-private-key>
VAPID_ADMIN_EMAIL=admin@xbooking.dev
```

**Important**: Never commit these keys to version control. Keep them secure.

## Step 4: Configure Frontend Environment

1. Create or update `xbooking/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
# Copy the VAPID_PUBLIC_KEY from Step 2
NEXT_PUBLIC_VAPID_PUBLIC_KEY=<your-public-key>
```

## Step 5: Run Database Migrations

The push notification system requires database tables for storing user subscriptions:

```bash
cd Xbooking_backend/Xbooking
python manage.py makemigrations
python manage.py migrate
```

## Step 6: Restart Services

### Backend
```bash
cd Xbooking_backend/Xbooking
python manage.py runserver
```

### Celery Workers (for async push notifications)
```bash
cd Xbooking_backend/Xbooking
celery -A Xbooking worker --loglevel=info
```

### Frontend
```bash
cd xbooking
pnpm dev
```

## Step 7: Test Push Notifications

1. Open your browser to `http://localhost:3000`
2. Log in to your account
3. Navigate to Settings → Notifications tab
4. Look for the "Browser Push Notifications" section
5. Click "Enable Push Notifications"
6. Accept the browser permission prompt
7. You should see a success message confirming subscription

## Testing Push Delivery

To test if push notifications are working:

1. Create a booking or trigger any notification event
2. Check that you receive a browser notification
3. Click the notification to verify it navigates correctly

## Troubleshooting

### "Service Worker Registration Failed"
- Ensure service worker is at `/sw.js` in public folder
- Check browser console for specific errors
- HTTPS is required for production (localhost works for development)

### "Push Subscription Failed"
- Verify VAPID public key is correctly set in frontend `.env.local`
- Check that browser supports Push API (most modern browsers do)
- Ensure user granted notification permissions

### "No Push Notifications Received"
- Verify backend has VAPID keys configured
- Check Celery worker is running (push notifications are sent async)
- Ensure notification preferences allow push notifications
- Check browser notification settings (not blocked)

### "Invalid VAPID Public Key" Error
- Keys must be base64url encoded without padding
- Ensure you copied the full key from generate script
- Keys are case-sensitive

## Production Deployment

### HTTPS Requirement
Push notifications require HTTPS in production. Ensure:
- Your domain has a valid SSL certificate
- Service worker is served over HTTPS
- API endpoints use HTTPS

### Environment Variables
- Never commit `.env` or `.env.local` files
- Use secure environment variable management (e.g., AWS Secrets Manager, Azure Key Vault)
- Rotate VAPID keys periodically for security

### Performance Considerations
- Push notifications are sent asynchronously via Celery
- Redis is used for event deduplication (prevents duplicate sends)
- Monitor Celery worker performance under load

## Architecture Overview

### Frontend Components
- **Service Worker** (`public/sw.js`): Handles push events and displays notifications
- **Push Notification Provider** (`lib/push-notifications.ts`): Manages subscription lifecycle
- **Settings UI** (`components/settings/push-notification-settings.tsx`): User interface for managing push

### Backend Services
- **PushSubscription Model** (`notifications/models_push.py`): Stores user subscriptions
- **Push Service** (`notifications/services/push_service.py`): Sends push notifications
- **API Endpoints** (`notifications/views/v1/push.py`): Subscribe/unsubscribe endpoints
- **Celery Tasks** (`notifications/tasks.py`): Async notification delivery

### Flow
1. User enables push in settings
2. Frontend requests notification permission
3. Service worker registers push subscription
4. Subscription sent to backend and stored
5. When notification created, Celery task sends push to all user subscriptions
6. Service worker receives push and displays notification

## API Endpoints

### Subscribe to Push
```
POST /api/v1/notifications/push/subscribe/
```

### Unsubscribe from Push
```
POST /api/v1/notifications/push/unsubscribe/
```

### Get User Subscriptions
```
GET /api/v1/notifications/push/subscriptions/
```

## Browser Compatibility

Push notifications are supported in:
- Chrome 50+
- Firefox 44+
- Safari 16+ (macOS 13+)
- Edge 17+
- Opera 37+

Not supported:
- Internet Explorer
- Safari on iOS (as of iOS 17)

## Security Notes

- VAPID keys authenticate your application to push services
- Private key must be kept secure (never expose to frontend)
- Public key is safe to expose (used by browser for subscription)
- Subscriptions are user-specific and browser-specific
- Users can revoke permissions at any time
