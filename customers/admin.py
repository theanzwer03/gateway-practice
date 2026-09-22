from django.contrib import admin

from .models import Client, Customer

admin.site.register(Customer)
admin.site.register(Client)
