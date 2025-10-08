
from django.urls import path
from core.views import (
    base_view, home_view, explore_view, search_view,
    add_recent_search, clear_recent_searches, remove_recent_search,
    spa_content_view
)
from core.auth_view import signin_view, signup_view, signout_view, profile_view, forgot_password_view, reset_password_view
from core.follow_views import (
    send_follow_request, unfollow_user, accept_follow_request, 
    decline_follow_request, follow_requests_view, followers_view, 
    following_view, suggested_users_view, get_follow_status
)
from core.story_views import (
    story_home_view, story_viewer, create_story_view, delete_story,
    story_viewers, get_stories_data, story_highlights_view, create_highlight
)
from core.post_views import (
    toggle_like, add_comment, toggle_save, post_detail, create_post, user_posts, delete_post
)
from core.message_views import (
    messages_home, chat_thread, send_message, start_chat, delete_thread,
    search_users, share_post, message_status, mark_thread_read, delete_message
)
from core.notification_views import (
    notifications_page, mark_notification_read, mark_all_seen, 
    mark_all_read, get_notifications_count
)

urlpatterns = [
    path('', view=base_view, name='base'),
    path('home/', view=home_view, name='home'),
    path('explore/', view=explore_view, name='explore'),
    path('search/', view=search_view, name='search'),
    path('signin/', view=signin_view, name='signin'),
    path('signup/', view=signup_view, name='signup'),
    path('signout/', view=signout_view, name='signout'),
    path('forgot-password/', view=forgot_password_view, name='forgot_password'),
    path('reset-password/<uidb64>/<token>/', view=reset_password_view, name='reset_password'),
    path('profile/', view=profile_view, name='profile'),
    path('profile/<str:username>/', view=profile_view, name='profile'),
    
    # Follow system URLs
    path('follow/send/<str:username>/', send_follow_request, name='send_follow_request'),
    path('follow/unfollow/<str:username>/', unfollow_user, name='unfollow_user'),
    path('follow/accept-request/<int:request_id>/', accept_follow_request, name='accept_follow_request'),
    path('follow/decline-request/<int:request_id>/', decline_follow_request, name='decline_follow_request'),
    path('follow/requests/', follow_requests_view, name='follow_requests'),
    path('follow/followers/<str:username>/', followers_view, name='followers'),
    path('follow/following/<str:username>/', following_view, name='following'),
    path('follow/suggested/', suggested_users_view, name='suggested_users'),
    path('api/follow-status/<str:username>/', get_follow_status, name='follow_status'),
    
    # Story URLs
    path('stories/', story_home_view, name='story_home'),
    path('stories/create/', create_story_view, name='create_story'),
    path('stories/delete/<int:story_id>/', delete_story, name='delete_story'),
    path('stories/viewers/<int:story_id>/', story_viewers, name='story_viewers'),
    path('stories/<str:username>/', story_viewer, name='story_viewer'),
    path('stories/<str:username>/<int:story_id>/', story_viewer, name='story_viewer_specific'),
    path('api/stories/<str:username>/', get_stories_data, name='get_stories_data'),
    path('highlights/<str:username>/', story_highlights_view, name='story_highlights'),
    path('highlights/create/', create_highlight, name='create_highlight'),
    
    # Post URLs
    path('posts/create/', create_post, name='create_post'),
    path('posts/<int:post_id>/', post_detail, name='post_detail'),
    path('posts/user/<str:username>/', user_posts, name='user_posts'),
    path('posts/<int:post_id>/like/', toggle_like, name='toggle_like'),
    path('posts/<int:post_id>/comment/', add_comment, name='add_comment'),
    path('posts/<int:post_id>/save/', toggle_save, name='toggle_save'),
    path('posts/<int:post_id>/delete/', delete_post, name='delete_post'),
    
    # Search URLs
    path('search/add-recent/<str:username>/', add_recent_search, name='add_recent_search'),
    path('search/clear-recent/', clear_recent_searches, name='clear_recent_searches'),
    path('search/remove-recent/<str:username>/', remove_recent_search, name='remove_recent_search'),
    
    # SPA URLs
    path('spa/content/<str:page>/', spa_content_view, name='spa_content'),
    
    # Message URLs
    path('messages/', messages_home, name='messages_home'),
    path('messages/thread/<int:thread_id>/', chat_thread, name='chat_thread'),
    path('messages/thread/<int:thread_id>/send/', send_message, name='send_message'),
    path('messages/start/<str:username>/', start_chat, name='start_chat'),
    path('messages/thread/<int:thread_id>/delete/', delete_thread, name='delete_thread'),
    path('messages/search-users/', search_users, name='search_users'),
    path('messages/share-post/<int:post_id>/', share_post, name='share_post'),
    path('messages/status/', message_status, name='message_status'),
    path('messages/thread/<int:thread_id>/mark-read/', mark_thread_read, name='mark_thread_read'),
    path('messages/delete/<int:message_id>/', delete_message, name='delete_message'),
    
    # Notification URLs
    path('notifications/', notifications_page, name='notifications'),
    path('api/notifications/<int:notification_id>/mark-read/', mark_notification_read, name='mark_notification_read'),
    path('api/notifications/mark-all-seen/', mark_all_seen, name='mark_all_seen'),
    path('api/notifications/mark-all-read/', mark_all_read, name='mark_all_read'),
    path('api/notifications/count/', get_notifications_count, name='notifications_count'),
]
