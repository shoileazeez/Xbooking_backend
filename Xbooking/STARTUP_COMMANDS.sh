#!/bin/bash
# =============================================================================
# XBOOKING STARTUP COMMANDS
# =============================================================================
# This file contains all the commands needed to start the Xbooking backend
# Redis is already running, so we only need to start Django, Celery Worker, and Celery Beat
# =============================================================================

echo "=========================================="
echo "XBOOKING BACKEND - STARTUP GUIDE"
echo "=========================================="
echo ""

# =============================================================================
# TERMINAL 1: Django Development Server
# =============================================================================
echo "TERMINAL 1: Django Development Server"
echo "--------------------------------------"
echo "cd /c/Users/Admin/Xbooking_backend/Xbooking"
echo "python manage.py runserver"
echo ""
echo "Server will start at: http://127.0.0.1:8000"
echo "API Docs: http://127.0.0.1:8000/api/docs/"
echo ""

# =============================================================================
# TERMINAL 2: Celery Worker
# =============================================================================
echo "TERMINAL 2: Celery Worker"
echo "--------------------------------------"
echo "cd /c/Users/Admin/Xbooking_backend/Xbooking"
echo "celery -A Xbooking worker -l info --pool=solo"
echo ""
echo "Note: Use --pool=solo for Windows compatibility"
echo ""

# =============================================================================
# TERMINAL 3: Celery Beat (Scheduler)
# =============================================================================
echo "TERMINAL 3: Celery Beat"
echo "--------------------------------------"
echo "cd /c/Users/Admin/Xbooking_backend/Xbooking"
echo "celery -A Xbooking beat -l info"
echo ""
echo "This runs periodic tasks like reminders and QR expiry"
echo ""

# =============================================================================
# ONE-TIME SETUP COMMANDS (Run these first if not done)
# =============================================================================
echo "=========================================="
echo "ONE-TIME SETUP COMMANDS"
echo "=========================================="
echo ""
echo "1. Apply migrations:"
echo "   python manage.py migrate"
echo ""
echo "2. Create superuser:"
echo "   python manage.py createsuperuser"
echo ""
echo "3. Populate workspaces (creates 10 workspaces with branches/spaces):"
echo "   python manage.py populate_workspaces"
echo ""
echo "   Or specify number of workspaces:"
echo "   python manage.py populate_workspaces --workspaces 5"
echo ""
echo "   Or specify admin email:"
echo "   python manage.py populate_workspaces --admin-email admin@xbooking.com"
echo ""
echo "4. Collect static files (for production):"
echo "   python manage.py collectstatic --noinput"
echo ""

# =============================================================================
# CHECKING SERVICES
# =============================================================================
echo "=========================================="
echo "CHECKING RUNNING SERVICES"
echo "=========================================="
echo ""
echo "Check Redis is running:"
echo "   redis-cli ping"
echo "   (Should return: PONG)"
echo ""
echo "Check Django server:"
echo "   curl http://127.0.0.1:8000/"
echo ""
echo "Check Celery worker:"
echo "   celery -A Xbooking inspect active"
echo ""

# =============================================================================
# HELPFUL COMMANDS
# =============================================================================
echo "=========================================="
echo "HELPFUL COMMANDS"
echo "=========================================="
echo ""
echo "Stop Celery worker:"
echo "   Ctrl+C in the worker terminal"
echo ""
echo "Stop Celery beat:"
echo "   Ctrl+C in the beat terminal"
echo ""
echo "View Celery tasks:"
echo "   celery -A Xbooking inspect registered"
echo ""
echo "Purge all Celery tasks:"
echo "   celery -A Xbooking purge"
echo ""
echo "Django shell:"
echo "   python manage.py shell"
echo ""
echo "Run tests:"
echo "   python manage.py test"
echo ""

# =============================================================================
# QUICK START (All commands in sequence)
# =============================================================================
echo "=========================================="
echo "QUICK START SEQUENCE"
echo "=========================================="
echo ""
echo "Run these commands in order:"
echo ""
echo "1. Terminal 1 - Django Server:"
echo "   cd /c/Users/Admin/Xbooking_backend/Xbooking && python manage.py runserver"
echo ""
echo "2. Terminal 2 - Celery Worker:"
echo "   cd /c/Users/Admin/Xbooking_backend/Xbooking && celery -A Xbooking worker -l info --pool=solo"
echo ""
echo "3. Terminal 3 - Celery Beat:"
echo "   cd /c/Users/Admin/Xbooking_backend/Xbooking && celery -A Xbooking beat -l info"
echo ""
echo "=========================================="
echo "ALL DONE! Ready to start development!"
echo "=========================================="
