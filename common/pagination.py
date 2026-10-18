from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.paginator import Page, Paginator

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from django.http import HttpRequest


def paginate(
    request: HttpRequest, queryset: QuerySet, *, page_size: int
) -> tuple[Page, str | None, str | None]:
    """
    Paginate ``queryset`` using the ``page`` GET param.

    Returns ``(page_obj, prev_page_url, next_page_url)`` where the URLs keep the
    current query string (filters, sort) and are ``None`` at either end.
    """
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(request.GET.get("page"))

    def page_url(page_number: int) -> str | None:
        if page_number < 1 or page_number > paginator.num_pages:
            return None
        params = request.GET.copy()
        params["page"] = str(page_number)
        return f"?{params.urlencode()}"

    return page_obj, page_url(page_obj.number - 1), page_url(page_obj.number + 1)
