"""
Cart Views V1
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, extend_schema_view
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, timedelta

from core.views import CachedModelViewSet
from core.responses import SuccessResponse, ErrorResponse
from core.pagination import StandardResultsSetPagination
from booking.models import Cart, CartItem, Space
from booking.serializers.v1 import (
    CartSerializer,
    CartItemSerializer,
    AddToCartSerializer,
    RemoveFromCartSerializer,
    CheckoutSerializer
)


@extend_schema_view(
    list=extend_schema(description="Get user cart"),
    create=extend_schema(description="Add item to cart"),
)
class CartViewSet(CachedModelViewSet):
    """ViewSet for managing shopping cart"""
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    cache_timeout = 300  # 5 minutes
    http_method_names = ['get', 'post', 'delete']
    
    def get_queryset(self):
        user = self.request.user
        return Cart.objects.filter(user=user).prefetch_related('items__space')
    
    def list(self, request):
        """Get user's cart"""
        cart, created = Cart.objects.get_or_create(user=request.user)
        serializer = self.get_serializer(cart)
        return SuccessResponse(
            message='Cart retrieved successfully',
            data=serializer.data
        )
    
    def create(self, request):
        """Redirect POST to add_item action for backward compatibility"""
        return self.add_item(request)
    
    @extend_schema(request=AddToCartSerializer)
    @action(detail=False, methods=['post'])
    def add_item(self, request):
        """Add item to cart"""
        serializer = AddToCartSerializer(data=request.data)
        
        if not serializer.is_valid():
            return ErrorResponse(
                message='Invalid cart item data',
                errors=serializer.errors,
                status_code=400
            )
        
        data = serializer.validated_data
        
        # Get or create cart
        cart, _ = Cart.objects.get_or_create(user=request.user)
        
        # Get space
        try:
            space = Space.objects.get(id=data['space_id'])
        except Space.DoesNotExist:
            return ErrorResponse(
                message='Space not found',
                status_code=404
            )
        
        # Validate guests based on space type
        space_type = space.space_type.lower()
        number_of_guests = data.get('number_of_guests', 0)
        if space_type == 'office' and number_of_guests == 0:
            return ErrorResponse(
                message='At least 1 guest is required for private office spaces',
                status_code=400
            )
        elif space_type != 'office' and number_of_guests > 0:
            return ErrorResponse(
                message='Guests are only allowed for private office spaces',
                status_code=400
            )
        
        # Calculate check-in/out times
        if data.get('slot_id'):
            # TODO: Implement slot-based booking
            return ErrorResponse(
                message='Slot-based booking not yet implemented',
                status_code=400
            )
        else:
            booking_date = data['booking_date']
            start_time = data['start_time']
            end_time = data['end_time']
            # Make timezone-aware datetimes
            from django.utils import timezone as tz
            check_in = tz.make_aware(datetime.combine(booking_date, start_time))
            check_out = tz.make_aware(datetime.combine(booking_date, end_time))
        
        # Calculate price based on booking type
        booking_type = data['booking_type']
        if booking_type == 'hourly':
            hours = (check_out - check_in).total_seconds() / 3600
            price = space.price_per_hour * Decimal(str(hours))
        elif booking_type == 'daily':
            price = space.daily_rate
        elif booking_type == 'monthly':
            price = space.monthly_rate
        else:
            price = space.daily_rate
        
        # Find available slots for this time range to mark as reserved
        from workspace.models import SpaceCalendarSlot
        slots = SpaceCalendarSlot.objects.filter(
            calendar__space=space,
            date=booking_date
        ).exclude(
            status__in=['booked', 'reserved', 'blocked', 'maintenance']
        )
        
        if booking_type == 'hourly':
            slots = slots.filter(
                start_time__gte=start_time,
                end_time__lte=end_time
            )
        
        if not slots.exists():
            return ErrorResponse(
                message=f'No available slots found for {space.name}',
                status_code=400
            )
        
        # Get the slot objects for marking as reserved
        slot_objects = list(slots)
        
        # Create reservation and cart item atomically
        from booking.services import BookingService
        
        try:
            # Create reservation using service (handles validation)
            reservation = BookingService.create_reservation(
                space=space,
                user=request.user,
                start_datetime=check_in,
                end_datetime=check_out,
                expiry_minutes=15,
                slots=slot_objects  # Pass slots to mark as reserved
            )
            
            # Create cart item with reservation
            cart_item = CartItem.objects.create(
                cart=cart,
                space=space,
                booking_date=booking_date,
                start_time=start_time,
                end_time=end_time,
                check_in=check_in,
                check_out=check_out,
                booking_type=booking_type,
                number_of_guests=number_of_guests,
                price=price,
                special_requests=data.get('special_requests', ''),
                reservation=reservation
            )
            
            # Recalculate cart totals
            cart.calculate_totals()
            
        except ValueError as e:
            return ErrorResponse(
                message=str(e),
                status_code=409
            )
        
        return SuccessResponse(
            message='Item added to cart',
            data=CartItemSerializer(cart_item).data,
            status_code=201
        )
    
    @action(detail=False, methods=['post'])
    def update_item(self, request):
        """Update cart item (e.g., number of guests)"""
        item_id = request.data.get('item_id')
        if not item_id:
            return ErrorResponse(
                message='item_id is required',
                status_code=400
            )
        
        try:
            cart_item = CartItem.objects.get(
                id=item_id,
                cart__user=request.user
            )
        except CartItem.DoesNotExist:
            return ErrorResponse(
                message='Cart item not found',
                status_code=404
            )
        
        # Update allowed fields
        if 'number_of_guests' in request.data:
            cart_item.number_of_guests = request.data['number_of_guests']
        if 'special_requests' in request.data:
            cart_item.special_requests = request.data['special_requests']
        
        cart_item.save()
        cart_item.cart.calculate_totals()
        
        return SuccessResponse(
            message='Cart item updated',
            data=CartItemSerializer(cart_item).data
        )
    
    @extend_schema(request=RemoveFromCartSerializer)
    @action(detail=False, methods=['post'])
    def remove_item(self, request):
        """Remove item from cart"""
        serializer = RemoveFromCartSerializer(data=request.data)
        
        if not serializer.is_valid():
            return ErrorResponse(
                message='Invalid request',
                errors=serializer.errors,
                status_code=400
            )
        
        cart_item_id = serializer.validated_data['cart_item_id']
        
        try:
            cart_item = CartItem.objects.get(
                id=cart_item_id,
                cart__user=request.user
            )
        except CartItem.DoesNotExist:
            return ErrorResponse(
                message='Cart item not found',
                status_code=404
            )
        
        from booking.services import BookingService
        
        # Cancel the associated reservation if it exists
        if cart_item.reservation:
            try:
                BookingService.cancel_reservation(cart_item.reservation)
            except ValueError:
                # Log but allow cart item removal
                pass
        
        cart = cart_item.cart
        cart_item.delete()
        cart.calculate_totals()
        
        return SuccessResponse(
            message='Item removed from cart',
            data=CartSerializer(cart).data
        )
    
    @action(detail=False, methods=['post'])
    def clear(self, request):
        """Clear all items from cart"""
        from booking.services import BookingService
        
        cart, _ = Cart.objects.get_or_create(user=request.user)
        
        # Cancel all reservations before deleting items
        for cart_item in cart.items.all():
            if cart_item.reservation:
                try:
                    BookingService.cancel_reservation(cart_item.reservation)
                except ValueError:
                    pass
        
        cart.items.all().delete()
        cart.calculate_totals()
        
        return SuccessResponse(
            message='Cart cleared successfully',
            data=CartSerializer(cart).data
        )
    
    @extend_schema(request=CheckoutSerializer)
    @action(detail=False, methods=['post'])
    @transaction.atomic
    def checkout(self, request):
        """Checkout cart and create bookings"""
        serializer = CheckoutSerializer(data=request.data)
        
        if not serializer.is_valid():
            return ErrorResponse(
                message='Invalid checkout data',
                errors=serializer.errors,
                status_code=400
            )
        
        cart, _ = Cart.objects.get_or_create(user=request.user)
        
        if cart.items.count() == 0:
            return ErrorResponse(
                message='Cart is empty',
                status_code=400
            )
        
        # Create bookings from cart items
        from booking.models import Booking
        from booking.services import BookingService
        
        bookings = []
        for item in cart.items.all():
            # Confirm reservation if it exists and is still active
            if item.reservation:
                try:
                    if not item.reservation.is_expired():
                        BookingService.confirm_reservation(item.reservation)
                    else:
                        return ErrorResponse(
                            message=f'Reservation for {item.space.name} has expired',
                            status_code=400
                        )
                except ValueError as e:
                    return ErrorResponse(
                        message=str(e),
                        status_code=400
                    )
            
            booking = Booking.objects.create(
                workspace=item.space.branch.workspace,
                space=item.space,
                user=request.user,
                booking_type=item.booking_type,
                booking_date=item.booking_date,
                start_time=item.start_time,
                end_time=item.end_time,
                check_in=item.check_in,
                check_out=item.check_out,
                number_of_guests=item.number_of_guests,
                base_price=item.price,
                discount_amount=item.discount_amount,
                tax_amount=item.tax_amount,
                total_price=item.price - item.discount_amount + item.tax_amount,
                status='pending',  # Pending until payment
                special_requests=item.special_requests
            )
            
            # Publish booking created event
            from core.services import EventBus, Event, EventTypes
            event = Event(
                event_type=EventTypes.BOOKING_CREATED,
                data={
                    'booking_id': str(booking.id),
                    'user_id': str(request.user.id),
                    'workspace_id': str(booking.workspace.id),
                    'space_id': str(booking.space.id),
                    'booking_type': booking.booking_type,
                    'check_in': booking.check_in.isoformat(),
                    'check_out': booking.check_out.isoformat(),
                },
                source_module='booking'
            )
            EventBus.publish(event)
            bookings.append(booking)
        
        # Create order from bookings
        from payment.services import PaymentService
        try:
            booking_ids = [booking.id for booking in bookings]
            order = PaymentService.create_order(
                booking_ids=booking_ids,
                user=request.user,
                notes=serializer.validated_data.get('notes', '')
            )
            
            # Mark all slots as booked for confirmed bookings
            from workspace.models import SpaceCalendarSlot
            for booking in bookings:
                SpaceCalendarSlot.objects.filter(
                    calendar__space=booking.space,
                    date__gte=booking.check_in.date(),
                    date__lte=booking.check_out.date(),
                    status='reserved'
                ).update(status='booked', booking=booking)
            
        except ValueError as e:
            return ErrorResponse(
                message=f'Failed to create order: {str(e)}',
                status_code=400
            )
        
        # Clear cart
        cart.items.all().delete()
        cart.calculate_totals()
        
        from booking.serializers.v1 import BookingListSerializer
        from payment.serializers.v1 import OrderListSerializer
        return SuccessResponse(
            message='Checkout successful',
            data={
                'bookings': BookingListSerializer(bookings, many=True).data,
                'order': OrderListSerializer(order).data,
                'total_bookings': len(bookings),
                'order_id': str(order.id)
            },
            status_code=201
        )
