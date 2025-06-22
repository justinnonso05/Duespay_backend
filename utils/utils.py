from django.core.exceptions import ValidationError

def validate_file_type(file):
    valid_mime_types = ['image/jpeg', 'image/png', 'application/pdf']
    if file.content_type not in valid_mime_types:
        raise ValidationError('Only JPG, PNG, or PDF files are allowed.')
