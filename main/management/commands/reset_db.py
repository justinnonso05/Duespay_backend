from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connection
from django.conf import settings

class Command(BaseCommand):
    help = 'Reset database completely'

    def add_arguments(self, parser):
        parser.add_argument(
            '--noinput',
            action='store_true',
            help='Do not prompt for input',
        )

    def handle(self, *args, **options):
        self.stdout.write('Resetting database...')
        
        with connection.cursor() as cursor:
            # Get all table names
            cursor.execute("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public'
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            if tables:
                # Disable foreign key checks and drop all tables
                for table in tables:
                    cursor.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')
                
                self.stdout.write(f'Dropped {len(tables)} tables')
            
            # Reset sequences
            cursor.execute("""
                SELECT sequence_name FROM information_schema.sequences 
                WHERE sequence_schema = 'public'
            """)
            sequences = [row[0] for row in cursor.fetchall()]
            
            for sequence in sequences:
                cursor.execute(f'DROP SEQUENCE IF EXISTS "{sequence}" CASCADE')
                
            self.stdout.write(f'Dropped {len(sequences)} sequences')

        self.stdout.write(self.style.SUCCESS('Database reset complete'))