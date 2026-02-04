"""
Clean up expired push subscriptions
Run with: python cleanup_expired_subs.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Xbooking.settings')
django.setup()

from notifications.models_push import PushSubscription

def cleanup():
    print("\n" + "="*80)
    print("CLEANING UP EXPIRED PUSH SUBSCRIPTIONS")
    print("="*80 + "\n")
    
    # Mark all as inactive to force re-subscription
    total = PushSubscription.objects.filter(is_active=True).count()
    print(f"Found {total} active subscriptions")
    print("Marking all as inactive to force fresh subscriptions...")
    
    updated = PushSubscription.objects.filter(is_active=True).update(is_active=False)
    print(f"✓ Marked {updated} subscriptions as inactive")
    print("\nUsers will need to re-subscribe to get new valid subscriptions.")
    print("The app will do this automatically on next visit.\n")

if __name__ == '__main__':
    cleanup()
