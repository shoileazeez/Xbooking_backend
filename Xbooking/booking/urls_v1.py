"""
Booking V1 URL Configuration
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter


from booking.views.v1 import (
    BookingViewSet,
    CartViewSet,
    BookingReviewViewSet,
    AdminBookingViewSet,
    GuestViewSet,
    BookingCancellationViewSet,
)

app_name = 'booking_v1'


router = DefaultRouter()
router.register(r'bookings', BookingViewSet, basename='booking')
router.register(r'cart', CartViewSet, basename='cart')
router.register(r'reviews', BookingReviewViewSet, basename='review')
router.register(r'guests', GuestViewSet, basename='guest')
router.register(r'cancellations', BookingCancellationViewSet, basename='cancellation')

# Admin routes with workspace context
admin_router = DefaultRouter()
admin_router.register(r'bookings', AdminBookingViewSet, basename='admin-booking')

urlpatterns = [
    path('', include(router.urls)),
    # Admin routes under workspaces/<workspace_id>/admin/
    path('workspaces/<uuid:workspace_id>/admin/', include(admin_router.urls)),
]
