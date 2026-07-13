from django.contrib import admin
from django.utils import timezone
from unfold.admin import ModelAdmin

from .models import Task


@admin.register(Task)
class TaskAdmin(ModelAdmin):
    list_display = (
        "title",
        "status",
        "priority",
        "due_datetime",
        "scheduled_date",
        "created_at",
        "modified_at",  # Changed from updated_at
    )
    list_filter = (
        "status",
        "priority",
        "due_datetime",
        "scheduled_date",
        "created_at",
        "modified_at",  # Changed from updated_at
    )
    search_fields = ("title", "description")
    readonly_fields = ("created_at", "modified_at")  # Changed from updated_at

    fieldsets = (
        (None, {"fields": ("title", "description")}),
        ("Status & Priority", {"fields": ("status", "priority")}),
        (
            "Important Dates",
            {
                "fields": ("due_datetime", "scheduled_date"),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "modified_at"),  # Changed from updated_at
                "classes": ("collapse",),
            },
        ),
    )

    # Custom Admin Actions to update status
    @admin.display(description="Mark selected as To Do")
    def mark_as_todo(self, request, queryset):
        queryset.update(status=Task.Status.TODO, modified_at=timezone.now())

    @admin.display(description="Mark selected as In Progress")
    def mark_as_in_progress(self, request, queryset):
        queryset.update(status=Task.Status.IN_PROGRESS, modified_at=timezone.now())

    @admin.display(description="Mark selected as On Hold")
    def mark_as_on_hold(self, request, queryset):
        queryset.update(status=Task.Status.ON_HOLD, modified_at=timezone.now())

    @admin.display(description="Mark selected as Completed")
    def mark_as_completed(self, request, queryset):
        queryset.update(status=Task.Status.COMPLETED, modified_at=timezone.now())

    actions = [
        "mark_as_todo",
        "mark_as_in_progress",
        "mark_as_on_hold",
        "mark_as_completed",
    ]
