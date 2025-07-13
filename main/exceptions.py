from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

def custom_exception_handler(exc, context):
    """
    Custom exception handler that formats validation errors consistently
    """
    response = exception_handler(exc, context)
    
    if response is not None:
        if response.status_code == 400:  # Bad Request (validation errors)
            custom_response_data = {
                'success': False,
                'message': 'Please check your input and try again',
                'errors': {}
            }
            
            # Handle field-specific errors
            if isinstance(response.data, dict):
                for field, errors in response.data.items():
                    if isinstance(errors, list):
                        custom_response_data['errors'][field] = errors[0]  # Take first error
                    else:
                        custom_response_data['errors'][field] = str(errors)
                
                # If only one error, put it in message
                if len(custom_response_data['errors']) == 1:
                    field_name = list(custom_response_data['errors'].keys())[0]
                    custom_response_data['message'] = custom_response_data['errors'][field_name]
            
            return Response(custom_response_data, status=response.status_code)
    
    return response