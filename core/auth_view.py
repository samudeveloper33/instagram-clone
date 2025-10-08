from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
import json

def signin_view(request):
    """Handle user signin"""
    # Redirect to home if already authenticated
    if request.user.is_authenticated:
        return redirect('home')
        
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if username and password:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.first_name or user.username}!')
                return redirect('home')  # Redirect to home page after successful login
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Please provide both username and password.')
    
    return render(request, 'signin.html')

def signup_view(request):
    """Handle user signup"""
    # Redirect to home if already authenticated
    if request.user.is_authenticated:
        return redirect('home')
        
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        full_name = request.POST.get('full_name')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        
        # Validation
        if not all([username, email, full_name, password, password_confirm]):
            messages.error(request, 'All fields are required.')
            return render(request, 'signup.html')
        
        if password != password_confirm:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'signup.html')
        
        if len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return render(request, 'signup.html')
        
        # Additional validation
        if len(username) < 3:
            messages.error(request, 'Username must be at least 3 characters long.')
            return render(request, 'signup.html')
        
        if len(username) > 30:
            messages.error(request, 'Username must be less than 30 characters.')
            return render(request, 'signup.html')
        
        # Check for valid email format (basic check)
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            messages.error(request, 'Please enter a valid email address.')
            return render(request, 'signup.html')
        
        # Check if username already exists (username must be unique)
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists. Please choose a different username.')
            return render(request, 'signup.html')
        
        # Note: Email doesn't need to be unique in this system
        # Multiple users can have the same email if needed
        
        try:
            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=full_name.split()[0] if full_name else '',
                last_name=' '.join(full_name.split()[1:]) if len(full_name.split()) > 1 else ''
            )
            
            # Ensure UserProfile is created (should be created by signal)
            if not hasattr(user, 'profile'):
                from .models import UserProfile
                UserProfile.objects.create(user=user)
            
            # Automatically log in the user after registration
            # Specify backend explicitly since we have multiple auth backends configured
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, f'Welcome to Instagram, {user.first_name or user.username}!')
            return redirect('home')  # Redirect to home page after successful signup
            
        except Exception as e:
            # Log the actual error for debugging
            print(f"Registration error: {str(e)}")
            import traceback
            print(traceback.format_exc())
            messages.error(request, 'An error occurred during registration. Please try again.')
    
    return render(request, 'signup.html')

def signout_view(request):
    """Handle user signout"""
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('signin')

@login_required
def profile_view(request, username=None):
    """Display user profile (requires login)"""
    from django.shortcuts import get_object_or_404
    from .models import Follow, FollowRequest, UserProfile, RecentSearch
    from .story_models import Story
    
    if username:
        profile_user = get_object_or_404(User, username=username)
        # Add to recent searches if visiting someone else's profile
        if profile_user != request.user:
            RecentSearch.add_search(request.user, profile_user)
    else:
        profile_user = request.user
    
    # Ensure UserProfile exists for the user
    profile, created = UserProfile.objects.get_or_create(user=profile_user)
    if created:
        print(f"Created new profile for user: {profile_user.username}")
    
    # Ensure current user also has a profile
    if not hasattr(request.user, 'profile'):
        UserProfile.objects.get_or_create(user=request.user)
    
    # Get follow status
    is_own_profile = request.user == profile_user
    is_following = Follow.is_following(request.user, profile_user) if not is_own_profile else False
    has_pending_request = FollowRequest.objects.filter(
        from_user=request.user,
        to_user=profile_user,
        status='pending'
    ).exists() if not is_own_profile else False
    
    # Check if can view profile
    can_view_profile = (
        is_own_profile or
        not profile_user.profile.is_private or
        is_following
    )
    
    # Get user's active stories
    user_stories = Story.get_user_active_stories(profile_user).order_by('-created_at')
    
    # Get user's posts
    from .post_models import Post
    user_posts = []
    posts_count = 0
    if can_view_profile:
        user_posts = Post.objects.filter(user=profile_user).prefetch_related('media_files', 'post_likes', 'comments').order_by('-created_at')
        posts_count = user_posts.count()
    
    # Check if we can see follow button
    can_see_follow_button = not is_own_profile
    
    context = {
        'profile_user': profile_user,
        'is_own_profile': is_own_profile,
        'is_following': is_following,
        'has_pending_request': has_pending_request,
        'can_view_profile': can_view_profile,
        'can_see_follow_button': can_see_follow_button,
        'followers_count': profile_user.profile.followers_count,
        'following_count': profile_user.profile.following_count,
        'post_count': posts_count,
        'posts_count': posts_count,  # For template compatibility
        'user_posts': user_posts,
        'user_stories': user_stories,
    }
    return render(request, 'profile.html', context)

def forgot_password_view(request):
    """Handle forgot password requests using username"""
    if request.method == 'POST':
        username = request.POST.get('username')
        
        if not username:
            messages.error(request, 'Please enter your username.')
            return render(request, 'forgot_password.html')
        
        # Check if user exists with this username
        try:
            user = User.objects.get(username=username)
            
            # Generate password reset token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Directly redirect to reset password page instead of showing link
            return redirect('reset_password', uidb64=uid, token=token)
            
        except User.DoesNotExist:
            messages.error(request, 'Username not found. Please check your username and try again.')
            return render(request, 'forgot_password.html')
        except Exception as e:
            print(f"Forgot password error: {str(e)}")
            messages.error(request, 'An error occurred. Please try again.')
    
    return render(request, 'forgot_password.html')

def reset_password_view(request, uidb64, token):
    """Handle password reset with token"""
    from django.utils.http import urlsafe_base64_decode
    from django.utils.encoding import force_str
    
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            if not new_password or not confirm_password:
                messages.error(request, 'Please fill in all fields.')
                return render(request, 'reset_password.html', {'validlink': True})
            
            if new_password != confirm_password:
                messages.error(request, 'Passwords do not match.')
                return render(request, 'reset_password.html', {'validlink': True})
            
            if len(new_password) < 8:
                messages.error(request, 'Password must be at least 8 characters long.')
                return render(request, 'reset_password.html', {'validlink': True})
            
            # Set new password
            user.set_password(new_password)
            user.save()
            
            # Automatically log in the user after password reset
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, f'Password reset successful! Welcome back, {user.first_name or user.username}!')
            return redirect('home')
        
        return render(request, 'reset_password.html', {'validlink': True})
    else:
        return render(request, 'reset_password.html', {'validlink': False})