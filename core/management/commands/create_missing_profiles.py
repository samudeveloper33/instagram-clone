from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import UserProfile

class Command(BaseCommand):
    help = 'Create missing UserProfile objects for existing users'

    def handle(self, *args, **options):
        users_without_profiles = []
        
        for user in User.objects.all():
            try:
                # Try to access the profile
                profile = user.profile
            except UserProfile.DoesNotExist:
                # Create profile if it doesn't exist
                UserProfile.objects.create(user=user)
                users_without_profiles.append(user.username)
        
        if users_without_profiles:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Created profiles for {len(users_without_profiles)} users: {", ".join(users_without_profiles)}'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('All users already have profiles.')
            )
