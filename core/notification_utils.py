"""
Helper functions for creating Instagram-style notifications
"""
from .models import Notification

class NotificationManager:
    """Centralized notification creation"""
    
    @staticmethod
    def create_like_notification(post, liker):
        """Create notification when someone likes a post"""
        if post.user == liker:
            return None  # Don't notify if user likes their own post
        
        # Check if notification already exists (prevent duplicates)
        existing = Notification.objects.filter(
            recipient=post.user,
            sender=liker,
            notification_type='like',
            post_id=post.id
        ).first()
        
        if existing:
            # Update timestamp
            existing.created_at = timezone.now()
            existing.is_read = False
            existing.save()
            return existing
        
        return Notification.objects.create(
            recipient=post.user,
            sender=liker,
            notification_type='like',
            message=f"{liker.username} liked your post.",
            post_id=post.id
        )
    
    @staticmethod
    def create_comment_notification(comment, post):
        """Create notification when someone comments on a post"""
        if post.user == comment.user:
            return None  # Don't notify if user comments on their own post
        
        return Notification.objects.create(
            recipient=post.user,
            sender=comment.user,
            notification_type='comment',
            message=f"{comment.user.username} commented: {comment.text[:50]}",
            post_id=post.id,
            comment_id=comment.id
        )
    
    @staticmethod
    def create_comment_reply_notification(reply, parent_comment):
        """Create notification when someone replies to a comment"""
        if parent_comment.user == reply.user:
            return None
        
        return Notification.objects.create(
            recipient=parent_comment.user,
            sender=reply.user,
            notification_type='comment_reply',
            message=f"{reply.user.username} replied: {reply.text[:50]}",
            post_id=reply.post.id,
            comment_id=reply.id
        )
    
    @staticmethod
    def create_follow_notification(follower, following):
        """Create notification when someone follows you"""
        if follower == following:
            return None
        
        return Notification.objects.create(
            recipient=following,
            sender=follower,
            notification_type='follow',
            message=f"{follower.username} started following you."
        )
    
    @staticmethod
    def create_follow_request_notification(requester, requested):
        """Create notification for follow request (private accounts)"""
        return Notification.objects.create(
            recipient=requested,
            sender=requester,
            notification_type='follow_request',
            message=f"{requester.username} requested to follow you."
        )
    
    @staticmethod
    def create_follow_accepted_notification(accepter, requester):
        """Create notification when follow request is accepted"""
        return Notification.objects.create(
            recipient=requester,
            sender=accepter,
            notification_type='follow_accepted',
            message=f"{accepter.username} accepted your follow request."
        )
    
    @staticmethod
    def create_mention_notification(post, mentioned_user, mentioner):
        """Create notification when someone mentions you"""
        if mentioned_user == mentioner:
            return None
        
        return Notification.objects.create(
            recipient=mentioned_user,
            sender=mentioner,
            notification_type='mention',
            message=f"{mentioner.username} mentioned you in a post.",
            post_id=post.id
        )
    
    @staticmethod
    def create_tag_notification(post, tagged_user):
        """Create notification when someone tags you in a post"""
        if tagged_user == post.user:
            return None
        
        return Notification.objects.create(
            recipient=tagged_user,
            sender=post.user,
            notification_type='tag',
            message=f"{post.user.username} tagged you in a post.",
            post_id=post.id
        )
    
    @staticmethod
    def create_message_notification(message, recipient):
        """Create notification for new direct message"""
        return Notification.objects.create(
            recipient=recipient,
            sender=message.sender,
            notification_type='message',
            message=f"{message.sender.username} sent you a message.",
            message_id=message.id
        )
    
    @staticmethod
    def create_story_reply_notification(story, replier, reply_text):
        """Create notification when someone replies to your story"""
        if story.user == replier:
            return None
        
        return Notification.objects.create(
            recipient=story.user,
            sender=replier,
            notification_type='story_reply',
            message=f"{replier.username} replied to your story: {reply_text[:50]}",
            story_id=story.id
        )
    
    @staticmethod
    def create_story_mention_notification(story, mentioned_user):
        """Create notification when someone mentions you in their story"""
        if mentioned_user == story.user:
            return None
        
        return Notification.objects.create(
            recipient=mentioned_user,
            sender=story.user,
            notification_type='story_mention',
            message=f"{story.user.username} mentioned you in their story.",
            story_id=story.id
        )
    
    @staticmethod
    def create_live_video_notification(live_session, follower):
        """Create notification when someone you follow goes live"""
        return Notification.objects.create(
            recipient=follower,
            sender=live_session.user,
            notification_type='live_video',
            message=f"{live_session.user.username} started a live video. Watch now!"
        )
    
    @staticmethod
    def create_system_notification(user, message, notification_type='system_update'):
        """Create system notification"""
        return Notification.objects.create(
            recipient=user,
            sender=None,  # System notifications don't have a sender
            notification_type=notification_type,
            message=message
        )
    
    @staticmethod
    def delete_like_notification(post, unliker):
        """Delete notification when someone unlikes a post"""
        Notification.objects.filter(
            recipient=post.user,
            sender=unliker,
            notification_type='like',
            post_id=post.id
        ).delete()
    
    @staticmethod
    def delete_follow_notification(follower, unfollowed):
        """Delete notification when someone unfollows"""
        Notification.objects.filter(
            recipient=unfollowed,
            sender=follower,
            notification_type='follow'
        ).delete()
    
    @staticmethod
    def mark_as_read(notification_id):
        """Mark notification as read"""
        try:
            notification = Notification.objects.get(id=notification_id)
            notification.is_read = True
            notification.save()
            return True
        except Notification.DoesNotExist:
            return False
    
    @staticmethod
    def mark_all_as_seen(user):
        """Mark all notifications as seen (but not read)"""
        Notification.objects.filter(
            recipient=user,
            is_seen=False
        ).update(is_seen=True)
    
    @staticmethod
    def get_unread_count(user):
        """Get count of unread notifications"""
        return Notification.objects.filter(
            recipient=user,
            is_read=False
        ).count()
    
    @staticmethod
    def get_unseen_count(user):
        """Get count of unseen notifications (red dot indicator)"""
        return Notification.objects.filter(
            recipient=user,
            is_seen=False
        ).count()


# Import at bottom to avoid circular imports
from django.utils import timezone
