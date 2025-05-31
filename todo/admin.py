from django.contrib import admin
from django.utils import timezone
from .models import TodoItem


@admin.register(TodoItem)
class TodoItemAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "status",
        "priority",
        "due_date",
        "scheduled_date",
        "created_at",
        "modified_at",  # Changed from updated_at
    )
    list_filter = (
        "status",
        "priority",
        "due_date",
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
                "fields": ("due_date", "scheduled_date"),
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
    def mark_as_todo(self, request, queryset):
        queryset.update(
            status=TodoItem.Status.TODO, modified_at=timezone.now()
        )  # Changed to modified_at

    mark_as_todo.short_description = "Mark selected as To Do"

    def mark_as_in_progress(self, request, queryset):
        queryset.update(
            status=TodoItem.Status.IN_PROGRESS, modified_at=timezone.now()
        )  # Changed to modified_at

    mark_as_in_progress.short_description = "Mark selected as In Progress"

    def mark_as_on_hold(self, request, queryset):
        queryset.update(
            status=TodoItem.Status.ON_HOLD, modified_at=timezone.now()
        )  # Changed to modified_at

    mark_as_on_hold.short_description = "Mark selected as On Hold"

    def mark_as_completed(self, request, queryset):
        queryset.update(
            status=TodoItem.Status.COMPLETED, modified_at=timezone.now()
        )  # Changed to modified_at

    mark_as_completed.short_description = "Mark selected as Completed"

    actions = [mark_as_todo, mark_as_in_progress, mark_as_on_hold, mark_as_completed]
