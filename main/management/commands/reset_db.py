import os
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Fully reset the database (SQLite or PostgreSQL), delete all migration files, and rebuild schema."

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-input",
            "--noinput",
            action="store_false",
            dest="interactive",
            help="Do not prompt for confirmation.",
        )

    def handle(self, *args, **options):
        interactive = options["interactive"]
        db_vendor = connection.vendor
        env = os.getenv("DJANGO_ENV", "dev").lower()

        if interactive:
            self.stdout.write(
                self.style.WARNING(
                    f"\nThis will WIPE the '{db_vendor}' database for environment: {env.upper()}"
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
        call_command("migrate", "--run-syncdb", database=connection.alias)

        self.stdout.write("\nCreating default superuser...")
        try:
            call_command("create_default_superuser")
        except Exception:
            self.stdout.write("⚠ Skipped creating superuser (command not found).")

        self.stdout.write(
            self.style.SUCCESS("\n✅ Database reset complete and superuser created.")
        )

    def _reset_database(self, db_vendor):
        self.stdout.write(f"\nResetting '{db_vendor}' database...")
        if db_vendor == "sqlite":
            db_path = Path(settings.DATABASES["default"]["NAME"])
            if db_path.exists():
                db_path.unlink()
                self.stdout.write(
                    self.style.SUCCESS(f"  -> Deleted SQLite file: {db_path}")
                )
        elif db_vendor == "postgresql":
            with connection.cursor() as cursor:
                self.stdout.write("  -> Dropping and recreating the 'public' schema...")
                cursor.execute("DROP SCHEMA public CASCADE;")
                cursor.execute("CREATE SCHEMA public;")
                cursor.execute("GRANT ALL ON SCHEMA public TO public;")
            self.stdout.write(
                self.style.SUCCESS("  -> PostgreSQL public schema wiped.")
            )

    def _delete_migrations(self):
        self.stdout.write("\nDeleting old migration files...")
        for app_config in apps.get_app_configs():
            if str(settings.BASE_DIR) in app_config.path:
                migrations_dir = Path(app_config.path) / "migrations"
                if migrations_dir.exists():
                    for file in migrations_dir.glob("*.py"):
                        if file.name != "__init__.py":
                            file.unlink()
                            self.stdout.write(
                                f"  -> Deleted {file.relative_to(settings.BASE_DIR)}"
                            )
                    for file in migrations_dir.glob("*.pyc"):
                        file.unlink()
                        self.stdout.write(
                            f"  -> Deleted {file.relative_to(settings.BASE_DIR)}"
                        )
