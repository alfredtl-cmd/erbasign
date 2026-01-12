from django.contrib import admin
from .models import Customer, Product, Order


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("id", "full_name", "email", "phone", "created_at")
    search_fields = ("full_name", "email", "phone")
    list_filter = ("created_at",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "sku", "name", "price", "is_active", "created_at")
    search_fields = ("sku", "name")
    list_filter = ("is_active", "created_at")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "product", "quantity", "order_date")
    search_fields = (
        "customer__full_name",
        "customer__email",
        "product__sku",
        "product__name",
    )
    list_filter = ("order_date", "product")
