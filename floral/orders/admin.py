from django.contrib import admin
from .models import Order, OrderItem, Cart, CartItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['product']
    extra = 0

class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'user', 'first_name', 'last_name', 'email', 'phone',
                    'status', 'total', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['order_number', 'first_name', 'last_name', 'email', 'phone']
    inlines = [OrderItemInline]

class CartItemInline(admin.TabularInline):
    model = CartItem
    raw_id_fields = ['product']
    extra = 0

class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at', 'total_items']
    inlines = [CartItemInline]

admin.site.register(Order, OrderAdmin)
admin.site.register(Cart, CartAdmin)