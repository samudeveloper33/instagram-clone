from django import template
from django.templatetags.static import static

register = template.Library()

@register.filter
def profile_picture_or_default(profile_picture):
    """Return profile picture URL or default avatar"""
    if profile_picture:
        try:
            # Check if file exists
            if profile_picture.storage.exists(profile_picture.name):
                return profile_picture.url
        except:
            pass
    
    # Return a default avatar - you can create a default image or use a placeholder service
    return "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100' height='100' viewBox='0 0 100 100'%3E%3Ccircle cx='50' cy='50' r='50' fill='%23e5e7eb'/%3E%3Cpath d='M50 45c-8.284 0-15-6.716-15-15s6.716-15 15-15 15 6.716 15 15-6.716 15-15 15zm0 10c16.569 0 30 13.431 30 30v10H20V85c0-16.569 13.431-30 30-30z' fill='%239ca3af'/%3E%3C/svg%3E"

@register.filter  
def avatar_url(user):
    """Get user avatar URL with fallback to default"""
    if hasattr(user, 'profile') and user.profile.profile_picture:
        return profile_picture_or_default(user.profile.profile_picture)
    return profile_picture_or_default(None)
