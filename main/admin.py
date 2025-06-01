from django.contrib import admin
from .models import Association, ReceiverBankAccount, PaymentItem, Transaction, TransactionReceipt, Payer

admin.site.register((Association, ReceiverBankAccount, PaymentItem, Transaction, TransactionReceipt, Payer))