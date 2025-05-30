from django.contrib import admin
from .models import TodoItem
from django.utils import timezone


@admin.register(TodoItem)
class TodoItemAdmin(admin.ModelAdmin):
    list_display = ("title", "completed", "created_at", "modified_at")
    list_filter = ("completed", "created_at", "modified_at")
    search_fields = ("title", "description")
    readonly_fields = ("created_at", "modified_at")  # These are auto-managed
    fieldsets = (
        (None, {"fields": ("title", "description", "completed")}),
        (
            "Date Information",
            {
                "fields": ("created_at", "modified_at"),
                "classes": ("collapse",),  # Make this section collapsible
            },
        ),
    )

    def mark_completed(self, request, queryset):
        queryset.update(completed=True, modified_at=timezone.now())

    mark_completed.short_description = "Mark selected items as completed"

    def mark_incomplete(self, request, queryset):
        queryset.update(completed=False, modified_at=timezone.now())

    mark_incomplete.short_description = "Mark selected items as incomplete"

    actions = [mark_completed, mark_incomplete]
