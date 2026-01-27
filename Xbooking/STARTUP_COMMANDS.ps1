# =============================================================================
# XBOOKING BACKEND - STARTUP COMMANDS (Windows PowerShell)
# =============================================================================
# This file contains all the commands needed to start the Xbooking backend
# Redis is already running, so we only need to start Django, Celery Worker, and Celery Beat
# =============================================================================

Write-Host "==========================================" -ForegroundColor Green
Write-Host "XBOOKING BACKEND - STARTUP GUIDE" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""

# =============================================================================
# TERMINAL 1: Django Development Server
# =============================================================================
Write-Host "TERMINAL 1: Django Development Server" -ForegroundColor Cyan
Write-Host "--------------------------------------" -ForegroundColor Cyan
Write-Host "cd C:\Users\Admin\Xbooking_backend\Xbooking"
Write-Host "python manage.py runserver"
Write-Host ""
Write-Host "Server will start at: http://127.0.0.1:8000" -ForegroundColor Yellow
Write-Host "API Docs: http://127.0.0.1:8000/api/docs/" -ForegroundColor Yellow
Write-Host ""

# =============================================================================
# TERMINAL 2: Celery Worker
# =============================================================================
Write-Host "TERMINAL 2: Celery Worker" -ForegroundColor Cyan
Write-Host "--------------------------------------" -ForegroundColor Cyan
Write-Host "cd C:\Users\Admin\Xbooking_backend\Xbooking"
Write-Host "celery -A Xbooking worker -l info --pool=solo"
Write-Host ""
Write-Host "Note: Use --pool=solo for Windows compatibility" -ForegroundColor Yellow
Write-Host ""

# =============================================================================
# TERMINAL 3: Celery Beat (Scheduler)
# =============================================================================
Write-Host "TERMINAL 3: Celery Beat" -ForegroundColor Cyan
Write-Host "--------------------------------------" -ForegroundColor Cyan
Write-Host "cd C:\Users\Admin\Xbooking_backend\Xbooking"
Write-Host "celery -A Xbooking beat -l info"
Write-Host ""
Write-Host "This runs periodic tasks like reminders and QR expiry" -ForegroundColor Yellow
Write-Host ""

# =============================================================================
# ONE-TIME SETUP COMMANDS
# =============================================================================
Write-Host "==========================================" -ForegroundColor Green
Write-Host "ONE-TIME SETUP COMMANDS" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "1. Apply migrations:"
Write-Host "   python manage.py migrate"
Write-Host ""
Write-Host "2. Create superuser:"
Write-Host "   python manage.py createsuperuser"
Write-Host ""
Write-Host "3. Populate workspaces (creates 10 workspaces with branches/spaces):" -ForegroundColor Yellow
Write-Host "   python manage.py populate_workspaces"
Write-Host ""
Write-Host "   Or specify number of workspaces:"
Write-Host "   python manage.py populate_workspaces --workspaces 5"
Write-Host ""
Write-Host "   Or specify admin email:"
Write-Host "   python manage.py populate_workspaces --admin-email admin@xbooking.com"
Write-Host ""
Write-Host "4. Collect static files (for production):"
Write-Host "   python manage.py collectstatic --noinput"
Write-Host ""

# =============================================================================
# CHECKING SERVICES
# =============================================================================
Write-Host "==========================================" -ForegroundColor Green
Write-Host "CHECKING RUNNING SERVICES" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Check Redis is running:"
Write-Host "   redis-cli ping"
Write-Host "   (Should return: PONG)"
Write-Host ""

# =============================================================================
# QUICK START
# =============================================================================
Write-Host "==========================================" -ForegroundColor Green
Write-Host "QUICK START - Copy these commands" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "TERMINAL 1 (Django):" -ForegroundColor Yellow
Write-Host "cd C:\Users\Admin\Xbooking_backend\Xbooking; python manage.py runserver" -ForegroundColor White
Write-Host ""
Write-Host "TERMINAL 2 (Celery Worker):" -ForegroundColor Yellow
Write-Host "cd C:\Users\Admin\Xbooking_backend\Xbooking; celery -A Xbooking worker -l info --pool=solo" -ForegroundColor White
Write-Host ""
Write-Host "TERMINAL 3 (Celery Beat):" -ForegroundColor Yellow
Write-Host "cd C:\Users\Admin\Xbooking_backend\Xbooking; celery -A Xbooking beat -l info" -ForegroundColor White
Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "READY TO START! Open 3 terminals and run commands above" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
