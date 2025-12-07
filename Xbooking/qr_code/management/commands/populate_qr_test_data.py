"""
Django management command to populate test data for QR code testing
Creates workspaces, spaces, users, orders, and bookings
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, time
from user.models import User
from workspace.models import Workspace, Branch, Space, SpaceCalendar, SpaceCalendarSlot, WorkspaceUser
from payment.models import Order
from booking.models import Booking
from decimal import Decimal
import uuid


class Command(BaseCommand):
    help = 'Populate database with test data for QR code testing'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n🚀 Starting test data population...\n'))
        
        # Create or get test user
        user_email = "qrcode_test@example.com"
        user, created = User.objects.get_or_create(
            email=user_email,
            defaults={
                'full_name': 'QR Code Test User',
                'is_active': True,
            }
        )
        if created:
            user.set_password('TestPass123!')
            user.save()
            self.stdout.write(self.style.SUCCESS(f'✓ Created test user: {user_email}'))
        else:
            self.stdout.write(self.style.WARNING(f'ℹ Using existing user: {user_email}'))
        
        # Create or get admin user
        admin_email = "qrcode_admin@example.com"
        admin_user, created = User.objects.get_or_create(
            email=admin_email,
            defaults={
                'full_name': 'QR Code Admin User',
                'is_active': True,
                'is_staff': True,
            }
        )
        if created:
            admin_user.set_password('AdminPass123!')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS(f'✓ Created admin user: {admin_email}'))
        else:
            self.stdout.write(self.style.WARNING(f'ℹ Using existing admin user: {admin_email}'))
        
        # Create workspace
        workspace, created = Workspace.objects.get_or_create(
            name='QR Code Test Workspace',
            defaults={
                'admin': admin_user,
                'email': 'qrcode-workspace@example.com',
                'description': 'Test workspace for QR code functionality',
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'✓ Created workspace: {workspace.name}'))
        else:
            self.stdout.write(self.style.WARNING(f'ℹ Using existing workspace: {workspace.name}'))
        
        # Add test user to workspace
        workspace_user, created = WorkspaceUser.objects.get_or_create(
            workspace=workspace,
            user=user,
            defaults={'role': 'member'}
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'✓ Added test user to workspace'))
        else:
            self.stdout.write(self.style.WARNING(f'ℹ Test user already in workspace'))
        
        # Create branch
        branch, created = Branch.objects.get_or_create(
            workspace=workspace,
            name='Main Branch',
            defaults={
                'email': 'branch@example.com',
                'address': '123 Main Street',
                'city': 'Test City',
                'country': 'Test Country',
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'✓ Created branch: {branch.name}'))
        else:
            self.stdout.write(self.style.WARNING(f'ℹ Using existing branch: {branch.name}'))
        
        # Create 5 spaces
        spaces = []
        space_types = ['meeting_room', 'office', 'coworking', 'event_space', 'desk']
        
        for i, space_type in enumerate(space_types, 1):
            space, created = Space.objects.get_or_create(
                branch=branch,
                name=f'Test Space {i}',
                defaults={
                    'space_type': space_type,
                    'capacity': 10 + i * 5,
                    'price_per_hour': Decimal('25.00'),
                    'daily_rate': Decimal('150.00'),
                    'monthly_rate': Decimal('2000.00'),
                    'description': f'Test {space_type} for QR code testing',
                }
            )
            spaces.append(space)
            if created:
                self.stdout.write(self.style.SUCCESS(f'✓ Created space: {space.name} ({space_type})'))
            else:
                self.stdout.write(self.style.WARNING(f'ℹ Using existing space: {space.name}'))
            
            # Create space calendar if it doesn't exist
            calendar, created = SpaceCalendar.objects.get_or_create(
                space=space,
                defaults={
                    'hourly_price': Decimal('25.00'),
                    'daily_price': Decimal('150.00'),
                    'monthly_price': Decimal('2000.00'),
                }
            )
            
            # Create available slots for the next 7 days
            base_date = timezone.now().date()
            for day_offset in range(7):
                slot_date = base_date + timedelta(days=day_offset)
                
                # Create 3 hourly slots per day: 9-10am, 10-11am, 2-3pm
                slot_times = [
                    (time(9, 0), time(10, 0), 'hourly'),
                    (time(10, 0), time(11, 0), 'hourly'),
                    (time(14, 0), time(15, 0), 'hourly'),
                    (time(9, 0), time(17, 0), 'daily'),  # Full day slot
                ]
                
                for start_time, end_time, booking_type in slot_times:
                    SpaceCalendarSlot.objects.get_or_create(
                        calendar=calendar,
                        date=slot_date,
                        start_time=start_time,
                        end_time=end_time,
                        booking_type=booking_type,
                        defaults={
                            'status': 'available',
                        }
                    )
        
        self.stdout.write(self.style.SUCCESS(f'\n✓ Test data populated successfully!'))
        self.stdout.write(self.style.WARNING(f'\nTest Credentials:'))
        self.stdout.write(f'  User Email: {user_email}')
        self.stdout.write(f'  User Password: TestPass123!')
        self.stdout.write(f'  Admin Email: {admin_email}')
        self.stdout.write(f'  Admin Password: AdminPass123!')
        self.stdout.write(f'  Workspace: {workspace.name}')
        self.stdout.write(f'  Spaces Created: {len(spaces)}')
        self.stdout.write(f'\n')
