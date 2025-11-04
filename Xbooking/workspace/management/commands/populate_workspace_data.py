from django.core.management.base import BaseCommand
from workspace.models import Workspace, Branch, Space
from django.contrib.auth import get_user_model
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Populate database with mock workspace data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Starting to populate database...')
        
        # Create test admin user if not exists
        admin_user, created = User.objects.get_or_create(
            email='admin@example.com',
            defaults={
                'full_name': 'Admin User',
                'is_active': True
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS('Created admin user'))

        # List of available amenities
        amenities = [
            'WiFi', 'Projector', 'Whiteboard', 'Air Conditioning',
            'Coffee Machine', 'Water Dispenser', 'Parking', 'Printer',
            'TV Screen', 'Microphone', 'Speaker System', 'Kitchen Access'
        ]

        # Create workspaces
        workspace_data = [
            {
                'name': 'Tech Hub Lagos',
                'description': 'Premier tech workspace in Lagos',
                'branches': ['Yaba', 'Victoria Island', 'Ikeja']
            },
            {
                'name': 'Creative Space',
                'description': 'Workspace for creative professionals',
                'branches': ['Lekki Phase 1', 'Ikoyi']
            },
            {
                'name': 'Business Center',
                'description': 'Professional business environment',
                'branches': ['Marina', 'Ajah', 'Surulere']
            }
        ]

        space_types = ['meeting_room', 'office', 'coworking', 'event_space', 'desk', 'lounge']
        
        for workspace_info in workspace_data:
            workspace, created = Workspace.objects.get_or_create(
                name=workspace_info['name'],
                defaults={
                    'description': workspace_info['description'],
                    'admin': admin_user,
                    'email': f'info@{workspace_info["name"].lower().replace(" ", "")}.com',
                    'is_active': True,
                    'social_media_links': {
                        'twitter': f'https://twitter.com/{workspace_info["name"].lower().replace(" ", "")}',
                        'instagram': f'https://instagram.com/{workspace_info["name"].lower().replace(" ", "")}',
                        'linkedin': f'https://linkedin.com/company/{workspace_info["name"].lower().replace(" ", "")}'
                    }
                }
            )
            if created:
                self.stdout.write(f'Created workspace: {workspace.name}')
            else:
                self.stdout.write(f'Using existing workspace: {workspace.name}')

            # Create branches for each workspace
            for branch_name in workspace_info['branches']:
                branch, created = Branch.objects.get_or_create(
                    workspace=workspace,
                    name=branch_name,
                    defaults={
                        'address': f'{branch_name}, Lagos, Nigeria',
                        'email': f'{branch_name.lower().replace(" ", "")}@{workspace_info["name"].lower().replace(" ", "")}.com',
                        'phone': f'+234{random.randint(7000000000, 9999999999)}',
                        'is_active': True,
                        'operating_hours': {
                            'monday': {'open': '09:00', 'close': '18:00'},
                            'tuesday': {'open': '09:00', 'close': '18:00'},
                            'wednesday': {'open': '09:00', 'close': '18:00'},
                            'thursday': {'open': '09:00', 'close': '18:00'},
                            'friday': {'open': '09:00', 'close': '18:00'},
                            'saturday': {'open': '10:00', 'close': '16:00'},
                            'sunday': None
                        },
                        'images': [
                            f'https://example.com/branches/{workspace_info["name"].lower().replace(" ", "")}/{branch_name.lower().replace(" ", "")}/1.jpg',
                            f'https://example.com/branches/{workspace_info["name"].lower().replace(" ", "")}/{branch_name.lower().replace(" ", "")}/2.jpg'
                        ]
                    }
                )
                if created:
                    self.stdout.write(f'Created branch: {branch.name}')
                else:
                    self.stdout.write(f'Using existing branch: {branch.name}')

                # Create 3-5 spaces for each branch
                for _ in range(random.randint(3, 5)):
                    space_type = random.choice(space_types)
                    capacity = random.randint(4, 50)
                    price = random.randint(5000, 50000)
                    
                    space = Space.objects.create(
                        branch=branch,
                        name=f'{space_type.title().replace("_", " ")} {capacity}',
                        description=f'A {space_type.lower().replace("_", " ")} that can accommodate {capacity} people',
                        space_type=space_type,
                        capacity=capacity,
                        price_per_hour=price,
                        is_available=True,
                        rules='''
                        1. No smoking
                        2. Keep the space clean and tidy
                        3. Respect other users
                        4. Follow booking hours strictly
                        5. Report any issues immediately
                        ''',
                        cancellation_policy='''
                        - Free cancellation up to 24 hours before booking
                        - 50% refund for cancellations within 24 hours
                        - No refund for no-shows or same-day cancellations
                        - Contact support for special circumstances
                        ''',
                        operational_hours={
                            'monday': {'open': '09:00', 'close': '18:00'},
                            'tuesday': {'open': '09:00', 'close': '18:00'},
                            'wednesday': {'open': '09:00', 'close': '18:00'},
                            'thursday': {'open': '09:00', 'close': '18:00'},
                            'friday': {'open': '09:00', 'close': '18:00'},
                            'saturday': {'open': '10:00', 'close': '16:00'},
                            'sunday': None
                        },
                        availability_schedule={
                            'exceptions': [],
                            'recurring_blocks': [
                                {
                                    'day': 'monday',
                                    'blocked_periods': []
                                }
                            ]
                        }
                    )
                    
                    # Add random amenities to space
                    space.amenities = random.sample(amenities, random.randint(3, len(amenities)))
                    space.image_url = f'https://example.com/spaces/{space.id}.jpg'
                    space.save()
                    
                    self.stdout.write(f'Created space: {space.name} in {branch.name}')

        self.stdout.write(self.style.SUCCESS('Successfully populated database'))