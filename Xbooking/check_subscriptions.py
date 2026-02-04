"""
Quick script to check push subscriptions in database
Run with: python check_subscriptions.py
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Xbooking.settings')
django.setup()

from notifications.models_push import PushSubscription
from user.models import User

def check_subscriptions():
    print("\n" + "="*80)
    print("PUSH SUBSCRIPTIONS DATABASE CHECK")
    print("="*80 + "\n")
    
    total = PushSubscription.objects.count()
    active = PushSubscription.objects.filter(is_active=True).count()
    
    print(f"Total Subscriptions: {total}")
    print(f"Active Subscriptions: {active}")
    print(f"Inactive Subscriptions: {total - active}")
    print("\n" + "-"*80 + "\n")
    
    if total == 0:
        print("❌ NO SUBSCRIPTIONS FOUND IN DATABASE!")
        print("\nThis means:")
        print("  1. Frontend is not calling the subscribe API")
        print("  2. The API call is failing silently")
        print("  3. Database migration hasn't run")
        print("\nTo fix:")
        print("  - Check browser console for errors")
        print("  - Check Django logs for API errors")
        print("  - Run: python manage.py migrate")
    else:
        print("SUBSCRIPTION DETAILS:\n")
        
        for sub in PushSubscription.objects.all():
            print(f"ID: {sub.id}")
            print(f"User: {sub.user.email}")
            print(f"Active: {'✓' if sub.is_active else '✗'}")
            print(f"Endpoint: {sub.endpoint[:100]}...")
            print(f"Created: {sub.created_at}")
            print(f"Last Used: {sub.last_used_at or 'Never'}")
            print(f"User Agent: {sub.user_agent[:80] if sub.user_agent else 'N/A'}...")
            print("-" * 80)
    
    print("\n" + "="*80)
    print("USERS WITH ACTIVE SUBSCRIPTIONS")
    print("="*80 + "\n")
    
    users_with_subs = User.objects.filter(
        push_subscriptions__is_active=True
    ).distinct()
    
    for user in users_with_subs:
        user_subs = PushSubscription.objects.filter(user=user, is_active=True).count()
        print(f"✓ {user.email}: {user_subs} active subscription(s)")
    
    if not users_with_subs.exists():
        print("❌ No users have active subscriptions!")

if __name__ == '__main__':
    check_subscriptions()
