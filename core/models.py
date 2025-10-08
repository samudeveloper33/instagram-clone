from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class UserProfile(models.Model):
    """Extended user profile for Instagram-like features"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(max_length=150, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    website = models.URLField(blank=True)
    is_private = models.BooleanField(default=False)  # Private account like Instagram
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s profile"

    @property
    def profile_picture_url(self):
        """Return profile picture URL or default if file doesn't exist"""
        if self.profile_picture:
            try:
                # Check if file exists
                if self.profile_picture.storage.exists(self.profile_picture.name):
                    return self.profile_picture.url
            except:
                pass
        # Return None for missing files - templates should handle default display
        return None

    @property
    def followers_count(self):
        return self.user.followers.count()

    @property
    def following_count(self):
        return self.user.following.count()

    @property
    def posts_count(self):
        return self.user.posts.count()

class FollowRequest(models.Model):
    """Follow request system like Instagram"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
    ]

    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_follow_requests')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_follow_requests')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('from_user', 'to_user')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.from_user.username} -> {self.to_user.username} ({self.status})"

    def accept(self):
        """Accept the follow request"""
        self.status = 'accepted'
        self.updated_at = timezone.now()
        self.save()
        
        # Create the actual follow relationship
        Follow.objects.get_or_create(
            follower=self.from_user,
            following=self.to_user
        )

    def decline(self):
        """Decline the follow request"""
        self.status = 'declined'
        self.updated_at = timezone.now()
        self.save()

class Follow(models.Model):
    """Actual follow relationship after request is accepted"""
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following')
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'following')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.follower.username} follows {self.following.username}"

    @classmethod
    def is_following(cls, user1, user2):
        """Check if user1 is following user2"""
        return cls.objects.filter(follower=user1, following=user2).exists()

    @classmethod
    def get_mutual_followers(cls, user1, user2):
        """Get mutual followers between two users"""
        user1_following = cls.objects.filter(follower=user1).values_list('following', flat=True)
        user2_followers = cls.objects.filter(following=user2).values_list('follower', flat=True)
        return User.objects.filter(id__in=user1_following).filter(id__in=user2_followers)

class Notification(models.Model):
    """Comprehensive Instagram-style notification system"""
    NOTIFICATION_TYPES = [
        # Engagement Notifications
        ('like', 'Like'),
        ('comment', 'Comment'),
        ('comment_reply', 'Comment Reply'),
        ('mention', 'Mention'),
        ('tag', 'Tag'),
        
        # Social Notifications
        ('follow', 'New Follower'),
        ('follow_request', 'Follow Request'),
        ('follow_accepted', 'Follow Request Accepted'),
        
        # Message Notifications
        ('message', 'Direct Message'),
        ('message_like', 'Message Like'),
        ('group_message', 'Group Message'),
        
        # Story Notifications
        ('story_reply', 'Story Reply'),
        ('story_mention', 'Story Mention'),
        ('story_like', 'Story Like'),
        
        # Video Notifications
        ('live_video', 'Live Video'),
        ('video_upload', 'Video Upload'),
        
        # System Notifications
        ('security_alert', 'Security Alert'),
        ('system_update', 'System Update'),
    ]

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_notifications', null=True, blank=True)
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    message = models.TextField()
    
    # Link to related content (optional)
    post_id = models.IntegerField(null=True, blank=True)
    comment_id = models.IntegerField(null=True, blank=True)
    story_id = models.IntegerField(null=True, blank=True)
    message_id = models.IntegerField(null=True, blank=True)
    
    # Notification state
    is_read = models.BooleanField(default=False)
    is_seen = models.BooleanField(default=False)  # Seen in notification list but not clicked
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['recipient', 'is_read']),
        ]

    def __str__(self):
        sender_name = self.sender.username if self.sender else "System"
        return f"{sender_name} -> {self.recipient.username}: {self.notification_type}"
    
    def get_notification_url(self):
        """Get the URL to navigate to when notification is clicked"""
        if self.notification_type in ['like', 'comment', 'tag', 'mention'] and self.post_id:
            return f'/post/{self.post_id}/'
        elif self.notification_type == 'comment_reply' and self.comment_id:
            return f'/post/{self.post_id}/#comment-{self.comment_id}'
        elif self.notification_type in ['follow', 'follow_request', 'follow_accepted'] and self.sender:
            return f'/profile/{self.sender.username}/'
        elif self.notification_type in ['message', 'message_like', 'group_message'] and self.message_id:
            return f'/messages/'
        elif self.notification_type in ['story_reply', 'story_like', 'story_mention'] and self.story_id:
            return f'/stories/{self.sender.username}/'
        return '/notifications/'

class RecentSearch(models.Model):
    """Store recent search history for users"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recent_searches')
    searched_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='searched_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'searched_user')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} searched {self.searched_user.username}"

    @classmethod
    def add_search(cls, user, searched_user):
        """Add or update a recent search"""
        if user != searched_user:  # Don't add self-searches
            search, created = cls.objects.get_or_create(
                user=user,
                searched_user=searched_user
            )
            if not created:
                # Update timestamp if already exists
                search.created_at = timezone.now()
                search.save()
            return search
        return None

    @classmethod
    def get_recent_searches(cls, user, limit=10):
        """Get recent searches for a user"""
        return cls.objects.filter(user=user).select_related('searched_user__profile')[:limit]

# Import story models
from .story_models import Story, StoryView, StoryHighlight

# Import post models
from .post_models import Post, PostMedia, Like, Comment, CommentLike, SavedPost

# Import message models
from .message_models import Thread, Message, MessageRead

# Signal to create UserProfile when User is created
from django.db.models.signals import post_save
from django.dispatch import receiver
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()