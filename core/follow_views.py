from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .models import FollowRequest, Follow, UserProfile, Notification
from .notification_utils import NotificationManager
import json

@login_required
def send_follow_request(request, username):
    """Send a follow request to another user"""
    if request.method == 'POST':
        to_user = get_object_or_404(User, username=username)
        from_user = request.user

        # Can't follow yourself
        if from_user == to_user:
            if request.headers.get('content-type') == 'application/json':
                return JsonResponse({'error': 'You cannot follow yourself'}, status=400)
            messages.error(request, 'You cannot follow yourself.')
            return redirect('profile', username=username)

        # Check if already following or request exists
        existing_request = FollowRequest.objects.filter(from_user=from_user, to_user=to_user).first()
        already_following = Follow.objects.filter(follower=from_user, following=to_user).exists()

        if already_following:
            if request.headers.get('content-type') == 'application/json':
                return JsonResponse({'error': 'Already following this user'}, status=400)
            messages.info(request, f'You are already following {to_user.username}.')
            return redirect('profile', username=username)

        if existing_request:
            if existing_request.status == 'pending':
                if request.headers.get('content-type') == 'application/json':
                    return JsonResponse({'error': 'Follow request already sent'}, status=400)
                messages.info(request, f'Follow request already sent to {to_user.username}.')
            elif existing_request.status == 'declined':
                # Allow re-sending if previously declined
                existing_request.status = 'pending'
                existing_request.save()
                if request.headers.get('content-type') == 'application/json':
                    return JsonResponse({'success': 'Follow request sent'})
                messages.success(request, f'Follow request sent to {to_user.username}.')
        else:
            # Create new follow request
            follow_request = FollowRequest.objects.create(from_user=from_user, to_user=to_user)
            
            # If the account is public, auto-accept the request
            if not to_user.profile.is_private:
                follow_request.accept()
                message = f'You are now following {to_user.username}.'
                notification_type = 'new_follower'
            else:
                message = f'Follow request sent to {to_user.username}.'
                notification_type = 'follow_request'

            # Create notification
            Notification.objects.create(
                recipient=to_user,
                sender=from_user,
                notification_type=notification_type,
                message=f'{from_user.username} wants to follow you.' if notification_type == 'follow_request' else f'{from_user.username} started following you.'
            )

            if request.headers.get('content-type') == 'application/json':
                return JsonResponse({'success': message})
            messages.success(request, message)

        # Check if request came from search page
        referer = request.META.get('HTTP_REFERER', '')
        if 'search' in referer:
            return redirect('search')
        return redirect('profile', username=username)

    return redirect('home')

@login_required
def unfollow_user(request, username):
    """Unfollow a user"""
    if request.method == 'POST':
        to_user = get_object_or_404(User, username=username)
        from_user = request.user

        # Remove follow relationship
        follow_relationship = Follow.objects.filter(follower=from_user, following=to_user).first()
        if follow_relationship:
            follow_relationship.delete()
            
            # Also remove any accepted follow request
            FollowRequest.objects.filter(
                from_user=from_user, 
                to_user=to_user, 
                status='accepted'
            ).delete()

            if request.headers.get('content-type') == 'application/json':
                return JsonResponse({'success': f'Unfollowed {to_user.username}'})
            messages.success(request, f'You unfollowed {to_user.username}.')
        else:
            if request.headers.get('content-type') == 'application/json':
                return JsonResponse({'error': 'You are not following this user'}, status=400)
            messages.error(request, 'You are not following this user.')

        # Check if request came from search page
        referer = request.META.get('HTTP_REFERER', '')
        if 'search' in referer:
            return redirect('search')
        return redirect('profile', username=username)
    
    return redirect('home')

@login_required
def accept_follow_request(request, request_id):
    """Accept a follow request"""
    if request.method == 'POST':
        follow_request = get_object_or_404(FollowRequest, id=request_id, to_user=request.user, status='pending')
        
        follow_request.accept()
        
        # Create notification for the requester
        Notification.objects.create(
            recipient=follow_request.from_user,
            sender=request.user,
            notification_type='follow_accepted',
            message=f'{request.user.username} accepted your follow request.'
        )

        if request.headers.get('content-type') == 'application/json':
            return JsonResponse({'success': f'Accepted follow request from {follow_request.from_user.username}'})
        
        messages.success(request, f'Accepted follow request from {follow_request.from_user.username}.')
        return redirect('follow_requests')

    return redirect('home')

@login_required
def decline_follow_request(request, request_id):
    """Decline a follow request"""
    if request.method == 'POST':
        follow_request = get_object_or_404(FollowRequest, id=request_id, to_user=request.user, status='pending')
        
        follow_request.decline()

        if request.headers.get('content-type') == 'application/json':
            return JsonResponse({'success': f'Declined follow request from {follow_request.from_user.username}'})
        
        messages.success(request, f'Declined follow request from {follow_request.from_user.username}.')
        return redirect('follow_requests')

    return redirect('home')

@login_required
def follow_requests_view(request):
    """View all pending follow requests"""
    pending_requests = FollowRequest.objects.filter(
        to_user=request.user, 
        status='pending'
    ).select_related('from_user', 'from_user__profile')

    paginator = Paginator(pending_requests, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'follow_requests': page_obj,
        'total_requests': pending_requests.count()
    }
    return render(request, 'follow_requests.html', context)

@login_required
def followers_view(request, username):
    """View followers of a user"""
    user = get_object_or_404(User, username=username)
    is_own_profile = request.user == user
    
    # Check if user can view followers (public account or following each other)
    can_view = (
        user == request.user or
        not user.profile.is_private or
        Follow.is_following(request.user, user)
    )

    if not can_view:
        messages.error(request, 'This account is private.')
        return redirect('profile', username=username)

    followers = Follow.objects.filter(following=user).select_related('follower', 'follower__profile')
    
    # Get pending follow requests if viewing own profile
    pending_requests = None
    total_pending = 0
    if is_own_profile:
        pending_requests = FollowRequest.objects.filter(
            to_user=user, 
            status='pending'
        ).select_related('from_user', 'from_user__profile')[:5]  # Show first 5
        total_pending = FollowRequest.objects.filter(to_user=user, status='pending').count()
    
    paginator = Paginator(followers, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'user': user,
        'followers': page_obj,
        'total_followers': followers.count(),
        'view_type': 'followers',
        'is_own_profile': is_own_profile,
        'pending_requests': pending_requests,
        'total_pending': total_pending,
    }
    return render(request, 'follow_list.html', context)

@login_required
def following_view(request, username):
    """View users that a user is following"""
    user = get_object_or_404(User, username=username)
    
    # Check if user can view following list
    can_view = (
        user == request.user or
        not user.profile.is_private or
        Follow.is_following(request.user, user)
    )

    if not can_view:
        messages.error(request, 'This account is private.')
        return redirect('profile', username=username)

    following = Follow.objects.filter(follower=user).select_related('following', 'following__profile')
    
    paginator = Paginator(following, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'user': user,
        'following': page_obj,
        'total_following': following.count(),
        'view_type': 'following'
    }
    return render(request, 'follow_list.html', context)

@login_required
def suggested_users_view(request):
    """Get suggested users to follow"""
    current_user = request.user
    
    # Get users that current user is not following
    following_ids = Follow.objects.filter(follower=current_user).values_list('following_id', flat=True)
    pending_request_ids = FollowRequest.objects.filter(
        from_user=current_user, 
        status='pending'
    ).values_list('to_user_id', flat=True)
    
    # Exclude current user, already following, and pending requests
    exclude_ids = list(following_ids) + list(pending_request_ids) + [current_user.id]
    
    # Get suggested users (you can implement more complex algorithm here)
    suggested_users = User.objects.exclude(id__in=exclude_ids).select_related('profile')[:10]

    context = {
        'suggested_users': suggested_users
    }
    return render(request, 'suggested_users.html', context)

@login_required
def get_follow_status(request, username):
    """Get follow status for a user (AJAX endpoint)"""
    target_user = get_object_or_404(User, username=username)
    current_user = request.user

    if current_user == target_user:
        status = 'self'
    elif Follow.is_following(current_user, target_user):
        status = 'following'
    else:
        pending_request = FollowRequest.objects.filter(
            from_user=current_user,
            to_user=target_user,
            status='pending'
        ).exists()
        status = 'requested' if pending_request else 'not_following'

    return JsonResponse({
        'status': status,
        'is_private': target_user.profile.is_private,
        'followers_count': target_user.profile.followers_count,
        'following_count': target_user.profile.following_count
    })