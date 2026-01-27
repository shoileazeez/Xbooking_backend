"""
XBOOKING API ENDPOINTS DOCUMENTATION
Complete guide for normal users (booking flow)
Base URL: http://localhost:8000 or https://your-domain.com
"""

API_ENDPOINTS = {
    # ========================================================================
    # 1. USER AUTHENTICATION & PROFILE
    # ========================================================================
    "user_registration": {
        "url": "/api/v1/user/auth/register/",
        "method": "POST",
        "description": "Register a new user account",
        "authentication": "None",
        "request_body": {
            "email": "user@example.com",
            "password": "SecurePass123!",
            "full_name": "John Doe",
            "phone": "+2348012345678"
        },
        "response_201": {
            "user": {
                "id": "uuid",
                "email": "user@example.com",
                "full_name": "John Doe",
                "phone": "+2348012345678",
                "role": "user"
            },
            "tokens": {
                "access": "jwt_access_token",
                "refresh": "jwt_refresh_token"
            }
        }
    },
    
    "user_login": {
        "url": "/api/v1/user/auth/login/",
        "method": "POST",
        "description": "Login and get JWT tokens",
        "authentication": "None",
        "request_body": {
            "email": "user@example.com",
            "password": "SecurePass123!"
        },
        "response_200": {
            "user": {
                "id": "uuid",
                "email": "user@example.com",
                "full_name": "John Doe"
            },
            "tokens": {
                "access": "jwt_access_token",
                "refresh": "jwt_refresh_token"
            }
        }
    },
    
    "token_refresh": {
        "url": "/api/v1/user/auth/token/refresh/",
        "method": "POST",
        "description": "Refresh access token using refresh token",
        "authentication": "None",
        "request_body": {
            "refresh": "jwt_refresh_token"
        },
        "response_200": {
            "access": "new_jwt_access_token"
        }
    },
    
    "user_profile": {
        "url": "/api/v1/user/profile/",
        "method": "GET",
        "description": "Get current user profile",
        "authentication": "Bearer Token",
        "response_200": {
            "id": "uuid",
            "email": "user@example.com",
            "full_name": "John Doe",
            "phone": "+2348012345678",
            "avatar_url": "https://...",
            "role": "user",
            "is_active": True,
            "created_at": "2026-01-01T00:00:00Z"
        }
    },
    
    "update_profile": {
        "url": "/api/v1/user/profile/",
        "method": "PATCH",
        "description": "Update user profile",
        "authentication": "Bearer Token",
        "request_body": {
            "full_name": "John Updated Doe",
            "phone": "+2348087654321",
            "avatar_url": "https://new-avatar.com/image.jpg"
        },
        "response_200": {
            "id": "uuid",
            "full_name": "John Updated Doe",
            "phone": "+2348087654321"
        }
    },
    
    "password_change": {
        "url": "/api/v1/user/password/change/",
        "method": "POST",
        "description": "Change user password",
        "authentication": "Bearer Token",
        "request_body": {
            "old_password": "OldPass123!",
            "new_password": "NewPass123!"
        },
        "response_200": {
            "message": "Password changed successfully"
        }
    },
    
    "onboarding": {
        "url": "/api/v1/user/onboarding/",
        "method": "POST",
        "description": "Complete user onboarding (mark as completed)",
        "authentication": "Bearer Token",
        "response_200": {
            "message": "Onboarding completed successfully"
        }
    },
    
    # ========================================================================
    # 2. USER PREFERENCES (FOR RECOMMENDATIONS)
    # ========================================================================
    "get_preferences": {
        "url": "/api/v1/user/preferences/",
        "method": "GET",
        "description": "Get user booking preferences for recommendations",
        "authentication": "Bearer Token",
        "response_200": {
            "id": "uuid",
            "user": "uuid",
            "preferred_booking_type": "daily",
            "preferred_space_types": ["meeting_room", "office"],
            "preferred_capacity_min": 2,
            "preferred_capacity_max": 10,
            "preferred_cities": ["Lagos", "Abuja"],
            "budget_min": "5000.00",
            "budget_max": "50000.00",
            "notify_on_recommendation": True
        }
    },
    
    "update_preferences": {
        "url": "/api/v1/user/preferences/{id}/",
        "method": "PATCH",
        "description": "Update user preferences",
        "authentication": "Bearer Token",
        "request_body": {
            "preferred_booking_type": "hourly",
            "preferred_space_types": ["coworking", "desk"],
            "budget_min": "3000.00",
            "budget_max": "30000.00"
        },
        "response_200": {
            "id": "uuid",
            "preferred_booking_type": "hourly",
            "budget_min": "3000.00"
        }
    },
    
    # ========================================================================
    # 3. WORKSPACE & SPACE DISCOVERY (PUBLIC)
    # ========================================================================
    "list_workspaces": {
        "url": "/api/v1/workspace/public/workspaces/",
        "method": "GET",
        "description": "List all active workspaces (paginated)",
        "authentication": "None",
        "query_params": {
            "page": 1,
            "page_size": 20,
            "city": "Lagos",
            "search": "hub"
        },
        "response_200": {
            "count": 100,
            "next": "http://.../api/v1/workspace/public/workspaces/?page=2",
            "previous": None,
            "results": [
                {
                    "id": "uuid",
                    "name": "Hub1 Lagos",
                    "description": "Modern workspace",
                    "city": "Lagos",
                    "state": "Lagos",
                    "address": "123 Main St",
                    "email": "hub1@xbooking.com",
                    "phone": "+2348012345678"
                }
            ]
        }
    },
    
    "workspace_detail": {
        "url": "/api/v1/workspace/public/workspaces/{id}/",
        "method": "GET",
        "description": "Get workspace details",
        "authentication": "None",
        "response_200": {
            "id": "uuid",
            "name": "Hub1 Lagos",
            "description": "Modern workspace with all amenities",
            "city": "Lagos",
            "branches": [
                {
                    "id": "uuid",
                    "name": "Hub1 Lagos Branch 1",
                    "city": "Lagos"
                }
            ]
        }
    },
    
    "list_branches": {
        "url": "/api/v1/workspace/public/branches/",
        "method": "GET",
        "description": "List all branches (paginated)",
        "authentication": "None",
        "query_params": {
            "page": 1,
            "workspace": "workspace_uuid",
            "city": "Lagos"
        },
        "response_200": {
            "count": 50,
            "results": [
                {
                    "id": "uuid",
                    "workspace": "workspace_uuid",
                    "name": "Branch 1",
                    "city": "Lagos",
                    "address": "123 Ave"
                }
            ]
        }
    },
    
    "list_spaces": {
        "url": "/api/v1/workspace/public/spaces/",
        "method": "GET",
        "description": "List all available spaces (paginated)",
        "authentication": "None",
        "query_params": {
            "page": 1,
            "page_size": 20,
            "branch": "branch_uuid",
            "space_type": "meeting_room",
            "min_capacity": 5,
            "max_capacity": 20,
            "city": "Lagos",
            "price_min": "5000",
            "price_max": "50000"
        },
        "response_200": {
            "count": 200,
            "next": "http://.../api/v1/workspace/public/spaces/?page=2",
            "previous": None,
            "results": [
                {
                    "id": "uuid",
                    "branch": "branch_uuid",
                    "name": "Meeting Room 1",
                    "space_type": "meeting_room",
                    "capacity": 10,
                    "price_per_hour": "5000.00",
                    "daily_rate": "40000.00",
                    "monthly_rate": "800000.00",
                    "amenities": ["WiFi", "Projector", "Whiteboard"],
                    "is_available": True
                }
            ]
        }
    },
    
    "space_detail": {
        "url": "/api/v1/workspace/public/spaces/{id}/",
        "method": "GET",
        "description": "Get space details",
        "authentication": "None",
        "response_200": {
            "id": "uuid",
            "name": "Meeting Room 1",
            "description": "Well-equipped meeting room",
            "space_type": "meeting_room",
            "capacity": 10,
            "price_per_hour": "5000.00",
            "daily_rate": "40000.00",
            "monthly_rate": None,
            "amenities": ["WiFi", "Projector", "Whiteboard"],
            "branch": {
                "id": "uuid",
                "name": "Branch 1",
                "city": "Lagos"
            }
        }
    },
    
    "check_availability": {
        "url": "/api/v1/workspace/public/slots/check-availability/",
        "method": "POST",
        "description": "Check if space is available for specific date/time",
        "authentication": "None",
        "request_body": {
            "space": "space_uuid",
            "booking_type": "hourly",
            "date": "2026-01-15",
            "start_time": "09:00",
            "end_time": "12:00"
        },
        "response_200": {
            "available": True,
            "message": "Space is available",
            "available_slots": [
                {
                    "id": "uuid",
                    "date": "2026-01-15",
                    "start_time": "09:00:00",
                    "end_time": "10:00:00",
                    "booking_type": "hourly",
                    "status": "available"
                }
            ]
        }
    },
    
    "get_available_slots": {
        "url": "/api/v1/workspace/public/slots/available/",
        "method": "GET",
        "description": "Get all available slots for a space within date range",
        "authentication": "None",
        "query_params": {
            "space": "space_uuid",
            "start_date": "2026-01-15",
            "end_date": "2026-01-20",
            "booking_type": "hourly"
        },
        "response_200": {
            "space": "space_uuid",
            "space_name": "Meeting Room 1",
            "start_date": "2026-01-15",
            "end_date": "2026-01-20",
            "availability": [
                {
                    "date": "2026-01-15",
                    "hourly_slots": [
                        {
                            "id": "uuid",
                            "start_time": "09:00:00",
                            "end_time": "10:00:00",
                            "status": "available"
                        }
                    ],
                    "daily_slots": [],
                    "monthly_slots": []
                }
            ]
        }
    },
    
    "list_calendars": {
        "url": "/api/v1/workspace/public/calendars/",
        "method": "GET",
        "description": "List space calendars",
        "authentication": "None",
        "query_params": {
            "space": "space_uuid"
        },
        "response_200": {
            "count": 1,
            "results": [
                {
                    "id": "uuid",
                    "space": "space_uuid",
                    "space_name": "Meeting Room 1",
                    "time_interval_minutes": 60,
                    "operating_hours": {"0": {"start": "08:00", "end": "20:00"}},
                    "hourly_enabled": True,
                    "daily_enabled": True,
                    "monthly_enabled": False,
                    "hourly_price": "5000.00",
                    "daily_price": "40000.00",
                    "monthly_price": "0.00"
                }
            ]
        }
    },
    
    "list_slots": {
        "url": "/api/v1/workspace/public/slots/",
        "method": "GET",
        "description": "List space calendar slots (paginated)",
        "authentication": "None",
        "query_params": {
            "space": "space_uuid",
            "date": "2026-01-15",
            "booking_type": "hourly",
            "status": "available"
        },
        "response_200": {
            "count": 12,
            "results": [
                {
                    "id": "uuid",
                    "calendar": "calendar_uuid",
                    "space": {
                        "id": "space_uuid",
                        "name": "Meeting Room 1",
                        "space_type": "meeting_room"
                    },
                    "date": "2026-01-15",
                    "start_time": "09:00:00",
                    "end_time": "10:00:00",
                    "booking_type": "hourly",
                    "status": "available",
                    "booking": None
                }
            ]
        }
    },
    
    # ========================================================================
    # 4. CART MANAGEMENT
    # ========================================================================
    "get_cart": {
        "url": "/api/v1/booking/cart/",
        "method": "GET",
        "description": "Get user's current cart",
        "authentication": "Bearer Token",
        "response_200": {
            "id": "uuid",
            "user": "user_uuid",
            "items": [
                {
                    "id": "uuid",
                    "space": {
                        "id": "uuid",
                        "name": "Meeting Room 1",
                        "price_per_hour": "5000.00"
                    },
                    "booking_type": "hourly",
                    "check_in_date": "2026-01-15",
                    "check_in_time": "09:00:00",
                    "check_out_time": "12:00:00",
                    "number_of_guests": 5,
                    "price": "15000.00"
                }
            ],
            "total_items": 1,
            "total_price": "15000.00",
            "created_at": "2026-01-10T10:00:00Z"
        }
    },
    
    "add_to_cart": {
        "url": "/api/v1/booking/cart/add_item/",
        "method": "POST",
        "description": "Add space to cart",
        "authentication": "Bearer Token",
        "request_body": {
            "space": "space_uuid",
            "booking_type": "hourly",
            "check_in_date": "2026-01-15",
            "check_in_time": "09:00",
            "check_out_time": "12:00",
            "number_of_guests": 5
        },
        "response_201": {
            "id": "cart_item_uuid",
            "cart": "cart_uuid",
            "space": "space_uuid",
            "price": "15000.00",
            "message": "Item added to cart"
        }
    },
    
    "update_cart_item": {
        "url": "/api/v1/booking/cart/update_item/",
        "method": "PATCH",
        "description": "Update cart item",
        "authentication": "Bearer Token",
        "request_body": {
            "item_id": "cart_item_uuid",
            "number_of_guests": 8,
            "check_in_time": "10:00"
        },
        "response_200": {
            "id": "cart_item_uuid",
            "number_of_guests": 8,
            "message": "Cart item updated"
        }
    },
    
    "remove_from_cart": {
        "url": "/api/v1/booking/cart/remove_item/",
        "method": "POST",
        "description": "Remove item from cart",
        "authentication": "Bearer Token",
        "request_body": {
            "item_id": "cart_item_uuid"
        },
        "response_200": {
            "message": "Item removed from cart"
        }
    },
    
    "clear_cart": {
        "url": "/api/v1/booking/cart/clear/",
        "method": "POST",
        "description": "Clear entire cart",
        "authentication": "Bearer Token",
        "response_200": {
            "message": "Cart cleared successfully"
        }
    },
    
    # ========================================================================
    # 5. CHECKOUT & ORDER
    # ========================================================================
    "checkout": {
        "url": "/api/v1/booking/cart/checkout/",
        "method": "POST",
        "description": "Checkout cart and create order with bookings",
        "authentication": "Bearer Token",
        "request_body": {
            "guests": [
                {
                    "full_name": "Guest Name",
                    "email": "guest@example.com",
                    "phone_number": "+2348012345678"
                }
            ]
        },
        "response_201": {
            "order": {
                "id": "order_uuid",
                "order_number": "ORD-123456",
                "total_amount": "15000.00",
                "status": "pending",
                "bookings": [
                    {
                        "id": "booking_uuid",
                        "space": "space_uuid",
                        "check_in_date": "2026-01-15",
                        "total_price": "15000.00",
                        "status": "pending"
                    }
                ]
            },
            "message": "Order created successfully. Proceed to payment."
        }
    },
    
    "list_orders": {
        "url": "/api/v1/payment/orders/",
        "method": "GET",
        "description": "List user's orders (paginated)",
        "authentication": "Bearer Token",
        "query_params": {
            "page": 1,
            "status": "completed"
        },
        "response_200": {
            "count": 10,
            "results": [
                {
                    "id": "uuid",
                    "order_number": "ORD-123456",
                    "total_amount": "15000.00",
                    "status": "completed",
                    "created_at": "2026-01-10T10:00:00Z"
                }
            ]
        }
    },
    
    "order_detail": {
        "url": "/api/v1/payment/orders/{id}/",
        "method": "GET",
        "description": "Get order details",
        "authentication": "Bearer Token",
        "response_200": {
            "id": "uuid",
            "order_number": "ORD-123456",
            "total_amount": "15000.00",
            "currency": "NGN",
            "status": "completed",
            "bookings": [
                {
                    "id": "booking_uuid",
                    "space_name": "Meeting Room 1",
                    "check_in_date": "2026-01-15"
                }
            ]
        }
    },
    
    # ========================================================================
    # 6. PAYMENT
    # ========================================================================
    "initiate_payment": {
        "url": "/api/v1/payment/payments/",
        "method": "POST",
        "description": "Initiate payment for an order",
        "authentication": "Bearer Token",
        "request_body": {
            "order": "order_uuid",
            "payment_method": "paystack",
            "amount": "15000.00",
            "currency": "NGN"
        },
        "response_201": {
            "id": "payment_uuid",
            "order": "order_uuid",
            "amount": "15000.00",
            "payment_method": "paystack",
            "status": "pending",
            "payment_url": "https://paystack.com/pay/xyz123",
            "reference": "REF_12345"
        }
    },
    
    "wallet_payment": {
        "url": "/api/v1/payment/payments/pay_with_wallet/",
        "method": "POST",
        "description": "Pay for order using wallet balance",
        "authentication": "Bearer Token",
        "request_body": {
            "order": "order_uuid"
        },
        "response_200": {
            "message": "Payment successful",
            "payment": {
                "id": "payment_uuid",
                "amount": "15000.00",
                "status": "completed"
            },
            "order": {
                "id": "order_uuid",
                "status": "completed"
            }
        }
    },
    
    "verify_payment": {
        "url": "/api/v1/payment/payments/{id}/verify/",
        "method": "POST",
        "description": "Verify payment status",
        "authentication": "Bearer Token",
        "response_200": {
            "id": "payment_uuid",
            "status": "completed",
            "verified": True,
            "message": "Payment verified successfully"
        }
    },
    
    "list_payments": {
        "url": "/api/v1/payment/payments/",
        "method": "GET",
        "description": "List user's payments (paginated)",
        "authentication": "Bearer Token",
        "query_params": {
            "page": 1,
            "status": "completed",
            "order": "order_uuid"
        },
        "response_200": {
            "count": 5,
            "results": [
                {
                    "id": "uuid",
                    "order": "order_uuid",
                    "amount": "15000.00",
                    "payment_method": "paystack",
                    "status": "completed",
                    "paid_at": "2026-01-10T11:00:00Z"
                }
            ]
        }
    },
    
    # ========================================================================
    # 7. BOOKINGS
    # ========================================================================
    "list_bookings": {
        "url": "/api/v1/booking/bookings/",
        "method": "GET",
        "description": "List user's bookings (paginated)",
        "authentication": "Bearer Token",
        "query_params": {
            "page": 1,
            "status": "confirmed",
            "booking_type": "hourly",
            "ordering": "-created_at"
        },
        "response_200": {
            "count": 20,
            "next": "http://.../api/v1/booking/bookings/?page=2",
            "previous": None,
            "results": [
                {
                    "id": "uuid",
                    "space": {
                        "id": "uuid",
                        "name": "Meeting Room 1"
                    },
                    "workspace": "workspace_uuid",
                    "booking_type": "hourly",
                    "check_in_date": "2026-01-15",
                    "check_in_time": "09:00:00",
                    "check_out_time": "12:00:00",
                    "number_of_guests": 5,
                    "total_price": "15000.00",
                    "status": "confirmed",
                    "payment_status": "completed",
                    "created_at": "2026-01-10T10:00:00Z"
                }
            ]
        }
    },
    
    "booking_detail": {
        "url": "/api/v1/booking/bookings/{id}/",
        "method": "GET",
        "description": "Get booking details",
        "authentication": "Bearer Token",
        "response_200": {
            "id": "uuid",
            "user": "user_uuid",
            "space": {
                "id": "uuid",
                "name": "Meeting Room 1",
                "space_type": "meeting_room"
            },
            "workspace": "workspace_uuid",
            "order": "order_uuid",
            "booking_type": "hourly",
            "check_in_date": "2026-01-15",
            "check_out_date": "2026-01-15",
            "check_in_time": "09:00:00",
            "check_out_time": "12:00:00",
            "number_of_guests": 5,
            "total_price": "15000.00",
            "status": "confirmed",
            "payment_status": "completed",
            "guests": [
                {
                    "id": "uuid",
                    "full_name": "Guest Name",
                    "email": "guest@example.com"
                }
            ],
            "qr_code": {
                "id": "uuid",
                "qr_code_image_url": "https://...",
                "verification_code": "ABC123"
            }
        }
    },
    
    "cancel_booking": {
        "url": "/api/v1/booking/bookings/{id}/cancel/",
        "method": "POST",
        "description": "Cancel a booking",
        "authentication": "Bearer Token",
        "request_body": {
            "cancellation_reason": "Schedule changed"
        },
        "response_200": {
            "id": "booking_uuid",
            "status": "cancelled",
            "message": "Booking cancelled successfully"
        }
    },
    
    "upcoming_bookings": {
        "url": "/api/v1/booking/bookings/upcoming/",
        "method": "GET",
        "description": "Get user's upcoming bookings",
        "authentication": "Bearer Token",
        "response_200": {
            "count": 5,
            "results": [
                {
                    "id": "uuid",
                    "space_name": "Meeting Room 1",
                    "check_in_date": "2026-01-15",
                    "check_in_time": "09:00:00"
                }
            ]
        }
    },
    
    "past_bookings": {
        "url": "/api/v1/booking/bookings/past/",
        "method": "GET",
        "description": "Get user's past bookings",
        "authentication": "Bearer Token",
        "response_200": {
            "count": 10,
            "results": [
                {
                    "id": "uuid",
                    "space_name": "Meeting Room 1",
                    "check_in_date": "2026-01-05",
                    "status": "completed"
                }
            ]
        }
    },
    
    # ========================================================================
    # 8. WALLET & TRANSACTIONS
    # ========================================================================
    "get_wallet": {
        "url": "/api/v1/bank/v1/wallets/",
        "method": "GET",
        "description": "Get user's wallet details",
        "authentication": "Bearer Token",
        "response_200": {
            "id": "uuid",
            "user": "user_uuid",
            "balance": "50000.00",
            "currency": "NGN",
            "created_at": "2026-01-01T00:00:00Z"
        }
    },
    
    "wallet_transactions": {
        "url": "/api/v1/bank/v1/transactions/",
        "method": "GET",
        "description": "Get wallet transaction history (paginated)",
        "authentication": "Bearer Token",
        "query_params": {
            "page": 1,
            "transaction_type": "debit"
        },
        "response_200": {
            "count": 50,
            "results": [
                {
                    "id": "uuid",
                    "wallet": "wallet_uuid",
                    "transaction_type": "debit",
                    "amount": "15000.00",
                    "description": "Payment for booking",
                    "balance_after": "35000.00",
                    "created_at": "2026-01-10T11:00:00Z"
                }
            ]
        }
    },
    
    "fund_wallet": {
        "url": "/api/v1/bank/v1/deposits/",
        "method": "POST",
        "description": "Initiate wallet funding",
        "authentication": "Bearer Token",
        "request_body": {
            "amount": "50000.00",
            "payment_method": "paystack"
        },
        "response_201": {
            "id": "deposit_uuid",
            "amount": "50000.00",
            "payment_url": "https://paystack.com/pay/xyz",
            "reference": "DEP_12345"
        }
    },
    
    # ========================================================================
    # 9. REVIEWS
    # ========================================================================
    "create_review": {
        "url": "/api/v1/booking/reviews/",
        "method": "POST",
        "description": "Create a review for a booking",
        "authentication": "Bearer Token",
        "request_body": {
            "booking": "booking_uuid",
            "rating": 5,
            "comment": "Excellent space and service!"
        },
        "response_201": {
            "id": "review_uuid",
            "booking": "booking_uuid",
            "rating": 5,
            "comment": "Excellent space and service!",
            "created_at": "2026-01-16T10:00:00Z"
        }
    },
    
    "list_reviews": {
        "url": "/api/v1/booking/reviews/",
        "method": "GET",
        "description": "List user's reviews",
        "authentication": "Bearer Token",
        "response_200": {
            "count": 5,
            "results": [
                {
                    "id": "uuid",
                    "booking": "booking_uuid",
                    "rating": 5,
                    "comment": "Great!",
                    "created_at": "2026-01-16T10:00:00Z"
                }
            ]
        }
    },
    
    # ========================================================================
    # 10. NOTIFICATIONS
    # ========================================================================
    "list_notifications": {
        "url": "/api/v1/notifications/",
        "method": "GET",
        "description": "List user notifications (paginated)",
        "authentication": "Bearer Token",
        "query_params": {
            "page": 1,
            "unread": "true"
        },
        "response_200": {
            "count": 10,
            "results": [
                {
                    "id": "uuid",
                    "type": "booking_confirmation",
                    "title": "Booking Confirmed",
                    "message": "Your booking has been confirmed",
                    "is_read": False,
                    "created_at": "2026-01-10T11:00:00Z"
                }
            ]
        }
    },
    
    "mark_notification_read": {
        "url": "/api/v1/notifications/{id}/mark_read/",
        "method": "PATCH",
        "description": "Mark notification as read",
        "authentication": "Bearer Token",
        "response_200": {
            "id": "uuid",
            "is_read": True
        }
    },
    
    "mark_all_read": {
        "url": "/api/v1/notifications/mark_all_read/",
        "method": "POST",
        "description": "Mark all notifications as read",
        "authentication": "Bearer Token",
        "response_200": {
            "message": "All notifications marked as read"
        }
    }
}


# ========================================================================
# COMPLETE BOOKING FLOW EXAMPLE
# ========================================================================
BOOKING_FLOW_EXAMPLE = """
COMPLETE USER BOOKING FLOW:

1. REGISTER/LOGIN
   POST /api/v1/user/auth/register/ or /login/
   → Get JWT tokens

2. BROWSE WORKSPACES & SPACES
   GET /api/v1/workspace/public/workspaces/?city=Lagos&page=1
   GET /api/v1/workspace/public/spaces/?page=1&space_type=meeting_room

3. VIEW SPACE CALENDAR & AVAILABLE SLOTS
   GET /api/v1/workspace/public/calendars/?space={space_id}
   GET /api/v1/workspace/public/slots/available/?space={space_id}&start_date=2026-01-15&end_date=2026-01-20
   → View all available time slots

4. CHECK SPECIFIC AVAILABILITY
   POST /api/v1/workspace/public/slots/check-availability/
   Body: {"space": "uuid", "booking_type": "hourly", "date": "2026-01-15", "start_time": "09:00", "end_time": "12:00"}
   → Confirm exact time slot is available

5. ADD TO CART
   POST /api/v1/booking/cart/add_item/
   Body: {"space": "uuid", "booking_type": "hourly", "check_in_date": "2026-01-15", ...}

6. VIEW CART
   GET /api/v1/booking/cart/

7. CHECKOUT (Creates Order & Bookings)
   POST /api/v1/booking/cart/checkout/
   Body: {"guests": [{"full_name": "...", "email": "..."}]}
   → Returns order with bookings

8. PAYMENT
   Option A - Paystack:
     POST /api/v1/payment/payments/
     Body: {"order": "uuid", "payment_method": "paystack", "amount": "15000"}
     → Get payment_url, redirect user
     → Webhook updates payment status
   
   Option B - Wallet:
     POST /api/v1/payment/payments/pay_with_wallet/
     Body: {"order": "uuid"}
     → Instant payment

9. VIEW BOOKINGS
   GET /api/v1/booking/bookings/
   GET /api/v1/booking/bookings/{id}/  (QR code included)

10. CHECK WALLET
    GET /api/v1/bank/v1/wallets/
    GET /api/v1/bank/v1/transactions/

11. LEAVE REVIEW (After booking)
    POST /api/v1/booking/reviews/
    Body: {"booking": "uuid", "rating": 5, "comment": "Great!"}
"""

if __name__ == "__main__":
    print("="*70)
    print("XBOOKING API ENDPOINTS DOCUMENTATION")
    print("="*70)
    print(f"\nTotal Endpoints: {len(API_ENDPOINTS)}")
    print("\nCategories:")
    print("  1. User Authentication & Profile (7 endpoints)")
    print("  2. User Preferences (2 endpoints)")
    print("  3. Workspace & Space Discovery (11 endpoints)")
    print("  4. Cart Management (5 endpoints)")
    print("  5. Checkout & Orders (3 endpoints)")
    print("  6. Payment (4 endpoints)")
    print("  7. Bookings (6 endpoints)")
    print("  8. Wallet & Transactions (3 endpoints)")
    print("  9. Reviews (2 endpoints)")
    print("  10. Notifications (3 endpoints)")
    print("\n" + "="*70)
    print(BOOKING_FLOW_EXAMPLE)
