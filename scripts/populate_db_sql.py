import os
import sys
import random
from pathlib import Path
from datetime import timedelta, time
from decimal import Decimal

DATABASE_URL = os.environ.get('DATABASE_URL', '')
if DATABASE_URL:
    os.environ['DATABASE_URL'] = DATABASE_URL

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Xbooking.Xbooking.settings')

import django
django.setup()

from django.utils import timezone
from django.contrib.auth import get_user_model
from workspace.models import Workspace, Branch, Space, SpaceCalendar, SpaceCalendarSlot


def parse_time(s):
    try:
        h, m = map(int, s.split(':'))
        return time(hour=h, minute=m)
    except Exception:
        return None


def populate_calendar_slots(calendar_obj, days_ahead):
    start_date = timezone.now().date()
    operating_hours = calendar_obj.operating_hours
    interval_minutes = calendar_obj.time_interval_minutes
    slots_created = 0
    for day_offset in range(days_ahead):
        current_date = start_date + timedelta(days=day_offset)
        weekday = str(current_date.weekday())
        if weekday not in operating_hours:
            continue
        day_hours = operating_hours.get(weekday)
        if not day_hours:
            continue
        open_time = parse_time(day_hours.get('start', '09:00'))
        close_time = parse_time(day_hours.get('end', '18:00'))
        if not open_time or not close_time:
            continue
        current_time = open_time
        while current_time < close_time:
            end_minutes = current_time.hour * 60 + current_time.minute + interval_minutes
            end_hour = end_minutes // 60
            end_minute = end_minutes % 60
            if end_hour > close_time.hour or (end_hour == close_time.hour and end_minute > close_time.minute):
                break
            end_time = time(hour=end_hour, minute=end_minute)
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
            current_time = end_time
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
    print(f'      Created {slots_created} calendar slots for {calendar_obj.space.name}')


def pricing_for_type(space_type):
    if space_type == 'meeting_room':
        hourly = Decimal(random.randint(5000, 15000))
    elif space_type == 'office':
        hourly = Decimal(random.randint(10000, 30000))
    elif space_type == 'coworking':
        hourly = Decimal(random.randint(3000, 8000))
    elif space_type == 'event_space':
        hourly = Decimal(random.randint(20000, 80000))
    elif space_type == 'desk':
        hourly = Decimal(random.randint(2000, 5000))
    else:
        hourly = Decimal(random.randint(3000, 7000))
    daily = (hourly * Decimal(8)).quantize(Decimal('1'))
    monthly = (daily * Decimal(22)).quantize(Decimal('1'))
    return hourly, daily, monthly


def main(workspaces=5, branches_per_workspace=15, spaces_per_branch=10, days_ahead=90):
    print('Starting standalone production data population...')
    User = get_user_model()
    admin_user, created = User.objects.get_or_create(
        email='admin@xbooking.com',
        defaults={'full_name': 'Admin User', 'is_active': True, 'is_staff': True}
    )
    if created:
        admin_user.set_password('admin123')
        admin_user.save()
        print('Created admin user: admin@xbooking.com')
    else:
        print('Using existing admin user')

    amenities = [
        'WiFi', 'Projector', 'Whiteboard', 'Air Conditioning',
        'Coffee Machine', 'Water Dispenser', 'Parking', 'Printer',
        'TV Screen', 'Microphone', 'Speaker System', 'Kitchen Access',
        'Standing Desk', 'Meeting Table', 'Chairs', 'Power Outlets',
        'Natural Lighting', 'Video Conference Setup', 'Soundproofing'
    ]

    workspace_names = [
        'Tech Hub Africa', 'Creative Works', 'Business Prime',
        'Innovation Space', 'Professional Hub', 'Startup Central',
        'Enterprise Plus', 'Digital Hub', 'Collaborative Space', 'Elite Workspace'
    ]

    locations = [
        {'city': 'Lagos', 'state': 'Lagos', 'country': 'Nigeria'},
        {'city': 'Abuja', 'state': 'FCT', 'country': 'Nigeria'},
        {'city': 'Ibadan', 'state': 'Oyo', 'country': 'Nigeria'},
        {'city': 'Port Harcourt', 'state': 'Rivers', 'country': 'Nigeria'},
        {'city': 'Kano', 'state': 'Kano', 'country': 'Nigeria'},
    ]

    branch_names = [
        'Yaba', 'Victoria Island', 'Ikeja', 'Lekki', 'Ikoyi',
        'Ajah', 'Marina', 'Surulere', 'Apapa', 'Mushin',
        'Phase 1', 'Phase 2', 'Garki', 'Wuse', 'Maitama',
        'New Bussa', 'Koton Karfe', 'Minna', 'Central Business District',
        'Downtown'
    ]

    for i in range(workspaces):
        workspace_name = workspace_names[i % len(workspace_names)] + f' {i+1}'
        location = locations[i % len(locations)]
        workspace, w_created = Workspace.objects.get_or_create(
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
        print(('Created' if w_created else 'Using existing') + f' workspace: {workspace.name}')

        for branch_idx in range(branches_per_workspace):
            branch_name = branch_names[branch_idx % len(branch_names)]
            if branch_idx >= len(branch_names):
                branch_name = f'{branch_names[branch_idx % len(branch_names)]} {branch_idx // len(branch_names)}'
            branch, b_created = Branch.objects.get_or_create(
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
                        '0': {'open': '09:00', 'close': '18:00'},
                        '1': {'open': '09:00', 'close': '18:00'},
                        '2': {'open': '09:00', 'close': '18:00'},
                        '3': {'open': '09:00', 'close': '18:00'},
                        '4': {'open': '09:00', 'close': '18:00'},
                        '5': {'open': '09:00', 'close': '18:00'},
                        '6': {'open': '10:00', 'close': '16:00'},
                    },
                    'images': [
                        'https://images.unsplash.com/photo-1552664730-d307ca884978?w=500&h=400',
                        'https://images.unsplash.com/photo-1552664884-8b9a6be9f4a1?w=500&h=400',
                        'https://images.unsplash.com/photo-1560264357-8d9766a55a9f?w=500&h=400',
                    ]
                }
            )
            if b_created:
                print(f'  Created branch: {branch.name}')

            space_types = ['meeting_room', 'office', 'coworking', 'event_space', 'desk', 'lounge']
            for space_idx in range(spaces_per_branch):
                space_type = space_types[space_idx % len(space_types)]
                capacity = random.randint(2, 50)
                hourly_price, daily_price, monthly_price = pricing_for_type(space_type)
                image_url = f'https://picsum.photos/seed/{workspace_name.lower().replace(" ", "-")}-{branch_name.lower().replace(" ", "-")}-{space_idx}/800/600'
                space, s_created = Space.objects.get_or_create(
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
                        'rules': 'House rules apply',
                        'cancellation_policy': 'Standard cancellation policy',
                        'image_url': image_url,
                        'amenities': random.sample(amenities, random.randint(5, 12))
                    }
                )
                if s_created:
                    print(f'    Created space: {space.name}')
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
                                '0': {'start': '09:00', 'end': '18:00'},
                                '1': {'start': '09:00', 'end': '18:00'},
                                '2': {'start': '09:00', 'end': '18:00'},
                                '3': {'start': '09:00', 'end': '18:00'},
                                '4': {'start': '09:00', 'end': '18:00'},
                                '5': {'start': '09:00', 'end': '18:00'},
                                '6': {'start': '10:00', 'end': '16:00'},
                            }
                        }
                    )
                    populate_calendar_slots(calendar_obj, days_ahead)

    total_spaces = workspaces * branches_per_workspace * spaces_per_branch
    print('Completed population')
    print(f'Workspaces: {workspaces}')
    print(f'Branches per workspace: {branches_per_workspace}')
    print(f'Spaces per branch: {spaces_per_branch}')
    print(f'Days ahead: {days_ahead}')
    print(f'Total spaces intended: {total_spaces}')


if __name__ == '__main__':
    main()

