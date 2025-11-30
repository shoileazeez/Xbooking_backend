from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from workspace.models import Space, Branch
from booking.models import Booking, Reservation
from workspace.serializers.workspace import SpaceSerializer, SpaceDetailSerializer, SpaceSimpleSerializer
from workspace.permissions import (
    check_workspace_admin, check_workspace_member, check_branch_manager
)


class CreateSpaceView(APIView):
    """Create a new space in a branch"""
    permission_classes = [IsAuthenticated]
    serializer_class = SpaceSerializer

    @extend_schema(
        request=SpaceSerializer,
        responses={201: SpaceSerializer},
        description="Create a new space in branch"
    )
    def post(self, request, branch_id):
        """Create space"""
        branch = get_object_or_404(Branch, id=branch_id)
        workspace = branch.workspace

        # Check if user is workspace admin or branch manager using permission helper
        if not (check_workspace_admin(request.user, workspace) or check_branch_manager(request.user, branch)):
            return Response({
                'success': False,
                'message': 'Only workspace admin or branch manager can create spaces'
            }, status=status.HTTP_403_FORBIDDEN)

        data = request.data.copy()
        data['branch'] = branch.id

        serializer = SpaceSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Space created successfully',
                'space': serializer.data
            }, status=status.HTTP_201_CREATED)

        return Response({
            'success': False,
            'message': 'Space creation failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class ListSpacesView(APIView):
    """List spaces in a branch"""
    permission_classes = [IsAuthenticated]
    serializer_class = SpaceSimpleSerializer

    @extend_schema(
        responses={200: SpaceSimpleSerializer(many=True)},
        description="Get all spaces in a branch"
    )
    def get(self, request, branch_id):
        """Get all spaces"""
        branch = get_object_or_404(Branch, id=branch_id)
        workspace = branch.workspace

        # Check if user has access using permission helper
        # Relaxed permission: Any authenticated user can view spaces
        # if not check_workspace_member(request.user, workspace):
        #     return Response({
        #         'success': False,
        #         'message': 'You do not have permission to access this branch'
        #     }, status=status.HTTP_403_FORBIDDEN)

        spaces = branch.spaces.all()
        serializer = SpaceSimpleSerializer(spaces, many=True)

        return Response({
            'success': True,
            'count': len(spaces),
            'spaces': serializer.data
        }, status=status.HTTP_200_OK)


class SpaceDetailView(APIView):
    """Get, update, delete space"""
    permission_classes = [IsAuthenticated]
    serializer_class = SpaceDetailSerializer

    def get_space(self, space_id, user):
        """Helper to get space and check permissions"""
        space = get_object_or_404(Space, id=space_id)
        branch = space.branch
        workspace = branch.workspace

        # Check if user has access to workspace using permission helper
        # Relaxed permission: Any authenticated user can view space details
        # if not check_workspace_member(user, workspace):
        #     return None, Response({
        #         'success': False,
        #         'message': 'You do not have permission to access this space'
        #     }, status=status.HTTP_403_FORBIDDEN)

        return space, None

    @extend_schema(
        responses={200: SpaceDetailSerializer},
        description="Get space details"
    )
    def get(self, request, space_id):
        """Get space details"""
        space, error = self.get_space(space_id, request.user)
        if error:
            return error

        serializer = SpaceDetailSerializer(space)
        return Response({
            'success': True,
            'space': serializer.data
        }, status=status.HTTP_200_OK)


class SpaceCalendarView(APIView):
    """Return availability calendar for a space.

    Supports modes: hourly (slots for a date), daily (day availability for a month),
    monthly (month availability for a year).
    """
    permission_classes = []  # public

    def get(self, request, space_id):
        mode = request.query_params.get('mode', 'daily')
        space = get_object_or_404(Space, id=space_id)

        from datetime import datetime, date, time, timedelta
        import calendar as _calendar
        from workspace.models import SpaceCalendar, SpaceCalendarSlot

        def parse_date(s):
            return datetime.fromisoformat(s).date()

        if mode == 'hourly':
            date_str = request.query_params.get('date')
            if not date_str:
                return Response(
                    {'success': False, 'message': 'date parameter required for hourly mode'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            query_date = parse_date(date_str)

            # Get SpaceCalendarSlots for this date
            # Prefer explicit hourly slots for the date. If none exist, fall back to any available slot
            # This ensures the frontend sees booking_type='hourly' when appropriate.
            slots_qs = SpaceCalendarSlot.objects.filter(
                calendar__space=space,
                date=query_date,
                booking_type='hourly'
            ).values('id', 'start_time', 'end_time', 'status', 'booking_type').order_by('start_time')

            if not slots_qs.exists():
                # fallback to any slot for the date
                slots_qs = SpaceCalendarSlot.objects.filter(
                    calendar__space=space,
                    date=query_date
                ).values('id', 'start_time', 'end_time', 'status', 'booking_type').order_by('start_time')

            if not slots_qs.exists():
                return Response(
                    {'mode': 'hourly', 'date': date_str, 'slots': []},
                    status=status.HTTP_200_OK
                )

            slots = []
            for slot in slots_qs:
                # format times and return booking_type per slot
                slots.append({
                    'id': str(slot['id']),
                    'start': slot['start_time'].strftime('%H:%M'),
                    'end': slot['end_time'].strftime('%H:%M'),
                    'available': slot['status'] == 'available',
                    'status': slot['status'],
                    'booking_type': slot['booking_type']
                })

            return Response(
                {'mode': 'hourly', 'date': date_str, 'slots': slots},
                status=status.HTTP_200_OK
            )

        if mode == 'daily':
            month_str = request.query_params.get('month')
            if not month_str:
                return Response(
                    {'success': False, 'message': 'month parameter required for daily mode (YYYY-MM)'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            year, month = map(int, month_str.split('-'))
            _, num_days = _calendar.monthrange(year, month)

            days = []
            for d in range(1, num_days + 1):
                day_date = date(year, month, d)

                # Find availability for the day. Prefer a slot that matches the 'daily' booking type
                # so the frontend sees "daily" when a daily booking is available. Fallback to any
                # available slot if no daily slot exists.
                available_slot = SpaceCalendarSlot.objects.filter(
                    calendar__space=space,
                    date=day_date,
                    status='available',
                    booking_type='daily'
                ).values('id', 'booking_type').first()

                if not available_slot:
                    # fallback to any available slot (hourly or monthly)
                    available_slot = SpaceCalendarSlot.objects.filter(
                        calendar__space=space,
                        date=day_date,
                        status='available'
                    ).values('id', 'booking_type').first()

                days.append({
                    'id': str(available_slot['id']) if available_slot else None,
                    'date': day_date.isoformat(),
                    'available': available_slot is not None,
                    'booking_type': available_slot['booking_type'] if available_slot else None,
                })

            return Response(
                {'mode': 'daily', 'month': month_str, 'days': days},
                status=status.HTTP_200_OK
            )

        if mode == 'monthly':
            year_str = request.query_params.get('year')
            if not year_str:
                return Response(
                    {'success': False, 'message': 'year parameter required for monthly mode (YYYY)'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            year = int(year_str)
            months = []

            for m in range(1, 13):
                # Check if any slot is available for this month
                month_start = date(year, m, 1)
                _, num_days = _calendar.monthrange(year, m)
                month_end = date(year, m, num_days)

                # For monthly overview prefer monthly booking_type slots. Fall back to daily or hourly
                # if no monthly slots are available in the month range. This avoids showing 'daily'
                # for a month when a true monthly slot exists.
                available_slot = SpaceCalendarSlot.objects.filter(
                    calendar__space=space,
                    date__gte=month_start,
                    date__lte=month_end,
                    status='available',
                    booking_type='monthly'
                ).values('id', 'booking_type', 'status').first()

                if not available_slot:
                    # try daily
                    available_slot = SpaceCalendarSlot.objects.filter(
                        calendar__space=space,
                        date__gte=month_start,
                        date__lte=month_end,
                        status='available',
                        booking_type='daily'
                    ).values('id', 'booking_type', 'status').first()

                if not available_slot:
                    # fallback to any available slot
                    available_slot = SpaceCalendarSlot.objects.filter(
                        calendar__space=space,
                        date__gte=month_start,
                        date__lte=month_end,
                        status='available'
                    ).values('id', 'booking_type', 'status').first()

                months.append({
                    'id': str(available_slot['id']) if available_slot else None,
                    'month': f"{year}-{m:02d}",
                    'available': available_slot['status'] == "available" if available_slot else False,
                    'booking_type': available_slot['booking_type'] if available_slot else None,
                })

            return Response(
                {'mode': 'monthly', 'year': year_str, 'months': months},
                status=status.HTTP_200_OK
            )

        return Response(
            {'success': False, 'message': 'Invalid mode'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @extend_schema(
        request=SpaceSerializer,
        responses={200: SpaceSerializer},
        description="Update space"
    )
    def put(self, request, space_id):
        """Update space"""
        space, error = self.get_space(space_id, request.user)
        if error:
            return error

        # Check if user is admin or manager using permission helper
        branch = space.branch
        workspace = branch.workspace
        if not (check_workspace_admin(request.user, workspace) or check_branch_manager(request.user, branch)):
            return Response({
                'success': False,
                'message': 'Only workspace admin or branch manager can update spaces'
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = SpaceSerializer(space, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Space updated successfully',
                'space': serializer.data
            }, status=status.HTTP_200_OK)

        return Response({
            'success': False,
            'message': 'Update failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        description="Delete space"
    )
    def delete(self, request, space_id):
        """Delete space"""
        space, error = self.get_space(space_id, request.user)
        if error:
            return error

        # Check if user is admin using permission helper
        if not check_workspace_admin(request.user, space.branch.workspace):
            return Response({
                'success': False,
                'message': 'Only workspace admin can delete spaces'
            }, status=status.HTTP_403_FORBIDDEN)

        space.delete()
        return Response({
            'success': True,
            'message': 'Space deleted successfully'
        }, status=status.HTTP_200_OK)

