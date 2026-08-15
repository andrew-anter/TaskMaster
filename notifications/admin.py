from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Notification


class ReadStateListFilter(admin.SimpleListFilter):
    """Filter notifications by read state (driven by ``read_at``)."""

    title = _("read state")
    parameter_name = "read_state"

    def lookups(self, request, model_admin):
        return [
            ("read", _("Read")),
            ("unread", _("Unread")),
        ]

    def queryset(self, request, queryset):
        if self.value() == "read":
            return queryset.filter(read_at__isnull=False)
        if self.value() == "unread":
            return queryset.filter(read_at__isnull=True)
        return queryset


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "recipient",
        "type",
        "message",
        "link",
        "read_at",
        "created_at",
    )
    list_filter = ("type", ReadStateListFilter, "created_at")
    search_fields = ("message", "recipient__username", "recipient__email")
    readonly_fields = ("created_at", "read_at")
    date_hierarchy = "created_at"

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "recipient",
                    "actor",
                    "type",
                    "message",
                    "link",
                )
            },
        ),
        (
            "Target",
            {
                "fields": ("target_content_type", "target_object_id"),
                "classes": ("collapse",),
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "read_at"), "classes": ("collapse",)},
        ),
    )
