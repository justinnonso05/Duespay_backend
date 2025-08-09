import os
from pathlib import Path

from django.apps import apps
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connection
from django.conf import settings

class Command(BaseCommand):
    help = (
        "Resets the database by deleting the DB file (SQLite) or dropping the "
        "public schema (PostgreSQL), removing all migration files, and then "
        "running migrate and creating a superuser."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-input",
            "--noinput",
            action="store_false",
            dest="interactive",
            help="Tells Django to NOT prompt the user for input of any kind.",
        )

    def handle(self, *args, **options):
        interactive = options["interactive"]
        db_vendor = connection.vendor

        if interactive:
            self.stdout.write(
                self.style.WARNING(
                    "\nThis command will completely WIPE the database and all migration files."
                )
            )
            self.stdout.write(
                self.style.WARNING(
                    f"You are about to reset the '{db_vendor}' database defined in your settings."
                )
            )
            confirm = input("Are you sure you want to continue? [y/N] ")
            if confirm.lower() != "y":
                self.stdout.write("Operation cancelled.")
                return

        self._reset_database(db_vendor)
        self._delete_migrations()

        self.stdout.write("\nCreating and applying new migrations...")
        call_command("makemigrations")
        call_command("migrate", database=connection.alias)

        self.stdout.write("\nCreating default superuser...")
        call_command("create_default_superuser")

        self.stdout.write(
            self.style.SUCCESS("\n✅ Database reset complete and superuser created.")
        )

    def _reset_database(self, db_vendor):
        self.stdout.write(f"\nResetting '{db_vendor}' database...")
        if db_vendor == "sqlite":
            db_path = Path(settings.DATABASES["default"]["NAME"])
            if db_path.exists():
                db_path.unlink()
                self.stdout.write(self.style.SUCCESS(f"  -> Deleted SQLite file: {db_path}"))
        elif db_vendor == "postgresql":
            with connection.cursor() as cursor:
                self.stdout.write("  -> Dropping and recreating the 'public' schema...")
                cursor.execute("DROP SCHEMA public CASCADE;")
                cursor.execute("CREATE SCHEMA public;")
                cursor.execute("GRANT ALL ON SCHEMA public TO public;")
            self.stdout.write(self.style.SUCCESS("  -> PostgreSQL public schema wiped."))

    def _delete_migrations(self):
        self.stdout.write("\nDeleting old migration files...")
        for app_config in apps.get_app_configs():
            if str(settings.BASE_DIR) in app_config.path:
                migrations_dir = Path(app_config.path) / "migrations"
                if migrations_dir.exists():
                    for file in migrations_dir.glob("*.py"):
                        if file.name != "__init__.py":
                            file.unlink()
                            self.stdout.write(f"  -> Deleted {file.relative_to(settings.BASE_DIR)}")
                    for file in migrations_dir.glob("*.pyc"):
                        file.unlink()
                        self.stdout.write(f"  -> Deleted {file.relative_to(settings.BASE_DIR)}")