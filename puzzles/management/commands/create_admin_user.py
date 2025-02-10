from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from puzzles.models import UserProfile

class Command(BaseCommand):
    help = 'Skapar eller uppdaterar admin-användaren'

    def handle(self, *args, **options):
        username = 'jvhadmin'
        email = 'admin@example.com'
        password = 'admin123'

        try:
            user = User.objects.get(username=username)
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS('Admin-lösenord uppdaterat'))
        except User.DoesNotExist:
            user = User.objects.create_superuser(username, email, password)
            UserProfile.objects.create(user=user, role='admin')
            self.stdout.write(self.style.SUCCESS('Admin-användare skapad')) 