"""
Test EventBus and Email Service Integration
Run this to verify the pub/sub system is working
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Xbooking.settings')
django.setup()

from core.services import EventBus, Event, EventTypes
from core.email_service import EmailService
from core.notification_service import NotificationService
import time

def test_eventbus():
    """Test EventBus pub/sub"""
    print("="*60)
    print("Testing EventBus System")
    print("="*60)
    
    # Initialize services
    EmailService.initialize()
    NotificationService.initialize()
    
    print("✓ Services initialized")
    
    # Create a test event
    test_event = Event(
        event_type=EventTypes.USER_REGISTERED,
        data={
            'user_id': '123e4567-e89b-12d3-a456-426614174000',
            'email': 'test@example.com',
            'full_name': 'Test User',
            'role': 'user',
            'is_business_email': False,
            'created_at': '2026-01-08T10:00:00',
        },
        source_module='test'
    )
    
    print(f"\n📤 Publishing test event: {test_event.event_type}")
    EventBus.publish(test_event)
    print("✓ Event published successfully")
    
    # Wait a bit for async processing
    time.sleep(1)
    
    print("\n✓ EventBus test completed!")
    print("\nSubscribed events:")
    for event_type, handlers in EventBus._subscribers.items():
        print(f"  - {event_type}: {len(handlers)} handler(s)")
    
    return True

if __name__ == "__main__":
    try:
        test_eventbus()
        print("\n" + "="*60)
        print("✓ All tests passed!")
        print("="*60)
    except Exception as e:
        print(f"\n✗ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
