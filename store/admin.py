from django.contrib import admin

# Register your models here.
from .models import Customer, Product, Order, OrderItem, ShippingAddress

class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'date_orderd', 'payment_method', 'payment_status', 'complete')
    list_filter = ('payment_status', 'payment_method', 'complete')
    search_fields = ('id', 'customer__user__username', 'transaction_id')
    # Remove payment_status from list_editable to prevent bulk editing
    # list_editable = ('payment_status',)  # Do not include this line

admin.site.register(Customer)
admin.site.register(Product)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem)
admin.site.register(ShippingAddress)