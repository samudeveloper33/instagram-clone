from django.db.models import Count, Q
from .models import FollowRequest, Notification

def global_context(request):
    """Add global context variables to all templates"""
    context = {}
    
    if request.user.is_authenticated:
        # Get pending follow requests count
        context['pending_requests_count'] = FollowRequest.objects.filter(
            to_user=request.user, 
            status='pending'
        ).count()
        
        # Get total unread messages count
        try:
            from .message_models import Thread
            threads = Thread.objects.filter(participants=request.user)
            total_unread_messages = 0
            
            for thread in threads:
                unread_count = thread.messages.filter(
                    is_read=False
                ).exclude(sender=request.user).count()
                total_unread_messages += unread_count
            
            context['total_unread_messages'] = total_unread_messages
        except:
            context['total_unread_messages'] = 0
        
        # Get unread notifications count (for badge)
        context['unread_notifications_count'] = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
        
        # Get unseen notifications count (for red dot indicator)
        context['unseen_notifications_count'] = Notification.objects.filter(
            recipient=request.user,
            is_seen=False
        ).count()
    else:
        context['pending_requests_count'] = 0
        context['total_unread_messages'] = 0
        context['unread_notifications_count'] = 0
        context['unseen_notifications_count'] = 0
    
    return context
