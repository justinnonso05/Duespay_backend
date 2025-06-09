from django.db.models import Q
from .models import Payer

class VerificationService:
    def __init__(self, proof_file):
        self.proof_file = proof_file
    
    def verify_proof(self):
        """
        Veifies the transaction proof of payment.
        """
        if self.proof_file:
            return True
        return False
    

class PayerService:
    @staticmethod
    def check_or_update_payer(association, matric_number, email, phone_number, first_name, last_name, faculty=None, department=None):
        payer = Payer.objects.filter(association=association, matric_number=matric_number).first()
        if payer:
            email_conflict = Payer.objects.filter(
                association=association, email=email
            ).exclude(matric_number=matric_number).exists()
            phone_conflict = Payer.objects.filter(
                association=association, phone_number=phone_number
            ).exclude(matric_number=matric_number).exists()

            if email_conflict and phone_conflict:
                return None, "Email and phone number already belong to another user with different matric number."
            elif email_conflict:
                return None, "Email already belongs to another user with different matric number."
            elif phone_conflict:
                return None, "Phone number already belongs to another user with different matric number."

            updated = False
            for field, value in [
                ('first_name', first_name),
                ('last_name', last_name),
                ('email', email),
                ('phone_number', phone_number),
                ('faculty', faculty),
                ('department', department)
            ]:
                if value and getattr(payer, field) != value:
                    setattr(payer, field, value)
                    updated = True
            if updated:
                payer.save()
            return payer, None

        email_conflict = Payer.objects.filter(association=association, email=email).exists()
        phone_conflict = Payer.objects.filter(association=association, phone_number=phone_number).exists()
        if email_conflict and phone_conflict:
            return None, "Email and phone number already belong to another user with different matric number."
        elif email_conflict:
            return None, "Email already belongs to another user with different matric number."
        elif phone_conflict:
            return None, "Phone number already belongs to another user with different matric number."

        payer = Payer.objects.create(
            association=association,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone_number=phone_number,
            matric_number=matric_number,
            faculty=faculty,
            department=department,
        )
        return payer, None