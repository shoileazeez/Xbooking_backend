"""
Django management command to cleanup expired push subscriptions
Run with: python manage.py cleanup_push_subscriptions
"""
from django.core.management.base import BaseCommand
from notifications.models_push import PushSubscription


class Command(BaseCommand):
    help = 'Cleanup expired push subscriptions'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('\nCleaning up expired push subscriptions...'))
        
        # Mark all as inactive to force re-subscription
        active_count = PushSubscription.objects.filter(is_active=True).count()
        
        if active_count == 0:
            self.stdout.write(self.style.SUCCESS('No active subscriptions to clean up'))
            return
        
        self.stdout.write(f'Found {active_count} active subscriptions')
        self.stdout.write('Marking all as inactive to force fresh subscriptions...')
        
        updated = PushSubscription.objects.filter(is_active=True).update(is_active=False)
        
        self.stdout.write(self.style.SUCCESS(f'✓ Marked {updated} subscriptions as inactive'))
        self.stdout.write(self.style.SUCCESS('\nUsers will automatically re-subscribe on next visit'))
