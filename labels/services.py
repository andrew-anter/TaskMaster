from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import IntegrityError, transaction

from .exceptions import DuplicateLabelError
from .models import Label
from .selectors import LabelSelector

if TYPE_CHECKING:
    from accounts.models import User


class LabelService:
    def __init__(self, user: User):
        self.user = user
        self._check_permissions(user=user)
        self.selector = LabelSelector(user=user)

    def _check_permissions(self, user: User):
        # NOTE: Added for later expansion
        return

    def _check_name_is_free(self, name: str, *, exclude_pk: int | None = None) -> None:
        """Raise ``DuplicateLabelError`` when the user already owns ``name``."""
        duplicates = Label.objects.filter(owner=self.user, name__iexact=name)
        if exclude_pk is not None:
            duplicates = duplicates.exclude(pk=exclude_pk)
        if duplicates.exists():
            raise DuplicateLabelError()

    @transaction.atomic
    def create_label(self, name: str, color: str) -> Label:
        """
        Creates a new label for the user.

        Raises:
            DuplicateLabelError: If the user already owns a label with this name.
            django.core.exceptions.ValidationError: If the label is invalid
                (e.g. the name is too long).
        """
        self._check_name_is_free(name)
        label = Label(name=name, color=color, owner=self.user)
        label.full_clean()
        try:
            with transaction.atomic():
                label.save()
        except IntegrityError as exc:
            # The DB constraint is the case-sensitive race backstop behind the
            # case-insensitive pre-check above.
            raise DuplicateLabelError() from exc
        return label

    @transaction.atomic
    def update_label(
        self, pk: int, name: str | None = None, color: str | None = None
    ) -> Label:
        """
        Updates a label's name or color.

        Raises:
            DuplicateLabelError: If the new name is already used by another of
                the user's labels.
        """
        label = self.selector.get_label(pk=pk)

        fields_to_update = set()
        if name is not None:
            self._check_name_is_free(name, exclude_pk=pk)
            label.name = name
            fields_to_update.add("name")

        if color is not None:
            label.color = color
            fields_to_update.add("color")

        if fields_to_update:
            label.full_clean()
            try:
                with transaction.atomic():
                    label.save(update_fields=list(fields_to_update))
            except IntegrityError as exc:
                # The DB constraint is the race backstop behind the pre-check.
                raise DuplicateLabelError() from exc

        return label

    def delete_label(self, pk: int):
        """
        Deletes a label.
        """
        label = self.selector.get_label(pk=pk)
        label.delete()
