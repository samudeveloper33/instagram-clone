from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
from django.contrib import messages
from .post_models import Post, Like, Comment, SavedPost
from .notification_utils import NotificationManager

@login_required
@require_POST
def toggle_like(request, post_id):
    """Toggle like/unlike for a post"""
    post = get_object_or_404(Post, id=post_id)
    like, created = Like.objects.get_or_create(user=request.user, post=post)
    
    if not created:
        # Unlike - delete the like
        like.delete()
        # Delete the like notification
        NotificationManager.delete_like_notification(post, request.user)
    else:
        # Like - create notification using NotificationManager
        NotificationManager.create_like_notification(post, request.user)
    
    # Redirect back to the referring page
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/home/'))

@login_required
@require_POST
def add_comment(request, post_id):
    """Add a comment to a post"""
    post = get_object_or_404(Post, id=post_id)
    
    if post.comments_disabled:
        messages.error(request, 'Comments are disabled for this post')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/home/'))
    
    comment_text = request.POST.get('comment_text', '').strip()
    
    if not comment_text:
        messages.error(request, 'Comment text is required')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/home/'))
    
    if len(comment_text) > 500:
        messages.error(request, 'Comment is too long (max 500 characters)')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/home/'))
    
    comment = Comment.objects.create(
        user=request.user,
        post=post,
        text=comment_text
    )
    
    # Create notification for post owner using NotificationManager
    NotificationManager.create_comment_notification(comment, post)
    
    messages.success(request, 'Comment added successfully!')
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/home/'))

@login_required
@require_POST
def toggle_save(request, post_id):
    """Toggle save/unsave for a post"""
    post = get_object_or_404(Post, id=post_id)
    saved_post, created = SavedPost.objects.get_or_create(user=request.user, post=post)
    
    if not created:
        # Unsave - delete the saved post
        saved_post.delete()
        messages.success(request, 'Post removed from saved')
    else:
        # Save - saved post was created
        messages.success(request, 'Post saved successfully!')
    
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/home/'))

@login_required
def post_detail(request, post_id):
    """Get detailed view of a post with comments"""
    post = get_object_or_404(Post, id=post_id)
    comments = post.comments.select_related('user', 'user__profile').order_by('created_at')
    
    # Add interaction status
    post.is_liked_by_current_user = post.is_liked_by(request.user)
    post.is_saved_by_current_user = post.is_saved_by(request.user)
    
    context = {
        'post': post,
        'comments': comments,
    }
    return render(request, 'post_detail.html', context)

@login_required
def create_post(request):
    """Create a new post"""
    if request.method == 'GET':
        return render(request, 'create_post.html')
    
    elif request.method == 'POST':
        caption = request.POST.get('caption', '').strip()
        location = request.POST.get('location', '').strip()
        
        # Handle media files
        media_files = request.FILES.getlist('media_files')
        if not media_files:
            messages.error(request, 'At least one media file is required')
            return render(request, 'create_post.html')
        
        # Create the post
        post = Post.objects.create(
            user=request.user,
            caption=caption,
            location=location
        )
        
        from .post_models import PostMedia
        for i, media_file in enumerate(media_files):
            PostMedia.objects.create(
                post=post,
                media_file=media_file,
                order=i,
                alt_text=request.POST.get(f'alt_text_{i}', '')
            )
        
        messages.success(request, 'Post created successfully!')
        return redirect('home')

@login_required
def user_posts(request, username):
    """Get posts for a specific user"""
    user = get_object_or_404(User, username=username)
    posts = Post.objects.filter(user=user).select_related('user', 'user__profile').prefetch_related('media_files')
    
    context = {
        'profile_user': user,
        'posts': posts,
        'posts_count': posts.count()
    }
    return render(request, 'user_posts.html', context)

@login_required
@require_POST
def delete_post(request, post_id):
    """Delete a post (only by the post owner)"""
    post = get_object_or_404(Post, id=post_id)
    
    # Check if the current user is the owner of the post
    if post.user != request.user:
        messages.error(request, 'You can only delete your own posts')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/home/'))
    
    # Delete the post (this will cascade delete related media, likes, comments, etc.)
    post.delete()
    messages.success(request, 'Post deleted successfully!')
    
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/home/'))
