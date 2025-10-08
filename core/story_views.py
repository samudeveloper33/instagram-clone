from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils import timezone
from django.db.models import Q, Exists, OuterRef
from .story_models import Story, StoryView, StoryHighlight
from .models import Follow
import json
import os

@login_required
def story_home_view(request):
    """View stories from followed users"""
    # Get users that current user follows
    following_users = User.objects.filter(
        followers__follower=request.user
    ).prefetch_related('stories')
    
    # Get active stories from followed users + own stories
    users_with_stories = []
    
    # Add own stories first
    own_stories = Story.get_user_active_stories(request.user)
    if own_stories.exists():
        users_with_stories.append({
            'user': request.user,
            'stories': own_stories,
            'is_own': True,
            'latest_story': own_stories.first()
        })
    
    # Add followed users' stories
    for user in following_users:
        user_stories = Story.get_user_active_stories(user)
        if user_stories.exists():
            users_with_stories.append({
                'user': user,
                'stories': user_stories,
                'is_own': False,
                'latest_story': user_stories.first()
            })
    
    context = {
        'users_with_stories': users_with_stories,
    }
    return render(request, 'stories/story_home.html', context)

@login_required
def story_viewer(request, username, story_id=None):
    """View a specific user's stories"""
    user = get_object_or_404(User, username=username)
    stories = Story.get_user_active_stories(user).order_by('created_at')
    
    if not stories.exists():
        messages.info(request, f'{username} has no active stories.')
        return redirect('story_home')
    
    # Check if user can view stories (public profile or following)
    can_view = (
        user == request.user or
        not user.profile.is_private or
        Follow.is_following(request.user, user)
    )
    
    if not can_view:
        messages.error(request, 'You cannot view this user\'s stories.')
        return redirect('story_home')
    
    # Get specific story or first story
    if story_id:
        current_story = get_object_or_404(stories, id=story_id)
    else:
        current_story = stories.first()
    
    # Mark story as viewed
    if user != request.user:
        StoryView.objects.get_or_create(
            story=current_story,
            viewer=request.user
        )
    
    # Get navigation info
    current_index = list(stories.values_list('id', flat=True)).index(current_story.id)
    
    # Convert stories to JSON for JavaScript
    stories_data = []
    for story in stories:
        stories_data.append({
            'id': story.id,
            'media_url': story.media_file.url if story.media_file else '',
            'media_type': story.media_type,
            'caption': story.caption,
            'created_at': story.created_at.isoformat(),
        })
    stories_json = json.dumps(stories_data)
    
    context = {
        'user': user,
        'stories': stories,
        'current_story': current_story,
        'current_index': current_index,
        'total_stories': stories.count(),
        'can_view': can_view,
        'stories_json': stories_json,
    }
    return render(request, 'stories/story_viewer.html', context)

@login_required
def create_story_view(request):
    """Create a new story"""
    if request.method == 'POST':
        media_file = request.FILES.get('media_file')
        caption = request.POST.get('caption', '')
        background_color = request.POST.get('background_color', '#000000')
        text_color = request.POST.get('text_color', '#ffffff')
        
        if not media_file:
            return JsonResponse({'error': 'No media file provided'}, status=400)
        
        # Validate file type and size
        max_size = 50 * 1024 * 1024  # 50MB
        if media_file.size > max_size:
            return JsonResponse({'error': 'File too large. Maximum 50MB allowed.'}, status=400)
        
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.mp4', '.mov', '.webm']
        file_extension = os.path.splitext(media_file.name)[1].lower()
        
        if file_extension not in allowed_extensions:
            return JsonResponse({'error': 'Invalid file type. Only images and videos allowed.'}, status=400)
        
        try:
            story = Story.objects.create(
                user=request.user,
                media_file=media_file,
                caption=caption,
                background_color=background_color,
                text_color=text_color
            )
            
            return JsonResponse({
                'success': True,
                'story_id': story.id,
                'message': 'Story created successfully!'
            })
            
        except Exception as e:
            return JsonResponse({'error': f'Error creating story: {str(e)}'}, status=500)
    
    return render(request, 'stories/create_story.html')

@login_required
def delete_story(request, story_id):
    """Delete a story"""
    if request.method == 'POST':
        story = get_object_or_404(Story, id=story_id, user=request.user)
        
        # Delete the media file
        if story.media_file:
            try:
                default_storage.delete(story.media_file.name)
            except:
                pass
        
        story.delete()
        
        if request.headers.get('content-type') == 'application/json':
            return JsonResponse({'success': 'Story deleted successfully'})
        
        messages.success(request, 'Story deleted successfully.')
        return redirect('story_home')
    
    return redirect('story_home')

@login_required
def story_viewers(request, story_id):
    """View who has seen a story"""
    story = get_object_or_404(Story, id=story_id, user=request.user)
    viewers = StoryView.objects.filter(story=story).select_related('viewer', 'viewer__profile').order_by('-viewed_at')
    
    context = {
        'story': story,
        'viewers': viewers,
        'total_views': viewers.count()
    }
    return render(request, 'stories/story_viewers.html', context)

@login_required
def get_stories_data(request, username):
    """API endpoint to get user's stories data"""
    user = get_object_or_404(User, username=username)
    stories = Story.get_user_active_stories(user).order_by('created_at')
    
    # Check viewing permissions
    can_view = (
        user == request.user or
        not user.profile.is_private or
        Follow.is_following(request.user, user)
    )
    
    if not can_view:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    stories_data = []
    for story in stories:
        # Mark as viewed if not own story
        if user != request.user:
            StoryView.objects.get_or_create(story=story, viewer=request.user)
        
        stories_data.append({
            'id': story.id,
            'media_url': story.media_file.url,
            'media_type': story.media_type,
            'caption': story.caption,
            'created_at': story.created_at.isoformat(),
            'time_left': str(story.time_left),
            'views_count': story.views_count,
            'background_color': story.background_color,
            'text_color': story.text_color,
        })
    
    return JsonResponse({
        'user': {
            'username': user.username,
            'profile_picture': user.profile.profile_picture.url if user.profile.profile_picture else None,
        },
        'stories': stories_data,
        'total_count': len(stories_data)
    })

@login_required
def story_highlights_view(request, username):
    """View user's story highlights"""
    user = get_object_or_404(User, username=username)
    highlights = StoryHighlight.objects.filter(user=user).prefetch_related('stories')
    
    context = {
        'user': user,
        'highlights': highlights,
    }
    return render(request, 'stories/highlights.html', context)

@login_required
def create_highlight(request):
    """Create a new story highlight"""
    if request.method == 'POST':
        title = request.POST.get('title')
        story_ids = request.POST.getlist('story_ids')
        cover_image = request.FILES.get('cover_image')
        
        if not title or not story_ids:
            return JsonResponse({'error': 'Title and stories are required'}, status=400)
        
        # Get user's stories
        stories = Story.objects.filter(
            id__in=story_ids,
            user=request.user
        )
        
        if not stories.exists():
            return JsonResponse({'error': 'No valid stories found'}, status=400)
        
        highlight = StoryHighlight.objects.create(
            user=request.user,
            title=title,
            cover_image=cover_image
        )
        
        highlight.stories.set(stories)
        
        return JsonResponse({
            'success': True,
            'highlight_id': highlight.id,
            'message': 'Highlight created successfully!'
        })
    
    # Get user's stories for highlight creation
    user_stories = Story.objects.filter(user=request.user).order_by('-created_at')[:50]
    
    context = {
        'user_stories': user_stories,
    }
    return render(request, 'stories/create_highlight.html', context)