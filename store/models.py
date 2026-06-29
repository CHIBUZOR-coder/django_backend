from django.db import models
from django.contrib.auth.models import AbstractUser


from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


# 1. Create a custom manager to handle user and superuser generation
class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)

        # Ensure username isn't forced if it's null
        extra_fields.setdefault("username", None)

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


# 2. Update your User model to use the new manager
class User(AbstractUser):
    name = models.CharField(max_length=300, null=False, blank=False)
    username = models.CharField(max_length=300, null=True, blank=False, unique=False)
    phone = models.CharField(max_length=12, null=False, blank=False)
    email = models.EmailField(unique=True)
    image = models.ImageField(upload_to="userImage/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_verified = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    # ◄ CRITICAL: Assign the custom manager here so Django uses our logic!
    objects = UserManager()

    def __str__(self):
        return f"{self.email} {self.name}"


class Category(models.Model):
    name = models.CharField(max_length=300, null=False, blank=False)


class Sizes(models.TextChoices):
    S = "S", "Small"
    M = "M", "Medium"
    L = "L", "Large"
    XL = "XL", "Extra Large"


class Product(models.Model):
    name = models.CharField(max_length=300, null=False, blank=False)
    price = models.DecimalField(
        max_digits=10, decimal_places=2, null=False, blank=False
    )
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    defaultSize = models.CharField(
        max_length=20, choices=Sizes.choices, default=Sizes.L
    )
    image = models.ImageField(upload_to="product_image/", blank=False, null=False)
    new_hit = models.BooleanField(default=False)
    quantity = models.PositiveIntegerField(default=1, blank=False, null=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)


# store/models.py


class Product_cart(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1, blank=True, null=True)
    size = models.CharField(
        max_length=2, choices=Sizes.choices, blank=False, null=False
    )

    # ADD THIS LINE HERE ◄
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # If no size was selected, dynamically grab the defaultSize from the linked product
        if not self.size:
            self.size = self.product.defaultSize
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product", "cart", "size"],
                name="unique_product_cart_size",
            )
        ]


class Order(models.Model):
    class StatusChoices(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        SHIPPED = "SHIPPED", "Shipped"
        CANCELLED = "CANCELLED", "Cancelled"
        DELIVERED = "DELIVERED", "Delivered"

    status = models.CharField(
        max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    # FIXED: Added 'on_delete=models.PROTECT' so historical orders aren't wiped out
    # if a user account is deleted from the system.
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="orders")

    @property
    def user_email(self):
        """Dynamically grabs the customer's email from their linked profile account"""
        return self.user.email if self.user else "No User Linked"


class OrderedProduct(models.Model):
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    order = models.ForeignKey(
        Order, on_delete=models.PROTECT, related_name="order_items"
    )

    quantity = models.PositiveIntegerField(default=1)
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product", "order"],
                name="unique_product_order",
            )
        ]


class Receipt(models.Model):
    class StatusChoices(models.TextChoices):
        SUCCESSFUL = "successful", "Successful"
        FAILED = "failed", "Failed"
        PENDING = "pending", "Pending"

    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="receipts")
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="receipts")

    # Flutterwave data
    flw_transaction_id = models.CharField(
        max_length=100, unique=True, null=True, blank=True
    )
    tx_ref = models.CharField(max_length=100, unique=True, null=True, blank=True)
    amount_paid = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    currency = models.CharField(max_length=10, null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Receipt {self.flw_transaction_id} for Order {self.order.id}"
