from django.core.exceptions import ValidationError

def validate_file_type(file):
    """Validate file type (image or PDF only) and size (max 5MB)"""
    # Skip validation for CloudinaryResource objects (already uploaded)
    if hasattr(file, 'public_id'):  # Cloudinary objects have public_id
        return
    
    # Only validate for new file uploads
    if hasattr(file, 'content_type'):
        allowed_types = [
            'image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/jpg',
            'application/pdf'
        ]
        if file.content_type not in allowed_types:
            raise ValidationError(
                'Unsupported file type. Please upload JPEG, PNG, GIF, WebP images or PDF files only.'
            )
    
    # Check file size (limit to 5MB)
    if hasattr(file, 'size') and file.size > 5 * 1024 * 1024:
        raise ValidationError('File size cannot exceed 5MB.')

def validate_image_file(file):
    """Specific validation for image files"""
    # Skip validation for CloudinaryResource objects
    if hasattr(file, 'public_id'):
        return
        
    if hasattr(file, 'content_type'):
        if not file.content_type.startswith('image/'):
            raise ValidationError('Please upload a valid image file.')
    
    validate_file_type(file)
