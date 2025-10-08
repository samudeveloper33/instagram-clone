from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import os

def story_upload_path(instance, filename):
    """Generate upload path for story media"""
    return f'stories/{instance.user.username}/{timezone.now().strftime("%Y/%m/%d")}/{filename}'

class Story(models.Model):
    """Instagram-style story model"""
    MEDIA_TYPES = [
        ('image', 'Image'),
        ('video', 'Video'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='stories')
    media_file = models.FileField(upload_to=story_upload_path)
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPES)
    caption = models.TextField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    # Story customization
    background_color = models.CharField(max_length=7, default='#000000')  # Hex color
    text_color = models.CharField(max_length=7, default='#ffffff')
    
    # Story interactions
    viewers = models.ManyToManyField(User, through='StoryView', related_name='viewed_stories')
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Stories'
    
    def __str__(self):
        return f"{self.user.username}'s story - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        
        # Detect media type based on file extension
        if self.media_file:
            file_extension = os.path.splitext(self.media_file.name)[1].lower()
            if file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                self.media_type = 'image'
            elif file_extension in ['.mp4', '.mov', '.avi', '.webm']:
                self.media_type = 'video'
        
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    @property
    def time_left(self):
        if self.is_expired:
            return timedelta(0)
        return self.expires_at - timezone.now()
    
    @property
    def views_count(self):
        return self.story_views.count()
    
    @classmethod
    def get_active_stories(cls):
        """Get all non-expired stories"""
        return cls.objects.filter(expires_at__gt=timezone.now())
    
    @classmethod
    def get_user_active_stories(cls, user):
        """Get active stories for a specific user"""
        return cls.get_active_stories().filter(user=user)

class StoryView(models.Model):
    """Track who viewed which story"""
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='story_views')
    viewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='story_views')
    viewed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('story', 'viewer')
        ordering = ['-viewed_at']
    
    def __str__(self):
        return f"{self.viewer.username} viewed {self.story.user.username}'s story"

class StoryHighlight(models.Model):
    """Story highlights that stay permanently on profile"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='highlights')
    title = models.CharField(max_length=50)
    cover_image = models.ImageField(upload_to='highlights/covers/', blank=True, null=True)
    stories = models.ManyToManyField(Story, related_name='highlights')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.user.username}'s highlight: {self.title}"
    
    @property
    def stories_count(self):
        return self.stories.count()
    
    def get_cover_image(self):
        """Get cover image or first story's image"""
        if self.cover_image:
            return self.cover_image.url
        first_story = self.stories.filter(media_type='image').first()
        if first_story:
            return first_story.media_file.url
        return None

# Add to core/models.py imports
from .story_models import Story, StoryView, StoryHighlight