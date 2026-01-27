"""
Management command to populate the database with sample workspaces and related data
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from workspace.models import Workspace, Branch, Space, WorkspaceUser, SpaceCalendar, SpaceCalendarSlot
from decimal import Decimal
from datetime import date, time, timedelta
import random

User = get_user_model()


class Command(BaseCommand):
    help = 'Populate database with sample workspaces, branches, spaces, and amenities'

    def add_arguments(self, parser):
        parser.add_argument(
            '--workspaces',
            type=int,
            default=10,
            help='Number of workspaces to create (default: 10)'
        )
        parser.add_argument(
            '--admin-email',
            type=str,
            default='admin@xbooking.com',
            help='Email for the admin user (default: admin@xbooking.com)'
        )

    @transaction.atomic
    def handle(self, *args, **options):
        num_workspaces = options['workspaces']
        admin_email = options['admin_email']

        self.stdout.write(self.style.SUCCESS(f'Starting workspace population...'))

        # Create or get admin user
        admin_user, created = User.objects.get_or_create(
            email=admin_email,
            defaults={
                'full_name': 'Admin User',
                'is_staff': True,
                'is_superuser': True,
                'is_active': True,
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS(f'✓ Created admin user: {admin_email} (password: admin123)'))
        else:
            self.stdout.write(self.style.WARNING(f'✓ Admin user already exists: {admin_email}'))

        # Create regular test users
        test_users = []
        for i in range(1, 6):
            user, created = User.objects.get_or_create(
                email=f'user{i}@test.com',
                defaults={
                    'full_name': f'Test User{i}',
                    'is_active': True,
                }
            )
            if created:
                user.set_password('test123')
                user.save()
                self.stdout.write(self.style.SUCCESS(f'✓ Created test user: user{i}@test.com (password: test123)'))
            test_users.append(user)

        # Workspace data templates
        workspace_types = ['Coworking Space', 'Private Office', 'Meeting Hub', 'Creative Studio', 'Tech Hub']
        cities = ['Lagos', 'Abuja', 'Port Harcourt', 'Ibadan', 'Kano', 'Enugu', 'Kaduna', 'Jos', 'Benin', 'Calabar']
        
        workspace_names = [
            'Innovation Hub', 'Creative Space', 'Tech Valley', 'Business Center',
            'Work Station', 'Flex Space', 'Smart Office', 'Productive Hub',
            'Collaborative Space', 'Enterprise Center'
        ]

        space_types = ['meeting_room', 'office', 'coworking', 'event_space', 'desk', 'lounge']
        
        amenities_list = ['WiFi', 'Coffee', 'Printer', 'Parking', 'Air Conditioning', 
                         'Kitchen', 'Lounge', 'Whiteboard', 'Projector', 'Security']

        # Create workspaces
        self.stdout.write(self.style.SUCCESS(f'\nCreating {num_workspaces} workspaces...'))
        
        for i in range(1, num_workspaces + 1):
            workspace_name = f"{workspace_names[i % len(workspace_names)]} {cities[i % len(cities)]}"
            
            # Create individual admin for this workspace
            workspace_admin_email = f'admin.{workspace_name.lower().replace(" ", "")}@xbooking.com'
            workspace_admin, ws_admin_created = User.objects.get_or_create(
                email=workspace_admin_email,
                defaults={
                    'full_name': f'{workspace_name} Admin',
                    'is_staff': True,
                    'is_active': True,
                }
            )
            if ws_admin_created:
                workspace_admin.set_password('admin123')
                workspace_admin.save()
                self.stdout.write(self.style.SUCCESS(f'✓ Created workspace admin: {workspace_admin_email} (password: admin123)'))
            
            workspace, created = Workspace.objects.get_or_create(
                name=workspace_name,
                defaults={
                    'description': f'A modern {workspace_types[i % len(workspace_types)].lower()} located in {cities[i % len(cities)]}, offering premium facilities and flexible booking options.',
                    'address': f'{random.randint(1, 100)} {random.choice(["Main", "Victoria", "Allen", "Admiralty", "Ikoyi", "Lekki"])} Street, {cities[i % len(cities)]}, Nigeria',
                    'city': cities[i % len(cities)],
                    'state': random.choice(['Lagos', 'FCT', 'Rivers', 'Oyo', 'Kano', 'Enugu']),
                    'country': 'Nigeria',
                    'phone': f'+234{random.randint(7000000000, 9099999999)}',
                    'email': f'{workspace_name.lower().replace(" ", "")}@xbooking.com',
                    'website': f'https://{workspace_name.lower().replace(" ", "")}.com',
                    'is_active': True,
                    'admin': workspace_admin,
                    'logo_url': f'https://picsum.photos/seed/{workspace_name.replace(" ", "")}logo/200/200',
                }
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'\n{i}. Created workspace: {workspace_name}'))
                
                # Add workspace admin
                WorkspaceUser.objects.get_or_create(
                    workspace=workspace,
                    user=workspace_admin,
                    defaults={'role': 'admin'}
                )
                # Also add super admin for testing
                WorkspaceUser.objects.get_or_create(
                    workspace=workspace,
                    user=admin_user,
                    defaults={'role': 'admin'}
                )
                
                # Create 2-3 branches
                num_branches = random.randint(2, 3)
                for b in range(1, num_branches + 1):
                    branch_name = f'{workspace_name} - Branch {b}'
                    branch_city = cities[(i + b) % len(cities)]
                    
                    branch_seed = f'{workspace_name}{b}{branch_city}'.replace(" ", "")
                    branch = Branch.objects.create(
                        workspace=workspace,
                        name=branch_name,
                        address=f'{random.randint(1, 200)} {random.choice(["Commercial", "Business", "Corporate"])} Avenue, {branch_city}, Nigeria',
                        city=branch_city,
                        state=random.choice(['Lagos', 'FCT', 'Rivers', 'Oyo']),
                        country='Nigeria',
                        phone=f'+234{random.randint(7000000000, 9099999999)}',
                        email=f'{branch_name.lower().replace(" ", "").replace("-", "")}@xbooking.com',
                        is_active=True,
                        images=f'https://picsum.photos/seed/{branch_seed}/800/600',
                    )
                    self.stdout.write(f'   ✓ Created branch: {branch_name}')
                    
                    # Create 5-8 spaces per branch
                    num_spaces = random.randint(5, 8)
                    for s in range(1, num_spaces + 1):
                        space_type = space_types[s % len(space_types)]
                        
                        # Define pricing based on space type
                        if space_type == 'office':
                            hourly_rate = Decimal(random.randint(2000, 5000))
                            daily_rate = Decimal(random.randint(15000, 35000))
                            monthly_rate = Decimal(random.randint(200000, 500000))
                            capacity = random.randint(2, 8)
                        elif space_type == 'desk':
                            hourly_rate = Decimal(random.randint(500, 1500))
                            daily_rate = Decimal(random.randint(3000, 8000))
                            monthly_rate = Decimal(random.randint(50000, 120000))
                            capacity = random.randint(1, 3)
                        elif space_type == 'meeting_room':
                            hourly_rate = Decimal(random.randint(3000, 8000))
                            daily_rate = Decimal(random.randint(25000, 60000))
                            monthly_rate = Decimal(random.randint(300000, 600000))
                            capacity = random.randint(6, 15)
                        elif space_type == 'event_space':
                            hourly_rate = Decimal(random.randint(10000, 25000))
                            daily_rate = Decimal(random.randint(80000, 200000))
                            monthly_rate = Decimal(random.randint(1000000, 2000000))
                            capacity = random.randint(50, 200)
                        elif space_type == 'coworking':
                            hourly_rate = Decimal(random.randint(1000, 3000))
                            daily_rate = Decimal(random.randint(8000, 15000))
                            monthly_rate = Decimal(random.randint(100000, 250000))
                            capacity = random.randint(10, 50)
                        else:  # lounge
                            hourly_rate = Decimal(random.randint(1500, 4000))
                            daily_rate = Decimal(random.randint(10000, 30000))
                            monthly_rate = Decimal(random.randint(150000, 400000))
                            capacity = random.randint(5, 20)
                        
                        space_seed = f'{workspace_name}{b}{s}{space_type}'.replace(" ", "")
                        space_image_width = random.choice([800, 900, 1000])
                        space_image_height = random.choice([600, 700, 800])
                        space = Space.objects.create(
                            branch=branch,
                            name=f'{space_type.replace("_", " ").title()} {s}',
                            description=f'Well-equipped {space_type.replace("_", " ")} with modern amenities',
                            space_type=space_type,
                            capacity=capacity,
                            price_per_hour=hourly_rate,
                            daily_rate=daily_rate,
                            monthly_rate=monthly_rate,
                            amenities=random.sample(amenities_list, k=random.randint(3, 7)),
                            is_available=True,
                            image_url=f'https://picsum.photos/seed/{space_seed}/{space_image_width}/{space_image_height}',
                        )
                        
                        # Create calendar for the space
                        operating_hours = {
                            str(day): {"start": "09:00", "end": "18:00"}
                            for day in range(7)  # 0=Sunday to 6=Saturday
                        }
                        
                        calendar = SpaceCalendar.objects.create(
                            space=space,
                            time_interval_minutes=60,
                            operating_hours=operating_hours,
                            hourly_enabled=True,
                            daily_enabled=True,
                            monthly_enabled=True,
                            hourly_price=hourly_rate,
                            daily_price=daily_rate,
                            monthly_price=monthly_rate,
                            min_advance_booking_days=0,
                            max_advance_booking_days=90
                        )
                        
                        # Create slots for next 30 days
                        today = date.today()
                        for day_offset in range(30):
                            slot_date = today + timedelta(days=day_offset)
                            
                            # Create hourly slots (9 AM to 6 PM)
                            for hour in range(9, 18):
                                SpaceCalendarSlot.objects.create(
                                    calendar=calendar,
                                    date=slot_date,
                                    start_time=time(hour, 0),
                                    end_time=time(hour + 1, 0),
                                    booking_type='hourly',
                                    status='available'
                                )
                            
                            # Create daily slot
                            SpaceCalendarSlot.objects.create(
                                calendar=calendar,
                                date=slot_date,
                                start_time=time(9, 0),
                                end_time=time(18, 0),
                                booking_type='daily',
                                status='available'
                            )
                        
                        # Create monthly slots (first day of each month for next 3 months)
                        for month_offset in range(3):
                            first_day = (today.replace(day=1) + timedelta(days=32 * month_offset)).replace(day=1)
                            last_day_of_month = (first_day.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
                            
                            SpaceCalendarSlot.objects.create(
                                calendar=calendar,
                                date=first_day,
                                start_time=time(0, 0),
                                end_time=time(23, 59),
                                booking_type='monthly',
                                status='available'
                            )
                    
                    self.stdout.write(f'     ✓ Created {num_spaces} spaces with calendars and slots in {branch_name}')
            else:
                self.stdout.write(self.style.WARNING(f'{i}. Workspace already exists: {workspace_name}'))

        # Summary
        total_workspaces = Workspace.objects.count()
        total_branches = Branch.objects.count()
        total_spaces = Space.objects.count()
        total_calendars = SpaceCalendar.objects.count()
        total_slots = SpaceCalendarSlot.objects.count()

        self.stdout.write(self.style.SUCCESS(f'\n{"="*60}'))
        self.stdout.write(self.style.SUCCESS('DATABASE POPULATION COMPLETE!'))
        self.stdout.write(self.style.SUCCESS(f'{"="*60}'))
        self.stdout.write(self.style.SUCCESS(f'Total Workspaces: {total_workspaces}'))
        self.stdout.write(self.style.SUCCESS(f'Total Branches: {total_branches}'))
        self.stdout.write(self.style.SUCCESS(f'Total Spaces: {total_spaces}'))
        self.stdout.write(self.style.SUCCESS(f'Total Calendars: {total_calendars}'))
        self.stdout.write(self.style.SUCCESS(f'Total Calendar Slots: {total_slots}'))
        self.stdout.write(self.style.SUCCESS(f'{"="*60}'))
        self.stdout.write(self.style.SUCCESS('\nTEST CREDENTIALS:'))
        self.stdout.write(self.style.SUCCESS(f'Admin: {admin_email} / admin123'))
        self.stdout.write(self.style.SUCCESS('Users: user1@test.com through user5@test.com / test123'))
        self.stdout.write(self.style.SUCCESS(f'{"="*60}\n'))
