from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib import messages
from django.db.models import Q, Count, Max
from django.core.paginator import Paginator
from .message_models import Thread, Message, MessageRead
from .models import Follow
import json

@login_required
def messages_home(request):
    """Main messages page showing all chat threads"""
    # Get all threads for current user
    threads = Thread.objects.filter(
        participants=request.user
    ).annotate(
        unread_count=Count(
            'messages',
            filter=Q(messages__is_read=False) & ~Q(messages__sender=request.user)
        )
    ).prefetch_related(
        'participants', 
        'messages'
    ).order_by('-updated_at')
    
    # Add additional info to each thread
    for thread in threads:
        thread.other_participant = thread.get_other_participant(request.user)
        thread.user_unread_count = thread.get_unread_count(request.user)
    
    # Get total unread count
    total_unread = sum(thread.user_unread_count for thread in threads)
    
    context = {
        'threads': threads,
        'total_unread': total_unread,
    }
    return render(request, 'messages/messages_home.html', context)

@login_required
def chat_thread(request, thread_id):
    """Individual chat thread view"""
    thread = get_object_or_404(Thread, id=thread_id, participants=request.user)
    
    # Mark messages as read
    thread.mark_as_read(request.user)
    
    # Get messages with pagination
    messages_list = thread.messages.select_related('sender', 'sender__profile').order_by('created_at')
    paginator = Paginator(messages_list, 50)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Get other participant info
    other_participant = thread.get_other_participant(request.user)
    
    context = {
        'thread': thread,
        'messages': page_obj,
        'other_participant': other_participant,
        'is_following': Follow.is_following(request.user, other_participant) if other_participant else False,
    }
    return render(request, 'messages/chat_thread.html', context)

@login_required
def send_message(request, thread_id):
    """Send a message in a thread"""
    if request.method != 'POST':
        return redirect('chat_thread', thread_id=thread_id)
    
    thread = get_object_or_404(Thread, id=thread_id, participants=request.user)
    
    message_text = request.POST.get('message_text', '').strip()
    attachment = request.FILES.get('attachment')
    
    if not message_text and not attachment:
        messages.error(request, 'Message cannot be empty')
        return redirect('chat_thread', thread_id=thread_id)
    
    # Create message
    message = Message.objects.create(
        thread=thread,
        sender=request.user,
        text=message_text,
        attachment=attachment
    )
    
    # If AJAX request, return JSON response
    if request.headers.get('content-type') == 'application/json':
        return JsonResponse({
            'success': True,
            'message_id': message.id,
            'message_text': message.text,
            'sender': message.sender.username,
            'created_at': message.created_at.strftime('%H:%M')
        })
    
    messages.success(request, 'Message sent successfully')
    return redirect('chat_thread', thread_id=thread_id)

@login_required
def start_chat(request, username):
    """Start a new chat with a user"""
    other_user = get_object_or_404(User, username=username)
    
    if other_user == request.user:
        messages.error(request, 'You cannot chat with yourself')
        return redirect('messages_home')
    
    # Get or create thread
    thread, created = Thread.get_or_create_thread(request.user, other_user)
    
    if created:
        messages.success(request, f'Started new chat with {other_user.username}')
    
    return redirect('chat_thread', thread_id=thread.id)

@login_required
def delete_thread(request, thread_id):
    """Delete a chat thread"""
    if request.method != 'POST':
        return redirect('messages_home')
    
    thread = get_object_or_404(Thread, id=thread_id, participants=request.user)
    
    # For 1-on-1 chats, just remove the user from participants
    if not thread.is_group:
        thread.participants.remove(request.user)
        if thread.participants.count() == 0:
            thread.delete()
    else:
        # For group chats, remove user or delete if empty
        thread.participants.remove(request.user)
        if thread.participants.count() == 0:
            thread.delete()
    
    messages.success(request, 'Chat deleted successfully')
    return redirect('messages_home')

@login_required
def search_users(request):
    """Search users to start a chat with"""
    query = request.GET.get('q', '').strip()
    
    if not query:
        return JsonResponse({'users': []})
    
    # Search users (exclude current user)
    users = User.objects.filter(
        Q(username__icontains=query) |
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query)
    ).exclude(id=request.user.id).prefetch_related('profile')[:10]
    
    users_data = []
    for user in users:
        # Safely get profile picture
        profile_picture_url = None
        try:
            if hasattr(user, 'profile') and user.profile and user.profile.profile_picture:
                profile_picture_url = user.profile.profile_picture.url
        except:
            profile_picture_url = None
        
        users_data.append({
            'id': user.id,
            'username': user.username,
            'full_name': f"{user.first_name} {user.last_name}".strip() or user.username,
            'profile_picture': profile_picture_url,
            'is_following': Follow.is_following(request.user, user),
        })
    
    return JsonResponse({'users': users_data})

@login_required
def share_post(request, post_id):
    """Share a post via message"""
    from .post_models import Post
    
    post = get_object_or_404(Post, id=post_id)
    
    if request.method == 'GET':
        # Show share dialog with user list
        # Get recent chat partners
        recent_threads = Thread.objects.filter(
            participants=request.user
        ).prefetch_related('participants')[:10]
        
        recent_users = []
        for thread in recent_threads:
            other_user = thread.get_other_participant(request.user)
            if other_user:
                recent_users.append(other_user)
        
        context = {
            'post': post,
            'recent_users': recent_users,
        }
        return render(request, 'messages/share_post.html', context)
    
    elif request.method == 'POST':
        # Send post to selected users
        user_ids = request.POST.getlist('user_ids')
        message_text = request.POST.get('message_text', '').strip()
        
        if not user_ids:
            messages.error(request, 'Please select at least one user')
            return redirect('share_post', post_id=post_id)
        
        shared_count = 0
        for user_id in user_ids:
            try:
                other_user = User.objects.get(id=user_id)
                thread, created = Thread.get_or_create_thread(request.user, other_user)
                
                # Create message with shared post
                Message.objects.create(
                    thread=thread,
                    sender=request.user,
                    text=message_text,
                    shared_post=post
                )
                shared_count += 1
            except User.DoesNotExist:
                continue
        
        messages.success(request, f'Post shared with {shared_count} user(s)')
        return redirect('post_detail', post_id=post_id)

@login_required
def message_status(request):
    """Get unread message count (for AJAX)"""
    total_unread = Thread.objects.filter(
        participants=request.user
    ).annotate(
        unread_count=Count(
            'messages',
            filter=Q(messages__is_read=False) & ~Q(messages__sender=request.user)
        )
    ).aggregate(
        total=Count('unread_count')
    )['total'] or 0
    
    return JsonResponse({'unread_count': total_unread})

@login_required
def mark_thread_read(request, thread_id):
    """Mark all messages in thread as read"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    thread = get_object_or_404(Thread, id=thread_id, participants=request.user)
    thread.mark_as_read(request.user)
    
    return JsonResponse({'success': True})

@login_required
def delete_message(request, message_id):
    """Delete a specific message"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    message = get_object_or_404(Message, id=message_id, sender=request.user)
    message.is_deleted = True
    message.save()
    
    if request.headers.get('content-type') == 'application/json':
        return JsonResponse({'success': True})
    
    messages.success(request, 'Message deleted')
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/messages/'))
