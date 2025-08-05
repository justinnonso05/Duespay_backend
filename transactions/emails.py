from django.core.mail import EmailMultiAlternatives, EmailMessage
from django.conf import settings
from django.template.loader import render_to_string
from datetime import datetime

def send_admin_new_transaction_email(admin, association, transaction):
    subject = "New Transaction Alert"
    context = {
        "admin": admin,
        "association": association,
        "transaction": transaction,
    }
    html_content = render_to_string("transactions/new_transaction.html", context)
    text_content = (
        f"Dear {admin.first_name},\n\n"
        f"A new transaction has been made in your association ({association.association_name}).\n"
        f"Reference ID: {transaction.reference_id}\n"
        f"Payer: {transaction.payer.first_name} {transaction.payer.last_name}\n"
        f"Amount Paid: {transaction.amount_paid}\n"
        f"Date: {getattr(transaction, 'submitted_at', '')}\n\n"
        "Please log in to your dashboard for more details."
    )
    email = EmailMultiAlternatives(
        subject,
        text_content,
        settings.DEFAULT_FROM_EMAIL,
        [admin.email],
    )
    email.attach_alternative(html_content, "text/html")
    email.send(fail_silently=False)

def send_receipt_email(receipt):
    """Email: Send receipt with PDF attachment to payer"""
    transaction = receipt.transaction
    association = transaction.association
    current_year_short = str(datetime.now().year)[-2:]
    receipt_no = f"{association.association_short_name.upper()}/{receipt.receipt_no}/{current_year_short}"

    subject = f"Payment Receipt #{receipt_no} - {association.association_name}"

    context = {
        'payer_name': f"{transaction.payer.first_name} {transaction.payer.last_name}",
        'receipt_no': receipt_no,
        'session_title': transaction.session.title if transaction.session else 'N/A',
        'transaction_ref': transaction.reference_id,
        'transaction_date': transaction.submitted_at.strftime('%Y-%m-%d %H:%M:%S'),
        'association_name': association.association_name,
        'association_logo': association.logo.url if association.logo else '',
        'association_no': association.admin.phone_number,
        'amount_paid': transaction.amount_paid,
        'transaction_receipt_url': f"{settings.FRONTEND_URL}/transactions/receipt/{receipt.receipt_id}/",
    }
    
    message = render_to_string('transactions/receipt_template.html', context)
    
    email = EmailMessage(
        subject=subject,
        body=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[transaction.payer.email],
    )
    
    
    email.content_subtype = 'html'
    email.send(fail_silently=False)
    
