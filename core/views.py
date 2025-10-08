from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q
from django.template.loader import render_to_string
import re
from .models import FollowRequest, User, Follow, RecentSearch

# Create your views here.
def base_view(request):
    """Base view - redirect to signin if not authenticated, otherwise redirect to home"""
    if not request.user.is_authenticated:
        return redirect('signin')
    return redirect('home')

@login_required
def explore_view(request):
    """Explore page - shows all public posts from all users"""
    from .models import UserProfile
    from .post_models import Post
    from django.contrib.auth.models import User
    
    # Get pending requests count for navigation badge
    pending_requests_count = FollowRequest.objects.filter(
        to_user=request.user, 
        status='pending'
    ).count()
    
    # Get all posts from all users (excluding current user's posts)
    explore_posts = Post.objects.exclude(
        user=request.user
    ).select_related('user', 'user__profile').prefetch_related('media_files', 'post_likes').order_by('-created_at')[:30]
    
    # Add liked status to each post
    for post in explore_posts:
        post.is_liked_by_current_user = post.is_liked_by(request.user)
    
    context = {
        'pending_requests_count': pending_requests_count,
        'explore_posts': explore_posts,
    }
    return render(request, 'explore.html', context)

@login_required
def home_view(request):
    """Home page for authenticated users"""
    from .models import UserProfile
    from .story_models import Story
    from .post_models import Post
    from django.contrib.auth.models import User
    
    # Ensure current user has a profile
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    if created:
        print(f"Created new profile for user: {request.user.username}")
    
    # Get pending follow requests for current user
    pending_requests = FollowRequest.objects.filter(
        to_user=request.user, 
        status='pending'
    ).select_related('from_user', 'from_user__profile')[:10]
    
    # Get pending requests count for navigation badge
    pending_requests_count = FollowRequest.objects.filter(
        to_user=request.user, 
        status='pending'
    ).count()
    
    # Get suggested users (exclude current user, already following, and pending requests)
    following_ids = request.user.following.values_list('following_id', flat=True)
    pending_request_ids = request.user.sent_follow_requests.filter(
        status='pending'
    ).values_list('to_user_id', flat=True)
    
    exclude_ids = list(following_ids) + list(pending_request_ids) + [request.user.id]
    suggested_users = User.objects.exclude(id__in=exclude_ids).select_related('profile')[:10]
    
    # Get posts for home feed (from followed users + own posts)
    feed_posts = Post.get_feed_posts(request.user)[:20]  # Limit to 20 posts
    
    # Add liked status to each post
    for post in feed_posts:
        post.is_liked_by_current_user = post.is_liked_by(request.user)
    
    # Get stories for home feed
    # Get users that current user follows
    following_users = User.objects.filter(
        followers__follower=request.user
    ).prefetch_related('stories')
    
    # Get stories from followed users
    users_with_stories = []
    for user in following_users:
        user_stories = Story.get_user_active_stories(user)
        if user_stories.exists():
            users_with_stories.append({
                'user': user,
                'stories': user_stories,
                'is_own': False,
                'latest_story': user_stories.first()
            })
    
    # Check if current user has stories
    user_has_stories = Story.get_user_active_stories(request.user).exists()
    
    context = {
        'pending_requests': pending_requests,
        'pending_requests_count': pending_requests_count,
        'suggested_users': suggested_users,
        'users_with_stories': users_with_stories,
        'user_has_stories': user_has_stories,
        'feed_posts': feed_posts,
    }
    return render(request, 'home.html', context)

@login_required
def search_view(request):
    """Enhanced search page with recent searches and suggested users"""
    query = request.GET.get('q', '').strip()
    search_results = []
    recent_searches = []
    suggested_users = []
    
    # Get pending requests count for navigation badge
    pending_requests_count = FollowRequest.objects.filter(
        to_user=request.user, 
        status='pending'
    ).count()
    
    if query and len(query) >= 1:
        # Search users by username, first name, or last name
        search_results = User.objects.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        ).exclude(id=request.user.id).select_related('profile')[:20]
        
        # Add follow status for each search result
        for user in search_results:
            user.is_following = Follow.is_following(request.user, user)
            user.has_pending_request = FollowRequest.objects.filter(
                from_user=request.user,
                to_user=user,
                status='pending'
            ).exists()
    else:
        # Get recent searches
        recent_searches = RecentSearch.get_recent_searches(request.user, limit=10)
        for search in recent_searches:
            search.searched_user.is_following = Follow.is_following(request.user, search.searched_user)
            search.searched_user.has_pending_request = FollowRequest.objects.filter(
                from_user=request.user,
                to_user=search.searched_user,
                status='pending'
            ).exists()
        
        # Get suggested users (users not followed by current user)
        following_ids = Follow.objects.filter(follower=request.user).values_list('following_id', flat=True)
        suggested_users = User.objects.exclude(
            Q(id=request.user.id) | Q(id__in=following_ids)
        ).select_related('profile').order_by('?')[:10]
        
        for user in suggested_users:
            user.is_following = False  # By definition, these are not followed
            user.has_pending_request = FollowRequest.objects.filter(
                from_user=request.user,
                to_user=user,
                status='pending'
            ).exists()
    
    context = {
        'query': query,
        'search_results': search_results,
        'recent_searches': recent_searches,
        'suggested_users': suggested_users,
        'pending_requests_count': pending_requests_count,
    }
    return render(request, 'search.html', context)

@login_required
def add_recent_search(request, username):
    """Add a user to recent searches when their profile is visited from search"""
    try:
        searched_user = User.objects.get(username=username)
        RecentSearch.add_search(request.user, searched_user)
    except User.DoesNotExist:
        pass
    return redirect('profile', username=username)

@login_required
def clear_recent_searches(request):
    """Clear all recent searches for the current user"""
    if request.method == 'POST':
        RecentSearch.objects.filter(user=request.user).delete()
    return redirect('search')

@login_required
def remove_recent_search(request, username):
    """Remove a specific user from recent searches"""
    if request.method == 'POST':
        try:
            searched_user = User.objects.get(username=username)
            RecentSearch.objects.filter(user=request.user, searched_user=searched_user).delete()
        except User.DoesNotExist:
            pass
    return redirect('search')

@login_required
def spa_content_view(request, page):
    """Handle SPA content loading for smooth navigation"""
    try:
        # Import the profile_view function
        from .auth_view import profile_view
        from .story_views import story_home_view
        from .message_views import messages_home
        from .notification_views import notifications_page
        from .post_views import create_post
        
        # Map page names to view functions
        page_mapping = {
            'home': home_view,
            'search': search_view,
            'explore': explore_view,
            'stories': story_home_view,
            'messages': messages_home,
            'notifications': notifications_page,
            'create': create_post,
            'profile': lambda req: profile_view(req, username=None),  # Call with username=None for own profile
        }
        
        # Get the view function for the requested page
        view_func = page_mapping.get(page)
        if not view_func:
            return JsonResponse({'error': 'Page not found'}, status=404)
        
        # Call the view function to get the response
        response = view_func(request)
        
        # Extract content from the response
        if hasattr(response, 'content'):
            content = response.content.decode('utf-8')
            
            # Extract the main content - look for the content inside main tag
            # Remove the main tag wrapper but keep the inner content
            main_match = re.search(r'<main[^>]*>(.*?)</main>', content, re.DOTALL)
            if main_match:
                main_content = main_match.group(1).strip()
            else:
                # Fallback: try to extract content block
                block_match = re.search(r'{% block content %}(.*?){% endblock %}', content, re.DOTALL)
                if block_match:
                    main_content = block_match.group(1).strip()
                else:
                    # Last fallback: look for a div with common content classes
                    div_match = re.search(r'<div[^>]*class="[^"]*(?:container|content|page)[^"]*"[^>]*>(.*?)</div>', content, re.DOTALL)
                    if div_match:
                        main_content = div_match.group(1).strip()
                    else:
                        main_content = content
            
            return JsonResponse({
                'content': main_content,
                'title': f'Instagram - {page.title()}',
                'page': page
            })
        
        return JsonResponse({'error': 'Failed to load content'}, status=500)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
