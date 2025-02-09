from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from puzzles.models import UserProfile

class Command(BaseCommand):
    help = 'Skapar admin-användare om den inte redan finns'

    def handle(self, *args, **options):
        if not User.objects.filter(username='admin').exists():
            try:
                # Skapa admin-användare
                admin = User.objects.create_superuser(
                    username='admin',
                    email='admin@jvh.com',
                    password='Password'
                )
                
                # Skapa UserProfile för admin
                UserProfile.objects.create(
                    user=admin,
                    role='admin'
                )
                
                self.stdout.write(self.style.SUCCESS('Admin-användare har skapats framgångsrikt'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Kunde inte skapa admin-användare: {str(e)}'))
        else:
            self.stdout.write(self.style.SUCCESS('Admin-användare finns redan')) 