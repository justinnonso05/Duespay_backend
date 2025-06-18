import random
import string

def generate_unique_reference_id():
    digits4 = ''.join(random.choices(string.digits, k=4))
    digits3 = ''.join(random.choices(string.digits, k=3))
    letters2 = ''.join(random.choices(string.ascii_uppercase, k=2))
    return f"TX-{digits4}-{digits3}-{letters2}"