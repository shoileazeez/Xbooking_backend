"""
Landing Page View
"""
from django.views import generic


class LandingPageView(generic.TemplateView):
    """
    Landing page view that displays API documentation and information about Xbooking
    """
    template_name = "index.html"
