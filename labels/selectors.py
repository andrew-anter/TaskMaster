from __future__ import annotations

from typing import TYPE_CHECKING

from .models import Label

if TYPE_CHECKING:
    from django.db.models.query import QuerySet

    from accounts.models import User
    from tasks.models import Task


class LabelSelector:
    def __init__(self, user: User):
        self.user = user
        self._check_permissions()

    def _check_permissions(self):
        # NOTE: Added for later expansion
        return

    def get_label(self, pk: int) -> Label:
        return Label.objects.get(pk=pk)

    def get_labels_for_task(self, task: Task) -> QuerySet[Label]:
        return task.labels.all()  # type: ignore

    def get_labels_for_tasks(self, tasks: QuerySet[Task]) -> QuerySet[Label]:
        return Label.objects.filter(tasks__in=tasks).distinct()
