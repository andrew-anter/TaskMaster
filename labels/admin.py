from django.contrib import admin

from .models import Label


@admin.register(Label)
class LabelAdmin(admin.ModelAdmin):
    list_display = ("name", "color", "owner")
    list_filter = ("owner",)
    search_fields = ("name",)
    readonly_fields = ("color",)
