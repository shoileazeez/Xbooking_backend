"""
Custom middleware to disable CSRF protection for API endpoints
"""
from django.utils.deprecation import MiddlewareMixin


class DisableCSRFForAPIMiddleware(MiddlewareMixin):
    """Disable CSRF for API endpoints that use token authentication"""
    
    def process_request(self, request):
        """Mark API requests as CSRF exempt"""
        if request.path.startswith('/api/'):
            setattr(request, '_dont_enforce_csrf_checks', True)
