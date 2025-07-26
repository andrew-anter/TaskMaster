from __future__ import annotations

from typing import TYPE_CHECKING

from .models import Label
from .selectors import LabelSelector

if TYPE_CHECKING:
    from accounts.models import User
    from tasks.models import Task


class LabelService:
    def __init__(self, user: User):
        self._check_permissions(user=user)
        self.selector = LabelSelector(user=user)

    def _check_permissions(self, user: User):
        # NOTE: Added for later expansion
        return

    def create_label_for_task(self, name: str, color: str, task: Task) -> Label:
        """
        Creates or finds a label and associates it with a task.
        """
        label, _ = Label.objects.get_or_create(name=name, defaults={"color": color})
        task.labels.add(label)  # type: ignore
        return label

    def update_label(
        self, pk: int, name: str | None = None, color: str | None = None
    ) -> Label:
        """
        Updates a label's name or color.
        """
        label = self.selector.get_label(pk=pk)

        fields_to_update = []
        if name is not None:
            label.name = name
            fields_to_update.append("name")

        if color is not None:
            label.color = color
            fields_to_update.append("color")

        if fields_to_update:
            label.full_clean()
            label.save(update_fields=fields_to_update)

        return label

    def delete_label(self, pk: int):
        """
        Deletes a label.
        """
        label = self.selector.get_label(pk=pk)
        label.delete()
