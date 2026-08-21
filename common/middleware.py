from urllib.parse import urlparse

_REFERER_SESSION_KEY = "_http_referrer"


class ReferrerMiddleware:
    """Store the path of the previous page in the session so views can redirect
    back to it after completing an action."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        referer = request.META.get("HTTP_REFERER", "")
        if referer:
            parsed = urlparse(referer)
            if parsed.path and parsed.path != request.path:
                request.session[_REFERER_SESSION_KEY] = parsed.path
        return self.get_response(request)


class HtmxVaryMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if "HX-Request" in request.headers:
            response.headers["Vary"] = "HX-Request"
        return response
