from __future__ import annotations

from typing import TYPE_CHECKING

from tasks.models import Task
from tasks.selectors import get_tasks_by_label

from .forms import LABEL_COLORS, LabelForm

if TYPE_CHECKING:
    from accounts.models import User

    from .models import Label

LABEL_TASK_PREVIEW_LIMIT = 5


def build_label_detail_context(*, user: User, label: Label) -> dict:
    """
    Context for the read-only label detail body.

    Shared by the label detail page and the HTMX region re-render, so the
    task preview and its counters always agree.
    """
    label_tasks = get_tasks_by_label(user=user, label_id=label.pk)
    return {
        "label": label,
        "form": LabelForm(instance=label, user=user),
        "editing": False,
        "label_colors": LABEL_COLORS,
        "label_task_count": label_tasks.count(),
        "label_tasks": label_tasks[:LABEL_TASK_PREVIEW_LIMIT],
        # Matches ``tasks.views.ORIGIN_LABEL_DETAIL`` for the row forms.
        "origin": f"label_detail:{label.pk}",
        "Status": Task.Status,
        "Priority": Task.Priority,
        "page_title": label.name,
    }
