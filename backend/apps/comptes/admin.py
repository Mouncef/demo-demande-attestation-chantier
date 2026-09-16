"""Administration des utilisateurs (superuser uniquement)."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["email"]
    list_display = ["email", "first_name", "last_name", "role", "organisation", "is_active"]
    list_filter = ["role", "is_active", "is_staff"]
    search_fields = ["email", "first_name", "last_name", "organisation"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Identité",
            {"fields": ("first_name", "last_name", "organisation", "code_distributeur", "adresse", "telephone")},
        ),
        ("Rôle et droits", {"fields": ("role", "is_active", "is_staff", "is_superuser", "groups")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "role", "password1", "password2")}),)
