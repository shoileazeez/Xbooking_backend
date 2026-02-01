"""
Booking Service Layer
"""
import logging
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from core.services import EventBus, Event, EventTypes
from core.cache import CacheService
from booking.models import Booking, Cart, CartItem, Checkout, Guest, Reservation
from workspace.models import Space

logger = logging.getLogger(__name__)


class BookingService:
    """Service for managing bookings with event publishing"""
    
    @staticmethod
    @transaction.atomic
    def create_booking(booking_data, user):
        """Create a new booking and publish event"""
        booking = Booking.objects.create(**booking_data)
        
        # Publish booking created event
        from core.services import Event
        event = Event(
            event_type=EventTypes.BOOKING_CREATED,
            data={
                'booking_id': str(booking.id),
                'workspace_id': str(booking.workspace.id),
                'workspace_name': booking.workspace.name,
                'space_id': str(booking.space.id),
                'space_name': booking.space.name,
                'user_id': str(user.id),
                'user_email': user.email,
                'user_name': user.full_name or user.email,
                'booking_type': booking.booking_type,
                'check_in': booking.check_in.isoformat(),
                'check_out': booking.check_out.isoformat(),
                'total_price': str(booking.total_price),
                'status': booking.status,
                'timestamp': timezone.now().isoformat()
            },
            source_module='booking'
        )
        EventBus.publish(event)
        
        # Invalidate caches
        CacheService.delete_pattern(f'booking:{booking.id}:*')
        CacheService.delete_pattern(f'bookings:user:{user.id}:*')
        CacheService.delete_pattern(f'bookings:workspace:{booking.workspace.id}:*')
        
        return booking
    
    @staticmethod
    @transaction.atomic
    def confirm_booking(booking):
        """Confirm a booking and publish event"""
        booking.status = 'confirmed'
        booking.save(update_fields=['status', 'updated_at'])
        
        # Publish booking confirmed event
        event = Event(
            event_type=EventTypes.BOOKING_CONFIRMED,
            data={
                'booking_id': str(booking.id),
                'workspace_id': str(booking.workspace.id),
                'workspace_name': booking.workspace.name,
                'space_id': str(booking.space.id),
                'space_name': booking.space.name,
                'user_id': str(booking.user.id),
                'user_email': booking.user.email,
                'user_name': booking.user.full_name or booking.user.email,
                'check_in': booking.check_in.isoformat(),
                'check_out': booking.check_out.isoformat(),
                'timestamp': timezone.now().isoformat()
            },
            source_module='booking'
        )
        EventBus.publish(event)
        
        # Invalidate caches
        CacheService.delete_pattern(f'booking:{booking.id}:*')
        CacheService.delete_pattern(f'bookings:user:{booking.user.id}:*')
        
        return booking
    
    @staticmethod
    @transaction.atomic
    def cancel_booking(booking, cancelled_by=None, reason=None, reason_description=""):
        """
        Cancel a booking with enhanced validation, tiered refund policy and publish event
        
        Cancellation Policy:
        - 100% refund if cancelled 24+ hours before check-in
        - 50% refund if cancelled 6-24 hours before check-in  
        - 0% refund if cancelled less than 6 hours before check-in
        
        Args:
            booking: Booking instance to cancel
            cancelled_by: User who cancelled the booking
            reason: Optional cancellation reason code
            reason_description: Detailed reason for cancellation
            
        Raises:
            ValueError: If booking cannot be cancelled
            
        Returns:
            tuple: (booking, cancellation_record)
        """
        from booking.models_cancellation import BookingCancellation
        from bank.services import BankService
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Validation checks
        if booking.status == 'cancelled':
            raise ValueError("Booking is already cancelled")
        
        if booking.status == 'completed':
            raise ValueError("Cannot cancel a completed booking")
        
        if booking.is_checked_in and not booking.is_checked_out:
            raise ValueError("Cannot cancel an active booking. Please check out first.")
        
        # Check if cancellation record already exists
        if hasattr(booking, 'cancellation_detail'):
            raise ValueError("Cancellation already exists for this booking")
        
        # Calculate hours until check-in
        from django.utils import timezone as tz
        now = tz.now()
        hours_until_checkin = (booking.check_in - now).total_seconds() / 3600
        
        # Determine if admin approval is required
        # Late cancellations (< 6 hours) or after booking started need admin approval
        requires_approval = hours_until_checkin < 6
        
        if hours_until_checkin < 0 and not requires_approval:
            # Block cancellation after check-in unless it goes through admin approval
            raise ValueError("Cannot cancel a booking that has already started. Please contact the workspace admin.")
        
        # Calculate refund based on policy
        original_amount = booking.total_price
        refund_percentage, refund_amount, penalty_amount = BookingCancellation.calculate_refund_policy(
            hours_until_checkin, 
            original_amount
        )
        
        # Determine initial status
        if requires_approval:
            initial_status = 'pending'  # Needs admin approval
            initial_refund_status = 'pending'
        else:
            initial_status = 'approved'  # Auto-approved
            initial_refund_status = 'pending' if refund_amount > 0 else 'completed'
        
        # Create cancellation record
        cancellation = BookingCancellation.objects.create(
            booking=booking,
            cancelled_by=cancelled_by,
            reason=reason or 'user_request',
            reason_description=reason_description or f"Booking cancelled {hours_until_checkin:.1f} hours before check-in",
            status=initial_status,
            original_amount=original_amount,
            refund_percentage=refund_percentage,
            refund_amount=refund_amount,
            penalty_amount=penalty_amount,
            hours_until_checkin=Decimal(str(hours_until_checkin)),
            refund_status=initial_refund_status,
            approved_at=now if not requires_approval else None,
            approved_by=None
        )
        
        # Only process cancellation immediately if auto-approved
        if not requires_approval:
            # Auto-approved - process immediately
            booking.status = 'cancelled'
            booking.cancelled_at = now
            booking.save(update_fields=['status', 'cancelled_at', 'updated_at'])
            
            # Process refund if eligible
            if refund_amount > Decimal('0'):
                try:
                    # Smart refund: handles both pending and completed payments
                    user_wallet, refund_txn, refund_reference = BankService.process_booking_refund(
                        booking=booking,
                        refund_amount=refund_amount,
                        description=f"Refund for cancelled booking (Check-in: {booking.check_in.strftime('%Y-%m-%d %H:%M')}, Refund: {refund_percentage}%)"
                    )
                    
                    # Update cancellation with refund reference
                    cancellation.refund_reference = refund_reference
                    cancellation.refund_status = 'completed'
                    cancellation.refunded_at = now
                    cancellation.status = 'refunded'
                    cancellation.save()
                    
                    logger.info(f"Auto-approved: Processed {refund_percentage}% refund ({refund_amount}) for booking {booking.id}")
                except Exception as e:
                    logger.error(f"Failed to process refund for booking {booking.id}: {str(e)}", exc_info=True)
                    cancellation.refund_status = 'failed'
                    cancellation.admin_notes = f"Refund processing failed: {str(e)}"
                    cancellation.save()
                    raise ValueError(f"Cancellation recorded but refund failed: {str(e)}")
            else:
                # No refund (cancelled too late)
                cancellation.status = 'approved'
                cancellation.refund_status = 'completed'
                cancellation.save()
        else:
            # Requires admin approval - don't cancel booking yet
            logger.info(f"Late cancellation for booking {booking.id} - requires admin approval ({hours_until_checkin:.1f} hours until check-in)")
            # Don't change booking status yet - wait for admin
        
        # Publish booking cancelled event
        event = Event(
            event_type=EventTypes.BOOKING_CANCELLED,
            data={
                'booking_id': str(booking.id),
                'workspace_id': str(booking.workspace.id),
                'workspace_name': booking.workspace.name,
                'space_id': str(booking.space.id),
                'space_name': booking.space.name,
                'user_id': str(booking.user.id),
                'user_email': booking.user.email,
                'user_name': booking.user.full_name or booking.user.email,
                'cancelled_by': str(cancelled_by.id) if cancelled_by else None,
                'cancellation_id': str(cancellation.id),
                'reason': reason,
                'reason_description': reason_description,
                'hours_until_checkin': hours_until_checkin,
                'requires_approval': requires_approval,
                'original_amount': str(original_amount),
                'refund_percentage': str(refund_percentage),
                'refund_amount': str(refund_amount),
                'penalty_amount': str(penalty_amount),
                'cancellation_status': cancellation.status,
                'refund_status': cancellation.refund_status,
                'refund_reference': cancellation.refund_reference if not requires_approval else None,
                'auto_approved': not requires_approval,
                'timestamp': now.isoformat()
            },
            source_module='booking'
        )
        EventBus.publish(event)
        
        # Invalidate caches
        CacheService.delete_pattern(f'booking:{booking.id}:*')
        CacheService.delete_pattern(f'bookings:user:{booking.user.id}:*')
        CacheService.delete_pattern(f'bookings:workspace:{booking.workspace.id}:*')
        CacheService.delete_pattern(f'upcoming-bookings:user:{booking.user.id}')
        CacheService.delete_pattern(f'dashboard:user:{booking.user.id}')
        
        return booking, cancellation
    
    @staticmethod
    @transaction.atomic
    def approve_cancellation(cancellation, approved_by, custom_refund_amount=None, admin_notes=""):
        """
        Approve a pending cancellation request
        
        Args:
            cancellation: BookingCancellation instance
            approved_by: Admin user who is approving
            custom_refund_amount: Optional custom refund amount (can be more generous than policy)
            admin_notes: Optional admin notes
            
        Returns:
            tuple: (booking, cancellation)
        """
        from bank.services import BankService
        import logging
        logger = logging.getLogger(__name__)
        
        if cancellation.status != 'pending':
            raise ValueError(f"Cannot approve cancellation with status: {cancellation.status}")
        
        booking = cancellation.booking
        now = timezone.now()
        
        # Use custom refund if provided, otherwise use calculated amount
        refund_amount = custom_refund_amount if custom_refund_amount is not None else cancellation.refund_amount
        
        # Update cancellation
        cancellation.status = 'approved'
        cancellation.approved_by = approved_by
        cancellation.approved_at = now
        cancellation.admin_notes = admin_notes
        
        # If custom refund, update the amount
        if custom_refund_amount is not None:
            cancellation.refund_amount = custom_refund_amount
            cancellation.refund_percentage = (custom_refund_amount / cancellation.original_amount) * 100
            cancellation.penalty_amount = cancellation.original_amount - custom_refund_amount
        
        cancellation.save()
        
        # Cancel the booking
        booking.status = 'cancelled'
        booking.cancelled_at = now
        booking.save(update_fields=['status', 'cancelled_at', 'updated_at'])
        
        # Process refund if applicable
        if refund_amount > Decimal('0'):
            try:
                user_wallet, refund_txn, refund_reference = BankService.process_booking_refund(
                    booking=booking,
                    refund_amount=refund_amount,
                    description=f"Admin-approved refund for cancelled booking (Approved by: {approved_by.full_name or approved_by.email})"
                )
                
                cancellation.refund_reference = refund_reference
                cancellation.refund_status = 'completed'
                cancellation.refunded_at = now
                cancellation.status = 'refunded'
                cancellation.save()
                
                logger.info(f"Admin approved cancellation for booking {booking.id} - Refund: {refund_amount}")
            except Exception as e:
                logger.error(f"Failed to process admin-approved refund: {str(e)}", exc_info=True)
                cancellation.refund_status = 'failed'
                cancellation.save()
                raise
        else:
            cancellation.refund_status = 'completed'
            cancellation.status = 'approved'
            cancellation.save()
        
        # Publish event
        event = Event(
            event_type='CANCELLATION_APPROVED',
            data={
                'cancellation_id': str(cancellation.id),
                'booking_id': str(booking.id),
                'workspace_id': str(booking.workspace.id),
                'user_id': str(booking.user.id),
                'user_email': booking.user.email,
                'approved_by': str(approved_by.id),
                'approved_by_email': approved_by.email,
                'refund_amount': str(refund_amount),
                'admin_notes': admin_notes,
                'timestamp': now.isoformat()
            },
            source_module='booking'
        )
        EventBus.publish(event)
        
        # Invalidate caches
        CacheService.delete_pattern(f'booking:{booking.id}:*')
        CacheService.delete_pattern(f'bookings:user:{booking.user.id}:*')
        
        return booking, cancellation
    
    @staticmethod
    @transaction.atomic
    def reject_cancellation(cancellation, rejected_by, rejection_reason=""):
        """
        Reject a pending cancellation request
        
        Args:
            cancellation: BookingCancellation instance
            rejected_by: Admin user who is rejecting
            rejection_reason: Reason for rejection
            
        Returns:
            cancellation
        """
        if cancellation.status != 'pending':
            raise ValueError(f"Cannot reject cancellation with status: {cancellation.status}")
        
        now = timezone.now()
        
        # Update cancellation
        cancellation.status = 'rejected'
        cancellation.approved_by = rejected_by
        cancellation.approved_at = now
        cancellation.admin_notes = rejection_reason
        cancellation.refund_status = 'completed'  # No refund
        cancellation.save()
        
        # Publish event
        event = Event(
            event_type='CANCELLATION_REJECTED',
            data={
                'cancellation_id': str(cancellation.id),
                'booking_id': str(cancellation.booking.id),
                'workspace_id': str(cancellation.booking.workspace.id),
                'user_id': str(cancellation.booking.user.id),
                'user_email': cancellation.booking.user.email,
                'rejected_by': str(rejected_by.id),
                'rejected_by_email': rejected_by.email,
                'rejection_reason': rejection_reason,
                'timestamp': now.isoformat()
            },
            source_module='booking'
        )
        EventBus.publish(event)
        
        return cancellation
    
    @staticmethod
    @transaction.atomic
    def check_in_booking(booking, checked_in_by=None):
        """
        Check in a booking with validation and publish event
        
        Args:
            booking: Booking instance to check in
            checked_in_by: User who performed the check-in
            
        Raises:
            ValueError: If booking cannot be checked in
        """
        # Validation checks
        if booking.is_checked_in:
            raise ValueError("Booking is already checked in")
        
        if booking.status != 'confirmed':
            raise ValueError("Booking must be confirmed before check-in")
        
        if booking.status == 'cancelled':
            raise ValueError("Cannot check in to a cancelled booking")
        
        # Update booking
        booking.is_checked_in = True
        booking.status = 'active'
        booking.save(update_fields=['is_checked_in', 'status', 'updated_at'])
        
        # Release pending payment to workspace wallet
        from bank.services import BankService
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            released_transaction = BankService.release_pending_payment(booking)
            if released_transaction:
                logger.info(f"Released pending payment {released_transaction.reference} for booking {booking.id}")
            else:
                logger.warning(f"No pending payment found to release for booking {booking.id}")
        except Exception as e:
            logger.error(f"Failed to release pending payment for booking {booking.id}: {str(e)}", exc_info=True)
            # Don't block check-in if payment release fails
        
        # Publish booking check-in event
        event = Event(
            event_type=EventTypes.BOOKING_CHECKED_IN,
            data={
                'booking_id': str(booking.id),
                'workspace_id': str(booking.workspace.id),
                'workspace_name': booking.workspace.name,
                'space_id': str(booking.space.id),
                'space_name': booking.space.name,
                'user_id': str(booking.user.id),
                'user_email': booking.user.email,
                'user_name': booking.user.full_name or booking.user.email,
                'timestamp': timezone.now().isoformat()
            },
            source_module='booking'
        )
        EventBus.publish(event)
        
        # Invalidate caches
        CacheService.delete_pattern(f'booking:{booking.id}:*')
        
        return booking
    
    @staticmethod
    @transaction.atomic
    def check_out_booking(booking, checked_out_by=None):
        """
        Check out a booking with validation and publish event
        
        Args:
            booking: Booking instance to check out
            checked_out_by: User who performed the check-out
            
        Raises:
            ValueError: If booking cannot be checked out
        """
        # Validation checks
        if not booking.is_checked_in:
            raise ValueError("Must check in before checking out")
        
        if booking.is_checked_out:
            raise ValueError("Booking is already checked out")
        
        if booking.status == 'cancelled':
            raise ValueError("Cannot check out from a cancelled booking")
        
        # Update booking
        booking.is_checked_out = True
        booking.status = 'completed'
        booking.save(update_fields=['is_checked_out', 'status', 'updated_at'])
        
        # Publish booking check-out event
        event = Event(
            event_type=EventTypes.BOOKING_CHECKED_OUT,
            data={
                'booking_id': str(booking.id),
                'workspace_id': str(booking.workspace.id),
                'workspace_name': booking.workspace.name,
                'space_id': str(booking.space.id),
                'space_name': booking.space.name,
                'user_id': str(booking.user.id),
                'user_email': booking.user.email,
                'user_name': booking.user.full_name or booking.user.email,
                'timestamp': timezone.now().isoformat()
            },
            source_module='booking'
        )
        EventBus.publish(event)
        
        # Invalidate caches
        CacheService.delete_pattern(f'booking:{booking.id}:*')
        
        return booking
    
    @staticmethod
    @transaction.atomic
    def complete_booking(booking):
        """Mark a booking as completed and publish event"""
        booking.status = 'completed'
        booking.save(update_fields=['status', 'updated_at'])
        
        # Publish booking completed event
        event = Event(
            event_type=EventTypes.BOOKING_COMPLETED,
            data={
                'booking_id': str(booking.id),
                'workspace_id': str(booking.workspace.id),
                'workspace_name': booking.workspace.name,
                'space_id': str(booking.space.id),
                'space_name': booking.space.name,
                'user_id': str(booking.user.id),
                'user_email': booking.user.email,
                'user_name': booking.user.full_name or booking.user.email,
                'timestamp': timezone.now().isoformat()
            },
            source_module='booking'
        )
        EventBus.publish(event)
        
        # Invalidate caches
        CacheService.delete_pattern(f'booking:{booking.id}:*')
        
        return booking
    
    @staticmethod
    @transaction.atomic
    def create_reservation(space, user, start_datetime, end_datetime, expiry_minutes=15, slots=None):
        """
        Create a temporary reservation for a space slot
        
        Args:
            space: Space instance
            user: User instance
            start_datetime: Reservation start datetime
            end_datetime: Reservation end datetime
            expiry_minutes: Minutes until reservation expires (default: 15)
            slots: List of SpaceCalendarSlot objects to mark as reserved (optional)
            
        Returns:
            Reservation instance
            
        Raises:
            ValueError: If space is already reserved for the time slot
        """
        now = timezone.now()
        
        # First, clean up ALL expired reservations globally and reset their slots
        from workspace.models import SpaceCalendarSlot
        expired_reservations = Reservation.objects.filter(
            status='active',
            expires_at__lt=now
        )
        expired_count = expired_reservations.count()
        
        if expired_count > 0:
            # Reset slots from expired reservations back to available
            SpaceCalendarSlot.objects.filter(
                status='reserved'
            ).exclude(
                # Keep slots that have active non-expired reservations
                calendar__space__reservations__status='active',
                calendar__space__reservations__expires_at__gte=now
            ).update(status='available')
            
            expired_reservations.update(status='expired')
            logger.info(f"Cleaned up {expired_count} expired reservations and reset their slots")
        
        # Check for overlapping active (non-expired) reservations
        overlapping = Reservation.objects.filter(
            space=space,
            status='active',
            expires_at__gte=now,
            start__lt=end_datetime,
            end__gt=start_datetime
        ).exists()
        
        if overlapping:
            raise ValueError("Space is already reserved for this time slot")
        
        # Check for overlapping confirmed bookings
        overlapping_bookings = Booking.objects.filter(
            space=space,
            status__in=['confirmed', 'active'],
            check_in__lt=end_datetime,
            check_out__gt=start_datetime
        ).exists()
        
        if overlapping_bookings:
            raise ValueError("Space is already booked for this time slot")
        
        # Create reservation with expiry time
        expires_at = now + timedelta(minutes=expiry_minutes)
        
        reservation = Reservation.objects.create(
            space=space,
            user=user,
            start=start_datetime,
            end=end_datetime,
            status='active',
            expires_at=expires_at
        )
        
        # Mark slots as reserved
        if slots:
            from workspace.models import SpaceCalendarSlot
            slot_ids = [slot.id for slot in slots]
            SpaceCalendarSlot.objects.filter(id__in=slot_ids).update(status='reserved')
            logger.info(f"Marked {len(slot_ids)} slots as reserved for reservation {reservation.id}")
        
        # Publish reservation created event
        event = Event(
            event_type='RESERVATION_CREATED',
            data={
                'reservation_id': str(reservation.id),
                'space_id': str(space.id),
                'space_name': space.name,
                'user_id': str(user.id),
                'user_email': user.email,
                'start': start_datetime.isoformat(),
                'end': end_datetime.isoformat(),
                'expires_at': expires_at.isoformat(),
                'expires_in_minutes': expiry_minutes,
                'timestamp': now.isoformat()
            },
            source_module='booking'
        )
        EventBus.publish(event)
        
        return reservation
    
    @staticmethod
    @transaction.atomic
    def confirm_reservation(reservation):
        """
        Confirm a reservation (usually when payment is completed)
        
        Args:
            reservation: Reservation instance
        """
        if reservation.status != 'active':
            raise ValueError(f"Cannot confirm reservation with status: {reservation.status}")
        
        reservation.status = 'confirmed'
        reservation.save(update_fields=['status', 'updated_at'])
        
        # Mark slots as booked (payment completed)
        from workspace.models import SpaceCalendarSlot
        SpaceCalendarSlot.objects.filter(
            calendar__space=reservation.space,
            date__gte=reservation.start.date(),
            date__lte=reservation.end.date(),
            status='reserved'
        ).update(status='booked')
        logger.info(f"Marked slots as booked for confirmed reservation {reservation.id}")
        
        # Publish reservation confirmed event
        event = Event(
            event_type='RESERVATION_CONFIRMED',
            data={
                'reservation_id': str(reservation.id),
                'space_id': str(reservation.space.id),
                'space_name': reservation.space.name,
                'user_id': str(reservation.user.id),
                'user_email': reservation.user.email,
                'timestamp': timezone.now().isoformat()
            },
            source_module='booking'
        )
        EventBus.publish(event)
        
        return reservation
    
    @staticmethod
    @transaction.atomic
    def cancel_reservation(reservation):
        """
        Cancel a reservation
        
        Args:
            reservation: Reservation instance
        """
        if reservation.status == 'confirmed':
            raise ValueError("Cannot cancel confirmed reservation")
        
        reservation.status = 'cancelled'
        reservation.save(update_fields=['status', 'updated_at'])
        
        # Reset slots back to available
        from workspace.models import SpaceCalendarSlot
        SpaceCalendarSlot.objects.filter(
            calendar__space=reservation.space,
            date__gte=reservation.start.date(),
            date__lte=reservation.end.date(),
            status='reserved'
        ).update(status='available')
        logger.info(f"Reset slots to available for cancelled reservation {reservation.id}")
        
        # Remove associated cart items
        CartItem.objects.filter(reservation=reservation).delete()
        
        # Publish reservation cancelled event
        event = Event(
            event_type='RESERVATION_CANCELLED',
            data={
                'reservation_id': str(reservation.id),
                'space_id': str(reservation.space.id),
                'user_id': str(reservation.user.id),
                'timestamp': timezone.now().isoformat()
            },
            source_module='booking'
        )
        EventBus.publish(event)
        
        return reservation


__all__ = ['BookingService']
