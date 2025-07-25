# Generated by Django 5.2.4 on 2025-07-20 19:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0002_alter_adminuser_options_alter_adminuser_email'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='adminuser',
            options={'verbose_name': 'user', 'verbose_name_plural': 'users'},
        ),
        migrations.AlterField(
            model_name='adminuser',
            name='email',
            field=models.EmailField(max_length=254, unique=True),
        ),
    ]
