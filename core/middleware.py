"""Skip CSRF for API requests (token auth; no session/cookie)."""


class DisableCSRFForAPIMiddleware:
    """Set _dont_enforce_csrf_checks for /api/ so token-authenticated requests are allowed."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/api/"):
            setattr(request, "_dont_enforce_csrf_checks", True)
        return self.get_response(request)
