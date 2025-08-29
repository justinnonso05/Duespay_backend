# from django.core.mail import EmailMultiAlternatives
# from django.conf import settings
# from django.template.loader import render_to_string

# def send_payer_transaction_verified_email(payer, association, transaction):
#     print("Sending email to payer:", payer.email)
#     print(settings.EMAIL_HOST_USER)
#     print(settings.EMAIL_HOST_PASSWORD)
#     subject = "Your Payment Has Been Verified"
#     context = {
#         "payer": payer,
#         "transaction": transaction,
#         "association": association,
#     }
#     html_content = render_to_string("payers/verified_transaction.html", context)
#     text_content = (
#         f"Dear {payer.first_name},\n\n"
#         f"Your payment (Reference ID: {transaction.reference_id}) has been verified.\n"
#         f"Thank you for your payment to {association.association_name}.\n\n"
#         "Best regards,\nDuesPay Team"
#     )
#     email = EmailMultiAlternatives(
#         subject,
#         text_content,
#         settings.DEFAULT_FROM_EMAIL,
#         [payer.email],
#     )
#     email.attach_alternative(html_content, "text/html")
#     email.send(fail_silently=False)
