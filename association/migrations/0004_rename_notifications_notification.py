# Generated by Django 5.2.4 on 2025-07-12 10:11

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('association', '0003_notifications'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Notifications',
            new_name='Notification',
        ),
    ]
