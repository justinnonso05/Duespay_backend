from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string

def send_admin_new_transaction_email(admin, association, transaction):
    subject = "New Transaction Alert"
    context = {
        "admin": admin,
        "association": association,
        "transaction": transaction,
    }
    html_content = render_to_string("main/new_transaction.html", context)
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

def send_payer_transaction_verified_email(payer, transaction):
    print("Sending email to payer:", payer.email)
    print(settings.EMAIL_HOST_USER)
    print(settings.EMAIL_HOST_PASSWORD)
    subject = "Your Payment Has Been Verified"
    context = {
        "payer": payer,
        "transaction": transaction,
    }
    html_content = render_to_string("main/verified_transaction.html", context)
    text_content = (
        f"Dear {payer.first_name},\n\n"
        f"Your payment (Reference ID: {transaction.reference_id}) has been verified.\n"
        f"Thank you for your payment to {transaction.association.association_name}.\n\n"
        "Best regards,\nDuesPay Team"
    )
    email = EmailMultiAlternatives(
        subject,
        text_content,
        settings.DEFAULT_FROM_EMAIL,
        [payer.email],
    )
    email.attach_alternative(html_content, "text/html")
    email.send(fail_silently=False)