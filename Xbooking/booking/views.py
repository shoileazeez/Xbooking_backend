"""
Booking and Cart API Views
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from decimal import Decimal

from booking.models import Booking, Cart, CartItem, BookingReview
from booking.serializers import (
    CartSerializer, CartItemSerializer, AddToCartSerializer,
    BookingSerializer, CreateBookingSerializer, BookingListSerializer,
    BookingDetailSerializer, CancelBookingSerializer, BookingReviewSerializer,
    CreateReviewSerializer, CheckoutSerializer
)
from workspace.models import Space, Workspace
from workspace.permissions import check_workspace_member


class CartView(APIView):
    """Get user's shopping cart"""
    permission_classes = [IsAuthenticated]
    serializer_class = CartSerializer

    @extend_schema(
        responses={200: CartSerializer},
        description="Get current user's shopping cart"
    )
    def get(self, request):
        """Get cart for user"""
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        serializer = CartSerializer(cart)
        return Response({
            'success': True,
            'cart': serializer.data
        }, status=status.HTTP_200_OK)


class AddToCartView(APIView):
    """Add item to cart"""
    permission_classes = [IsAuthenticated]
    serializer_class = AddToCartSerializer

    @extend_schema(
        request=AddToCartSerializer,
        responses={201: CartItemSerializer},
        description="Add space booking to cart"
    )
    def post(self, request):
        """Add item to cart"""
        serializer = AddToCartSerializer(data=request.data)
        if serializer.is_valid():
            try:
                space = Space.objects.get(id=serializer.validated_data['space_id'])
                
                # Check if space is available
                if not space.is_available:
                    return Response({
                        'success': False,
                        'message': 'This space is not available'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Get or create cart
                cart, _ = Cart.objects.get_or_create(user=request.user)
                
                # Calculate price based on booking duration
                check_in = serializer.validated_data['check_in']
                check_out = serializer.validated_data['check_out']
                hours = (check_out - check_in).total_seconds() / 3600
                
                # Use hourly rate for calculation
                price = Decimal(str(space.price_per_hour)) * Decimal(str(hours))
                
                # Create cart item
                cart_item, created = CartItem.objects.update_or_create(
                    cart=cart,
                    space=space,
                    check_in=check_in,
                    check_out=check_out,
                    defaults={
                        'number_of_guests': serializer.validated_data.get('number_of_guests', 1),
                        'price': price,
                        'special_requests': serializer.validated_data.get('special_requests', '')
                    }
                )
                
                # Recalculate cart totals
                cart.calculate_totals()
                
                cart_item_serializer = CartItemSerializer(cart_item)
                return Response({
                    'success': True,
                    'message': 'Item added to cart',
                    'item': cart_item_serializer.data
                }, status=status.HTTP_201_CREATED)
                
            except Space.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Space not found'
                }, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            'success': False,
            'message': 'Invalid data',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class RemoveFromCartView(APIView):
    """Remove an item from cart"""
    permission_classes = [IsAuthenticated]
    serializer_class = None

    @extend_schema(
        description="Remove item from cart"
    )
    def delete(self, request, item_id):
        """Remove item from cart"""
        cart = get_object_or_404(Cart, user=request.user)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
        
        cart_item.delete()
        cart.calculate_totals()
        
        return Response({
            'success': True,
            'message': 'Item removed from cart'
        }, status=status.HTTP_200_OK)


class ClearCartView(APIView):
    """Clear all items from cart"""
    permission_classes = [IsAuthenticated]
    serializer_class = None

    @extend_schema(
        description="Clear all items from shopping cart"
    )
    def post(self, request):
        """Clear cart"""
        cart = get_object_or_404(Cart, user=request.user)
        cart.items.all().delete()
        cart.calculate_totals()
        
        return Response({
            'success': True,
            'message': 'Cart cleared'
        }, status=status.HTTP_200_OK)


class CheckoutView(APIView):
    """Checkout cart and create bookings"""
    permission_classes = [IsAuthenticated]
    serializer_class = CheckoutSerializer

    @extend_schema(
        request=CheckoutSerializer,
        description="Checkout cart items and create bookings"
    )
    def post(self, request):
        """Create bookings from cart"""
        cart = get_object_or_404(Cart, user=request.user)
        
        if not cart.items.exists():
            return Response({
                'success': False,
                'message': 'Cart is empty'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create bookings from cart items
        bookings = []
        for item in cart.items.all():
            # Check if space is still available
            if not item.space.is_available:
                continue
                
            booking = Booking.objects.create(
                workspace=item.space.branch.workspace,
                space=item.space,
                user=request.user,
                check_in=item.check_in,
                check_out=item.check_out,
                number_of_guests=item.number_of_guests,
                base_price=item.price,
                tax_amount=item.tax_amount,
                discount_amount=item.discount_amount,
                total_price=item.price - item.discount_amount + item.tax_amount,
                special_requests=item.special_requests,
                status='pending'
            )
            bookings.append(booking)
        
        if not bookings:
             return Response({
                'success': False,
                'message': 'No bookings could be created (spaces might be unavailable)'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Clear cart
        cart.items.all().delete()
        cart.calculate_totals()
        
        serializer = BookingSerializer(bookings, many=True)
        return Response({
            'success': True,
            'message': f'{len(bookings)} booking(s) created',
            'bookings': serializer.data
        }, status=status.HTTP_201_CREATED)


class CreateBookingView(APIView):
    """Create booking directly without cart"""
    permission_classes = [IsAuthenticated]
    serializer_class = CreateBookingSerializer

    @extend_schema(
        request=CreateBookingSerializer,
        responses={201: BookingSerializer},
        description="Create booking directly for a space"
    )
    def post(self, request):
        """Create booking"""
        serializer = CreateBookingSerializer(data=request.data)
        if serializer.is_valid():
            try:
                space = Space.objects.get(id=serializer.validated_data['space_id'])
                workspace = space.branch.workspace
                
                if not space.is_available:
                    return Response({
                        'success': False,
                        'message': 'This space is not available'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Calculate price
                check_in = serializer.validated_data['check_in']
                check_out = serializer.validated_data['check_out']
                hours = (check_out - check_in).total_seconds() / 3600
                base_price = Decimal(str(space.price_per_hour)) * Decimal(str(hours))
                
                booking = Booking.objects.create(
                    workspace=workspace,
                    space=space,
                    user=request.user,
                    booking_type=serializer.validated_data['booking_type'],
                    check_in=check_in,
                    check_out=check_out,
                    number_of_guests=serializer.validated_data['number_of_guests'],
                    base_price=base_price,
                    tax_amount=Decimal('0'),
                    discount_amount=Decimal('0'),
                    total_price=base_price,
                    special_requests=serializer.validated_data.get('special_requests', ''),
                    status='pending'
                )
                
                booking_serializer = BookingSerializer(booking)
                return Response({
                    'success': True,
                    'message': 'Booking created successfully',
                    'booking': booking_serializer.data
                }, status=status.HTTP_201_CREATED)
                
            except Space.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Space not found'
                }, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            'success': False,
            'message': 'Invalid data',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class ListBookingsView(APIView):
    """List user's bookings"""
    permission_classes = [IsAuthenticated]
    serializer_class = BookingListSerializer

    @extend_schema(
        responses={200: BookingListSerializer(many=True)},
        description="Get all user bookings"
    )
    def get(self, request):
        """Get user bookings"""
        bookings = Booking.objects.filter(
            user=request.user
        ).order_by('-created_at')
        
        # Pagination
        from rest_framework.pagination import PageNumberPagination
        paginator = PageNumberPagination()
        paginator.page_size = 20
        paginated_bookings = paginator.paginate_queryset(bookings, request)
        
        serializer = BookingListSerializer(paginated_bookings, many=True)
        return paginator.get_paginated_response(serializer.data)



class BookingDetailView(APIView):
    """Get booking details"""
    permission_classes = [IsAuthenticated]
    serializer_class = BookingDetailSerializer

    @extend_schema(
        responses={200: BookingDetailSerializer},
        description="Get detailed booking information"
    )
    def get(self, request, booking_id):
        """Get booking details"""
        booking = get_object_or_404(Booking, id=booking_id)
        
        if booking.user != request.user:
            return Response({
                'success': False,
                'message': 'You can only view your own bookings'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = BookingDetailSerializer(booking)
        return Response({
            'success': True,
            'booking': serializer.data
        }, status=status.HTTP_200_OK)


class CancelBookingView(APIView):
    """Cancel a booking"""
    permission_classes = [IsAuthenticated]
    serializer_class = CancelBookingSerializer

    @extend_schema(
        request=CancelBookingSerializer,
        description="Cancel a booking"
    )
    def post(self, request, booking_id):
        """Cancel booking"""
        booking = get_object_or_404(Booking, id=booking_id)
        
        if booking.user != request.user:
            return Response({
                'success': False,
                'message': 'You can only cancel your own bookings'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if booking.status in ['completed', 'cancelled']:
            return Response({
                'success': False,
                'message': f'Cannot cancel booking with status {booking.status}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        booking.status = 'cancelled'
        booking.cancelled_at = timezone.now()
        booking.save()
        
        serializer = BookingDetailSerializer(booking)
        return Response({
            'success': True,
            'message': 'Booking cancelled successfully',
            'booking': serializer.data
        }, status=status.HTTP_200_OK)


class ReviewBookingView(APIView):
    """Add review to booking"""
    permission_classes = [IsAuthenticated]
    serializer_class = CreateReviewSerializer

    @extend_schema(
        request=CreateReviewSerializer,
        responses={201: BookingReviewSerializer},
        description="Add review for completed booking"
    )
    def post(self, request, booking_id):
        """Add review"""
        booking = get_object_or_404(Booking, id=booking_id)
        
        if booking.user != request.user:
            return Response({
                'success': False,
                'message': 'You can only review your own bookings'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if booking.status != 'completed':
            return Response({
                'success': False,
                'message': 'Can only review completed bookings'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if BookingReview.objects.filter(booking=booking).exists():
            return Response({
                'success': False,
                'message': 'This booking already has a review'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = CreateReviewSerializer(data=request.data)
        if serializer.is_valid():
            review = BookingReview.objects.create(
                booking=booking,
                user=request.user,
                space=booking.space,
                rating=serializer.validated_data['rating'],
                comment=serializer.validated_data.get('comment', '')
            )
            
            review_serializer = BookingReviewSerializer(review)
            return Response({
                'success': True,
                'message': 'Review added successfully',
                'review': review_serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'message': 'Invalid data',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
