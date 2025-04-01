from django.db import models
from django.contrib.auth.models import User
from products.models import Product
import uuid


class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Корзина {self.user.username}"

    def total_items(self):
        return sum(item.quantity for item in self.cart_items.all())

    def subtotal(self):
        return sum(item.total_price() for item in self.cart_items.all())

    def shipping_cost(self):
        # Логика расчета стоимости доставки
        subtotal = self.subtotal()
        if subtotal > 5000:  # Бесплатная доставка при заказе от 5000 рублей
            return 0
        return 350  # Фиксированная стоимость доставки

    def total(self):
        return self.subtotal() + self.shipping_cost()


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='cart_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('cart', 'product')

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    def total_price(self):
        return self.product.price * self.quantity


class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'В ожидании'),
        ('processing', 'В обработке'),
        ('shipped', 'Отправлен'),
        ('delivered', 'Доставлен'),
        ('cancelled', 'Отменен'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    order_number = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.CharField(max_length=250)
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Заказ {self.order_number}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            while True:
                unique_number = str(uuid.uuid4().int)[:8]
                if not Order.objects.filter(order_number=unique_number).exists():
                    self.order_number = unique_number
                    break
        super().save(*args, **kwargs)

    def get_status_display(self):
        for status, display in self.STATUS_CHOICES:
            if status == self.status:
                return display
        return self.status


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    def total_price(self):
        return self.price * self.quantity


def cart_processor(request):
    """Вспомогательная функция для добавления информации о корзине в контекст"""
    if request.user.is_authenticated:
        try:
            cart = request.user.cart
            cart_items_count = cart.total_items()
        except (Cart.DoesNotExist, AttributeError):
            cart_items_count = 0
    else:
        cart_items_count = 0

    return {'cart_items_count': cart_items_count}