from django.contrib import admin

from .models import Invoice, Payment, Transaction

admin.site.register(Invoice)
admin.site.register(Payment)
admin.site.register(Transaction)
