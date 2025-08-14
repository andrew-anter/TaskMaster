from __future__ import annotations

from typing import TYPE_CHECKING

from .models import Label

if TYPE_CHECKING:
    from django.db.models.query import QuerySet

    from accounts.models import User


class LabelSelector:
    def __init__(self, user: User):
        self.user = user
        self._check_permissions()

    def _check_permissions(self):
        # NOTE: Added for later expansion
        return

    def get_label(self, pk: int) -> Label:
        return Label.objects.get(pk=pk)

    def get_labels(self, ids: set[int]) -> QuerySet[Label]:
        return Label.objects.filter(pk__in=ids)

    def get_labels_for_task(self, task_id: int) -> QuerySet[Label]:
        return Label.objects.filter(tasks__pk=task_id)

    def get_labels_for_tasks(self, tasks_ids: set[int]) -> QuerySet[Label]:
        return Label.objects.filter(tasks__pk__in=tasks_ids)
