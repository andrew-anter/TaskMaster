from __future__ import annotations

import json

from django.http import HttpResponse


def hx_location_response(path: str, *, target: str = "#main-content") -> HttpResponse:
    """
    Return an empty HTTP response that instructs HTMX to navigate to ``path``,
    swapping ``target`` into the page.

    Used after mutating actions so the UI reflects the new server state without
    a full page reload.
    """
    response = HttpResponse()
    response["HX-Location"] = json.dumps({"path": path, "target": target})
    return response
