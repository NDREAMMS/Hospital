from __future__ import annotations

from django.http import HttpRequest, HttpResponse


class DevCorsMiddleware:
    """
    Minimal CORS middleware for local dev (React on :5173 -> Django on :8000).

    Prefer django-cors-headers for production. This is intentionally limited to /api/.
    """

    allowed_origins: set[str] = {
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    }

    allowed_methods = "GET,POST,PATCH,PUT,DELETE,OPTIONS"
    allowed_headers = "Content-Type,Authorization"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.method == "OPTIONS" and request.path.startswith("/api/"):
            response = HttpResponse(status=204)
        else:
            response = self.get_response(request)

        origin = request.headers.get("Origin")
        if origin and origin in self.allowed_origins and request.path.startswith("/api/"):
            response["Access-Control-Allow-Origin"] = origin
            response["Vary"] = "Origin"
            response["Access-Control-Allow-Methods"] = self.allowed_methods
            response["Access-Control-Allow-Headers"] = self.allowed_headers
            response["Access-Control-Allow-Credentials"] = "true"

        return response
