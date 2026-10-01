from django.contrib import admin

from .models import Client, Customer

admin.site.register(Customer)
@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("email", "username", "email_verified", "is_active")
    readonly_fields = ("password", "last_login", "created_at", "updated_at")
    filter_horizontal = ("customers",)

    def has_add_permission(self, request):
        # Use registration or the API to hash passwords and create the first customer.
        return False
