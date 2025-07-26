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
        self._permission_check()

    def _permission_check(self):
        return
        ## raise PermissionDenied

    def get_label(self, pk: int) -> Label:
        self._permission_check()
        return Label.objects.get(pk=pk)

    def get_labels_for_task(self, task: Task) -> QuerySet[Label]:
        self._permission_check()
        return task.labels.all()  # type: ignore

    def get_labels_for_tasks(self, tasks: QuerySet[Task]) -> QuerySet[Label]:
        self._permission_check()
        return Label.objects.filter(tasks__in=tasks).distinct()
