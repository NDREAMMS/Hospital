from django.contrib import admin

from .models import Staff


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ("id", "first_name", "last_name", "email", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("first_name", "last_name", "email")
