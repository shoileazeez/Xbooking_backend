from django.core.management.base import BaseCommand
from workspace.models import Workspace, Branch, Space, SpaceCalendar, SpaceCalendarSlot
from booking.models import Booking
from django.utils import timezone
from django.contrib.auth import get_user_model
import random
from datetime import timedelta, time
from decimal import Decimal
import calendar

User = get_user_model()

class Command(BaseCommand):
    help = 'Populate production database with comprehensive workspace, branch, space, and calendar data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--workspaces',
            type=int,
            default=2,
            help='Number of workspaces to create (default: 2)'
        )
        parser.add_argument(
            '--branches-per-workspace',
            type=int,
            default=10,
            help='Number of branches per workspace (default: 10)'
        )
        parser.add_argument(
            '--spaces-per-branch',
            type=int,
            default=20,
            help='Number of spaces per branch (default: 20)'
        )
        parser.add_argument(
            '--days-ahead',
            type=int,
            default=90,
            help='Number of days ahead to populate calendar slots (default: 90)'
        )

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('🚀 Starting production data population...'))
        
        num_workspaces = kwargs['workspaces']
        branches_per_workspace = kwargs['branches_per_workspace']
        spaces_per_branch = kwargs['spaces_per_branch']
        days_ahead = kwargs['days_ahead']

        # Create or get test admin user
        admin_user, created = User.objects.get_or_create(
            email='admin@xbooking.com',
            defaults={
                'full_name': 'Admin User',
                'is_active': True,
                'is_staff': True,
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS('✓ Created admin user: admin@xbooking.com'))
        else:
            self.stdout.write('✓ Using existing admin user')

        # Amenities list
        amenities = [
            'WiFi', 'Projector', 'Whiteboard', 'Air Conditioning',
            'Coffee Machine', 'Water Dispenser', 'Parking', 'Printer',
            'TV Screen', 'Microphone', 'Speaker System', 'Kitchen Access',
            'Standing Desk', 'Meeting Table', 'Chairs', 'Power Outlets',
            'Natural Lighting', 'Video Conference Setup', 'Soundproofing'
        ]

        # Workspace data
        workspace_names = [
            'Tech Hub Africa', 'Creative Works', 'Business Prime',
            'Innovation Space', 'Professional Hub', 'Startup Central',
            'Enterprise Plus', 'Digital Hub', 'Collaborative Space', 'Elite Workspace'
        ]

        # Location data (various cities in Nigeria)
        locations = [
            {'city': 'Lagos', 'state': 'Lagos', 'country': 'Nigeria'},
            {'city': 'Abuja', 'state': 'FCT', 'country': 'Nigeria'},
            {'city': 'Ibadan', 'state': 'Oyo', 'country': 'Nigeria'},
            {'city': 'Port Harcourt', 'state': 'Rivers', 'country': 'Nigeria'},
            {'city': 'Kano', 'state': 'Kano', 'country': 'Nigeria'},
        ]

        # Branch names
        branch_names = [
            'Yaba', 'Victoria Island', 'Ikeja', 'Lekki', 'Ikoyi',
            'Ajah', 'Marina', 'Surulere', 'Apapa', 'Mushin',
            'Phase 1', 'Phase 2', 'Garki', 'Wuse', 'Maitama',
            'New Bussa', 'Koton Karfe', 'Minna', 'Central Business District',
            'Downtown'
        ]

        # Create workspaces
        for i in range(num_workspaces):
            workspace_name = workspace_names[i % len(workspace_names)] + f' {i+1}'
            location = locations[i % len(locations)]
            
            workspace, created = Workspace.objects.get_or_create(
                name=workspace_name,
                defaults={
                    'description': f'Premium workspace solution in {location["city"]} offering flexible office spaces',
                    'admin': admin_user,
                    'email': f'admin@{workspace_name.lower().replace(" ", "")}.com',
                    'is_active': True,
                    'address': f'{location["city"]}, {location["state"]}, {location["country"]}',
                    'city': location['city'],
                    'state': location['state'],
                    'country': location['country'],
                    'phone': f'+234{random.randint(701, 910)}{random.randint(1000000, 9999999)}',
                    'social_media_links': {
                        'twitter': f'https://twitter.com/{workspace_name.lower().replace(" ", "")}',
                        'instagram': f'https://instagram.com/{workspace_name.lower().replace(" ", "")}',
                        'linkedin': f'https://linkedin.com/company/{workspace_name.lower().replace(" ", "")}'
                    }
                }
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'✓ Created workspace: {workspace.name}'))
            else:
                self.stdout.write(f'ℹ Using existing workspace: {workspace.name}')

            # Create branches for workspace
            for branch_idx in range(branches_per_workspace):
                branch_name = branch_names[branch_idx % len(branch_names)]
                if branch_idx >= len(branch_names):
                    branch_name = f'{branch_names[branch_idx % len(branch_names)]} {branch_idx // len(branch_names)}'
                
                branch, created = Branch.objects.get_or_create(
                    workspace=workspace,
                    name=branch_name,
                    defaults={
                        'address': f'{branch_name}, {location["city"]}, {location["state"]}, {location["country"]}',
                        'city': location['city'],
                        'state': location['state'],
                        'country': location['country'],
                        'email': f'{branch_name.lower().replace(" ", "")}@{workspace_name.lower().replace(" ", "")}.com',
                        'phone': f'+234{random.randint(701, 910)}{random.randint(1000000, 9999999)}',
                        'is_active': True,
                        'operating_hours': {
                            '0': {'open': '09:00', 'close': '18:00'},  # Sunday
                            '1': {'open': '09:00', 'close': '18:00'},  # Monday
                            '2': {'open': '09:00', 'close': '18:00'},  # Tuesday
                            '3': {'open': '09:00', 'close': '18:00'},  # Wednesday
                            '4': {'open': '09:00', 'close': '18:00'},  # Thursday
                            '5': {'open': '09:00', 'close': '18:00'},  # Friday
                            '6': {'open': '10:00', 'close': '16:00'},  # Saturday
                        },
                        'images': [
                            'https://images.unsplash.com/photo-1552664730-d307ca884978?w=500&h=400',
                            'https://images.unsplash.com/photo-1552664884-8b9a6be9f4a1?w=500&h=400',
                            'https://images.unsplash.com/photo-1560264357-8d9766a55a9f?w=500&h=400',
                        ]
                    }
                )
                
                if created:
                    self.stdout.write(f'  ✓ Created branch: {branch.name}')
                
                # Create spaces for branch
                space_types = ['meeting_room', 'office', 'coworking', 'event_space', 'desk', 'lounge']
                
                for space_idx in range(spaces_per_branch):
                    space_type = space_types[space_idx % len(space_types)]
                    capacity = random.randint(2, 50)
                    hourly_price = Decimal(random.randint(5000, 50000))
                    daily_price = hourly_price * Decimal(6)  # 6x hourly rate
                    monthly_price = daily_price * Decimal(20)  # 20x daily rate
                    
                    space, created = Space.objects.get_or_create(
                        branch=branch,
                        name=f'{space_type.title().replace("_", " ")} {capacity}Cap - {space_idx + 1}',
                        defaults={
                            'description': f'Premium {space_type.lower().replace("_", " ")} accommodating {capacity} people with modern amenities',
                            'space_type': space_type,
                            'capacity': capacity,
                            'price_per_hour': hourly_price,
                            'daily_rate': daily_price,
                            'monthly_rate': monthly_price,
                            'is_available': True,
                            'rules': '''
1. No smoking inside the space
2. Keep the space clean and tidy after use
3. Respect other users and maintain professional conduct
4. Follow the booked time slots strictly
5. Report any damages or issues immediately to management
6. Do not move furniture without permission
7. Dispose of waste properly in designated bins
8. Turn off all equipment before leaving
9. Lock the space when vacating
10. No loud music or excessive noise
                            ''',
                            'cancellation_policy': '''
Free Cancellation: Up to 7 days before booking
50% Refund: 3-7 days before booking
25% Refund: 1-3 days before booking
No Refund: Same day or no-show
Special circumstances may qualify for exceptions - contact support
                            ''',
                            'image_url': f'https://images.unsplash.com/photo-1{random.randint(500000000, 600000000)}?w=500&h=400',
                            'amenities': random.sample(amenities, random.randint(5, 12))
                        }
                    )
                    
                    if created:
                        self.stdout.write(f'    ✓ Created space: {space.name}')
                        
                        # Create SpaceCalendar for the space
                        calendar_obj, _ = SpaceCalendar.objects.get_or_create(
                            space=space,
                            defaults={
                                'time_interval_minutes': 60,
                                'hourly_enabled': True,
                                'daily_enabled': True,
                                'monthly_enabled': True,
                                'hourly_price': hourly_price,
                                'daily_price': daily_price,
                                'monthly_price': monthly_price,
                                'min_advance_booking_days': 0,
                                'max_advance_booking_days': 365,
                                'operating_hours': {
                                    '0': {'start': '09:00', 'end': '18:00'},  # Sunday
                                    '1': {'start': '09:00', 'end': '18:00'},  # Monday
                                    '2': {'start': '09:00', 'end': '18:00'},  # Tuesday
                                    '3': {'start': '09:00', 'end': '18:00'},  # Wednesday
                                    '4': {'start': '09:00', 'end': '18:00'},  # Thursday
                                    '5': {'start': '09:00', 'end': '18:00'},  # Friday
                                    '6': {'start': '10:00', 'end': '16:00'},  # Saturday
                                }
                            }
                        )
                        
                        # Populate calendar slots for the next N days
                        self._populate_calendar_slots(calendar_obj, days_ahead)
                    
        self.stdout.write(self.style.SUCCESS('\n✓ Production data population completed successfully!'))
        self.stdout.write(self.style.WARNING(f'\nSummary:'))
        self.stdout.write(f'  • Workspaces: {num_workspaces}')
        self.stdout.write(f'  • Branches per workspace: {branches_per_workspace}')
        self.stdout.write(f'  • Spaces per branch: {spaces_per_branch}')
        self.stdout.write(f'  • Calendar slots populated for: {days_ahead} days ahead')
        total_spaces = num_workspaces * branches_per_workspace * spaces_per_branch
        self.stdout.write(f'  • Total spaces created: {total_spaces}')

    def _populate_calendar_slots(self, calendar_obj, days_ahead):
        """Populate calendar slots for a space for the next N days"""
        space = calendar_obj.space
        start_date = timezone.now().date()
        
        # Operating hours from calendar
        operating_hours = calendar_obj.operating_hours
        
        # Slot interval in minutes (convert to hours for slot creation)
        interval_minutes = calendar_obj.time_interval_minutes
        
        slots_created = 0
        
        for day_offset in range(days_ahead):
            current_date = start_date + timedelta(days=day_offset)
            weekday = str(current_date.weekday())  # 0=Monday, 6=Sunday
            
            # Check if space operates on this day
            if weekday not in operating_hours:
                continue
            
            day_hours = operating_hours.get(weekday)
            if not day_hours:
                continue
            
            # Get opening and closing times
            open_time = self._parse_time(day_hours.get('start', '09:00'))
            close_time = self._parse_time(day_hours.get('end', '18:00'))
            
            if not open_time or not close_time:
                continue
            
            # Create hourly slots
            current_time = open_time
            while current_time < close_time:
                # Calculate end time
                end_minutes = current_time.hour * 60 + current_time.minute + interval_minutes
                end_hour = end_minutes // 60
                end_minute = end_minutes % 60
                
                # Don't create slots that extend beyond closing time
                if end_hour > close_time.hour or (end_hour == close_time.hour and end_minute > close_time.minute):
                    break
                
                end_time = time(hour=end_hour, minute=end_minute)
                
                # Create hourly slots
                SpaceCalendarSlot.objects.get_or_create(
                    calendar=calendar_obj,
                    date=current_date,
                    start_time=current_time,
                    booking_type='hourly',
                    defaults={
                        'end_time': end_time,
                        'status': 'available',
                        'notes': 'Hourly booking slot'
                    }
                )
                slots_created += 1
                
                # Move to next slot
                current_time = end_time
            
            # Create daily slots (full day from open to close)
            SpaceCalendarSlot.objects.get_or_create(
                calendar=calendar_obj,
                date=current_date,
                start_time=open_time,
                booking_type='daily',
                defaults={
                    'end_time': close_time,
                    'status': 'available',
                    'notes': 'Daily booking slot'
                }
            )
            slots_created += 1
            
            # Create monthly slots (only once per space per month, on the 1st)
            if current_date.day == 1:
                SpaceCalendarSlot.objects.get_or_create(
                    calendar=calendar_obj,
                    date=current_date,
                    start_time=open_time,
                    booking_type='monthly',
                    defaults={
                        'end_time': close_time,
                        'status': 'available',
                        'notes': 'Monthly booking slot'
                    }
                )
                slots_created += 1
        
        self.stdout.write(f'      ✓ Created {slots_created} calendar slots for {space.name}')

    def _parse_time(self, time_string):
        """Parse time string in HH:MM format to time object"""
        try:
            if isinstance(time_string, str):
                hour, minute = map(int, time_string.split(':'))
                return time(hour=hour, minute=minute)
            return None
        except (ValueError, AttributeError):
            return None
