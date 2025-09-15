from .models import Payer
from django.db import IntegrityError


class PayerService:
    @staticmethod
    def check_or_update_payer(
        association,
        session,
        matric_number,
        email,
        level,
        phone_number,
        first_name,
        last_name,
        faculty="",
        department="",
    ):
        try:
            # Look for existing payer in the current session
            payer = Payer.objects.get(
                association=association, session=session, matric_number=matric_number
            )
            # Update existing payer details
            payer.email = email
            payer.phone_number = phone_number
            payer.first_name = first_name
            payer.last_name = last_name
            payer.level = level
            payer.faculty = faculty
            payer.department = department
            payer.save()
            return payer, None
        except Payer.DoesNotExist:
            # Check for email uniqueness within this session
            if Payer.objects.filter(
                association=association, session=session, email=email
            ).exists():
                return (
                    None,
                    f"A payer with email '{email}' already exists in this session.",
                )

            # Check for phone number uniqueness within this session
            if Payer.objects.filter(
                association=association, session=session, phone_number=phone_number
            ).exists():
                return (
                    None,
                    f"A payer with phone number '{phone_number}' already exists in this session.",
                )

            # Check for matric number uniqueness within this session (redundant check but good practice)
            if Payer.objects.filter(
                association=association, session=session, matric_number=matric_number
            ).exists():
                return (
                    None,
                    f"A payer with matric number '{matric_number}' already exists in this session.",
                )

            try:
                # Create new payer in the current session
                payer = Payer.objects.create(
                    association=association,
                    session=session,
                    matric_number=matric_number,
                    email=email,
                    level=level,
                    phone_number=phone_number,
                    first_name=first_name,
                    last_name=last_name,
                    faculty=faculty,
                    department=department,
                )
                return payer, None
            except IntegrityError as e:
                # Check which field caused the error
                msg = str(e)
                if "email" in msg:
                    return (
                        None,
                        f"A payer with email '{email}' already exists in this session.",
                    )
                if "phone_number" in msg:
                    return (
                        None,
                        f"A payer with phone number '{phone_number}' already exists in this session.",
                    )
                if "matric_number" in msg:
                    return (
                        None,
                        f"A payer with matric number '{matric_number}' already exists in this session.",
                    )
                return None, "A unique constraint failed while creating payer."
        except IntegrityError as e:
            # Catch any IntegrityError that bubbles up
            msg = str(e)
            if "email" in msg:
                return (
                    None,
                    f"A payer with email '{email}' already exists in this session.",
                )
            if "phone_number" in msg:
                return (
                    None,
                    f"A payer with phone number '{phone_number}' already exists in this session.",
                )
            if "matric_number" in msg:
                return (
                    None,
                    f"A payer with matric number '{matric_number}' already exists in this session.",
                )
            return None, "A unique constraint failed while creating payer."
        except Exception as e:
            return None, f"Unexpected error: {str(e)}"
