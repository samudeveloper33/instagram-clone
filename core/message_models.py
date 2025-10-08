from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import os

def message_upload_path(instance, filename):
    """Generate upload path for message attachments"""
    return f'messages/{instance.thread.id}/{timezone.now().strftime("%Y/%m/%d")}/{filename}'

class Thread(models.Model):
    """Chat thread between users"""
    participants = models.ManyToManyField(User, related_name='chat_threads')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Thread settings
    is_group = models.BooleanField(default=False)
    group_name = models.CharField(max_length=100, blank=True)
    group_image = models.ImageField(upload_to='chat_groups/', blank=True, null=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        if self.is_group:
            return f"Group: {self.group_name or 'Unnamed Group'}"
        participants = list(self.participants.all()[:2])
        if len(participants) == 2:
            return f"{participants[0].username} & {participants[1].username}"
        return f"Thread {self.id}"
    
    @property
    def last_message(self):
        """Get the last message in this thread"""
        return self.messages.first()
    
    def get_other_participant(self, user):
        """Get the other participant in a 1-on-1 chat"""
        if self.is_group:
            return None
        participants = self.participants.exclude(id=user.id)
        return participants.first() if participants.exists() else None
    
    def get_unread_count(self, user):
        """Get unread message count for a specific user"""
        return self.messages.filter(
            is_read=False
        ).exclude(sender=user).count()
    
    def mark_as_read(self, user):
        """Mark all messages as read for a specific user"""
        self.messages.filter(
            is_read=False
        ).exclude(sender=user).update(is_read=True)
    
    @classmethod
    def get_or_create_thread(cls, user1, user2):
        """Get or create a thread between two users"""
        # Check if thread already exists
        existing_thread = cls.objects.filter(
            participants=user1,
            is_group=False
        ).filter(
            participants=user2
        ).first()
        
        if existing_thread:
            return existing_thread, False
        
        # Create new thread
        thread = cls.objects.create()
        thread.participants.add(user1, user2)
        return thread, True

class Message(models.Model):
    """Individual message in a thread"""
    MESSAGE_TYPES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('video', 'Video'),
        ('file', 'File'),
        ('post_share', 'Post Share'),
        ('profile_share', 'Profile Share'),
    ]
    
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default='text')
    
    # Message content
    text = models.TextField(blank=True)
    attachment = models.FileField(upload_to=message_upload_path, blank=True, null=True)
    
    # Shared content
    shared_post = models.ForeignKey('Post', on_delete=models.CASCADE, blank=True, null=True)
    shared_profile = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, related_name='shared_in_messages')
    
    # Message status
    is_read = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        if self.message_type == 'text':
            return f"{self.sender.username}: {self.text[:50]}..."
        return f"{self.sender.username}: {self.get_message_type_display()}"
    
    def save(self, *args, **kwargs):
        # Auto-detect message type based on attachment
        if self.attachment:
            file_extension = os.path.splitext(self.attachment.name)[1].lower()
            if file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                self.message_type = 'image'
            elif file_extension in ['.mp4', '.mov', '.avi', '.webm']:
                self.message_type = 'video'
            else:
                self.message_type = 'file'
        elif self.shared_post:
            self.message_type = 'post_share'
        elif self.shared_profile:
            self.message_type = 'profile_share'
        
        super().save(*args, **kwargs)
        
        # Update thread's updated_at timestamp
        self.thread.updated_at = timezone.now()
        self.thread.save(update_fields=['updated_at'])
    
    @property
    def is_image(self):
        return self.message_type == 'image'
    
    @property
    def is_video(self):
        return self.message_type == 'video'
    
    @property
    def is_file(self):
        return self.message_type == 'file'
    
    @property
    def attachment_name(self):
        if self.attachment:
            return os.path.basename(self.attachment.name)
        return None

class MessageRead(models.Model):
    """Track read status of messages per user"""
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='read_by')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    read_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('message', 'user')
    
    def __str__(self):
        return f"{self.user.username} read message {self.message.id}"
