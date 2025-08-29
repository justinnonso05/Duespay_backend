from rest_framework.renderers import JSONRenderer


class CustomJSONRenderer(JSONRenderer):
    """
    Custom renderer to format all API responses consistently.
    """

    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get("response", None)

        # If it's already our custom error/success format, return as is
        if isinstance(data, dict) and "success" in data and "message" in data:
            return super().render(data, accepted_media_type, renderer_context)

        # Determine success/failure
        success = True if response and response.status_code < 400 else False

        # Allow views to override message
        message = ""
        if isinstance(data, dict) and "message" in data:
            message = data.pop("message") or ""
        elif success:
            message = "Request successful"

        # Wrap response
        response_data = {
            "success": success,
            "message": message,
            "data": data if data is not None else {},
        }

        return super().render(response_data, accepted_media_type, renderer_context)
