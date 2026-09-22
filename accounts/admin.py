from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class GatewayUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Gateway", {"fields": ("role",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Gateway", {"fields": ("email", "role")}),)
    list_display = ("username", "email", "role", "is_active", "is_staff")
