"""
Custom context processors for the films_app.
"""
from django.contrib.sites.models import Site

def site_context(request):
    """
    Add site information to the template context.
    This is needed for allauth templates that expect a 'site' variable.
    """
    try:
        site = Site.objects.get_current()
        return {'site': site}
    except Site.DoesNotExist:
        # Fallback if no site exists
        return {'site': {'name': 'YourCinemaFilms', 'domain': 'yourcinemafilms.onrender.com'}} 