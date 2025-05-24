from django.contrib import admin
from .models import PaySpace, ReceiverBankAccount, PaymentItem, Transaction, TransactionReceipt, Payer

admin.site.register((PaySpace, ReceiverBankAccount, PaymentItem, Transaction, TransactionReceipt, Payer))