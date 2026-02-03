# Push Notification Fix Documentation

## Issues Fixed

### 1. **Subscription Not Persisting After First Notification**

**Problem**: Users received the first notification but subsequent notifications failed because subscriptions weren't properly maintained.

**Root Causes**:
- Subscriptions were not being re-validated after first use
- Expired subscriptions (HTTP 410) were not being cleaned up
- Multiple subscriptions for same endpoint from different users weren't handled
- Frontend didn't periodically verify subscription status

**Solutions Implemented**:

#### Backend Changes (`notifications/views/v1/push.py`):
```python
# Deactivate duplicate subscriptions from other users
PushSubscription.objects.filter(
    endpoint=endpoint
).exclude(
    user=request.user
).update(is_active=False)

# Ensure user field is always set correctly
if subscription.user != request.user:
    subscription.user = request.user
    subscription.is_active = True
    subscription.save()
```

#### Frontend Changes (`lib/push-notifications.ts`):
```typescript
// Always validate and update subscription with backend
// Detect expired subscriptions (410 Gone) and resubscribe
try {
  const response = await fetch(subscription.endpoint, { method: 'HEAD' });
  if (response.status === 410) {
    await subscription.unsubscribe();
    // Create new subscription
  }
} catch (error) {
  // Handle validation errors
}

// Always send subscription to backend, even if exists locally
await sendSubscriptionToBackend(subscription);
```

#### Push Notification Provider (`components/providers/push-notification-provider.tsx`):
```typescript
// Periodic subscription check every 60 seconds
useEffect(() => {
  let interval: NodeJS.Timeout;
  if (supported && user) {
    interval = setInterval(() => {
      checkSubscriptionStatus();
    }, 60000);
  }
  return () => {
    if (interval) clearInterval(interval);
  };
}, [user]);
```

### 2. **"Sent to 0 Devices" Issue**

**Problem**: Test push notifications reported success but showed "sent to 0 devices".

**Root Causes**:
- No active subscriptions in database
- Subscriptions marked as inactive after first failure
- User not properly associated with subscription
- VAPID keys not configured

**Solutions**:

1. **Check VAPID Configuration**:
```bash
# In Django settings
python manage.py shell
from django.conf import settings
print(settings.VAPID_PRIVATE_KEY)
print(settings.VAPID_PUBLIC_KEY)
```

2. **Verify Subscriptions Exist**:
```bash
python manage.py shell
from notifications.models_push import PushSubscription
from user.models import User

user = User.objects.get(email='your@email.com')
subs = PushSubscription.objects.filter(user=user, is_active=True)
print(f"Active subscriptions: {subs.count()}")
for sub in subs:
    print(f"- Endpoint: {sub.endpoint[:50]}...")
    print(f"  Created: {sub.created_at}")
    print(f"  Last used: {sub.last_used_at}")
```

3. **Manual Test**:
```bash
# Send test push from Django shell
from notifications.services.push_service import PushNotificationService

notification_data = PushNotificationService.format_notification_data(
    title='Manual Test',
    message='Testing push notifications',
    url='/notifications'
)

result = PushNotificationService.send_push_to_user(
    user_id='your-user-id',
    notification_data=notification_data
)
print(result)
```

### 3. **Service Worker Improvements**

**Enhanced Features**:
- Unique tags for each notification (prevents duplicates)
- Better error logging with `[Service Worker]` prefix
- Timestamp tracking in notification data
- Improved navigation handling with origin checking
- Better cache strategy (separate runtime cache)

**Service Worker Updates** (`public/sw.js`):
```javascript
// Unique tags prevent notification overwriting
tag: 'xbooking-' + (data.notification_id || Date.now())

// Enhanced logging
console.log('[Service Worker] Push notification received:', event);

// Better navigation
client.navigate(fullUrl);
return client.focus();
```

## Performance Optimizations

### 1. **React Query Optimizations**

```typescript
// Increased staleTime for better caching
staleTime: 2 * 60 * 1000, // 2 minutes (was 1 minute)

// Prevent unnecessary refetches
refetchOnMount: false, // Don't refetch if data exists
refetchOnWindowFocus: false,

// Exponential backoff for retries
retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000)
```

### 2. **API Query Optimizations**

**Notifications**:
- `staleTime`: 30s (was 60s) - faster updates
- `refetchOnMount`: false - avoid duplicate fetches

**Wallet**:
- `staleTime`: 2 minutes (was 1 minute)
- `refetchOnMount`: false

**Spaces**:
- `staleTime`: 3 minutes (was 1 minute)
- `refetchOnMount`: false

### 3. **Service Worker Caching**

**Strategy**:
- **API requests**: Network first, no cache
- **Images/Fonts/Styles**: Cache first with runtime cache
- **Other requests**: Network first with cache fallback

**Benefits**:
- Faster static asset loading
- Always fresh API data
- Better offline experience

## Testing Guide

### 1. **Test Push Notification Subscription**

```bash
# Frontend Console (Browser DevTools)
// Check if service worker is registered
navigator.serviceWorker.getRegistrations().then(regs => {
  console.log('Registrations:', regs);
});

// Check subscription
navigator.serviceWorker.ready.then(reg => {
  reg.pushManager.getSubscription().then(sub => {
    console.log('Subscription:', sub);
  });
});
```

### 2. **Test Backend Push**

```bash
# Django shell
python manage.py shell

from user.models import User
from notifications.services.push_service import PushNotificationService

user = User.objects.get(email='your@email.com')

data = PushNotificationService.format_notification_data(
    title='Test Notification',
    message='This is a test',
    url='/notifications'
)

result = PushNotificationService.send_push_to_user(
    user_id=str(user.id),
    notification_data=data
)

print(f"Success: {result.get('success')}")
print(f"Sent to: {result.get('sent')} devices")
print(f"Total subscriptions: {result.get('total')}")
```

### 3. **Test via API**

```bash
# Get auth token first
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"your@email.com","password":"your-password"}'

# Send test push
curl -X POST http://localhost:8000/api/v1/notifications/test-push/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

## Troubleshooting

### Issue: "No active push subscriptions found"

**Check**:
1. User is logged in
2. Notification permission is granted
3. Service worker is registered
4. Subscription was sent to backend

**Fix**:
```javascript
// Frontend: Resubscribe
await subscribeToPushNotifications();
```

### Issue: "VAPID keys not configured"

**Check Django settings**:
```python
# settings.py or .env
VAPID_PRIVATE_KEY=your_private_key
VAPID_PUBLIC_KEY=your_public_key
VAPID_ADMIN_EMAIL=admin@xbooking.dev
```

**Generate new keys**:
```bash
python scripts/generate_vapid_keys.py
```

### Issue: Notifications work once then stop

**Likely causes**:
1. Subscription expired (410 Gone)
2. Service worker not updating
3. Subscription not in database

**Fixes**:
1. Clear browser cache and resubscribe
2. Update service worker version in `sw.js`
3. Check database for active subscriptions

### Issue: Service worker not updating

**Force update**:
```javascript
// Browser console
navigator.serviceWorker.getRegistrations().then(registrations => {
  registrations.forEach(reg => reg.update());
});

// Or unregister and re-register
navigator.serviceWorker.getRegistrations().then(registrations => {
  registrations.forEach(reg => reg.unregister());
});
// Then reload page
```

## Monitoring

### Check Subscription Health

```python
# Django management command (create this)
# management/commands/check_push_subscriptions.py

from django.core.management.base import BaseCommand
from notifications.models_push import PushSubscription
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        total = PushSubscription.objects.count()
        active = PushSubscription.objects.filter(is_active=True).count()
        
        # Subscriptions not used in 7 days
        week_ago = timezone.now() - timedelta(days=7)
        stale = PushSubscription.objects.filter(
            is_active=True,
            last_used_at__lt=week_ago
        ).count()
        
        self.stdout.write(f"Total subscriptions: {total}")
        self.stdout.write(f"Active: {active}")
        self.stdout.write(f"Stale (>7 days): {stale}")
```

### Logging

**Backend** (`notifications/services/push_service.py`):
```python
logger.info(f"Push notification sent to subscription {subscription.id}")
logger.error(f"WebPush error for subscription {subscription.id}: {str(e)}")
```

**Frontend** (Browser Console):
```
[Service Worker] Push notification received
[Service Worker] Notification shown successfully
[Service Worker] Notification clicked
```

## Best Practices

1. **Always validate subscriptions** before sending
2. **Clean up expired subscriptions** (410 status)
3. **Use unique tags** for notifications to prevent overwrites
4. **Log everything** for debugging
5. **Test regularly** with real devices
6. **Monitor subscription count** and health
7. **Handle errors gracefully** with fallbacks
8. **Update service worker version** when making changes

## Next Steps

1. ✅ Fix subscription persistence
2. ✅ Improve error handling
3. ✅ Optimize performance
4. ✅ Add periodic subscription checks
5. ⏳ Add subscription cleanup job (cron)
6. ⏳ Add push notification analytics
7. ⏳ Add user preference controls
8. ⏳ Test across different browsers/devices
