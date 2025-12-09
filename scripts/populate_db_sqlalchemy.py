import os
import uuid
import random
from datetime import datetime, timedelta, time, date, timezone
from decimal import Decimal

from sqlalchemy import (
    create_engine, Column, String, Integer, Boolean, DateTime, Date, Time, Text, Numeric, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.types import JSON

DATABASE_URL = os.environ.get("DATABASE_URL", "")
WORKSPACES = int(os.environ.get("WORKSPACES", "5"))
BRANCHES_PER_WORKSPACE = int(os.environ.get("BRANCHES_PER_WORKSPACE", "15"))
SPACES_PER_BRANCH = int(os.environ.get("SPACES_PER_BRANCH", "10"))
DAYS_AHEAD = int(os.environ.get("DAYS_AHEAD", "90"))

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)
Base = declarative_base()


class User(Base):
    __tablename__ = "user_user"
    id = Column(String(36), primary_key=True)
    full_name = Column(String(200), nullable=False)
    email = Column(String(254), nullable=False, unique=True)
    password = Column(String(128), nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    avatar_url = Column(String, nullable=True)
    google_id = Column(String(255), nullable=True)
    date_joined = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    is_staff = Column(Boolean, nullable=False, default=False)
    is_superuser = Column(Boolean, nullable=False, default=False)
    force_password_change = Column(Boolean, nullable=False, default=False)


class Workspace(Base):
    __tablename__ = "workspace"
    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    admin_id = Column(String(36), ForeignKey("user_user.id"), nullable=False)
    logo_url = Column(String, nullable=True)
    website = Column(String, nullable=True)
    email = Column(String(254), nullable=False, unique=True)
    social_media_links = Column(JSON, nullable=False, default={})
    phone = Column(String(20), nullable=True)
    address = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)


class Branch(Base):
    __tablename__ = "workspace_branch"
    id = Column(String(36), primary_key=True)
    workspace_id = Column(String(36), ForeignKey("workspace.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    manager_id = Column(String(36), ForeignKey("user_user.id"), nullable=True)
    operating_hours = Column(JSON, nullable=False, default={})
    images = Column(JSON, nullable=False, default=[])
    email = Column(String(254), nullable=False)
    phone = Column(String(20), nullable=True)
    address = Column(String(255), nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=False)
    postal_code = Column(String(20), nullable=True)
    latitude = Column(Integer, nullable=True)
    longitude = Column(Integer, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)
    __table_args__ = (UniqueConstraint("workspace_id", "name", name="uq_workspace_branch_name"),)


class Space(Base):
    __tablename__ = "workspace_space"
    id = Column(String(36), primary_key=True)
    branch_id = Column(String(36), ForeignKey("workspace_branch.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    space_type = Column(String(50), nullable=False)
    capacity = Column(Integer, nullable=False)
    price_per_hour = Column(Numeric(10, 2), nullable=False)
    daily_rate = Column(Numeric(10, 2), nullable=True)
    monthly_rate = Column(Numeric(10, 2), nullable=True)
    rules = Column(Text, nullable=True)
    cancellation_policy = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)
    amenities = Column(JSON, nullable=False, default=[])
    is_available = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)
    __table_args__ = (UniqueConstraint("branch_id", "name", name="uq_space_branch_name"),)


class SpaceCalendar(Base):
    __tablename__ = "workspace_space_calendar"
    id = Column(String(36), primary_key=True)
    space_id = Column(String(36), ForeignKey("workspace_space.id"), nullable=False)
    time_interval_minutes = Column(Integer, nullable=False)
    operating_hours = Column(JSON, nullable=False, default={})
    hourly_enabled = Column(Boolean, nullable=False, default=True)
    daily_enabled = Column(Boolean, nullable=False, default=True)
    monthly_enabled = Column(Boolean, nullable=False, default=True)
    hourly_price = Column(Numeric(10, 2), nullable=False)
    daily_price = Column(Numeric(10, 2), nullable=False)
    monthly_price = Column(Numeric(10, 2), nullable=False)
    min_advance_booking_days = Column(Integer, nullable=False)
    max_advance_booking_days = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)


class SpaceCalendarSlot(Base):
    __tablename__ = "workspace_space_calendar_slot"
    id = Column(String(36), primary_key=True)
    calendar_id = Column(String(36), ForeignKey("workspace_space_calendar.id"), nullable=False)
    date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    booking_type = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False)
    booking_id = Column(String(36), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)
    __table_args__ = (UniqueConstraint("calendar_id", "date", "start_time", "booking_type", name="uq_calendar_slot"),)


def parse_time(s):
    h, m = map(int, s.split(":"))
    return time(hour=h, minute=m)


def pricing_for_type(space_type):
    if space_type == "meeting_room":
        hourly = Decimal(random.randint(5000, 15000))
    elif space_type == "office":
        hourly = Decimal(random.randint(10000, 30000))
    elif space_type == "coworking":
        hourly = Decimal(random.randint(3000, 8000))
    elif space_type == "event_space":
        hourly = Decimal(random.randint(20000, 80000))
    elif space_type == "desk":
        hourly = Decimal(random.randint(2000, 5000))
    else:
        hourly = Decimal(random.randint(3000, 7000))
    daily = (hourly * Decimal(8)).quantize(Decimal("1"))
    monthly = (daily * Decimal(22)).quantize(Decimal("1"))
    return hourly, daily, monthly


def populate_calendar_slots(session, calendar_obj, days_ahead):
    start_date = date.today()
    operating_hours = calendar_obj.operating_hours
    interval_minutes = calendar_obj.time_interval_minutes
    for day_offset in range(days_ahead):
        current_date = start_date + timedelta(days=day_offset)
        weekday = str(current_date.weekday())
        if weekday not in operating_hours:
            continue
        day_hours = operating_hours.get(weekday)
        if not day_hours:
            continue
        open_time = parse_time(day_hours.get("start", "09:00"))
        close_time = parse_time(day_hours.get("end", "18:00"))
        current_time = open_time
        while current_time < close_time:
            end_minutes = current_time.hour * 60 + current_time.minute + interval_minutes
            end_hour = end_minutes // 60
            end_minute = end_minutes % 60
            if end_hour > close_time.hour or (end_hour == close_time.hour and end_minute > close_time.minute):
                break
            end_time = time(hour=end_hour, minute=end_minute)
            slot = SpaceCalendarSlot(
                id=str(uuid.uuid4()),
                calendar_id=calendar_obj.id,
                date=current_date,
                start_time=current_time,
                end_time=end_time,
                booking_type="hourly",
                status="available",
                booking_id=None,
                notes="Hourly booking slot",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(slot)
            current_time = end_time
        daily_slot = SpaceCalendarSlot(
            id=str(uuid.uuid4()),
            calendar_id=calendar_obj.id,
            date=current_date,
            start_time=open_time,
            end_time=close_time,
            booking_type="daily",
            status="available",
            booking_id=None,
            notes="Daily booking slot",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(daily_slot)
        if current_date.day == 1:
            monthly_slot = SpaceCalendarSlot(
                id=str(uuid.uuid4()),
                calendar_id=calendar_obj.id,
                date=current_date,
                start_time=open_time,
                end_time=close_time,
                booking_type="monthly",
                status="available",
                booking_id=None,
                notes="Monthly booking slot",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(monthly_slot)


def main():
    session = SessionLocal()
    try:
        admin = session.query(User).filter(User.email == "admin@xbooking.com").first()
        if not admin:
            admin = User(
                id=str(uuid.uuid4()),
                full_name="Admin User",
                email="admin@xbooking.com",
                password="!standalone",
                last_login=None,
                avatar_url=None,
                google_id=None,
                date_joined=datetime.now(timezone.utc),
                is_active=True,
                is_staff=True,
                is_superuser=True,
                force_password_change=False,
            )
            session.add(admin)
            session.commit()

        amenities = [
            "WiFi", "Projector", "Whiteboard", "Air Conditioning",
            "Coffee Machine", "Water Dispenser", "Parking", "Printer",
            "TV Screen", "Microphone", "Speaker System", "Kitchen Access",
            "Standing Desk", "Meeting Table", "Chairs", "Power Outlets",
            "Natural Lighting", "Video Conference Setup", "Soundproofing",
        ]

        workspace_names = [
            "Tech Hub Africa", "Creative Works", "Business Prime",
            "Innovation Space", "Professional Hub", "Startup Central",
            "Enterprise Plus", "Digital Hub", "Collaborative Space", "Elite Workspace",
        ]

        locations = [
            {"city": "Lagos", "state": "Lagos", "country": "Nigeria"},
            {"city": "Abuja", "state": "FCT", "country": "Nigeria"},
            {"city": "Ibadan", "state": "Oyo", "country": "Nigeria"},
            {"city": "Port Harcourt", "state": "Rivers", "country": "Nigeria"},
            {"city": "Kano", "state": "Kano", "country": "Nigeria"},
        ]

        branch_names = [
            "Yaba", "Victoria Island", "Ikeja", "Lekki", "Ikoyi",
            "Ajah", "Marina", "Surulere", "Apapa", "Mushin",
            "Phase 1", "Phase 2", "Garki", "Wuse", "Maitama",
            "New Bussa", "Koton Karfe", "Minna", "Central Business District", "Downtown",
        ]

        for i in range(WORKSPACES):
            workspace_name = workspace_names[i % len(workspace_names)] + f" {i+1}"
            location = locations[i % len(locations)]
            ws = session.query(Workspace).filter(Workspace.name == workspace_name).first()
            if not ws:
                ws = Workspace(
                    id=str(uuid.uuid4()),
                    name=workspace_name,
                    description=f"Premium workspace solution in {location['city']} offering flexible office spaces",
                    admin_id=admin.id,
                    logo_url=f"https://picsum.photos/seed/{workspace_name.lower().replace(' ', '-')}-logo/800/600",
                    website=None,
                    email=f"admin@{workspace_name.lower().replace(' ', '')}.com",
                    social_media_links={
                        "twitter": f"https://twitter.com/{workspace_name.lower().replace(' ', '')}",
                        "instagram": f"https://instagram.com/{workspace_name.lower().replace(' ', '')}",
                        "linkedin": f"https://linkedin.com/company/{workspace_name.lower().replace(' ', '')}",
                    },
                    phone=f"+234{random.randint(701, 910)}{random.randint(1000000, 9999999)}",
                    address=f"{location['city']}, {location['state']}, {location['country']}",
                    city=location["city"],
                    state=location["state"],
                    country=location["country"],
                    postal_code=None,
                    is_active=True,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                session.add(ws)
                session.commit()

            for branch_idx in range(BRANCHES_PER_WORKSPACE):
                branch_name = branch_names[branch_idx % len(branch_names)]
                if branch_idx >= len(branch_names):
                    branch_name = f"{branch_names[branch_idx % len(branch_names)]} {branch_idx // len(branch_names)}"
                br = session.query(Branch).filter(Branch.workspace_id == ws.id, Branch.name == branch_name).first()
                if not br:
                    br = Branch(
                        id=str(uuid.uuid4()),
                        workspace_id=ws.id,
                        name=branch_name,
                        description=None,
                        manager_id=None,
                        operating_hours={
                            "0": {"open": "09:00", "close": "18:00"},
                            "1": {"open": "09:00", "close": "18:00"},
                            "2": {"open": "09:00", "close": "18:00"},
                            "3": {"open": "09:00", "close": "18:00"},
                            "4": {"open": "09:00", "close": "18:00"},
                            "5": {"open": "09:00", "close": "18:00"},
                            "6": {"open": "10:00", "close": "16:00"},
                        },
                        images=[
                            f"https://picsum.photos/seed/{workspace_name.lower().replace(' ', '-')}-{branch_name.lower().replace(' ', '-')}-1/800/600",
                            f"https://picsum.photos/seed/{workspace_name.lower().replace(' ', '-')}-{branch_name.lower().replace(' ', '-')}-2/800/600",
                            f"https://picsum.photos/seed/{workspace_name.lower().replace(' ', '-')}-{branch_name.lower().replace(' ', '-')}-3/800/600",
                        ],
                        email=f"{branch_name.lower().replace(' ', '')}@{workspace_name.lower().replace(' ', '')}.com",
                        phone=f"+234{random.randint(701, 910)}{random.randint(1000000, 9999999)}",
                        address=f"{branch_name}, {location['city']}, {location['state']}, {location['country']}",
                        city=location["city"],
                        state=location["state"],
                        country=location["country"],
                        postal_code=None,
                        latitude=None,
                        longitude=None,
                        is_active=True,
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc),
                    )
                    session.add(br)
                    session.commit()

                space_types = ["meeting_room", "office", "coworking", "event_space", "desk", "lounge"]
                for space_idx in range(SPACES_PER_BRANCH):
                    space_type = space_types[space_idx % len(space_types)]
                    capacity = random.randint(2, 50)
                    hourly_price, daily_price, monthly_price = pricing_for_type(space_type)
                    image_url = f"https://picsum.photos/seed/{workspace_name.lower().replace(' ', '-')}-{branch_name.lower().replace(' ', '-')}-{space_idx}/800/600"
                    sp_name = f"{space_type.title().replace('_', ' ')} {capacity}Cap - {space_idx + 1}"
                    sp = session.query(Space).filter(Space.branch_id == br.id, Space.name == sp_name).first()
                    if not sp:
                        sp = Space(
                            id=str(uuid.uuid4()),
                            branch_id=br.id,
                            name=sp_name,
                            description=f"Premium {space_type.lower().replace('_', ' ')} accommodating {capacity} people with modern amenities",
                            space_type=space_type,
                            capacity=capacity,
                            price_per_hour=hourly_price,
                            daily_rate=daily_price,
                            monthly_rate=monthly_price,
                            rules="House rules apply",
                            cancellation_policy="Standard cancellation policy",
                            image_url=image_url,
                            amenities=random.sample(amenities, random.randint(5, 12)),
                            is_available=True,
                            created_at=datetime.now(timezone.utc),
                            updated_at=datetime.now(timezone.utc),
                        )
                        session.add(sp)
                        session.commit()

                        cal = SpaceCalendar(
                            id=str(uuid.uuid4()),
                            space_id=sp.id,
                            time_interval_minutes=60,
                            operating_hours={
                                "0": {"start": "09:00", "end": "18:00"},
                                "1": {"start": "09:00", "end": "18:00"},
                                "2": {"start": "09:00", "end": "18:00"},
                                "3": {"start": "09:00", "end": "18:00"},
                                "4": {"start": "09:00", "end": "18:00"},
                                "5": {"start": "09:00", "end": "18:00"},
                                "6": {"start": "10:00", "end": "16:00"},
                            },
                            hourly_enabled=True,
                            daily_enabled=True,
                            monthly_enabled=True,
                            hourly_price=hourly_price,
                            daily_price=daily_price,
                            monthly_price=monthly_price,
                            min_advance_booking_days=0,
                            max_advance_booking_days=365,
                            created_at=datetime.now(timezone.utc),
                            updated_at=datetime.now(timezone.utc),
                        )
                        session.add(cal)
                        session.commit()
                        populate_calendar_slots(session, cal, DAYS_AHEAD)
                        session.commit()

        total_spaces = WORKSPACES * BRANCHES_PER_WORKSPACE * SPACES_PER_BRANCH
        print("Completed population")
        print(f"Workspaces: {WORKSPACES}")
        print(f"Branches per workspace: {BRANCHES_PER_WORKSPACE}")
        print(f"Spaces per branch: {SPACES_PER_BRANCH}")
        print(f"Days ahead: {DAYS_AHEAD}")
        print(f"Total spaces intended: {total_spaces}")
    finally:
        session.close()


if __name__ == "__main__":
    if not DATABASE_URL:
        raise SystemExit("Set DATABASE_URL environment variable to your hosted DB")
    main()

