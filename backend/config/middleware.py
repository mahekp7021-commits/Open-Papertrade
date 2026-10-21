class TrailingSlashMiddleware:
    """Ensure API request paths end with a trailing slash.

    Only normalize API URLs. Static files, Django admin assets, and other
    non-API paths must remain untouched or their file URLs become invalid.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/api/') and not request.path.endswith('/'):
            request.path += '/'
            request.path_info += '/'
        return self.get_response(request)
