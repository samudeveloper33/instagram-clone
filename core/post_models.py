from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import os

def post_upload_path(instance, filename):
    """Generate upload path for post media"""
    return f'posts/{instance.post.user.username}/{timezone.now().strftime("%Y/%m/%d")}/{filename}'

class Post(models.Model):
    """Instagram-style post model"""
    MEDIA_TYPES = [
        ('image', 'Image'),
        ('video', 'Video'),
        ('carousel', 'Carousel'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    caption = models.TextField(max_length=2200, blank=True)
    location = models.CharField(max_length=100, blank=True)
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPES, default='image')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Post settings
    comments_disabled = models.BooleanField(default=False)
    likes_hidden = models.BooleanField(default=False)
    
    # Post interactions
    likes = models.ManyToManyField(User, through='Like', related_name='liked_posts')
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username}'s post - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def likes_count(self):
        return self.post_likes.count()
    
    @property
    def comments_count(self):
        return self.comments.count()
    
    def is_liked_by(self, user):
        """Check if post is liked by specific user"""
        return self.post_likes.filter(user=user).exists()
    
    def is_saved_by(self, user):
        """Check if post is saved by specific user"""
        return self.saved_by.filter(user=user).exists()
    
    def get_first_media(self):
        """Get the first media file for the post"""
        return self.media_files.first()
    
    @classmethod
    def get_feed_posts(cls, user):
        """Get posts for user's feed (from followed users + own posts)"""
        following_users = User.objects.filter(followers__follower=user)
        from django.db import models as django_models
        return cls.objects.filter(
            django_models.Q(user__in=following_users) | django_models.Q(user=user)
        ).select_related('user', 'user__profile').prefetch_related(
            'media_files', 'post_likes', 'comments'
        )

class PostMedia(models.Model):
    """Media files for posts (supports multiple images/videos per post)"""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='media_files')
    media_file = models.FileField(upload_to=post_upload_path)
    media_type = models.CharField(max_length=10, choices=Post.MEDIA_TYPES)
    order = models.PositiveIntegerField(default=0)
    alt_text = models.CharField(max_length=100, blank=True)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.post.user.username}'s post media {self.order + 1}"
    
    def save(self, *args, **kwargs):
        # Auto-detect media type based on file extension
        if self.media_file:
            file_extension = os.path.splitext(self.media_file.name)[1].lower()
            if file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                self.media_type = 'image'
            elif file_extension in ['.mp4', '.mov', '.avi', '.webm']:
                self.media_type = 'video'
        
        super().save(*args, **kwargs)

class Like(models.Model):
    """Like system for posts"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_likes')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='post_likes')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'post')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} likes {self.post.user.username}'s post"

class Comment(models.Model):
    """Comment system for posts"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_comments')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    text = models.TextField(max_length=500)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Comment interactions
    likes = models.ManyToManyField(User, through='CommentLike', related_name='liked_comments')
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.user.username} commented on {self.post.user.username}'s post"
    
    @property
    def likes_count(self):
        return self.comment_likes.count()
    
    @property
    def replies_count(self):
        return self.replies.count()
    
    def is_liked_by(self, user):
        """Check if comment is liked by specific user"""
        return self.comment_likes.filter(user=user).exists()

class CommentLike(models.Model):
    """Like system for comments"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comment_user_likes')
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='comment_likes')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'comment')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} likes {self.comment.user.username}'s comment"

class SavedPost(models.Model):
    """Saved posts functionality"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_posts')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='saved_by')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'post')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} saved {self.post.user.username}'s post"
