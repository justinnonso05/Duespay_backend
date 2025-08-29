from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        User = get_user_model()
        if not User.objects.filter(email="justondev05@gmail.com").exists():
            User.objects.create_superuser(
                username="justondev05", email="justondev05@gmail.com", password="nonso2005"
            )
            self.stdout.write(">>>> Superuser created.")
        else:
            self.stdout.write("!!!! Superuser already exists.")
