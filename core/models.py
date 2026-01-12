from django.db import models


class Customer(models.Model):
    full_name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.full_name} ({self.email})"


class Product(models.Model):
    sku = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=160)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.sku} - {self.name}"


class Order(models.Model):
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name="orders"
    )
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="orders"
    )
    quantity = models.PositiveIntegerField()
    order_date = models.DateField()
    note = models.CharField(max_length=255, blank=True)

    def __str__(self) -> str:
        return f"Order #{self.id} - {self.customer.full_name} - {self.product.sku}"
