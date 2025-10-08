from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import UserProfile
import os

class Command(BaseCommand):
    help = 'Fix broken profile picture references'

    def handle(self, *args, **options):
        self.stdout.write('Fixing broken profile picture references...')
        
        fixed_count = 0
        
        # Get all user profiles with profile pictures
        profiles_with_pics = UserProfile.objects.exclude(profile_picture='').exclude(profile_picture__isnull=True)
        
        for profile in profiles_with_pics:
            try:
                # Check if the file actually exists
                if not profile.profile_picture.storage.exists(profile.profile_picture.name):
                    self.stdout.write(f'Removing broken reference for {profile.user.username}: {profile.profile_picture.name}')
                    profile.profile_picture = None
                    profile.save()
                    fixed_count += 1
            except Exception as e:
                self.stdout.write(f'Error checking {profile.user.username}: {str(e)}')
                profile.profile_picture = None
                profile.save()
                fixed_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully fixed {fixed_count} broken profile picture references')
        )
