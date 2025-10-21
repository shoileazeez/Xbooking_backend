# Guest Management System - Complete Documentation

## Overview

The Guest Management System allows users to invite guests (coworkers, friends, family) to their bookings. Guests receive QR codes for check-in verification after admin approval. This system includes:

1. **Guest Registration**: Add guests to bookings with name, email, and phone
2. **Admin Verification**: Admins verify/reject guests per booking before QR codes are sent
3. **QR Code Generation**: Automatic QR code generation and email delivery upon verification
4. **Guest Check-in**: QR code-based check-in verification
5. **Check-out Tracking**: Track guest check-out status

---

## Database Models

### Guest Model

```python
class Guest(models.Model):
    # Status tracking
    GUEST_STATUS_CHOICES = [
        ('pending', 'Pending - Awaiting Verification'),
        ('verified', 'Verified - QR code sent'),
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
        ('rejected', 'Rejected by Admin'),
    ]
    
    VERIFICATION_STATUS_CHOICES = [
        ('pending', 'Pending Admin Verification'),
        ('verified', 'Verified by Admin'),
        ('rejected', 'Rejected by Admin'),
    ]
    
    # Fields
    booking              # ForeignKey to Booking
    first_name          # Guest's first name
    last_name           # Guest's last name
    email               # Guest's email (for QR code delivery)
    phone               # Optional phone number
    
    # Verification
    verification_status # pending/verified/rejected
    verified_by         # User who verified (admin/manager)
    verified_at         # Timestamp of verification
    rejection_reason    # Reason if rejected
    
    # QR Code
    qr_code_verification_code  # Unique code for guest check-in
    qr_code_sent        # Boolean flag
    qr_code_sent_at     # Timestamp
    
    # Check-in/out
    status              # Guest lifecycle status
    checked_in_at       # Timestamp of check-in
    checked_in_by       # User who checked them in
    checked_out_at      # Timestamp of check-out
```

---

## API Endpoints

### 1. User Endpoints - Add Guests to Booking

#### Add Guest to Booking
```
POST /api/booking/workspaces/{workspace_id}/bookings/{booking_id}/guests/
```

**Request Body:**
```json
{
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "phone": "+234812345678"
}
```

**Response (201 Created):**
```json
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "booking_id": "550e8400-e29b-41d4-a716-446655440001",
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "phone": "+234812345678",
    "status": "pending",
    "verification_status": "pending",
    "qr_code_sent": false,
    "qr_code_sent_at": null,
    "checked_in_at": null,
    "created_at": "2025-10-21T10:00:00Z"
}
```

---

#### Get All Guests for Booking
```
GET /api/booking/workspaces/{workspace_id}/bookings/{booking_id}/guests/
```

**Response (200 OK):**
```json
{
    "booking_id": "550e8400-e29b-41d4-a716-446655440001",
    "total_guests": 3,
    "guests": [
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "status": "pending",
            "verification_status": "pending",
            "created_at": "2025-10-21T10:00:00Z"
        },
        ...
    ]
}
```

---

#### Get Single Guest Details
```
GET /api/booking/workspaces/{workspace_id}/bookings/{booking_id}/guests/{guest_id}/
```

**Response (200 OK):**
```json
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "booking_id": "550e8400-e29b-41d4-a716-446655440001",
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "phone": "+234812345678",
    "status": "pending",
    "verification_status": "pending",
    "verified_by_email": null,
    "verified_at": null,
    "qr_code_verification_code": "GQR1234567890",
    "qr_code_sent": false,
    "checked_in_at": null,
    "created_at": "2025-10-21T10:00:00Z"
}
```

---

### 2. Admin Endpoints - Guest Verification (Per Booking)

#### List Pending Guests for Booking
```
GET /api/booking/workspaces/{workspace_id}/admin/bookings/{booking_id}/pending-guests/
```

**Response (200 OK):**
```json
{
    "booking_id": "550e8400-e29b-41d4-a716-446655440001",
    "count": 2,
    "guests": [
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "phone": "+234812345678",
            "verification_status": "pending",
            "created_at": "2025-10-21T10:00:00Z"
        }
    ]
}
```

---

#### Verify Guest (Approve)
```
POST /api/booking/workspaces/{workspace_id}/admin/bookings/{booking_id}/guests/{guest_id}/verify/
```

**Request Body:**
```json
{
    "notes": "Optional notes about the guest"
}
```

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Guest John Doe verified successfully",
    "guest": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "first_name": "John",
        "last_name": "Doe",
        "status": "verified",
        "verification_status": "verified",
        "verified_by_email": "admin@workspace.com",
        "verified_at": "2025-10-21T10:30:00Z",
        "qr_code_sent": true,
        "qr_code_sent_at": "2025-10-21T10:30:00Z"
    }
}
```

**Process Flow:**
1. Admin calls this endpoint
2. Guest `verification_status` → 'verified'
3. Guest `status` → 'verified'
4. QR code generation triggered (background task)
5. QR code email sent to guest
6. Booking creator notified

---

#### Reject Guest (Deny)
```
POST /api/booking/workspaces/{workspace_id}/admin/bookings/{booking_id}/guests/{guest_id}/reject/
```

**Request Body:**
```json
{
    "reason": "Guest does not meet workplace policy requirements"
}
```

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Guest John Doe rejected",
    "reason": "Guest does not meet workplace policy requirements",
    "guest": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "first_name": "John",
        "last_name": "Doe",
        "status": "rejected",
        "verification_status": "rejected",
        "rejection_reason": "Guest does not meet workplace policy requirements",
        "verified_by_email": "admin@workspace.com",
        "verified_at": "2025-10-21T10:30:00Z"
    }
}
```

---

#### Get Guest Details (Admin)
```
GET /api/booking/workspaces/{workspace_id}/admin/bookings/{booking_id}/guests/{guest_id}/
```

**Response (200 OK):**
```json
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "booking_id": "550e8400-e29b-41d4-a716-446655440001",
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "phone": "+234812345678",
    "status": "checked_in",
    "verification_status": "verified",
    "verified_by_email": "admin@workspace.com",
    "verified_at": "2025-10-21T10:30:00Z",
    "qr_code_verification_code": "GQR1234567890",
    "checked_in_at": "2025-10-21T15:00:00Z",
    "checked_in_by_email": "staff@workspace.com"
}
```

---

#### Get Guest Statistics for Booking
```
GET /api/booking/workspaces/{workspace_id}/admin/bookings/{booking_id}/guests/stats/
```

**Response (200 OK):**
```json
{
    "booking_id": "550e8400-e29b-41d4-a716-446655440001",
    "statistics": {
        "total_guests": 5,
        "verified": 4,
        "pending_verification": 1,
        "rejected": 0,
        "checked_in": 3,
        "checked_out": 1,
        "remaining": 1
    }
}
```

---

## Workflow Examples

### Example 1: Complete Guest Approval Flow

**Step 1: User Adds Guests to Booking**
```bash
POST /api/booking/workspaces/{workspace_id}/bookings/{booking_id}/guests/
{
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com"
}
```
→ Guest created with `verification_status=pending`

**Step 2: Admin Sees Pending Guests**
```bash
GET /api/booking/workspaces/{workspace_id}/admin/bookings/{booking_id}/pending-guests/
```
→ Returns list of guests awaiting verification

**Step 3: Admin Verifies Guest**
```bash
POST /api/booking/workspaces/{workspace_id}/admin/bookings/{booking_id}/guests/{guest_id}/verify/
{ "notes": "Approved" }
```
→ System:
- Sets `verification_status=verified`
- Generates unique QR code
- Sends QR code to guest email
- Notifies booking creator

**Step 4: Guest Receives QR Code**
→ Email contains:
- Booking details
- Space location
- Check-in time
- QR code image/link

**Step 5: Guest Check-in (via QR Code)**
```bash
POST /api/qr/workspaces/{workspace_id}/admin/qr-code/verify/guest/
{
    "qr_code": "GQR1234567890"
}
```
→ Guest `status=checked_in`, `checked_in_at=now()`

---

### Example 2: Guest Rejection Flow

**Step 1: Admin Reviews and Rejects**
```bash
POST /api/booking/workspaces/{workspace_id}/admin/bookings/{booking_id}/guests/{guest_id}/reject/
{
    "reason": "Background check failed"
}
```
→ System:
- Sets `verification_status=rejected`
- Stores rejection reason
- Notifies booking creator

**Step 2: Booking Creator Notified**
→ Email notification with rejection details

---

## State Diagram

```
GUEST LIFECYCLE:

                    ┌─────────────────────┐
                    │   Guest Created     │
                    │  status: pending    │
                    │ verify_status:      │
                    │ pending             │
                    └─────────────────────┘
                           │
                   ┌───────┴───────┐
                   │               │
                   ▼               ▼
            ┌──────────────┐  ┌──────────────┐
            │   VERIFIED   │  │   REJECTED   │
            │ by Admin     │  │ by Admin     │
            └──────────────┘  └──────────────┘
                   │               │
         QR sent   │               │
                   ▼               ▼
            ┌──────────────┐  ┌──────────────┐
            │  VERIFIED    │  │  REJECTED    │
            │ (QR sent)    │  │ (no QR)      │
            └──────────────┘  └──────────────┘
                   │
                   ▼
            ┌──────────────┐
            │ CHECKED_IN   │
            │ (via QR)     │
            └──────────────┘
                   │
                   ▼
            ┌──────────────┐
            │ CHECKED_OUT  │
            │ (completed)  │
            └──────────────┘
```

---

## Permissions Matrix

| Action | User | Staff | Manager | Admin | Owner |
|--------|------|-------|---------|-------|-------|
| Add Guest | ✓ | - | - | - | - |
| View Own Guests | ✓ | - | - | - | - |
| List All Guests (workspace) | - | - | ✓ | ✓ | ✓ |
| Verify Guest | - | - | ✓ | ✓ | ✓ |
| Reject Guest | - | - | ✓ | ✓ | ✓ |
| Check-in Guest | - | ✓ | ✓ | ✓ | ✓ |
| View Statistics | - | - | ✓ | ✓ | ✓ |

---

## Background Tasks (Celery)

### send_guest_qr_code_email
**Triggers:** After admin verifies guest

**Process:**
1. Generate unique QR code verification code
2. Create QR code image
3. Send email with QR code to guest
4. Update `qr_code_sent=True` and `qr_code_sent_at=now()`

**Example:**
```python
send_guest_qr_code_email.delay(guest_id)
```

---

## Implementation Checklist

- [x] Guest model with verification fields
- [x] Guest serializers
- [x] User endpoints (add/list guests)
- [x] Admin verification endpoints (per booking)
- [x] Admin guest statistics
- [x] QR code generation for guests
- [x] Email notifications
- [ ] Test all endpoints
- [ ] Create frontend UI for guest management
- [ ] Create admin verification dashboard
- [ ] Implement guest check-in via QR

---

## Error Handling

### Common Errors

```json
// Guest already verified
{
    "error": "Guest is already verified",
    "current_status": "verified"
}

// Booking not found
{
    "error": "Booking not found"
}

// Guest not found
{
    "error": "Guest not found"
}

// Permission denied
{
    "error": "Only admins/managers can verify guests"
}
```

---

## Security Considerations

1. ✅ **Unique QR Codes**: Each guest has unique `qr_code_verification_code`
2. ✅ **Admin Verification**: No QR sent without admin approval
3. ✅ **Email Verification**: QR only sent to registered email
4. ✅ **Booking Owner Notification**: Notified of all verification actions
5. ✅ **Permission Checks**: Only admins/managers can verify
6. ✅ **Audit Trail**: `verified_by`, `verified_at`, `rejection_reason` tracked

---

## Next Steps

1. Run migrations: `python manage.py makemigrations && python manage.py migrate`
2. Test all endpoints with Postman/curl
3. Create frontend guest management UI
4. Create admin verification dashboard
5. Implement guest check-in via QR code scanning
6. Create email templates for guest notifications
7. Add rate limiting for guest additions
8. Create reporting/analytics for guest statistics
