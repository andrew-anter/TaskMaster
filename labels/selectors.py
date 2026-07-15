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
        return Label.objects.get(pk=pk, owner=self.user)

    def get_labels(self, ids: set[int] | None = None) -> QuerySet[Label]:
        queryset = Label.objects.filter(owner=self.user)
        if ids is not None:
            queryset = queryset.filter(pk__in=ids)
        return queryset

    def get_labels_for_task(self, task_id: int) -> QuerySet[Label]:
        return Label.objects.filter(tasks__pk=task_id, owner=self.user)
