# Generated by Django 5.2.4 on 2025-07-07 12:21

import cloudinary.models
import django.db.models.deletion
import transactions.utils
import utils.utils
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('association', '0001_initial'),
        ('payers', '0001_initial'),
        ('payments', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount_paid', models.DecimalField(decimal_places=2, max_digits=10)),
                ('reference_id', models.CharField(default=transactions.utils.generate_unique_reference_id, editable=False, max_length=20, unique=True)),
                ('proof_of_payment', cloudinary.models.CloudinaryField(max_length=255, validators=[utils.utils.validate_file_type], verbose_name='file')),
                ('is_verified', models.BooleanField(default=False)),
                ('submitted_at', models.DateTimeField(auto_now_add=True)),
                ('association', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='association.association')),
                ('payer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='payers.payer')),
                ('payment_items', models.ManyToManyField(to='payments.paymentitem')),
            ],
        ),
        migrations.CreateModel(
            name='TransactionReceipt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('receipt_no', models.CharField(editable=False, max_length=10)),
                ('issued_at', models.DateTimeField(auto_now_add=True)),
                ('transaction', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='receipt', to='transactions.transaction')),
            ],
        ),
    ]
