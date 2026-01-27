#!/usr/bin/env python
"""
Comprehensive Database Population Script for Google Colab
Uses SQLAlchemy for direct database access
Creates 100 workspaces, 100 users, and 10,000 bookings for ML recommendation model
"""

import os
import random
import secrets
from datetime import datetime, date, time, timedelta
from decimal import Decimal
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import uuid

# ============================================================================
# CONFIGURATION - UPDATE THIS WITH YOUR DATABASE URL
# ============================================================================
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://user:password@host:port/dbname')
# Example: 'postgresql://postgres:password@localhost:5432/xbooking'
# Or for MySQL: 'mysql+pymysql://user:password@host:port/dbname'

# ============================================================================
# DATA POPULATION CLASS
# ============================================================================

class ColabPopulator:
    """Populate database using SQLAlchemy"""
    
    def __init__(self, database_url):
        self.engine = create_engine(database_url, echo=False)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        
        # Data storage
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
        
        self.amenities = ['WiFi', 'Coffee', 'Printer', 'Parking', 'Air Conditioning', 'Kitchen', 'Lounge', 'Whiteboard', 'Projector', 'Security', 'Conference Phone', 'Video Conferencing', 'Standing Desk', 'Lockers', 'Mail Service']
    
    def log(self, message, level='INFO'):
        """Print formatted log message"""
        print(f"[{level}] {message}")
    
    def create_users(self):
        """Create test users with wallets and preferences"""
        self.log(f"Creating {self.NUM_USERS} users...")
        
        from passlib.hash import pbkdf2_sha256
        
        for i in range(self.NUM_USERS):
            first_name = random.choice(self.first_names)
            last_name = random.choice(self.last_names)
            email = f"{first_name.lower()}.{last_name.lower()}{i}@test.com"
            user_id = str(uuid.uuid4())
            now = datetime.now()
            
            # Hash password (Django uses PBKDF2)
            password_hash = pbkdf2_sha256.hash('test123')
            
            # Insert user
            self.session.execute(text("""
                INSERT INTO "user" (id, password, last_login, is_superuser, full_name, email, phone, avatar_url, role, is_business_email, business_domain, onboarding_completed, google_id, is_active, is_staff, force_password_change, created_at, updated_at)
                VALUES (:id, :password, NULL, FALSE, :full_name, :email, :phone, NULL, 'user', FALSE, NULL, FALSE, NULL, TRUE, FALSE, FALSE, :created_at, :updated_at)
            """), {
                'id': user_id,
                'password': f'pbkdf2_sha256$600000${secrets.token_urlsafe(16)}${secrets.token_urlsafe(32)}',
                'full_name': f"{first_name} {last_name}",
                'email': email,
                'phone': f"+234{random.randint(7000000000, 9099999999)}",
                'created_at': now,
                'updated_at': now
            })
            
            # Create wallet
            self.session.execute(text("""
                INSERT INTO bank_wallet (id, user_id, balance, currency, created_at, updated_at)
                VALUES (:id, :user_id, :balance, 'NGN', :created_at, :updated_at)
            """), {
                'id': str(uuid.uuid4()),
                'user_id': user_id,
                'balance': float(random.randint(10000, 500000)),
                'created_at': now,
                'updated_at': now
            })
            
            # Create user preference
            preferred_space_types = random.sample(self.space_types, k=random.randint(1, 3))
            preferred_cities = random.sample(self.cities, k=random.randint(1, 3))
            
            self.session.execute(text("""
                INSERT INTO user_userpreference (id, user_id, preferred_booking_type, preferred_space_types, preferred_capacity_min, preferred_capacity_max, preferred_cities, max_distance_km, preferred_amenities, budget_min, budget_max, preferred_days_of_week, preferred_start_time, preferred_end_time, notify_on_recommendation, notify_on_price_drop, notify_on_availability, auto_suggest_similar, save_search_history, created_at, updated_at)
                VALUES (:id, :user_id, :preferred_booking_type, :preferred_space_types, :preferred_capacity_min, :preferred_capacity_max, :preferred_cities, NULL, '[]'::jsonb, :budget_min, :budget_max, '[]'::jsonb, NULL, NULL, TRUE, TRUE, TRUE, TRUE, TRUE, :created_at, :updated_at)
            """), {
                'id': str(uuid.uuid4()),
                'user_id': user_id,
                'preferred_booking_type': random.choice(['hourly', 'daily', 'monthly']),
                'preferred_space_types': f'{preferred_space_types}',
                'preferred_capacity_min': random.randint(1, 5),
                'preferred_capacity_max': random.randint(6, 20),
                'preferred_cities': f'{preferred_cities}',
                'budget_min': float(random.randint(1000, 5000)),
                'budget_max': float(random.randint(10000, 100000)),
                'created_at': now,
                'updated_at': now
            })
            
            self.users.append({'id': user_id, 'email': email})
            
            if (i + 1) % 10 == 0:
                self.session.commit()
                self.log(f"  Created {i + 1}/{self.NUM_USERS} users")
        
        self.session.commit()
        self.log(f"✓ Created {len(self.users)} users with wallets and preferences")
    
    def create_workspaces(self):
        """Create workspaces with branches, spaces, calendars, and slots"""
        self.log(f"Creating {self.NUM_WORKSPACES} workspaces...")
        
        admin_user_id = self.users[0]['id']
        today = date.today()
        
        for i in range(self.NUM_WORKSPACES):
            workspace_name = f"Hub{i+1} {random.choice(self.cities)}"
            workspace_id = str(uuid.uuid4())
            now = datetime.now()
            
            # Create workspace
            self.session.execute(text("""
                INSERT INTO workspace (id, name, description, admin_id, logo_url, website, email, social_media_links, phone, address, city, state, country, postal_code, is_active, created_at, updated_at)
                VALUES (:id, :name, :description, :admin_id, NULL, NULL, :email, '{}'::jsonb, :phone, :address, :city, :state, 'Nigeria', NULL, TRUE, :created_at, :updated_at)
            """), {
                'id': workspace_id,
                'name': workspace_name,
                'description': f'Modern workspace in {random.choice(self.cities)}',
                'admin_id': admin_user_id,
                'email': f"hub{i+1}@xbooking.com",
                'phone': f"+234{random.randint(7000000000, 9099999999)}",
                'address': f"{random.randint(1, 200)} Main St, {random.choice(self.cities)}",
                'city': random.choice(self.cities),
                'state': random.choice(self.states),
                'created_at': now,
                'updated_at': now
            })
            
            self.workspaces.append({'id': workspace_id, 'name': workspace_name})
            
            # Create branches
            for b in range(self.BRANCHES_PER_WORKSPACE):
                branch_id = str(uuid.uuid4())
                
                self.session.execute(text("""
                    INSERT INTO workspace_branch (id, workspace_id, name, description, manager_id, operating_hours, images, email, phone, address, city, state, country, postal_code, latitude, longitude, is_active, created_at, updated_at)
                    VALUES (:id, :workspace_id, :name, NULL, NULL, '{}'::jsonb, '[]'::jsonb, :email, :phone, :address, :city, :state, 'Nigeria', NULL, NULL, NULL, TRUE, :created_at, :updated_at)
                """), {
                    'id': branch_id,
                    'workspace_id': workspace_id,
                    'name': f"{workspace_name} Branch {b+1}",
                    'email': f"branch{b+1}@hub{i+1}.com",
                    'phone': f"+234{random.randint(7000000000, 9099999999)}",
                    'address': f"{random.randint(1, 100)} Ave, {random.choice(self.cities)}",
                    'city': random.choice(self.cities),
                    'state': random.choice(self.states),
                    'created_at': now,
                    'updated_at': now
                })
                
                self.branches.append({'id': branch_id, 'workspace_id': workspace_id})
                
                # Create spaces
                for s in range(self.SPACES_PER_BRANCH):
                    space_type = random.choice(self.space_types)
                    capacity = random.randint(1, 50)
                    hourly_rate = float(random.randint(500, 10000))
                    daily_rate = float(random.randint(5000, 80000))
                    monthly_rate = float(random.randint(50000, 500000)) if space_type in ['office', 'desk'] else None
                    space_id = str(uuid.uuid4())
                    space_amenities = random.sample(self.amenities, k=random.randint(3, 8))
                    
                    self.session.execute(text("""
                        INSERT INTO workspace_space (id, branch_id, name, description, space_type, capacity, price_per_hour, daily_rate, monthly_rate, rules, cancellation_policy, image_url, amenities, is_available, created_at, updated_at)
                        VALUES (:id, :branch_id, :name, :description, :space_type, :capacity, :price_per_hour, :daily_rate, :monthly_rate, NULL, NULL, NULL, :amenities, TRUE, :created_at, :updated_at)
                    """), {
                        'id': space_id,
                        'branch_id': branch_id,
                        'name': f"{space_type.replace('_', ' ').title()} {s+1}",
                        'description': f"Well-equipped {space_type}",
                        'space_type': space_type,
                        'capacity': capacity,
                        'price_per_hour': hourly_rate,
                        'daily_rate': daily_rate,
                        'monthly_rate': monthly_rate,
                        'amenities': f'{space_amenities}',
                        'created_at': now,
                        'updated_at': now
                    })
                    
                    self.spaces.append({
                        'id': space_id,
                        'workspace_id': workspace_id,
                        'branch_id': branch_id,
                        'space_type': space_type,
                        'capacity': capacity,
                        'price_per_hour': hourly_rate,
                        'daily_rate': daily_rate,
                        'monthly_rate': monthly_rate
                    })
                    
                    # Create calendar
                    calendar_id = str(uuid.uuid4())
                    operating_hours = {str(d): {"start": "08:00", "end": "20:00"} for d in range(7)}
                    
                    self.session.execute(text("""
                        INSERT INTO workspace_spacecalendar (id, space_id, time_interval_minutes, operating_hours, hourly_enabled, daily_enabled, monthly_enabled, hourly_price, daily_price, monthly_price, min_advance_booking_days, max_advance_booking_days, created_at, updated_at)
                        VALUES (:id, :space_id, 60, :operating_hours, TRUE, TRUE, :monthly_enabled, :hourly_price, :daily_price, :monthly_price, 0, 180, :created_at, :updated_at)
                    """), {
                        'id': calendar_id,
                        'space_id': space_id,
                        'operating_hours': f'{operating_hours}',
                        'monthly_enabled': monthly_rate is not None,
                        'hourly_price': hourly_rate,
                        'daily_price': daily_rate,
                        'monthly_price': monthly_rate or 0.0,
                        'created_at': now,
                        'updated_at': now
                    })
                    
                    # Create slots for next 60 days
                    slots_data = []
                    for day_offset in range(60):
                        slot_date = today + timedelta(days=day_offset)
                        
                        # Hourly slots (8 AM to 8 PM)
                        for hour in range(8, 20):
                            slots_data.append({
                                'id': str(uuid.uuid4()),
                                'calendar_id': calendar_id,
                                'date': slot_date,
                                'start_time': time(hour, 0),
                                'end_time': time(hour + 1, 0),
                                'booking_type': 'hourly',
                                'status': 'available',
                                'booking_id': None
                            })
                        
                        # Daily slot
                        slots_data.append({
                            'id': str(uuid.uuid4()),
                            'calendar_id': calendar_id,
                            'date': slot_date,
                            'start_time': time(8, 0),
                            'end_time': time(20, 0),
                            'booking_type': 'daily',
                            'status': 'available',
                            'booking_id': None
                        })
                    
                    # Monthly slots (next 6 months)
                    if monthly_rate:
                        for month_offset in range(6):
                            month_date = (today.replace(day=1) + timedelta(days=32 * month_offset)).replace(day=1)
                            slots_data.append({
                                'id': str(uuid.uuid4()),
                                'calendar_id': calendar_id,
                                'date': month_date,
                                'start_time': time(0, 0),
                                'end_time': time(23, 59),
                                'booking_type': 'monthly',
                                'status': 'available',
                                'booking_id': None
                            })
                    
                    # Bulk insert slots
                    for slot in slots_data:
                        self.session.execute(text("""
                            INSERT INTO workspace_spacecalendarslot (id, calendar_id, date, start_time, end_time, booking_type, status, booking_id)
                            VALUES (:id, :calendar_id, :date, :start_time, :end_time, :booking_type, :status, :booking_id)
                        """), slot)
            
            if (i + 1) % 10 == 0:
                self.session.commit()
                self.log(f"  Created {i + 1}/{self.NUM_WORKSPACES} workspaces")
        
        self.session.commit()
        self.log(f"✓ Created {len(self.workspaces)} workspaces")
        self.log(f"✓ Created {len(self.branches)} branches")
        self.log(f"✓ Created {len(self.spaces)} spaces with calendars and slots")
    
    def create_bookings(self):
        """Create bookings with orders, payments, and QR codes"""
        self.log(f"Creating {self.NUM_BOOKINGS} bookings...")
        
        today = date.today()
        
        for i in range(self.NUM_BOOKINGS):
            user = random.choice(self.users)
            space = random.choice(self.spaces)
            booking_type = random.choice(self.booking_types)
            now = datetime.now()
            
            # Random booking date
            if booking_type == 'monthly':
                month_offset = random.randint(0, 5)
                booking_date = (today.replace(day=1) + timedelta(days=32 * month_offset)).replace(day=1)
            else:
                days_ahead = random.randint(0, 45)
                booking_date = today + timedelta(days=days_ahead)
            
            # Set times and price
            if booking_type == 'hourly':
                start_hour = random.randint(8, 18)
                duration_hours = random.randint(1, 4)
                check_in_time = time(start_hour, 0)
                check_out_time = time(min(start_hour + duration_hours, 20), 0)
                check_out_date = booking_date
                price = space['price_per_hour'] * duration_hours
            elif booking_type == 'daily':
                check_in_time = time(8, 0)
                check_out_time = time(20, 0)
                check_out_date = booking_date
                price = space['daily_rate']
            else:  # monthly
                check_in_time = time(0, 0)
                check_out_time = time(23, 59)
                if booking_date.month == 12:
                    check_out_date = booking_date.replace(year=booking_date.year + 1, month=1, day=1) - timedelta(days=1)
                else:
                    check_out_date = booking_date.replace(month=booking_date.month + 1, day=1) - timedelta(days=1)
                price = space['monthly_rate'] if space['monthly_rate'] else space['daily_rate'] * 30
            
            # Create order
            order_id = str(uuid.uuid4())
            order_number = f"ORD-{random.randint(100000, 999999)}"
            
            self.session.execute(text("""
                INSERT INTO payment_order (id, user_id, order_number, total_amount, currency, status, created_at, updated_at)
                VALUES (:id, :user_id, :order_number, :total_amount, 'NGN', 'completed', :created_at, :updated_at)
            """), {
                'id': order_id,
                'user_id': user['id'],
                'order_number': order_number,
                'total_amount': float(price),
                'created_at': now,
                'updated_at': now
            })
            
            # Create booking
            booking_id = str(uuid.uuid4())
            num_guests = random.randint(1, min(space['capacity'], 10))
            
            self.session.execute(text("""
                INSERT INTO booking_booking (id, user_id, workspace_id, space_id, order_id, check_in_date, check_out_date, check_in_time, check_out_time, booking_type, number_of_guests, total_price, status, payment_status, created_at, updated_at, cancelled_at, cancellation_reason, refund_amount, refund_status, special_requests, notes)
                VALUES (:id, :user_id, :workspace_id, :space_id, :order_id, :check_in_date, :check_out_date, :check_in_time, :check_out_time, :booking_type, :number_of_guests, :total_price, 'confirmed', 'completed', :created_at, :updated_at, NULL, NULL, NULL, NULL, NULL, NULL)
            """), {
                'id': booking_id,
                'user_id': user['id'],
                'workspace_id': space['workspace_id'],
                'space_id': space['id'],
                'order_id': order_id,
                'check_in_date': booking_date,
                'check_out_date': check_out_date,
                'check_in_time': check_in_time,
                'check_out_time': check_out_time,
                'booking_type': booking_type,
                'number_of_guests': num_guests,
                'total_price': float(price),
                'created_at': now,
                'updated_at': now
            })
            
            # Create payment
            payment_method = random.choice(['paystack', 'flutterwave', 'wallet'])
            self.session.execute(text("""
                INSERT INTO payment_payment (id, user_id, order_id, amount, currency, payment_method, status, gateway_reference, created_at, updated_at, paid_at, gateway_response, transaction_fee)
                VALUES (:id, :user_id, :order_id, :amount, 'NGN', :payment_method, 'completed', :gateway_reference, :created_at, :updated_at, :paid_at, '{}'::jsonb, 0.0)
            """), {
                'id': str(uuid.uuid4()),
                'user_id': user['id'],
                'order_id': order_id,
                'amount': float(price),
                'payment_method': payment_method,
                'gateway_reference': f"REF_{random.randint(10000000, 99999999)}",
                'created_at': now,
                'updated_at': now,
                'paid_at': now
            })
            
            # Create QR codes
            try:
                # Order QR Code
                self.session.execute(text("""
                    INSERT INTO qr_code_order_qrcode (id, order_id, qr_code_data, qr_code_image_url, appwrite_file_id, verification_code, status, scan_count, last_scanned_at, scanned_by_ip, verified, verified_at, verified_by_id, expires_at, created_at, updated_at, sent_at)
                    VALUES (:id, :order_id, :qr_code_data, NULL, NULL, :verification_code, 'generated', 0, NULL, NULL, FALSE, NULL, NULL, NULL, :created_at, :updated_at, NULL)
                """), {
                    'id': str(uuid.uuid4()),
                    'order_id': order_id,
                    'qr_code_data': f"ORDER-{order_id}",
                    'verification_code': secrets.token_urlsafe(16),
                    'created_at': now,
                    'updated_at': now
                })
                
                # Booking QR Code
                expires_at = datetime.combine(check_out_date, check_out_time)
                self.session.execute(text("""
                    INSERT INTO qr_code_booking_qrcode (id, booking_id, order_id, qr_code_data, qr_code_image_url, appwrite_file_id, verification_code, status, used, total_check_ins, max_check_ins, scan_count, last_scanned_at, scanned_by_ip, verified, verified_at, verified_by_id, expires_at, created_at, updated_at, sent_at)
                    VALUES (:id, :booking_id, :order_id, :qr_code_data, NULL, NULL, :verification_code, 'generated', FALSE, 0, NULL, 0, NULL, NULL, FALSE, NULL, NULL, :expires_at, :created_at, :updated_at, NULL)
                """), {
                    'id': str(uuid.uuid4()),
                    'booking_id': booking_id,
                    'order_id': order_id,
                    'qr_code_data': f"BOOKING-{booking_id}",
                    'verification_code': secrets.token_urlsafe(16),
                    'expires_at': expires_at,
                    'created_at': now,
                    'updated_at': now
                })
            except Exception as e:
                self.log(f"  Warning: QR code creation failed: {str(e)}", level='WARNING')
            
            # Add guests (30% of bookings)
            if random.random() < 0.3:
                guest_count = random.randint(1, min(num_guests, 5))
                for g in range(guest_count):
                    self.session.execute(text("""
                        INSERT INTO booking_guest (id, booking_id, first_name, last_name, full_name, email, phone_number, created_at, updated_at)
                        VALUES (:id, :booking_id, :first_name, :last_name, :full_name, :email, :phone_number, :created_at, :updated_at)
                    """), {
                        'id': str(uuid.uuid4()),
                        'booking_id': booking_id,
                        'first_name': random.choice(self.first_names),
                        'last_name': random.choice(self.last_names),
                        'full_name': f"{random.choice(self.first_names)} {random.choice(self.last_names)}",
                        'email': f"guest{g}_{booking_id[:8]}@test.com",
                        'phone_number': f"+234{random.randint(7000000000, 9099999999)}",
                        'created_at': now,
                        'updated_at': now
                    })
            
            self.bookings.append({'id': booking_id, 'order_id': order_id})
            
            if (i + 1) % 100 == 0:
                self.session.commit()
                self.log(f"  Created {i + 1}/{self.NUM_BOOKINGS} bookings")
        
        self.session.commit()
        self.log(f"✓ Created {len(self.bookings)} bookings with orders, payments, and QR codes")
    
    def run(self):
        """Run the complete population process"""
        start_time = datetime.now()
        
        self.log("="*60)
        self.log("STARTING COMPREHENSIVE DATABASE POPULATION")
        self.log("="*60)
        
        try:
            self.create_users()
            self.create_workspaces()
            self.create_bookings()
            
            duration = (datetime.now() - start_time).total_seconds()
            
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
            self.log(f"  Email: {self.users[0]['email']} to {self.users[-1]['email']}")
            self.log("  Password: test123 (for all users)")
            self.log("="*60)
            
        except Exception as e:
            self.log(f"ERROR: {str(e)}", level='ERROR')
            self.session.rollback()
            raise
        finally:
            self.session.close()


# ============================================================================
# GOOGLE COLAB USAGE
# ============================================================================
"""
To use this script in Google Colab:

1. Install required packages:
   !pip install sqlalchemy psycopg2-binary pymysql passlib

2. Set your database URL:
   import os
   os.environ['DATABASE_URL'] = 'postgresql://user:password@host:port/dbname'

3. Run the script:
   populator = ColabPopulator(os.environ['DATABASE_URL'])
   populator.run()

Or configure directly:
   DATABASE_URL = 'postgresql://user:password@host:port/dbname'
   populator = ColabPopulator(DATABASE_URL)
   populator.run()
"""

if __name__ == '__main__':
    if DATABASE_URL == 'postgresql://user:password@host:port/dbname':
        print("ERROR: Please update DATABASE_URL with your actual database credentials")
        print("Example: DATABASE_URL = 'postgresql://postgres:password@localhost:5432/xbooking'")
    else:
        populator = ColabPopulator(DATABASE_URL)
        populator.run()
