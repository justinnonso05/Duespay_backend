from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        User = get_user_model()
        if not User.objects.filter(email="justondev05@gmail.com").exists():
            User.objects.create_superuser(
                email="justondev05@gmail.com",
                password="nonso2005"
            )
            self.stdout.write(">>>> Superuser created.")
        else:
            self.stdout.write("!!!! Superuser already exists.")
