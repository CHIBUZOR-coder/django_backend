from rest_framework import serializers
from typing import TYPE_CHECKING, Dict, Any
from decimal import Decimal
from django.contrib.auth import authenticate
from rest_framework.exceptions import AuthenticationFailed
from .utils import send_verification_email
import cloudinary.uploader

from rest_framework import serializers

# from django.contrib.auth import get_user_model
# User = get_user_model()


from .models import (
    # Category as CategoryType,
    Product as ProductType,
    Cart as CartType,
    Product_cart as ProductCartType,
    User as UserType,
    Order as OrderTypes,
    OrderedProduct as OrderproductTypes,
)

# =====================================================================
# USER SERIALIZERS
# =====================================================================


class GetUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserType
        fields = ["id", "name", "phone", "email", "image"]


class CreateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserType
        fields = [
            "id",
            "name",
            "username",
            "phone",
            "email",
            "image",
            "password",
            "created_at",
            "updated_at",
        ]

    read_only_fields = ["id", "created_at", "updated_at"]
    extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data: Dict[str, Any]) -> UserType:
        password = validated_data.pop("password", None)

        # 1. Force the account state locks directly onto the initialization payload
        validated_data["is_verified"] = False
        validated_data["is_active"] = (
            True  # Ensure active so your login can read it later
        )

        # 2. Create the user instance with your remaining custom fields
        user = UserType.objects.create(**validated_data)

        # 3. Use Django's built-in tool to safely hash and set the password
        if password:
            user.set_password(password)
            user.save()

        # 4. ◄ NEW TRIGGER: Fire the frontend verification link immediately!
        send_verification_email(user)

        return user


import cloudinary.uploader  # ← add this at the top of serializers.py


class updateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserType
        fields = [
            "name",
            "username",
            "phone",
            "email",
            "image",
            "password",
        ]
        extra_kwargs = {"password": {"write_only": True, "required": False}}

    def update(self, instance: "UserType", validated_data: Dict[str, Any]) -> UserType:
        new_image = validated_data.get("image")

        # ← ADD THESE PRINTS
        print("NEW IMAGE:", new_image)
        print("INSTANCE IMAGE:", instance.image)
        print("INSTANCE IMAGE NAME:", instance.image.name if instance.image else None)

        if new_image and instance.image:
            old_public_id = instance.image.name
            print("DELETING OLD IMAGE:", old_public_id)
            try:
                result = cloudinary.uploader.destroy(old_public_id)
                print("CLOUDINARY DELETE RESULT:", result)
            except Exception as e:
                print("DELETE FAILED:", e)

        return super().update(instance, validated_data)


class LoginSerializer(serializers.Serializer):
    # 1. Define the input fields required for logging in
    username = serializers.CharField(write_only=True)
    password = serializers.CharField(
        write_only=True,
        style={
            "input_type": "password"
        },  # Helps browsable API render a password dot-field
    )

    def validate(self, attrs):
        username = attrs.get("username")
        password = attrs.get("password")

        user = authenticate(
            username=username, password=password  # because USERNAME_FIELD = "email"
        )

        if not user:
            raise AuthenticationFailed("Invalid email or password.")

        if not user.is_active:
            raise AuthenticationFailed("This user account has been deactivated.")
        # Resend verification email if user hasn't verified yet
        if not user.is_verified:
            send_verification_email(user)
            raise AuthenticationFailed(
                "Your email is not verified. "
                "A new verification link has been sent to your email."
            )

        attrs["user"] = user
        return attrs


# =====================================================================
# PRODUCT SERIALIZERS
# =====================================================================


class GetProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductType
        fields = [
            "id",
            "name",
            "price",
            "category",
            "defaultSize",
            "image",
            "new_hit",
            "quantity",
        ]


class AdminGetProduct(serializers.ModelSerializer):
    class Meta:
        model = ProductType
        fields = [
            "id",
            "name",
            "price",
            "category",
            "defaultSize",
            "image",
            "new_hit",
            "quantity",
            "created_at",
            "updated_at",
        ]


class CreatProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductType
        fields = [
            "name",
            "price",
            "category",
            "defaultSize",
            "image",
            "new_hit",
            "quantity",
        ]

    def validate_price(self, value: Decimal) -> Decimal:
        # Step: Enforce zero-negative threshold pricing business logic
        if value <= 0:
            raise serializers.ValidationError(
                "Price must be a positive value greater than zero."
            )
        return value

    def create(self, validated_data: Dict[str, Any]) -> ProductType:

        return ProductType.objects.create(**validated_data)


class upddateProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductType
        fields = [
            "name",
            "price",
            "category",
            "defaultSize",
            "image",
            "new_hit",
            "quantity",
        ]

    def update(
        self, instance: "ProductType", validated_data: Dict[str, Any]
    ) -> "ProductType":
        # Delete old image from Cloudinary if a new one is being uploaded
        new_image = validated_data.get("image")
        if new_image and instance.image:
            old_public_id = instance.image.name
            try:
                cloudinary.uploader.destroy(old_public_id)
            except Exception:
                pass  # Don't crash the update if deletion fails

        return super().update(instance, validated_data)


# =====================================================================
# PRODUCT-CART SERIALIZERS (CART ITEMS)
# =====================================================================


# 1. CART ITEM READ (VIEW DETAILS INSIDE THE CART)
class ProductCartDetailsSerializer(serializers.ModelSerializer):
    """Exposes deeply nested item attributes when reading active cart details."""

    # Step: Read product details to view product names/images inside a basket
    product = GetProductSerializer(read_only=True)

    class Meta:
        model = ProductCartType
        fields = ["id", "product", "quantity", "size"]


class AddToCartSerializer(serializers.ModelSerializer):
    """Processes validation logic whenever a user adds a product to a cart."""

    quantity = serializers.IntegerField(default=1)

    class Meta:
        model = ProductCartType
        fields = ["cart", "product", "quantity", "size"]
        validators = []  # ← disables model-level validators
        extra_kwargs = {
            "size": {"required": False, "allow_null": True, "allow_blank": True},
        }

    def get_validators(self):
        # ← THIS is what actually stops DRF's auto-generated UniqueTogetherValidator
        # Without this, DRF ignores validators=[] and still runs its own unique check
        return []

    def validate(self, attrs):
        product = attrs["product"]
        quantity = attrs["quantity"]
        cart = attrs["cart"]

        size = attrs.get("size") or product.defaultSize

        existing_item = ProductCartType.objects.filter(
            cart=cart, product=product, size=size
        ).first()

        already_in_cart = existing_item.quantity if existing_item else 0
        total_requested = already_in_cart + quantity

        if total_requested > product.quantity:
            raise serializers.ValidationError(
                f"Cannot add {quantity} more items. You already have {already_in_cart} in your cart, "
                f"and total stock is only {product.quantity}."
            )

        return attrs

    def create(self, validated_data):
        product = validated_data["product"]
        cart = validated_data["cart"]
        quantity = validated_data["quantity"]

        size = validated_data.get("size") or product.defaultSize

        cart_item, created = ProductCartType.objects.get_or_create(
            cart=cart,
            product=product,
            size=size,
            defaults={"quantity": quantity},
        )

        if not created:
            # Item already exists — just increment the quantity
            cart_item.quantity += quantity
            cart_item.save()

        return cart_item


# =====================================================================
# CART SERIALIZERS
# =====================================================================


# 1. CART VIEW (READ WITH ITEMS LIST)
class CartSerializer(serializers.ModelSerializer):
    """Main overview point linking active consumers to their active items list."""

    # Step: Access child rows via reverse relationship lookup ('product_cart_set')
    items = ProductCartDetailsSerializer(
        source="product_cart_set", many=True, read_only=True
    )
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = CartType
        fields = ["id", "user", "user_email", "items"]


# 2. INITIALIZE CART (CREATE)
class CartCreateSerializer(serializers.ModelSerializer):
    """Used behind the scenes to automate creation hooks, like user registration signals."""

    class Meta:
        model = CartType
        fields = ["user"]

    def create(self, validated_data: Dict[str, Any]) -> "CartType":
        # Step: Standard record creation for new carts
        return CartType.objects.create(**validated_data)


# =====================================================================
# ORDER / OrderedProduct SERIALIZERS
# =====================================================================
class GetOrderedProduct(serializers.ModelSerializer):
    product = GetProductSerializer(read_only=True)

    class Meta:
        model = OrderproductTypes
        fields = ["id", "product", "order", "quantity", "price_at_purchase"]


class GetOrderSerializer(serializers.ModelSerializer):
    items = GetOrderedProduct(source="order_items", many=True, read_only=True)  # ← fix
    user_email = serializers.EmailField(
        source="user.email", read_only=True
    )  # ← add this

    class Meta:
        model = OrderTypes
        fields = [
            "id",
            "status",
            "total_price",
            "user",
            "items",
            "user_email",
            "created_at",
        ]


class AddOrderSerializer(serializers.ModelSerializer):
    items = GetOrderedProduct(source="order_items", many=True, read_only=True)  # ← fix

    class Meta:
        model = OrderTypes
        fields = [
            "id",
            "status",
            "total_price",
            "created_at",
            "updated_at",
            "user",
            "items",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "status",
            "total_price",
            "items",
        ]

    def create(self, validated_data: Dict[str, Any]) -> OrderTypes:
        user = validated_data["user"]

        # 1. Grab all items with product data in ONE database query
        cart_items = ProductCartType.objects.filter(cart__user=user).select_related(
            "product"
        )  # ← fetches product data in the same query

        # Safety check: Prevent an empty checkout
        if not cart_items.exists():
            raise serializers.ValidationError(
                "Your cart is empty. Cannot place an order."
            )

        # 2. Calculate total price
        total_price = sum(item.quantity * item.product.price for item in cart_items)

        # 3. Save the parent Order record
        order = OrderTypes.objects.create(
            user=user,
            status=OrderTypes.StatusChoices.PENDING,
            total_price=total_price,
        )

        # 4. Build order items list AND track stock updates in ONE loop
        order_products_to_create = []
        products_to_update = []

        for item in cart_items:
            # Prepare order line item
            order_products_to_create.append(
                OrderproductTypes(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    price_at_purchase=item.product.price,
                )
            )

            # Prepare stock reduction
            item.product.quantity -= item.quantity
            products_to_update.append(item.product)

        # 5. Save order items in one batch call
        OrderproductTypes.objects.bulk_create(order_products_to_create)

        # 6. Save stock updates in one batch call
        ProductType.objects.bulk_update(products_to_update, ["quantity"])

        # 7. Clear the cart
        cart_items.delete()

        return order
