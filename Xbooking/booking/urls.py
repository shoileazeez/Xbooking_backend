from django.urls import path
from booking.views import (
    CartView, AddToCartView, RemoveFromCartView, ClearCartView,
    CheckoutView, CreateBookingView, ListBookingsView, BookingDetailView,
    CancelBookingView, ReviewBookingView
)
from booking.admin_views import (
    AdminListBookingsView, AdminBookingDetailView, AdminUpdateBookingStatusView,
    AdminBookingsByStatusView, AdminBookingsBySpaceView, AdminBookingReviewsView,
    AdminBookingStatisticsView
)

app_name = 'booking'

urlpatterns = [
    # Cart URLs
    path('workspaces/<uuid:workspace_id>/cart/', CartView.as_view(), name='cart'),
    path('workspaces/<uuid:workspace_id>/cart/add/', AddToCartView.as_view(), name='add_to_cart'),
    path('workspaces/<uuid:workspace_id>/cart/items/<uuid:item_id>/', RemoveFromCartView.as_view(), name='remove_from_cart'),
    path('workspaces/<uuid:workspace_id>/cart/clear/', ClearCartView.as_view(), name='clear_cart'),
    path('workspaces/<uuid:workspace_id>/cart/checkout/', CheckoutView.as_view(), name='checkout'),
    
    # Booking URLs (User)
    path('workspaces/<uuid:workspace_id>/bookings/create/', CreateBookingView.as_view(), name='create_booking'),
    path('workspaces/<uuid:workspace_id>/bookings/', ListBookingsView.as_view(), name='list_bookings'),
    path('workspaces/<uuid:workspace_id>/bookings/<uuid:booking_id>/', BookingDetailView.as_view(), name='booking_detail'),
    path('workspaces/<uuid:workspace_id>/bookings/<uuid:booking_id>/cancel/', CancelBookingView.as_view(), name='cancel_booking'),
    path('workspaces/<uuid:workspace_id>/bookings/<uuid:booking_id>/review/', ReviewBookingView.as_view(), name='review_booking'),
    
    # Admin Booking Management URLs
    path('workspaces/<uuid:workspace_id>/admin/bookings/', AdminListBookingsView.as_view(), name='admin_list_bookings'),
    path('workspaces/<uuid:workspace_id>/admin/bookings/<uuid:booking_id>/', AdminBookingDetailView.as_view(), name='admin_booking_detail'),
    path('workspaces/<uuid:workspace_id>/admin/bookings/<uuid:booking_id>/status/', AdminUpdateBookingStatusView.as_view(), name='admin_update_status'),
    path('workspaces/<uuid:workspace_id>/admin/bookings/filter/status/', AdminBookingsByStatusView.as_view(), name='admin_bookings_by_status'),
    path('workspaces/<uuid:workspace_id>/admin/spaces/<uuid:space_id>/bookings/', AdminBookingsBySpaceView.as_view(), name='admin_space_bookings'),
    path('workspaces/<uuid:workspace_id>/admin/bookings/<uuid:booking_id>/reviews/', AdminBookingReviewsView.as_view(), name='admin_booking_reviews'),
    path('workspaces/<uuid:workspace_id>/admin/bookings/statistics/', AdminBookingStatisticsView.as_view(), name='admin_booking_stats'),
]
