from .models import Payer


class PayerService:
    @staticmethod
    def check_or_update_payer(
        association,
        session,
        matric_number,
        email,
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
                    phone_number=phone_number,
                    first_name=first_name,
                    last_name=last_name,
                    faculty=faculty,
                    department=department,
                )
                return payer, None
            except Exception as e:
                return None, f"Error creating payer: {str(e)}"
        except Exception as e:
            return None, f"Error checking payer: {str(e)}"
