from django.shortcuts import render
from django.views import generic
# Create your views here.


class LandingPageView(generic.TemplateView):
    """
    Landing page view that displays API documentation and information about Xbooking
    """
    template_name = "index.html"