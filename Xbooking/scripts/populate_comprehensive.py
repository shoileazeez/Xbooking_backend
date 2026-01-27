#!/usr/bin/env python
"""
Comprehensive Database Population Script
Creates 100 workspaces, 100 users, and up to 10,000 bookings for recommendation model
"""
import os
import sys
import django
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).resolve().parent.parent  # Go up to Xbooking directory (where manage.py is)
sys.path.insert(0, str(BASE_DIR))  # Add Xbooking directory to path
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Xbooking.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from workspace.models import Workspace, Branch, Space, SpaceCalendar, SpaceCalendarSlot
from booking.models import Cart, CartItem, Booking, Guest
from payment.models import Order, Payment
from bank.models import Wallet, Transaction
from user.models import UserPreference
from qr_code.models import OrderQRCode, BookingQRCode
from decimal import Decimal
from datetime import datetime, date, time, timedelta
import random
import string
 
User = get_user_model()

class ComprehensivePopulator:
    """Populate database with comprehensive test data"""
    
    def __init__(self):
        self.users = []
        self.workspaces = []
        self.branches = []
        self.spaces = []
        self.bookings = []
        
        # Configuration
        self.NUM_WORKSPACES = 100
        self.NUM_USERS = 100
        self.NUM_BOOKINGS = 10000
        self.BRANCHES_PER_WORKSPACE = 5
        self.SPACES_PER_BRANCH = 20
        
        # Data templates
        self.cities = ['Lagos', 'Abuja', 'Port Harcourt', 'Ibadan', 'Kano', 'Enugu', 'Kaduna', 'Jos', 'Benin', 'Calabar', 'Owerri', 'Abeokuta', 'Uyo', 'Warri', 'Onitsha']
        self.states = ['Lagos', 'FCT', 'Rivers', 'Oyo', 'Kano', 'Enugu', 'Kaduna', 'Plateau', 'Edo', 'Cross River', 'Imo', 'Ogun', 'Akwa Ibom', 'Delta', 'Anambra']
        self.space_types = ['meeting_room', 'office', 'coworking', 'event_space', 'desk', 'lounge']
        self.booking_types = ['hourly', 'daily', 'monthly']
        
        self.first_names = ['Chinedu', 'Aisha', 'Oluwaseun', 'Fatima', 'Emeka', 'Zainab', 'Tunde', 'Hauwa', 'Chioma', 'Yusuf', 'Ngozi', 'Ibrahim', 'Amina', 'Babatunde', 'Kemi', 'Musa', 'Blessing', 'Ahmed', 'Grace', 'Aliyu']
        self.last_names = ['Okafor', 'Bello', 'Adeyemi', 'Mohammed', 'Okonkwo', 'Ibrahim', 'Williams', 'Abubakar', 'Okoro', 'Hassan', 'Eze', 'Suleiman', 'Nwankwo', 'Usman', 'Obiora', 'Kabir', 'Adekunle', 'Salisu', 'Chukwu', 'Garba']
    
    def log(self, message, level='INFO'):
        """Print formatted log message"""
        print(f"[{level}] {message}")
    
    # Amenity data as lists (stored as JSON in Space model)
    AMENITIES_LIST = [
        'WiFi', 'Coffee', 'Printer', 'Parking', 'Air Conditioning',
        'Kitchen', 'Lounge', 'Whiteboard', 'Projector', 'Security',
        'Conference Phone', 'Video Conferencing', 'Standing Desk',
        'Lockers', 'Mail Service'
    ]
    
    @transaction.atomic
    def create_users(self):
        """Create test users with preferences"""
        self.log(f"Creating {self.NUM_USERS} users...")
        
        for i in range(self.NUM_USERS):
            first_name = random.choice(self.first_names)
            last_name = random.choice(self.last_names)
            email = f"{first_name.lower()}.{last_name.lower()}{i}@test.com"
            
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'full_name': f"{first_name} {last_name}",
                    'phone': f"+234{random.randint(7000000000, 9099999999)}",
                    'is_active': True,
                }
            )
            
            if created:
                user.set_password('test123')
                user.save()
                
                # Create wallet
                Wallet.objects.get_or_create(
                    user=user,
                    defaults={'balance': Decimal(random.randint(10000, 500000))}
                )
                
                # Create preferences
                UserPreference.objects.get_or_create(
                    user=user,
                    defaults={
                        'preferred_booking_type': random.choice(['hourly', 'daily', 'monthly']),
                        'preferred_space_types': random.sample(self.space_types, k=random.randint(1, 3)),
                        'preferred_capacity_min': random.randint(1, 5),
                        'preferred_capacity_max': random.randint(6, 20),
                        'preferred_cities': random.sample(self.cities, k=random.randint(1, 3)),
                        'budget_min': Decimal(random.randint(1000, 5000)),
                        'budget_max': Decimal(random.randint(10000, 100000)),
                    }
                )
            
            self.users.append(user)
            
            if (i + 1) % 10 == 0:
                self.log(f"  Created {i + 1}/{self.NUM_USERS} users")
        
        self.log(f"✓ Created {len(self.users)} users with wallets and preferences")
    
    @transaction.atomic
    def create_workspaces(self):
        """Create workspaces with branches, spaces, calendars, and slots"""
        self.log(f"Creating {self.NUM_WORKSPACES} workspaces...")
        
        admin_user = self.users[0]  # First user is admin
        
        for i in range(self.NUM_WORKSPACES):
            workspace_name = f"Hub{i+1} {random.choice(self.cities)}"
            
            workspace, created = Workspace.objects.get_or_create(
                name=workspace_name,
                defaults={
                    'description': f'Modern workspace in {random.choice(self.cities)}',
                    'admin': admin_user,
                    'email': f"hub{i+1}@xbooking.com",
                    'phone': f"+234{random.randint(7000000000, 9099999999)}",
                    'address': f"{random.randint(1, 200)} Main St, {random.choice(self.cities)}",
                    'city': random.choice(self.cities),
                    'state': random.choice(self.states),
                    'country': 'Nigeria',
                    'is_active': True,
                }
            )
            
            if created:
                self.workspaces.append(workspace)
                
                # Create branches
                for b in range(self.BRANCHES_PER_WORKSPACE):
                    branch = Branch.objects.create(
                        workspace=workspace,
                        name=f"{workspace_name} Branch {b+1}",
                        address=f"{random.randint(1, 100)} Ave, {random.choice(self.cities)}",
                        city=random.choice(self.cities),
                        state=random.choice(self.states),
                        country='Nigeria',
                        email=f"branch{b+1}@hub{i+1}.com",
                        phone=f"+234{random.randint(7000000000, 9099999999)}",
                        is_active=True,
                    )
                    self.branches.append(branch)
                    
                    # Create spaces
                    for s in range(self.SPACES_PER_BRANCH):
                        space_type = random.choice(self.space_types)
                        capacity = random.randint(1, 50)
                        hourly_rate = Decimal(random.randint(500, 10000))
                        daily_rate = Decimal(random.randint(5000, 80000))
                        monthly_rate = Decimal(random.randint(50000, 500000)) if space_type in ['office', 'desk'] else None
                        
                        space = Space.objects.create(
                            branch=branch,
                            name=f"{space_type.replace('_', ' ').title()} {s+1}",
                            description=f"Well-equipped {space_type}",
                            space_type=space_type,
                            capacity=capacity,
                            price_per_hour=hourly_rate,
                            daily_rate=daily_rate,
                            monthly_rate=monthly_rate,
                            amenities=random.sample(self.AMENITIES_LIST, k=random.randint(3, 8)),
                            is_available=True,
                        )
                        self.spaces.append(space)
                        
                        # Create calendar
                        calendar = SpaceCalendar.objects.create(
                            space=space,
                            time_interval_minutes=60,
                            operating_hours={str(d): {"start": "08:00", "end": "20:00"} for d in range(7)},
                            hourly_enabled=True,
                            daily_enabled=True,
                            monthly_enabled=(monthly_rate is not None),
                            hourly_price=hourly_rate,
                            daily_price=daily_rate,
                            monthly_price=monthly_rate or Decimal('0'),
                            min_advance_booking_days=0,
                            max_advance_booking_days=180,
                        )
                        
                        # Create slots for next 60 days
                        today = date.today()
                        for day_offset in range(60):
                            slot_date = today + timedelta(days=day_offset)
                            
                            # Hourly slots
                            for hour in range(8, 20):
                                SpaceCalendarSlot.objects.create(
                                    calendar=calendar,
                                    date=slot_date,
                                    start_time=time(hour, 0),
                                    end_time=time(hour + 1, 0),
                                    booking_type='hourly',
                                    status='available'
                                )
                            
                            # Daily slot
                            SpaceCalendarSlot.objects.create(
                                calendar=calendar,
                                date=slot_date,
                                start_time=time(8, 0),
                                end_time=time(20, 0),
                                booking_type='daily',
                                status='available'
                            )
                        
                        # Monthly slots (next 6 months)
                        if monthly_rate:
                            for month_offset in range(6):
                                # First day of each month
                                month_date = (today.replace(day=1) + timedelta(days=32 * month_offset)).replace(day=1)
                                SpaceCalendarSlot.objects.create(
                                    calendar=calendar,
                                    date=month_date,
                                    start_time=time(0, 0),
                                    end_time=time(23, 59),
                                    booking_type='monthly',
                                    status='available'
                                )
            
            if (i + 1) % 10 == 0:
                self.log(f"  Created {i + 1}/{self.NUM_WORKSPACES} workspaces")
        
        self.log(f"✓ Created {len(self.workspaces)} workspaces")
        self.log(f"✓ Created {len(self.branches)} branches")
        self.log(f"✓ Created {len(self.spaces)} spaces with calendars and slots")
    
    @transaction.atomic
    def create_bookings(self):
        """Create bookings with full flow: cart -> order -> payment -> booking -> QR codes"""
        self.log(f"Creating {self.NUM_BOOKINGS} bookings...")
        
        today = date.today()
        
        for i in range(self.NUM_BOOKINGS):
            user = random.choice(self.users)
            space = random.choice(self.spaces)
            
            # Get user preference to influence booking type
            try:
                user_pref = UserPreference.objects.get(user=user)
                # 70% chance to use preferred booking type
                if random.random() < 0.7 and user_pref.preferred_booking_type:
                    booking_type = user_pref.preferred_booking_type
                else:
                    booking_type = random.choice(['hourly', 'daily', 'monthly'])
            except UserPreference.DoesNotExist:
                booking_type = random.choice(['hourly', 'daily', 'monthly'])
            
            # Random booking date within next 45 days (or first of month for monthly)
            if booking_type == 'monthly':
                # Book first day of a month within next 6 months
                month_offset = random.randint(0, 5)
                booking_date = (today.replace(day=1) + timedelta(days=32 * month_offset)).replace(day=1)
            else:
                days_ahead = random.randint(0, 45)
                booking_date = today + timedelta(days=days_ahead)
            
            # Set times based on booking type
            if booking_type == 'hourly':
                start_hour = random.randint(8, 18)
                duration_hours = random.randint(1, 4)
                check_in_time = time(start_hour, 0)
                check_out_time = time(min(start_hour + duration_hours, 20), 0)
                price = space.price_per_hour * duration_hours
            elif booking_type == 'daily':
                check_in_time = time(8, 0)
                check_out_time = time(20, 0)
                price = space.daily_rate
            else:  # monthly
                check_in_time = time(0, 0)
                check_out_time = time(23, 59)
                # Monthly booking spans the whole month
                if booking_date.month == 12:
                    check_out_date = booking_date.replace(year=booking_date.year + 1, month=1, day=1) - timedelta(days=1)
                else:
                    check_out_date = booking_date.replace(month=booking_date.month + 1, day=1) - timedelta(days=1)
                price = space.monthly_rate if space.monthly_rate else space.daily_rate * 30
            
            # Create order
            order = Order.objects.create(
                user=user,
                total_amount=price,
                currency='NGN',
                status='pending'
            )
            
            # Create booking
            num_guests = random.randint(1, min(space.capacity, 10))
            booking = Booking.objects.create(
                user=user,
                workspace=space.workspace,
                space=space,
                order=order,
                check_in_date=booking_date,
                check_out_date=check_out_date if booking_type == 'monthly' else booking_date,
                check_in_time=check_in_time,
                check_out_time=check_out_time,
                booking_type=booking_type,
                number_of_guests=num_guests,
                total_price=price,
                status='confirmed',
                payment_status='completed'
            )
            
            # Create payment
            payment_method = random.choice(['paystack', 'flutterwave', 'wallet'])
            Payment.objects.create(
                user=user,
                order=order,
                amount=price,
                currency='NGN',
                payment_method=payment_method,
                status='completed',
                gateway_reference=f"REF_{random.randint(10000000, 99999999)}"
            )
            
            # Update order
            order.status = 'completed'
            order.save()
            
            # Generate QR codes (just create records, no image generation)
            try:
                # Order QR Code
                import secrets
                OrderQRCode.objects.create(
                    order=order,
                    qr_code_data=f"ORDER-{order.id}",
                    verification_code=secrets.token_urlsafe(16),
                    status='generated'
                )
                
                # Booking QR Code
                BookingQRCode.objects.create(
                    booking=booking,
                    order=order,
                    qr_code_data=f"BOOKING-{booking.id}",
                    verification_code=secrets.token_urlsafe(16),
                    status='generated',
                    expires_at=timezone.make_aware(
                        datetime.combine(booking.check_out_date, booking.check_out_time)
                    ) if booking.check_out_date and booking.check_out_time else None
                )
                
            except Exception as e:
                self.log(f"  Warning: QR code creation failed for booking {booking.id}: {str(e)}", level='WARNING')
            
            # Add guests (30% of bookings)
            if random.random() < 0.3:
                guest_count = random.randint(1, min(num_guests, 5))
                for g in range(guest_count):
                    Guest.objects.create(
                        booking=booking,
                        full_name=f"{random.choice(self.first_names)} {random.choice(self.last_names)}",
                        email=f"guest{g}_{booking.id}@test.com",
                        phone_number=f"+234{random.randint(7000000000, 9099999999)}",
                    )
            
            # Update slots
            slots = SpaceCalendarSlot.objects.filter(
                calendar__space=space,
                date=booking_date,
                booking_type=booking_type,
                status='available'
            )
            
            if booking_type == 'hourly':
                slots = slots.filter(
                    start_time__gte=check_in_time,
                    end_time__lte=check_out_time
                )
            
            slots.update(status='booked', booking=booking)
            
            self.bookings.append(booking)
            
            if (i + 1) % 100 == 0:
                self.log(f"  Created {i + 1}/{self.NUM_BOOKINGS} bookings")
        
        self.log(f"✓ Created {len(self.bookings)} bookings with orders, payments, and QR codes")
    
    def run(self):
        """Run the complete population process"""
        start_time = timezone.now()
        
        self.log("="*60)
        self.log("STARTING COMPREHENSIVE DATABASE POPULATION")
        self.log("="*60)
        
        self.create_users()
        self.create_workspaces()
        self.create_bookings()
        
        duration = (timezone.now() - start_time).total_seconds()
        
        self.log("="*60)
        self.log("POPULATION COMPLETE!")
        self.log("="*60)
        self.log(f"Workspaces: {len(self.workspaces)}")
        self.log(f"Branches: {len(self.branches)}")
        self.log(f"Spaces: {len(self.spaces)}")
        self.log(f"Users: {len(self.users)}")
        self.log(f"Bookings: {len(self.bookings)}")
        self.log(f"Duration: {duration:.2f} seconds")
        self.log("="*60)
        self.log("\nTest Credentials:")
        self.log(f"  Users: {self.users[0].email} through {self.users[-1].email}")
        self.log("  Password: test123 (for all users)")
        self.log("="*60)


if __name__ == '__main__':
    populator = ComprehensivePopulator()
    populator.run()
