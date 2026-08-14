from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_display = (
        "recipient",
        "type",
        "message",
        "link",
        "is_read",
        "created_at",
    )
    list_filter = ("type", "is_read", "created_at")
    search_fields = ("message", "recipient__username", "recipient__email")
    readonly_fields = ("created_at",)
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
                    "is_read",
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
        ("Timestamps", {"fields": ("created_at",), "classes": ("collapse",)}),
    )
