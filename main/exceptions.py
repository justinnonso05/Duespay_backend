from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated
from rest_framework.response import Response
from rest_framework.views import exception_handler
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        if response.status_code == 400:  # Bad Request (validation errors)
            custom_response_data = {
                "success": False,
                "message": "Please check your input and try again",
                "errors": {},
            }

            if isinstance(response.data, dict):
                for field, errors in response.data.items():
                    if isinstance(errors, list):
                        custom_response_data["errors"][field] = errors[0]
                    else:
                        custom_response_data["errors"][field] = str(errors)

                if len(custom_response_data["errors"]) == 1:
                    field_name = list(custom_response_data["errors"].keys())[0]
                    error_message = custom_response_data["errors"][field_name]
                    custom_response_data["message"] = error_message

            return Response(custom_response_data, status=response.status_code)

        elif response.status_code == 401:
            # Handle JWT errors
            if isinstance(exc, (InvalidToken, TokenError)):
                return Response(
                    {
                        "success": False,
                        "message": "Invalid or expired token",
                        # "errors": response.data,
                    },
                    status=response.status_code,
                )

            if isinstance(exc, AuthenticationFailed):
                return Response(
                    {
                        "success": False,
                        "message": str(exc) or "Invalid credentials",
                        "errors": {},
                    },
                    status=response.status_code,
                )

            if isinstance(exc, NotAuthenticated):
                return Response(
                    {
                        "success": False,
                        "message": "Authentication required",
                        "errors": {},
                    },
                    status=response.status_code,
                )

            return Response(
                {"success": False, "message": "Unauthorized", "errors": {}},
                status=response.status_code,
            )

        elif response.status_code == 403:
            return Response(
                {
                    "success": False,
                    "message": "You do not have permission to perform this action",
                    "errors": {},
                },
                status=response.status_code,
            )

        elif response.status_code == 404:
            return Response(
                {"success": False, "message": "Resource not found", "errors": {}},
                status=response.status_code,
            )

    return response
