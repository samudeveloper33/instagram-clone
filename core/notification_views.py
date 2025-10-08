from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Notification
from .notification_utils import NotificationManager

@login_required
def notifications_page(request):
    """Display all notifications for the logged-in user"""
    notifications = Notification.objects.filter(
        recipient=request.user
    ).select_related('sender', 'sender__profile').order_by('-created_at')
    
    context = {
        'notifications': notifications,
    }
    
    return render(request, 'notifications.html', context)

@login_required
@require_POST
def mark_notification_read(request, notification_id):
    """Mark a single notification as read"""
    try:
        notification = Notification.objects.get(
            id=notification_id,
            recipient=request.user
        )
        notification.is_read = True
        notification.is_seen = True
        notification.save()
        return JsonResponse({'success': True})
    except Notification.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Notification not found'}, status=404)

@login_required
@require_POST
def mark_all_seen(request):
    """Mark all notifications as seen (removes red dot)"""
    NotificationManager.mark_all_as_seen(request.user)
    return JsonResponse({'success': True})

@login_required
@require_POST
def mark_all_read(request):
    """Mark all notifications as read"""
    Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).update(is_read=True, is_seen=True)
    return JsonResponse({'success': True})

@login_required
def get_notifications_count(request):
    """Get unread and unseen notification counts"""
    unread_count = NotificationManager.get_unread_count(request.user)
    unseen_count = NotificationManager.get_unseen_count(request.user)
    
    return JsonResponse({
        'unread_count': unread_count,
        'unseen_count': unseen_count
    })
